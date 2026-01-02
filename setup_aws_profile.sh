#!/usr/bin/env bash
set -euo pipefail

CREDS_FILE="${1:-./aws-credentials.local}"
PROFILE="${2:-ocr}"
REGION="${3:-us-east-1}"
OUTPUT="${4:-json}"

if ! command -v aws >/dev/null 2>&1; then
  echo "ERRO: aws cli não encontrado no PATH."
  exit 1
fi

if [[ ! -f "$CREDS_FILE" ]]; then
  echo "ERRO: arquivo de credenciais não existe: $CREDS_FILE"
  exit 1
fi

# Função awk: pega o valor após o primeiro "=" (mantém '=' finais do token)
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

echo "Configurando profile '${PROFILE}'..."
aws configure set aws_access_key_id     "${AWS_ACCESS_KEY_ID}"     --profile "${PROFILE}"
aws configure set aws_secret_access_key "${AWS_SECRET_ACCESS_KEY}" --profile "${PROFILE}"
aws configure set aws_session_token     "${AWS_SESSION_TOKEN}"     --profile "${PROFILE}"
aws configure set region                "${REGION}"                --profile "${PROFILE}"
aws configure set output                "${OUTPUT}"                --profile "${PROFILE}"

echo "Testando credenciais..."
aws sts get-caller-identity --profile "${PROFILE}" >/dev/null

echo "OK: profile '${PROFILE}' configurado com sucesso."

export AWS_PROFILE=${PROFILE}
export AWS_SDK_LOAD_CONFIG=1
export AWS_REGION=${REGION}
export AWS_DEFAULT_REGION=${REGION}
export AWS_EC2_METADATA_DISABLED=true
