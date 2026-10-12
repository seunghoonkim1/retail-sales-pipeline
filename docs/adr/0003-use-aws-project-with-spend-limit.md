# 3. Use an AWS project with a spend limit in us-east-2

Date: 2026-10-12

## Status

Accepted

## Context

The pipeline needs an AWS account. The account was created through AWS's new sign-up experience, which organizes work into a project containing one AWS account. Sign-in uses an AWS Builder ID with MFA, and AWS manages the root user and the organization behind the project.

The free plan was not available for this account, so it runs on the paid plan. Cost control therefore matters from day one.

Options considered:
- Stay in the new experience: simple setup, temporary CLI credentials through `aws login`, and a hard monthly spend limit.
- Activate advanced features: a traditional account with a root user and full AWS Organizations control. This cannot be reversed and removes the spend limit.

## Decision

- Use the AWS project from the new experience, without activating advanced features.
- Use the paid plan with a $20 monthly spend limit, set by hand in AWS Settings. If reached, AWS pauses the project.
- Use a $5 monthly AWS Budget with email alerts as an early warning, managed in Terraform in infra/account/.
- Deploy all resources in us-east-2, the region the project was set up in.
- Access AWS from the command line only through `aws login`, never long-lived access keys.

## Consequences

Positive:
- Costs cannot exceed $20 per month before tax.
- No long-lived credentials exist for this account.
- All services in the design (S3, Lambda, ECR, Glue, Athena, IAM, Budgets) are supported.

Negative:
- The spend limit is not managed in Terraform, so it is documented here instead. If Terraform support is added, it should move into infra/account/.
- Reaching the spend limit pauses the whole project until the limit is raised or the month ends.
- Deploying to a traditional AWS account later, such as a company account, needs a different access setup (for example, IAM Identity Center). The Terraform code for the pipeline itself is unaffected.