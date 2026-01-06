# Tutorial completo — Subir o projeto OCR híbrido (AWS + Docker Compose)

Este guia mostra como executar o projeto do zero, usando:
- **AWS CLI** (credenciais temporárias de laboratório/AWS Academy)
- **Terraform** (criar DynamoDB)
- **Docker + Docker Compose** (subir API, worker, Postgres, Redis, MinIO e frontend)
- Copiar `.env.example` → `.env`

---

## 1. Pré-requisitos

Você precisará ter instalado:

- Git (para clonar o repositório)
- Docker + Docker Compose
- AWS CLI
- Terraform

Links oficiais:

- AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html  
- Terraform: https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli  
- Docker: https://docs.docker.com/get-docker/  
- Docker Engine (Linux): https://docs.docker.com/engine/install/  

---

## 2. Configurações

1. **Crie o arquivo de credenciais AWS local:**
   ```sh
   touch aws-credentials.local
   chmod 600 aws-credentials.local
   ```

2. **Copie as informações da CLI do laboratório aws e cole no arquivo `aws-credential.local`** 

3. **Dê permissão de execução ao script de setup:**
   ```sh
   chmod +x setup_aws_profile.sh
   ```

4. **Configure o perfil AWS usando o script:**
   ```sh
   ./setup_aws_profile.sh ./aws-credentials.local ocr us-east-1 json
   ```

5. **Exporte as variáveis de ambiente AWS:**
   ```sh
   export AWS_PROFILE=ocr
   export AWS_REGION=us-east-1
   export AWS_DEFAULT_REGION=us-east-1
   export AWS_SDK_LOAD_CONFIG=1
   export AWS_EC2_METADATA_DISABLED=true
   ```

6. **Clone o repositório e acesse a pasta do projeto:**
   ```sh
   git clone <URL_DO_REPOSITORIO>
   cd PROJETO-OCR-AWS-DevNuvem
   ```

7. **Copie o arquivo de variáveis de ambiente:**
   ```sh
   cp .env.example .env
   ```

8. **Suba a infraestrutura do DynamoDB com Terraform:**
   ```sh
   cd infra/terraform-dynamodb
   terraform init
   terraform apply
   cd ../..
   ```

9. **Suba os containers com Docker Compose (incluindo 3 workers):**
   ```sh
   docker compose up --build --scale worker=3
   ```