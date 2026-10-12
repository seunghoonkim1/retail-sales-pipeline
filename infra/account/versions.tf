terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  backend "s3" {
    bucket       = "retail-sales-pipeline-tfstate-84135748"
    key          = "account/terraform.tfstate" # its own key in the same bucket
    region       = "us-east-2"
    use_lockfile = true
    encrypt      = true
  }
}