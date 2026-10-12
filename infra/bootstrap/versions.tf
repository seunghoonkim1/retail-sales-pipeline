# versions is about how the tool runs, not about your infrastructure.
# which Terraform version to require, which plugins (providers) to download, and where to keep its state.
# versions.tf configures Terraform itself
# It rarely changes.
terraform {
  # Terraform 1.10+ supports state locking directly in S3
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0" # any 6.x version, but not 7.0
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Store this folder's state in S3 instead of on this laptop
  backend "s3" {
    bucket       = "retail-sales-pipeline-tfstate-84135748"
    key          = "bootstrap/terraform.tfstate" # path inside the bucket
    region       = "us-east-2"
    use_lockfile = true # lock the state while someone is applying
    encrypt      = true
  }
}