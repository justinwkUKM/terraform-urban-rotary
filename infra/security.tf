# ==============================================================================
# Advanced Security: Binary Authorization & KMS (Flag-Gated)
# Included: KMS KeyRing, CryptoKey, Attestor, BinAuthz Policy
# ==============================================================================

# 1. Enable Required APIs
resource "google_project_service" "security_apis" {
  for_each = var.enable_enterprise ? toset([
    "cloudkms.googleapis.com",
    "binaryauthorization.googleapis.com",
    "containeranalysis.googleapis.com"
  ]) : []

  service            = each.key
  disable_on_destroy = false
}

# 2. Cloud KMS (Key Management Service)
# We need a key to verify the Attestor's signature.
resource "google_kms_key_ring" "keyring" {
  count    = var.enable_enterprise ? 1 : 0
  name     = "attestor-keyring"
  location = var.region
  depends_on = [google_project_service.security_apis]
}

resource "google_kms_crypto_key" "signing_key" {
  count    = var.enable_enterprise ? 1 : 0
  name     = "attestor-signing-key-v2"
  key_ring = google_kms_key_ring.keyring[0].id
  purpose  = "ASYMMETRIC_SIGN"

  version_template {
    algorithm = "RSA_SIGN_PKCS1_4096_SHA512"
  }
}

# 3. Binary Authorization Attestor
# This resource represents the "authority" that verifies images.
# It links to the KMS key above.
resource "google_binary_authorization_attestor" "attestor" {
  count = var.enable_enterprise ? 1 : 0
  name  = "quality-assurance-attestor"
  
  attestation_authority_note {
    note_reference = google_container_analysis_note.note[0].name
    public_keys {
      # This ID must match --public-key-id in build_and_sign.sh
      id = "//cloudkms.googleapis.com/v1/${google_kms_crypto_key.signing_key[0].id}/cryptoKeyVersions/1"
      pkix_public_key {
        public_key_pem      = data.google_kms_crypto_key_version.latest_version[0].public_key[0].pem
        signature_algorithm = "RSA_SIGN_PKCS1_4096_SHA512"
      }
    }
  }
}

# Container Analysis Note (Required for Attestor)
resource "google_container_analysis_note" "note" {
  count = var.enable_enterprise ? 1 : 0
  name = "attestor-note"
  attestation_authority {
    hint {
      human_readable_name = "Quality Assurance Attestor"
    }
  }
}

# Data source to retrieve the public key from KMS
data "google_kms_crypto_key_version" "latest_version" {
  count      = var.enable_enterprise ? 1 : 0
  crypto_key = google_kms_crypto_key.signing_key[0].id
}


# 4. Binary Authorization Policy
# Defines the rules for deployment.
resource "google_binary_authorization_policy" "policy" {
  count = var.enable_enterprise ? 1 : 0

  # Default: Block everything unless it checks out
  global_policy_evaluation_mode = "ENABLE"

  # Rule: specific images (like system images) might be exempted, 
  # but here we set the default admission rule.
  default_admission_rule {
    evaluation_mode  = "REQUIRE_ATTESTATION"
    enforcement_mode = "ENFORCED_BLOCK_AND_AUDIT_LOG"
    require_attestations_by = [
      google_binary_authorization_attestor.attestor[0].name
    ]
  }

  # Allow Google-managed system images (optional, but recommended for Cloud Run/GKE system pods)
  # Cloud Run doesn't use system pods in the same way, but it's good practice.
}
