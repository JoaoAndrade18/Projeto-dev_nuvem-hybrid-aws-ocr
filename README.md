# Tutorial completo — Subir o projeto OCR híbrido (AWS + Docker Compose)

Este guia mostra como executar o projeto do zero, usando:
- **AWS CLI** (credenciais temporárias de laboratório/AWS Academy)
- **Terraform** (criar DynamoDB)
- **Docker + Docker Compose** (subir API, worker, Postgres, RabbitMQ, MinIO e frontend)
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

1. **Clone o repositório e acesse a pasta do projeto:**
   ```sh
   git clone https://github.com/JoaoAndrade18/Projeto-dev_nuvem-hybrid-aws-ocr.git
   cd Projeto-dev_nuvem-hybrid-aws-ocr
   ```

2. **Crie o arquivo de credenciais AWS local e dê permissão de execução:**
   ```sh
   touch aws-credentials.local
   chmod +x setup_aws_profile.sh
   ```

3. **Copie as informações da CLI do laboratório aws e cole no arquivo `aws-credential.local`** 

4. **Configure o perfil AWS usando o script:**
   ```sh
   source ./setup_aws_profile.sh ./aws-credentials.local ocr us-east-1 json
   ```

5. **Copie o arquivo de variáveis de ambiente:**
   ```sh
   cp .env.example .env
   ```

6. **Suba a infraestrutura do DynamoDB com Terraform:**
   ```sh
   cd infra/terraform-dynamodb
   terraform init
   terraform apply
   cd ../..
   ```

7. **Suba os containeres com Docker Compose (incluindo 3 workers):**
   ```sh
   docker compose up --build --scale worker=3
   ```