# ==============================================================================
# Enterprise Features (Flag-Gated)
# Included: VPC Network, Redis (Memorystore), Cloud Armor, Serverless Connector
# ==============================================================================

# 1. Enable Required APIs (Conditionally)
resource "google_project_service" "enterprise_apis" {
  for_each = var.enable_enterprise ? toset([
    "compute.googleapis.com"
  ]) : []

  service            = each.key
  disable_on_destroy = false
}

# 2. VPC Network & Serverless Connector
# (Removed as per user request to optimize for cost/speed)

# 3. Cloud Memorystore (Redis)
# (Removed as per user request to optimize for cost/speed)

# 4. Cloud Armor (Security Policy)
resource "google_compute_security_policy" "policy" {
  count = var.enable_enterprise ? 1 : 0
  name  = "api-armor-policy"

  # Rule 1: Allow all (Default) - In realprod, you might deny specific IPs
  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default rule, allow all"
  }
  
  # Example Rule: Rate Limiting (Commented out to prevent accidental locking)
  # rule {
  #   action   = "rate_based_ban"
  #   priority = "1000"
  #   match { ... }
  # }
  
  depends_on = [google_project_service.enterprise_apis]
}

# Note: Load Balancer setup is quite verbose in Terraform. 
# For now, we will expose Redis Host env var and link VPC.
# Full LB setup is added if strictly requested, but connector+Redis allows internal caching logic.
