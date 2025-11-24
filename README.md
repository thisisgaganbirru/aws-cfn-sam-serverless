# AWS CloudFormation + SAM Serverless Starter

This repository separates infrastructure (CloudFormation) from application (AWS SAM) for a production-ready serverless stack.

## How to Destroy Safely
1) Ensure AWS credentials target the right account/region.
2) Set env vars and run locally: `ENV=dev REGION=us-east-1 ./destroy.sh` (optionally override `APP_STACK` and `INFRA_STACK`).
3) Or trigger the destroy CodePipeline (`serverless-destroy-<env>`) which runs the same script via CodeBuild.
4) Verify stacks are gone: `aws cloudformation list-stacks --stack-status-filter DELETE_COMPLETE`.
5) Artifact bucket cleanup is handled by the destroy CodeBuild role; confirm bucket empties if you delete stacks manually.
