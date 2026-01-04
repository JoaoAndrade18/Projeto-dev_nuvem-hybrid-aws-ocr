# Tutorial completo — Subir o projeto OCR híbrido (AWS + Docker Compose)

Este guia mostra como executar o projeto do zero, usando:
- **AWS CLI** (credenciais temporárias de laboratório/AWS Academy)
- **Terraform** (criar DynamoDB)
- **Docker + Docker Compose** (subir API, worker, Postgres, Redis, MinIO e frontend)
- Copiar `.env.example` → `.env`

---

## 1) Pré-requisitos

Você precisará ter instalado:

- Git (para clonar o repositório)
- Docker + Docker Compose
- AWS CLI v2
- Terraform

Links oficiais:

- AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html  
- Terraform: https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli  
- Docker: https://docs.docker.com/get-docker/  
- Docker Engine (Linux): https://docs.docker.com/engine/install/  

---

touch aws-credentials.local
chmod 600 aws-credentials.local

chmod +x setup_aws_profile.sh

./setup_aws_profile.sh ./aws-credentials.local ocr us-east-1 json

export AWS_PROFILE=ocr
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
export AWS_SDK_LOAD_CONFIG=1
export AWS_EC2_METADATA_DISABLED=true

git clone <URL_DO_REPOSITORIO>
cd PROJETO-OCR-AWS-DevNuvem

erifique se existe docker-compose.yml na raiz:

cp .env.example .env

cd infra/terraform-dynamodb
terraform init
terraform apply

docker compose up --build --scale worker=3




