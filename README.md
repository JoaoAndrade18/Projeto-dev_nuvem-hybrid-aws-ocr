# Overview sobre o projeto OCR híbrido (AWS + Docker Compose)

## 1. Visão Geral

Este projeto tem o objetivo de implementar uma **aplicação distribuída** de `OCR` baseada em uma arquitetura híbrida combinando:
- Serviços locais containerizados (`Docker Compose`)
- Serviços gerenciados da AWS (`DynamoDB`)
  
O objetivo ao final do tutorial do nosso projeto é demonstrar:

- **Provisionamento automatizado** da Infraestrutura (`Terraform`) para criação e acesso à tabela `DynamoDB` na AWS. 
- **Processamento assíncrono** e **escalável** (`RabbitMQ` + múltiplos `workers`)
- **Persistência híbrida** (`Postgres + DynamoDB`)
- **Separação** clara entre controle de **estado** e **dados** pesados

## 2. Arquitetura e Tecnologias Utilizadas

Este projeto utiliza as seguintes ferramentas e tecnologias:

- **AWS CLI** (**credenciais temporárias** de laboratório/AWS Academy usadas para **autenticação** e **operações** - `leitura`, `escrita` e `atualização` do status dos `jobs` - no `DynamoDB`)
- **Terraform** (`Ferramenta de Infraestrutura como Código (IaC)` usada para **provisionar automaticamente** a **tabela** `DynamoDB`)
- **Docker + Docker Compose** responsáveis por orquestrar os serviços locais da aplicação, incluindo:
  - API (FastAPI)
    - Endpoints REST
  - Frontend (Web)
    - Interface para criar jobs, enviar imagens e acompanhar o status e o texto OCR.
  - Worker (Celery)
    - Processamento OCR
  - Serviços auxiliares
    - Postgres SQL
    - RabittMQ
    - MinIO
<!-- - (subir API, worker, Postgres, RabbitMQ, MinIO e frontend) -->
- Arquivos de ambiente
  - Copiar `.env.example` → `.env`

---
**Tutorial — Executando o Projeto do Zero**

## 3. Pré-requisitos

- `Git` (Usado apenas para obter o código-fonte do projeto.)
- `Docker + Docker` Compose (Utilizados para containerizar e orquestrar os serviços da aplicação)
- `AWS CLI` (Configurar credenciais temporárias do ambiente de laboratório)
- `Terraform` (Provisionamento automatizado da infraestrutura na AWS para criar e configurar o DynamoDB)

Links oficiais:

- AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html  
- Terraform: https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli  
- Docker: https://docs.docker.com/get-docker/  
- Docker Engine (Linux): https://docs.docker.com/engine/install/  

---

## 4. Configurações inciais

### 4.1 **Clone o repositório e acesse a pasta do projeto:**
   ```sh
   git clone https://github.com/JoaoAndrade18/Projeto-dev_nuvem-hybrid-aws-ocr.git
   cd Projeto-dev_nuvem-hybrid-aws-ocr
   ```

### 4.2 **Crie o arquivo de credenciais AWS local e dê permissão de execução:**
   ```sh
   touch aws-credentials.local
   chmod +x setup_aws_profile.sh
   ```
   - Este procedimento tem o objetivo de criar um arquivo para armazenar as credenciais temporárias do laboratório.

### 4.3 **Copie as informações da CLI do AWS Learner Lab os valores:**
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_SESSION_TOKEN`

E Cole no arquivo `aws-credential.local`.

### 4.4 **Configure o perfil AWS usando o script:**
   ```sh
   source ./setup_aws_profile.sh ./aws-credentials.local ocr us-east-1 json
   ```
- Esse comando cria um **perfil local** que será utilizado automaticamente pelos containers para acessar o `DynamoDB`.

### 4.5 **Copie o arquivo de variáveis de ambiente:**
   ```sh
   cp .env.example .env
   ```
   - O arquivo `.env` contém, entre outras configurações:
     - Região `AWS`
     - Nome da tabela `DynamoDB`
     - Endereço do `MinIO`
     - Credenciais do banco `Postgres`
     - URL do `RabbitMQ`
     - As credenciais `AWS` não ficam no `.env`, pois são carregadas via volume do perfil `AWS`

## 5 **Provisionamento do DynamoDB com Terraform:**

Nesta etapa, utilizamos o `Terraform` para **criar automaticamente** a **tabela** do `DynamoDB` na `AWS` que será usada pela aplicação para **armazenar** e **consultar** o estado dos **jobs** de OCR.
   
   ```sh
   cd infra/terraform-dynamodb
   terraform init
   terraform apply
   cd ../..
   ```
**Explicação dos comandos:**
- `cd infra/terraform-dynamodb`
  - Acessa o diretório que contém os arquivos Terraform responsáveis pelo DynamoDB
- `terraform init`
  - Inicializa o Terraform:
    - Baixa o provider da AWS
    - Prepara o diretório para execução
    - Deve ser executado uma vez antes do apply
- `terraform apply`
  - Executa o **plano de infraestrutura**:
    - Cria a tabela `DynamoDB na AWS`
    - Aplica exatamente o **schema** esperado pela aplicação (`chave de partição job_id`)
    - Solicita **confirmação** antes de **aplicar as mudanças**
- `cd ../..`
  - Retorna à raiz do projeto para continuar o fluxo de execução. 

## 6 **Subindo a Aplicação com Docker Compose:**

   Nesta etapa, todos os **serviços da aplicação** são **iniciados** localmente utilizando **`Docker Compose`**, incluindo a `API`, `frontend`, `banco de dados`, `mensageria` e múltiplos `workers` de OCR.

   ```sh
   docker compose up --build --scale worker=3
   ```
   - **Explicação do comando**
     - `docker compose up`
       - Inicia todos os serviços definidos no arquivo `docker-compose.yml`
     - `--build`
       - **Força** a **reconstrução das imagens** `Docker`
     - `--scale worker=3`
       - Cria **3 instâncias** do serviço **`worker`**, permitindo:
         - **Processamento paralelo** de múltiplas **imagens**
         - Demonstração prática de **escala horizontal**
         - **Distribuição de carga** via **RabbitMQ**
