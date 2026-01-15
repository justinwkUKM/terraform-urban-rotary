# ==============================================================================
# Variables
# ==============================================================================

# The Google Cloud Project ID where resources will be deployed.
# This is typically provided via a terraform.tfvars file or command line.
variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

# The Google Cloud Region for resource placement.
# Default is 'us-central1' but can be overridden.
variable "region" {
  description = "The Google Cloud Region"
  type        = string
  default     = "us-central1"
}

# The secret key to be stored in Secret Manager.
# Marked as sensitive to prevent it from showing in logs.
variable "application_secrets" {
  description = "Map of secrets to be stored in Secret Manager and injected as env vars"
  type        = map(string)
  # sensitive = true  <-- Helper: Keys must be known for for_each. Values will be hidden by Secret Manager.
}

# ==============================================================================
# Provider Configuration
# ==============================================================================

# Configure the Google Cloud provider with the specified project and region.
provider "google" {
  project = var.project_id
  region  = var.region
}

# ==============================================================================
# API Enablement
# ==============================================================================

# Enable Artifact Registry API to store Docker images.
# disable_on_destroy is false to prevent accidental API disabling which can affect other services.
resource "google_project_service" "artifactregistry" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

# Enable Cloud Run API to deploy containerized applications.
resource "google_project_service" "cloudrun" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

# Enable Cloud Build API to build Docker images in the cloud.
resource "google_project_service" "cloudbuild" {
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}

# Enable Secret Manager API
resource "google_project_service" "secretmanager" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

# Enable Firestore API
resource "google_project_service" "firestore" {
  service            = "firestore.googleapis.com"
  disable_on_destroy = false
}

# ==============================================================================
# Firestore Database
# ==============================================================================

resource "google_firestore_database" "database" {
  project     = var.project_id
  name        = "(default)" # The default database must be named "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.firestore]
}

# ==============================================================================
# Artifact Registry
# ==============================================================================

# Create a Docker repository in Artifact Registry.
# This will store the container images built from the application code.
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "my-repo"
  description   = "Docker repository for FastAPI app"
  format        = "DOCKER"

  # Ensure the API is enabled before creating the repository.
  depends_on = [google_project_service.artifactregistry]
}

# ==============================================================================
# Secret Manager (Dynamic)
# ==============================================================================

# Create a secret in Secret Manager for each key in the application_secrets map
resource "google_secret_manager_secret" "secrets" {
  for_each = var.application_secrets
  
  # Replace underscores with hyphens for secret IDs (GCP naming convention preference)
  # But keeping original key is simpler for mapping. Google allows underscores.
  secret_id = each.key

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

# Add the version (value) for each secret
resource "google_secret_manager_secret_version" "secrets_version" {
  for_each = var.application_secrets

  secret      = google_secret_manager_secret.secrets[each.key].id
  secret_data = each.value
}


# ==============================================================================
# Docker Image Build Logic (Automated)
# ==============================================================================

locals {
  # Select all Python source files to track changes.
  source_files = fileset("${path.module}/../backend", "*.py")
  
  # Include Dockerfile and requirements.txt in the change tracking.
  # This ensures a rebuild is triggered if dependencies or the build definition changes.
  all_files = setunion(local.source_files, ["Dockerfile", "requirements.txt"])
  
  # Calculate a single SHA1 hash of all tracked files.
  # logical: If the content of any file changes, this hash changes, triggering the null_resource.
  dir_sha1 = sha1(join("", [for f in local.all_files : filesha1("${path.module}/../backend/${f}")]))
  
  # Define the image tag using the content hash. 
  # This ensures unique, immutable tags for every code change.
  image_tag = "fastapi-app:${local.dir_sha1}"
  
  # The full URI for the image in Artifact Registry.
  image_uri = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}/fastapi-app:${local.dir_sha1}"
}

# Resource to trigger the build process.
# This uses a 'local-exec' provisioner to run gcloud commands on the machine running Terraform.
resource "null_resource" "build_image" {
  # The trigger ensures this resource is recreated (and thus the command re-run) 
  # whenever the calculated content hash changes.
  triggers = {
    dir_sha1 = local.dir_sha1
  }

  provisioner "local-exec" {
    # Provide the exact command to build the image using Cloud Build.
    # We pass the calculated content-based tag.
    # Points to ../backend which contains Dockerfile and source code
    command = "gcloud builds submit --tag ${local.image_uri} ../backend"
  }

  # Dependencies ensuring the Repo and Build API exist before we try to build.
  depends_on = [
    google_artifact_registry_repository.repo,
    google_project_service.cloudbuild
  ]
}

# ==============================================================================
# Cloud Run Service Deployment
# ==============================================================================

# Deploy the container to Cloud Run.
resource "google_cloud_run_v2_service" "default" {
  name     = "fastapi-service"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"
  
  # IMPORTANT: Set to false to allow 'terraform destroy' to delete the service.
  # Default is often true to prevent accidental deletion of production services.
  deletion_protection = false

  template {
    containers {
      # Reference the image URI computed in locals. 
      # Because this URI changes when code changes, Terraform will update the service revision.
      image = local.image_uri
      ports {
        container_port = 8080
      }
      
      # Dynamically inject each secret as an environment variable
      dynamic "env" {
        for_each = var.application_secrets
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.secrets[env.key].secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  # Ensure the image is built and the Cloud Run API is enabled before deployment.
  depends_on = [
    null_resource.build_image,
    google_project_service.cloudrun,
    google_secret_manager_secret_version.secrets_version
  ]
}

# ==============================================================================
# IAM & Permissions
# ==============================================================================

# Allow Cloud Run Service Account to access the Secret
# By default, Cloud Run uses the Compute Engine default service account.
data "google_project" "project" {
}

# Grant permission to access ALL created secrets
resource "google_secret_manager_secret_iam_member" "secret_access" {
  for_each = var.application_secrets

  secret_id = google_secret_manager_secret.secrets[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

# Grant permission to write log entries to Firestore
resource "google_project_iam_member" "firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user" # Permissions to read/write Firestore
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

# ==============================================================================
# Public Access Control
# ==============================================================================

# Allow unauthenticated (public) access to the service.
# Without this, only authenticated Google Cloud identities can invoke the URL.
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.default.location
  service  = google_cloud_run_v2_service.default.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ==============================================================================
# Outputs
# ==============================================================================

# Output the final URL of the deployed Cloud Run service.
output "service_url" {
  description = "The URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.default.uri
}
