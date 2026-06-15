variable "aws_region" { type = string; default = "us-east-1" }
variable "environment" { type = string }
variable "container_image" { type = string; default = "placeholder" }

variable "opensearch_host_param_name" {
  type        = string
  description = "The name of the SSM parameter for the OpenSearch host."
  default     = "ssp/search/opensearch_host"
}
