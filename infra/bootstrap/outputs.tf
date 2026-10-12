# Key results worth reporting, like the bucket’s name
output "state_bucket_name" {
  description = "Name of the bucket that stores Terraform state"
  value       = aws_s3_bucket.tfstate.bucket
}