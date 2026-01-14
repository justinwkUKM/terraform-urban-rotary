# FastAPI on Cloud Run with Terraform

This project deploys a Python FastAPI application to Google Cloud Run using Terraform. It includes an automated build pipeline where Terraform triggers Google Cloud Build to containerize the application and push it to Artifact Registry whenever the source code changes.

## 🚀 Architecture

1.  **FastAPI Application**: A Python web service running on port 8080.
2.  **Artifact Registry**: Stores the Docker images.
3.  **Cloud Build**: Builds the Docker image from source.
4.  **Cloud Run**: Runs the stateless containerized service (publicly accessible).
5.  **Terraform**: Manages the entire lifecycle (APIs, Build, Deployment).

---

## 📋 Prerequisites

Ensure you have the following installed and authenticated:

1.  **Google Cloud SDK (`gcloud`)**
    ```sh
    gcloud auth login
    gcloud auth application-default login
    gcloud config set project <YOUR_PROJECT_ID>
    ```

2.  **Terraform (`v1.0+`)**
    ```sh
    brew install terraform
    ```

---

## 🛠️ Deployment Instructions

### 1. Initialize Terraform
Run this command once to download the necessary providers and plugins.
```sh
terraform init
```

### 2. Review the Plan
See what changes Terraform will make to your infrastructure.
```sh
terraform plan
```

### 3. Deploy
Apply the configuration to create/update resources.
```sh
terraform apply
```
*Type `yes` when prompted, or utilize the `-auto-approve` flag.*

### 4. Verify
After successful deployment, Terraform will output the `service_url`.
```sh
curl <service_url>
# Example: curl https://fastapi-service-xyz.a.run.app/health
```

---

## ⌨️ Common Terraform Commands
# FastAPI on Cloud Run with Terraform (Automated Secrets)

This project deploys a **FastAPI** application to **Google Cloud Run** using **Terraform**. It features:
- **Automated Secret Management**: Reads secrets from `terraform.tfvars` and automatically creates Google Secret Manager secrets and mounts them into the application.
- **Project Structure**: Clean separation of `backend`, `frontend`, and `infra`.
- **Optimization**: Smart caching and ignored files for fast builds (~40s).

## 📂 Project Structure

```
.
├── backend/                # Application Code
│   ├── main.py            # FastAPI App
│   ├── Dockerfile         # Container Definition
│   ├── requirements.txt   # Python Dependencies
│   └── .env.local         # Local Secrets (Git Ignored)
├── infra/                  # Infrastructure as Code
│   ├── main.tf            # Main Terraform Configuration
│   ├── terraform.tfvars   # Secret Values (Git Ignored)
│   └── ...
├── frontend/               # (Placeholder for future UI)
└── README.md
```

## 🚀 Prerequisites

1.  **Google Cloud CLI (`gcloud`)**: Installed and authenticated (`gcloud auth login`).
2.  **Terraform**: Installed.
3.  **Git**: Installed.

## 🛠️ Setup & Deployment

### 1. Secrets Configuration
Create a `terraform.tfvars` file in the `infra/` directory. **This file is git-ignored** to keep your secrets safe.

**File:** `infra/terraform.tfvars`
```hcl
project_id = "your-project-id"
region     = "us-central1"

application_secrets = {
  "OPENAI_API_KEY" = "sk-..."
  "DB_PASSWORD"    = "super-secret"
  # Add any other keys here
}
```

### 2. Deploy Infrastructure
Navigate to the `infra` directory and apply the configuration. Terraform will build the Docker image (from `backend/`) and deploy everything.

```bash
cd infra
terraform init
terraform apply
```

### 3. Verify Deployment
After a successful apply, Terraform will output the `service_url`.

```bash
# Output example
service_url = "https://fastapi-service-xp3...a.run.app"
```

Access the health check or secret verification endpoint:
- **Health**: `$URL/health`
- **Secrets**: `$URL/secret` (Shows masked values to prove secret injection worked)

## 🔒 Security

- **Secrets**: are NEVER hardcoded in `main.tf`. They are passed via `terraform.tfvars` (local) or CI/CD secrets (production).
- **Git**: `.gitignore` ensures `tfvars`, `.env`, and state files are not committed.
- **Secret Manager**: Terraform automatically creates Secret Manager resources for every entry in `application_secrets` map.

## ⚠️ Important Note
The `application_secrets` variable in `main.tf` allows you to manage ALL your environment secrets in one place (`infra/terraform.tfvars`). Terraform handles the heavy lifting of creating the secret resource, the secret version, IAM permissions, and Cloud Run environment storage.
