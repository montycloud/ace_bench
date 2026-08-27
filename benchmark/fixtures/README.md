# WAFR CloudFormation Stack Manager

Deploy and cleanup compliant / non-compliant / combined AWS Well-Architected assessment stacks across AWS regions.

---

## Prerequisites

### 1. AWS CLI
Install the AWS CLI if not already installed.

**macOS (Homebrew):**
```bash
brew install awscli
```

**macOS / Linux (official installer):**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

Verify:
```bash
aws --version
```

### 2. AWS Credentials
Configure your AWS credentials before running the script.

**Option A — AWS SSO (recommended for org accounts):**
```bash
aws configure sso
aws sso login --profile <your-profile>
export AWS_PROFILE=<your-profile>
```

**Option B — Access keys:**
```bash
aws configure
# Enter: AWS Access Key ID, Secret Access Key, default region, output format
```

Verify credentials are working:
```bash
aws sts get-caller-identity
```

### 3. Python3
Required for S3 bucket cleanup operations.

**macOS:** comes pre-installed. Verify with `python3 --version`

**Linux:**
```bash
sudo apt install python3      # Debian/Ubuntu
sudo yum install python3      # Amazon Linux / RHEL
```

---

## How to Run

Unzip the folder, open a terminal inside the `benchmark/fixtures` directory, and run:

```bash
chmod +x deploy.sh
./deploy.sh
```

The script is fully interactive — it will guide you through every step.

---

## Menu Options

| Option | Description |
|--------|-------------|
| 1 | Deploy Compliant stacks to a selected region |
| 2 | Deploy Non-Compliant stacks to a selected region |
| 3 | Deploy Compliant + Non-Compliant combined in the same region |
| 4 | Cleanup all WAFR stacks from one or more regions |

---

## Deployment Behaviour

- **Auto-cleanup before deploy**: If leftover WAFR stacks are found in the selected region from a previous run, they are automatically cleaned up before deploying fresh.
- **Parallel deployment**: Independent stacks deploy simultaneously. Only VPC-dependent stacks wait for the VPC stack to complete first.
- **Compliant vs Non-Compliant in separate regions** is recommended to keep assessments clean and isolated.
- **Combined mode (option 3)**: Deploys both sets in the same region using one shared VPC. Conflicting account-global resources (IAM password policy, Cost Optimization Hub) default to the compliant version automatically — no manual choices required.

---

## Cleanup Behaviour

- Enter one or more region codes (e.g. `us-east-1` or `us-east-1 eu-west-1`)
- The script auto-discovers all `wafr-comp-*`, `wafr-nc-*`, and `wafr-mix-*` stacks in those regions
- S3 buckets are emptied (including versioned objects and delete markers) before stack deletion
- CloudTrails are stopped before their buckets are emptied
- Stacks are deleted in the correct dependency order — VPC stack is always deleted last
- **No other stacks in your account are touched**

---

## Folder Structure

```
benchmark/fixtures/
├── deploy.sh                ← Main script (run this)
├── README.md                ← This file
├── compliant/               ← 14 compliant CFN templates
└── non_compliant/           ← 14 non-compliant CFN templates
```

---

## Required AWS Permissions

The IAM identity running this script needs permissions for:
- CloudFormation (full access)
- IAM (create/delete users, roles, policies, access keys)
- S3 (create/delete buckets, objects)
- Lambda (create/delete functions)
- EC2 / VPC (create/delete VPCs, subnets, security groups, NACLs)
- KMS (create/delete keys)
- CloudWatch / CloudTrail / SNS / SQS / DynamoDB / ECR / API Gateway / Budgets

Using `AdministratorAccess` or an equivalent broad policy is simplest for a test environment.
