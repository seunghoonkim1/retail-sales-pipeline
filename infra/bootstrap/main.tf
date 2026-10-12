# main holds the resources: the actual things built from those inputs(variables), like the bucket and its settings
provider "aws" {
  region = var.region

  # Tags are labels added to every resource, so you can see
  # what each one belongs to and who manages it
  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
    }
  }
}

# Bucket names must be unique across all of AWS,
# so add a random suffix
resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "tfstate" {
  bucket = "${var.project}-tfstate-${random_id.suffix.hex}"

  # Refuse to delete this bucket, even with terraform destroy.
  # Losing it would mean losing track of all infrastructure.
  lifecycle {
    prevent_destroy = true
  }
}

# Keep every previous version of the state file,
# so a corrupted or bad state can be rolled back
resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Encrypt everything stored in the bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Make it impossible to expose this bucket publicly
resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}