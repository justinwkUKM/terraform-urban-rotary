# FastAPI on Cloud Run with Terraform

This project deploys a **FastAPI** application to **Google Cloud Run** using **Terraform**. It features:
- **Automated Secret Management**: Reads secrets from `terraform.tfvars` and automatically creates Google Secret Manager secrets and mounts them into the application.
- **Enterprise Security (Optional)**: Binary Authorization with KMS image signing.
- **Firestore Integration**: Persistent database storage.
- **Smart Build Caching**: Content-hash based image tagging for efficient rebuilds (~40s).

## 📂 Project Structure

```
.
├── backend/                 # Application Code
│   ├── main.py             # FastAPI App
│   ├── Dockerfile          # Container Definition
│   └── requirements.txt    # Python Dependencies
├── infra/                   # Infrastructure as Code
│   ├── main.tf             # Core Terraform Configuration
│   ├── security.tf         # Binary Authorization & KMS (Enterprise)
│   ├── enterprise.tf       # VPC, Redis, Cloud Armor (Enterprise)
│   ├── build_and_sign.sh   # Image build & signing script
│   └── terraform.tfvars    # Secret Values (Git Ignored)
├── load_test.py             # Load testing utility
├── count_logs.py            # Log counting utility
└── README.md
```

## 🚀 Architecture

1.  **FastAPI Application**: A Python web service running on port 8080.
2.  **Artifact Registry**: Stores the Docker images.
3.  **Cloud Build**: Builds the Docker image from source.
4.  **Cloud Run**: Runs the stateless containerized service (publicly accessible).
5.  **Firestore**: NoSQL database for persistent storage.
6.  **Secret Manager**: Securely stores and injects application secrets.
7.  **Terraform**: Manages the entire lifecycle (APIs, Build, Deployment).

### Enterprise Features (Optional)
- **Binary Authorization**: Ensures only signed images can be deployed.
- **Cloud KMS**: Cryptographic key management for image signing.
- **VPC Connector**: Private network access.
- **Cloud Armor**: DDoS protection and WAF.
- **Redis (Memorystore)**: In-memory caching.
- **Sentinel System**: Covert intrusion detection with deceptive sensors.
- **Discord Alerting**: Real-time security notifications.

---

## 📋 Prerequisites

1.  **Google Cloud CLI (`gcloud`)**: Installed and authenticated.
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

## 🛠️ Setup & Deployment

### 1. Configure Secrets
Create `infra/terraform.tfvars` (**git-ignored**):

```hcl
project_id = "your-project-id"
region     = "us-central1"

# Set to true to enable Binary Authorization, VPC, Redis, Cloud Armor
enable_enterprise = false

application_secrets = {
  "GOOGLE_API_KEY"    = "your-api-key"
  "DB_PASSWORD"       = "super-secret"
  # Add any other keys here
}
```

### 2. Deploy Infrastructure

```bash
cd infra
terraform init
terraform apply
```

### 3. Verify Deployment
After successful deployment, Terraform outputs the `service_url`:

```bash
# Test the endpoints
curl <service_url>/health
curl <service_url>/
```

---

## ⌨️ Common Commands

| Command | Description |
|---------|-------------|
| `terraform init` | Initialize Terraform (run once) |
| `terraform plan` | Preview changes |
| `terraform apply` | Deploy infrastructure |
| `terraform destroy` | Tear down all resources |
| `terraform apply -auto-approve` | Deploy without confirmation |

### Redeploy Workflow
To destroy and redeploy:
```bash
cd infra
terraform destroy -auto-approve
terraform apply -auto-approve
```

---

## 🔧 Load Testing

Run load tests against the deployed service:

```bash
python load_test.py
```

---

## 🔒 Security

- **Secrets**: Never hardcoded. Passed via `terraform.tfvars` (local) or CI/CD secrets (production).
- **Git**: `.gitignore` ensures `tfvars`, `.env`, and state files are not committed.
- **Secret Manager**: Terraform automatically creates Secret Manager resources for every entry in `application_secrets`.
- **Binary Authorization** (Enterprise): Only cryptographically signed images can be deployed.

---

## 🛡️ Sentinel Security System

A covert security monitoring system that detects threats without revealing itself.

### Key Features
1. **Monitored Paths**: 40+ endpoints that look like admin panels, configs, or backups but trigger alerts when accessed (e.g., `/.env`, `/admin`).
2. **Static Responses**: Serves realistic fake content (like fake API keys or SQL dumps) to mislead attackers.
3. **Pattern Analysis**: Detects SQL injection, XSS, and other attack signatures in requests.
4. **Discord Alerts**: Sends real-time notifications for high-severity security events.

### Security Events API
View recorded security events:
```bash
curl <service_url>/events
curl <service_url>/events/stats
```

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.
