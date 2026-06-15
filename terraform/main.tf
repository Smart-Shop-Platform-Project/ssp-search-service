terraform {
  required_providers { aws = { source = "hashicorp/aws", version = "~> 5.0" } }
  backend "s3" {}
}

provider "aws" { region = var.aws_region }

data "aws_caller_identity" "current" {}

# IAM Policy for SSM Parameter Store Access
resource "aws_iam_policy" "ssm_policy" {
  name        = "ssp-search-service-ssm-policy-${var.environment}"
  description = "Allows reading the OpenSearch host from SSM"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "ssm:GetParameter",
        Effect   = "Allow",
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.opensearch_host_param_name}"
      }
    ]
  })
}

data "terraform_remote_state" "base_infra" {
  backend = "s3"
  config = {
    bucket = "ssp-terraform-state-bucket"
    key    = "infrastructure/base/terraform.tfstate"
    region = var.aws_region
  }
}

module "ecr" {
  source          = "git::https://github.com/DeathGod049/terraform-infra-child.git//modules/ecr?ref=v0.1.0"
  repository_name = "ssp-search-service"
  environment     = var.environment
}

module "ecs_service" {
  source              = "git::https://github.com/DeathGod049/terraform-infra-child.git//modules/ecs-service?ref=v0.1.0"
  service_name        = "ssp-search-service"
  environment         = var.environment
  cluster_id          = data.terraform_remote_state.base_infra.outputs.ecs_cluster_id
  vpc_id              = data.terraform_remote_state.base_infra.outputs.vpc_id
  private_subnets     = data.terraform_remote_state.base_infra.outputs.private_subnets
  container_image     = var.container_image
  container_port      = 80

  task_policy_arns    = [aws_iam_policy.ssm_policy.arn]

  environment_variables = [
    { name = "OPENSEARCH_HOST_PARAM_NAME", value = var.opensearch_host_param_name },
    { name = "AWS_REGION", value = var.aws_region }
  ]
}
