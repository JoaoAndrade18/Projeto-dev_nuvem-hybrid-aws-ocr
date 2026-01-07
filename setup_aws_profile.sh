#!/usr/bin/env bash
set -euo pipefail

CREDS_FILE="${1:-./aws-credentials.local}"
PROFILE="${2:-ocr}"
REGION="${3:-us-east-1}"
OUTPUT="${4:-json}"

if ! command -v aws >/dev/null 2>&1; then
  echo "[ERROR] aws cli not found."
  exit 1
fi

if [[ ! -f "$CREDS_FILE" ]]; then
  echo "[ERROR] Credentials file not found: $CREDS_FILE"
  exit 1
fi

# Extract AWS credentials from the [default] section of the credentials file
extract_key() {
  local key="$1"
  awk -v target="$key" '
    function trim(s) { sub(/^[ \t]+/, "", s); sub(/[ \t\r]+$/, "", s); return s }
    /^\[default\][ \t]*$/ { inside_default=1; next }
    /^\[/ { inside_default=0 }
    inside_default && $0 ~ ("^" target "[ \t]*=") {
      line=$0
      sub(/^[^=]*=/, "", line)
      print trim(line)
      exit
    }
  ' "$CREDS_FILE"
}

AWS_ACCESS_KEY_ID="$(extract_key aws_access_key_id)"
AWS_SECRET_ACCESS_KEY="$(extract_key aws_secret_access_key)"
AWS_SESSION_TOKEN="$(extract_key aws_session_token)"

if [[ -z "${AWS_ACCESS_KEY_ID}" || -z "${AWS_SECRET_ACCESS_KEY}" || -z "${AWS_SESSION_TOKEN}" ]]; then
  echo "ERRO: não foi possível ler aws_access_key_id / aws_secret_access_key / aws_session_token da seção [default]."
  echo "Verifique o arquivo: $CREDS_FILE"
  exit 1
fi

echo "Setting profile '${PROFILE}'..."
aws configure set aws_access_key_id     "${AWS_ACCESS_KEY_ID}"     --profile "${PROFILE}"
aws configure set aws_secret_access_key "${AWS_SECRET_ACCESS_KEY}" --profile "${PROFILE}"
aws configure set aws_session_token     "${AWS_SESSION_TOKEN}"     --profile "${PROFILE}"
aws configure set region                "${REGION}"                --profile "${PROFILE}"
aws configure set output                "${OUTPUT}"                --profile "${PROFILE}"

echo "[INFO] testing credentials for profile '${PROFILE}'..."
aws sts get-caller-identity --profile "${PROFILE}" >/dev/null

export AWS_PROFILE=ocr
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
export AWS_SDK_LOAD_CONFIG=1
export AWS_EC2_METADATA_DISABLED=true

echo "[INFO] profile '${PROFILE}' load is successful."

set +euo pipefail