# Variables configure your infrastructure:
# values that end up in the resources, like the project name, region, and later the stage (dev or prod). 
# They exist so these values can change without editing the resource code.
variable "project" {
  description = "Project name, used in resource names"
  type        = string
  default     = "retail-sales-pipeline"
}

variable "region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-2"
}