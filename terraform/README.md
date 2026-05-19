# Infrastructure-as-Code (terraform/)

This directory contains Terraform configurations for managing GCP infrastructure.

## Gated Deployment Process
1. Update Terraform configs for any infra-dependent feature.
2. Run `terraform plan` and calculate projected costs.
3. Cost and infra reviews must be finalized before GitHub tagging.
4. Deployment triggers automatically upon tagging.

## Structure
- `environments/`: Environment-specific configurations (dev, prod).
- `modules/`: Reusable infrastructure modules.
