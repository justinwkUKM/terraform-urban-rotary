# ==============================================================================
# GitHub Actions CI/CD Configuration (Workload Identity Federation)
# ==============================================================================

# 1. Service Account for GitHub Actions
# This "Deployer" identity is what GitHub Actions will assume to deploy resources.
resource "google_service_account" "github_actions" {
  account_id   = "github-actions-deployer"
  display_name = "GitHub Actions Deployer"
  description  = "Used by GitHub Actions to deploy Cloud Run and Infra"
}

# 2. Grant Admin Permissions
# The deployer needs broad access to manage Cloud Run, Secret Manager, etc.
resource "google_project_iam_member" "deployer_roles" {
  for_each = toset([
    "roles/run.admin",                  # Deploy Cloud Run services
    "roles/storage.admin",              # Manage GCS (backend state)
    "roles/iam.serviceAccountUser",     # Act as the runtime SA (fastapi-runner)
    "roles/iam.workloadIdentityUser",   # Required for using WIF
    "roles/artifactregistry.admin",     # Push Docker images
    "roles/cloudbuild.builds.editor",   # Submit builds
    "roles/cloudbuild.builds.viewer",   # View build logs
    "roles/logging.viewer",             # Stream Cloud Build logs
    "roles/secretmanager.admin",        # Manage secrets
    "roles/datastore.owner",            # Manage Firestore indexes
    "roles/serviceusage.serviceUsageAdmin" # Enable APIs
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# 3. Workload Identity Pool
# Serves as a container for identity providers (GitHub).
resource "google_iam_workload_identity_pool" "github_pool" {
  workload_identity_pool_id = "github-actions-pool-v1"
  display_name              = "GitHub Actions Pool"
  description               = "Identity pool for GitHub Actions CI/CD"
}

# 4. Workload Identity Provider
# Configures the trust relationship with GitHub.
resource "google_iam_workload_identity_pool_provider" "github_provider" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Provider"
  description                        = "OIDC Provider for GitHub Actions"
  
  # Restriction: Only allow this repository
  attribute_condition = "assertion.repository == 'justinwkUKM/terraform-urban-rotary'"

  # Map GitHub OIDC token claims to Google attributes
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }
  
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# 5. Allow Impersonation
# Grant specific GitHub Repositories permission to impersonate the Service Account.
resource "google_service_account_iam_member" "wif_impersonation" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  
  # LOCK DOWN: Only allow the 'main' branch of THIS specific repository
  member = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_pool.name}/attribute.repository/justinwkUKM/terraform-urban-rotary"
}

# 6. Outputs for GitHub Secrets
output "wif_provider_name" {
  description = "Workload Identity Provider Resource Name (use in GitHub Actions)"
  value       = google_iam_workload_identity_pool_provider.github_provider.name
}

output "github_service_account" {
  description = "Service Account Email for GitHub Actions"
  value       = google_service_account.github_actions.email
}
