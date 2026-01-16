#!/bin/bash
set -e

# Arguments
PROJECT_ID=$1
REGION=$2
IMAGE_URI=$3
ENABLE_ENTERPRISE=$4

echo "🚀 Starting Build for ${IMAGE_URI}..."
echo "🔒 Enterprise Security Mode: ${ENABLE_ENTERPRISE}"

# 1. Build the image
gcloud builds submit --project "${PROJECT_ID}" --quiet --tag "${IMAGE_URI}" ../backend

if [ "$ENABLE_ENTERPRISE" = "true" ]; then
    echo "🔏 Enterprise enabled: Signing image for Binary Authorization..."
    
    # Get the digest of the pushed image
    DIGEST=$(gcloud container images describe "${IMAGE_URI}" --format='get(image_summary.digest)')
    BARE_URI="${IMAGE_URI%:*}"
    FQ_IMAGE="${BARE_URI}@${DIGEST}"
    
    echo "🔍 Found Digest: ${DIGEST}"
    echo "🎯 Attesting: ${FQ_IMAGE}"
    
    # Configuration
    ATTESTOR="quality-assurance-attestor"
    KEYRING="attestor-keyring"
    KEY="attestor-signing-key-v2"
    VERSION="1"
    
    # Public Key ID - must match the ID configured in the Attestor resource
    PUBLIC_KEY_ID="//cloudkms.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/keyRings/${KEYRING}/cryptoKeys/${KEY}/cryptoKeyVersions/${VERSION}"
    
    # Create temp files for signing
    PAYLOAD_FILE=$(mktemp)
    SIGNATURE_FILE=$(mktemp)
    
    # Step 1: Generate payload (the artifact URL)
    gcloud container binauthz create-signature-payload \
      --artifact-url="${FQ_IMAGE}" > "${PAYLOAD_FILE}"
    
    echo "📝 Payload generated."
    
    # Step 2: Sign the payload with KMS
    gcloud kms asymmetric-sign \
      --location="${REGION}" \
      --keyring="${KEYRING}" \
      --key="${KEY}" \
      --version="${VERSION}" \
      --digest-algorithm=sha512 \
      --input-file="${PAYLOAD_FILE}" \
      --signature-file="${SIGNATURE_FILE}"
    
    echo "🔑 Signature created."
    
    # Step 3: Create the attestation
    gcloud container binauthz attestations create \
      --project="${PROJECT_ID}" \
      --artifact-url="${FQ_IMAGE}" \
      --attestor="${ATTESTOR}" \
      --attestor-project="${PROJECT_ID}" \
      --public-key-id="${PUBLIC_KEY_ID}" \
      --signature-file="${SIGNATURE_FILE}"
    
    # Cleanup temp files
    rm -f "${PAYLOAD_FILE}" "${SIGNATURE_FILE}"

    echo "✅ Image Signed and Attestation Created."
fi
