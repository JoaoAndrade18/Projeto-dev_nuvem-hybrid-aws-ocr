terraform {
  required_providers {
    aws = { 
      source = "hashicorp/aws", 
      version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_dynamodb_table" "ocr_jobs" {
  name         = var.dynamodb_table
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "job_id"

  attribute {
    name = "job_id"
    type = "S"
  }

  # Se quiser consultar por status/created_at, adicione GSI depois.
}

variable "aws_region" { type = string }
variable "dynamodb_table" { type = string }

output "dynamodb_table_name" { value = aws_dynamodb_table.ocr_jobs.name }
