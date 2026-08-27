# AWS Bedrock Agents Platform

Four AI-powered cloud operations agents built on:
- **[Strands Agents SDK](https://github.com/strands-agents/sdk-python)** — open-sourced by AWS, manages the agentic loop
- **Amazon Bedrock** — Claude Sonnet 4 as the LLM
- **[AWS API MCP Server](https://awslabs.github.io/mcp/servers/aws-api-mcp-server)** — gives the agent access to all AWS APIs

Each agent is a fully independent Lambda function with its own HTTPS endpoint, bearer token, and IAM policy scoped to only what it needs.

---

## The Agents

| Agent | What it does | Scope |
|-------|-------------|-------|
| **S3SOA** — S3 Security Optimization | Scans every S3 bucket for public access, missing encryption, absent logging, ACL issues. Remediates after approval. | S3 only |
| **SOA** — Storage Optimization | Finds unattached EBS volumes, stale snapshots (>90 days), orphaned AMIs. Estimates monthly cost. Deletes after approval. | EC2 storage |
| **EOA** — EC2 Optimization | Pulls 14-day CPU metrics, identifies over-provisioned instances, recommends right-sizing with projected savings. Resizes after approval. | EC2 compute |
| **POA** — Processor Optimization | Inventories Intel/AMD/Graviton across all instances. Recommends Graviton migration paths with cost savings. Migrates after approval. | EC2 processor |

---

## How it works

```
You (curl / Python / invoke_remote.py)
    │
    │  POST  Authorization: Bearer <token>
    │  Body: { "prompt": "scan my account", "messages": [] }
    ▼
Lambda Function URL  (public HTTPS, streaming, 15-min timeout)
    │
    ├── Validates Bearer token  ←── Secrets Manager
    ├── Strands Agent (agentic loop)
    │       ├── Claude Sonnet 4 on Bedrock  (reasoning)
    │       └── AWS API MCP Server          (executes AWS CLI commands)
    │
    └── Streams back:
            {"type":"tool",  "name":"call_aws"}   ← live progress
            {"type":"text",  "text":"I found..."}  ← response tokens
            {"type":"done",  "elapsed":42.1, "messages":[...]}
```

Each agent has its own Lambda, IAM role, and Secrets Manager secret — fully isolated.

---

## Prerequisites

Before you start, make sure you have:

| Requirement | Check |
|---|---|
| AWS CLI v2 | `aws --version` |
| Python 3.10+ | `python3 --version` |
| pip3 | `pip3 --version` |
| zip | `zip --version` |
| AWS credentials configured | `aws sts get-caller-identity` |
| Claude Sonnet 4 enabled in Bedrock | See Step 2 |

---

## Step 1 — Configure AWS credentials

```bash
# Option A — SSO (recommended for teams)
aws sso login --profile your-profile
export AWS_PROFILE=your-profile

# Option B — static credentials
aws configure
```

Verify it works:
```bash
aws sts get-caller-identity
```
You should see your Account ID and ARN printed.

---

## Step 2 — Enable Claude Sonnet 4 in Bedrock

This is a one-time step per AWS account.

1. Open [Bedrock Model Access](https://console.aws.amazon.com/bedrock/home#/modelaccess)
2. Click **Manage model access**
3. Find **Claude Sonnet 4** under Anthropic and check it
4. Click **Save changes** — takes about 1 minute to activate

Verify:
```bash
aws bedrock list-inference-profiles --region us-east-1 \
  --query "inferenceProfileSummaries[?inferenceProfileId=='us.anthropic.claude-sonnet-4-6'].status" \
  --output text
```
Expected output: `ACTIVE`

---

## Step 3 — Deploy

```bash
chmod +x deploy.sh cleanup.sh
./deploy.sh
```

The script shows an interactive menu. You can deploy one, several, or all agents in a single run:

```
  Which agent(s) do you want to deploy?

  1) s3soa — S3 Security Optimization Agent
  2) soa   — Storage Optimization Agent
  3) eoa   — EC2 Optimization Agent
  4) poa   — Processor Optimization Agent
  5) all   — Deploy all four agents

  Enter number(s) or name(s), space-separated [e.g. 1 3 or s3soa eoa]:
```

**Examples:**
- Enter `1` → deploys S3SOA only
- Enter `1 3` → deploys S3SOA and EOA
- Enter `5` or `all` → deploys all four

Or skip the menu entirely with flags:
```bash
./deploy.sh --agent s3soa                    # one agent
./deploy.sh --agent s3soa --agent soa        # two agents
./deploy.sh --all                            # all four
./deploy.sh --all --region eu-west-1         # all four in EU
```

**What the script does for each agent:**
1. Creates a private S3 bucket for the Lambda deployment zip
2. Installs Python dependencies and packages the Lambda zip
3. Uploads the zip to S3
4. Deploys a CloudFormation stack (Lambda + IAM role + Secrets Manager secret + Function URL)
5. Fetches the bearer token from Secrets Manager
6. Writes `AGENT_URL` and `AGENT_TOKEN` to `.env.<agent>`

**What gets created per agent:**

| Resource | Name |
|----------|------|
| CloudFormation stack | `s3soa` / `soa` / `eoa` / `poa` |
| Lambda function | `s3soa-agent` / `soa-agent` / `eoa-agent` / `poa-agent` |
| IAM role | `s3soa-lambda-role` / etc. |
| Secrets Manager secret | `s3soa/bearer-token` / etc. |
| S3 deployment bucket | `s3soa-deploy-<account-id>` / etc. |

**Expected output (deploying all four):**
```
  Agents  : eoa poa s3soa soa
  Region  : us-east-1

▶  Checking prerequisites...
  ✓ aws, python3, pip3, zip
  ✓ AWS credentials valid (account: 559271155384)
▶  Checking Bedrock model access...
  ✓ Claude Sonnet 4 (us.anthropic.claude-sonnet-4-6) is ACTIVE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Deploying: s3soa  →  stack: s3soa  →  region: us-east-1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶  Setting up deployment bucket: s3soa-deploy-559271155384
  ✓ Bucket created (public access blocked)
▶  Building Lambda package...
  ✓ Package built (45M)
▶  Uploading to s3://s3soa-deploy-559271155384/s3soa/lambda.zip...
  ✓ Uploaded
▶  Deploying CloudFormation stack 's3soa'...
  ✓ Stack deployed
▶  Fetching endpoint and bearer token...
  ✓ Credentials saved to .env.s3soa

  Lambda function : s3soa-agent
  Endpoint        : https://abc123.lambda-url.us-east-1.on.aws/
  Token           : xK9mP2qR...

[ ... repeats for soa, eoa, poa ... ]

╔══════════════════════════════════════════════════════════════╗
║                  Deployment Complete ✓                      ║
╚══════════════════════════════════════════════════════════════╝

  s3soa
    Endpoint : https://abc123.lambda-url.us-east-1.on.aws/
    Token    : xK9mP2qR...
    Env file : .env.s3soa

  soa
    Endpoint : https://def456.lambda-url.us-east-1.on.aws/
    Token    : yL0nQ3rS...
    Env file : .env.soa
  ...
```

---

## Step 4 — Get your endpoint and token

After deployment, each agent's credentials are in its own `.env` file:

```bash
cat .env.s3soa
# AGENT_URL=https://abc123.lambda-url.us-east-1.on.aws/
# AGENT_TOKEN=xK9mP2qR...

cat .env.soa
# AGENT_URL=https://def456.lambda-url.us-east-1.on.aws/
# AGENT_TOKEN=yL0nQ3rS...
```

To retrieve a token at any time (e.g. to share with another team, or after credentials expire):

```bash
# Replace 's3soa' with the agent name you want
SECRET_ARN=$(aws cloudformation describe-stacks \
  --stack-name s3soa --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='BearerTokenSecretArn'].OutputValue" \
  --output text)

aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ARN" --region us-east-1 \
  --query SecretString --output text \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])"
```

**Share with external teams:** Give them the `AGENT_URL` and `AGENT_TOKEN` for the agent(s) they need access to, along with `TESTING_GUIDE.md`. Each agent has its own token — you can revoke one without affecting the others.

To rotate a token (revoke old access):
```bash
aws secretsmanager rotate-secret \
  --secret-id s3soa/bearer-token --region us-east-1
```

---

## Step 5 — Test locally with the interactive CLI

```bash
pip3 install requests rich
python3 invoke_remote.py
```

Shows a menu of deployed agents (marked with ✓):

```
  Select an agent:

  1) 🔒  S3 Security Optimization Agent  (s3soa)  ✓
  2) 💾  Storage Optimization Agent      (soa)    ✓
  3) ⚡  EC2 Optimization Agent          (eoa)    ✓
  4) 🔧  Processor Optimization Agent   (poa)    ✓

  Enter number or agent name:
```

Then use shortcuts or free-form questions:

```
You> scan          ← runs the full security scan
You> fix           ← remediates findings (confirms before each change)
You> report        ← generates a markdown report
You> how many S3 buckets do I have?   ← any free-form question
You> quit
```

Jump directly to a specific agent:
```bash
python3 invoke_remote.py --env .env.soa
python3 invoke_remote.py --env .env.eoa
```

---

## Step 6 — Test via direct API call

```bash
# Set credentials for the agent you want to test
export AGENT_URL="https://abc123.lambda-url.us-east-1.on.aws/"
export AGENT_TOKEN="xK9mP2qR..."

# Send a prompt
curl -X POST "$AGENT_URL" \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "scan my account for security issues", "messages": []}' \
  --no-buffer
```

You'll see the response stream in real time:
```json
{"type": "tool", "name": "call_aws"}
{"type": "tool", "name": "call_aws"}
{"type": "text", "text": "I found 2 issues in your account:\n\n"}
{"type": "text", "text": "| ID | Resource | Issue | Severity |\n"}
{"type": "done", "elapsed": 42.1, "messages": [...]}
```

See **[TESTING_GUIDE.md](TESTING_GUIDE.md)** for full curl examples per agent, Python integration code, Postman setup, and multi-turn conversation examples.

---

## Step 7 — Clean up

To remove a deployed agent and all its AWS resources:

```bash
./cleanup.sh
```

Same interactive menu as deploy — select one, several, or all. The script shows exactly what will be deleted and requires you to type `yes` before touching anything.

What gets removed per agent:
- CloudFormation stack (Lambda, IAM role, Secrets Manager secret, Function URL)
- S3 deployment bucket (emptied first, then deleted)
- Local `.env.<agent>` file

```bash
./cleanup.sh --agent s3soa          # remove one
./cleanup.sh --agent s3soa --agent soa  # remove two
./cleanup.sh --all                  # remove all four
```

---

## API reference

### Request format

```
POST <AGENT_URL>
Authorization: Bearer <AGENT_TOKEN>
Content-Type: application/json

{
  "prompt":   "your question or instruction",
  "messages": []
}
```

For multi-turn conversations, pass the `messages` array from the previous `done` event back in the next request.

### Response stream (newline-delimited JSON)

| Event type | Fields | What it means |
|---|---|---|
| `tool` | `name` | Agent is calling an AWS API right now |
| `text` | `text` | One token of Claude's response — concatenate all of these |
| `done` | `elapsed`, `messages` | Agent finished — save `messages` for the next turn |
| `error` | `message` | Something went wrong |

### HTTP status codes

| Code | Meaning |
|---|---|
| `200` | Success — consume the stream |
| `401` | Invalid or missing Bearer token |
| `400` | Missing `prompt` field or invalid JSON body |

---

## Project structure

```
.
├── deploy.sh              ← deploy one, many, or all agents
├── cleanup.sh             ← remove one, many, or all agents + their AWS resources
├── invoke_remote.py       ← interactive CLI to chat with any deployed agent
├── agent.py               ← local CLI (no deployment needed — runs on your machine)
├── requirements.txt       ← dependencies for agent.py (local CLI only)
├── README.md              ← this file (deployer guide)
├── TESTING_GUIDE.md       ← share with external teams for API testing
│
├── s3soa/                 ── S3 Security Optimization Agent
│   ├── agent/
│   │   ├── handler.py     ← Lambda handler + system prompt
│   │   └── requirements.txt
│   └── cloudformation.yaml
│
├── soa/                   ── Storage Optimization Agent
│   ├── agent/
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── cloudformation.yaml
│
├── eoa/                   ── EC2 Optimization Agent
│   ├── agent/
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── cloudformation.yaml
│
└── poa/                   ── Processor Optimization Agent
    ├── agent/
    │   ├── handler.py
    │   └── requirements.txt
    └── cloudformation.yaml
```

Credential files written by `deploy.sh`:
```
.env.s3soa   AGENT_URL + AGENT_TOKEN for S3SOA
.env.soa     AGENT_URL + AGENT_TOKEN for SOA
.env.eoa     AGENT_URL + AGENT_TOKEN for EOA
.env.poa     AGENT_URL + AGENT_TOKEN for POA
```

---

## Troubleshooting

**`ExpiredTokenException` — credentials expired**
```bash
aws sso login --profile your-profile
```

**`401 Unauthorized` from the API**

Your token is wrong or the `.env` file is stale. Re-fetch it:
```bash
SECRET_ARN=$(aws cloudformation describe-stacks \
  --stack-name s3soa --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='BearerTokenSecretArn'].OutputValue" \
  --output text)
aws secretsmanager get-secret-value --secret-id "$SECRET_ARN" \
  --query SecretString --output text \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])"
```

**`ValidationException: model not found`**
- Enable Claude Sonnet 4 in [Bedrock Model Access](https://console.aws.amazon.com/bedrock/home#/modelaccess)
- If deploying outside `us-*` regions, the model ID prefix changes. Set `BedrockModelId` parameter in CloudFormation to `eu.anthropic.claude-sonnet-4-6`

**Agent takes 60-120 seconds to respond**

This is normal for a full scan — the agent makes many AWS API calls across multiple regions. You should see `{"type":"tool","name":"call_aws"}` events streaming in while it works. If nothing appears for 30+ seconds, retry.

**`No MCP tools loaded` error**

The Lambda package is missing the MCP server. Redeploy:
```bash
./deploy.sh --agent <name>
```

**Check Lambda logs**
```bash
aws logs tail /aws/lambda/s3soa-agent --follow --region us-east-1
# Replace s3soa with soa, eoa, or poa as needed
```

**CloudFormation stack stuck in `_IN_PROGRESS`**

Check the AWS Console → CloudFormation → Events tab for the stack. Common cause: IAM role name conflict if you previously deployed with a different stack name.
