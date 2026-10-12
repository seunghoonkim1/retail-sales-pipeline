variable "project" {
  description = "Project name, used in resource names"
  type        = string
  default     = "retail-sales-pipeline"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "monthly_budget_usd" {
  description = "Monthly budget used for cost alerts"
  type        = number
  default     = 5
}

variable "alert_email" {
  description = "Email address that receives budget alerts"
  type        = string
  sensitive   = true # hide the value in plan and apply output
  # No default on purpose: the value comes from terraform.tfvars,
  # which is ignored by Git, so the email never enters the repo
}