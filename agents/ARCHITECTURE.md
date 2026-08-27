# Agent Architecture

Each agent follows the same pattern. This diagram shows one agent (EOA — EC2 Optimization).

---

## Request Flow

```
You
 │
 │  python3 chat.py  (or curl / invoke_remote.py)
 │
 ▼
╔══════════════════════════════════════════════════════════╗
║              API Gateway HTTP API                        ║
║                                                          ║
║   POST /chat          →   Dispatcher Lambda (30s)        ║
║   GET  /result/{id}   →   Poller Lambda    (10s)         ║
╚══════════════════════════════════════════════════════════╝
          │                          ▲
          │ fire & forget             │ poll every 3s
          ▼                          │
╔══════════════════════════════════════════════════════════╗
║              Agent Lambda  (up to 15 min)                ║
║                                                          ║
║   ┌─────────────────────────────────────────────────┐   ║
║   │  Strands Agents SDK  (agentic loop)             │   ║
║   │                                                 │   ║
║   │   Claude Sonnet 4  ◄──────────────────────────┐ │   ║
║   │   (Amazon Bedrock)                            │ │   ║
║   │         │                                     │ │   ║
║   │         │  tool call                          │ │   ║
║   │         ▼                                     │ │   ║
║   │   AWS MCP Server  ──► AWS APIs                │ │   ║
║   │   (remote, SigV4)     EC2, CloudWatch,        │ │   ║
║   │                       Pricing, IAM…           │ │   ║
║   │         │                                     │ │   ║
║   │         └─────── result ─────────────────────►┘ │   ║
║   └─────────────────────────────────────────────────┘   ║
║                         │                               ║
║          write progress + final result                  ║
╚══════════════════════════════════════════════════════════╝
                          │
                          ▼
╔══════════════════════════════════════════════════════════╗
║              DynamoDB  (eoa-jobs)                        ║
║                                                          ║
║   jobId  │ status  │ progress           │ response       ║
║   ──────────────────────────────────────────────────     ║
║   abc123 │ pending │ ["Calling: aws…"]  │ ""             ║
║   abc123 │ done    │ ["Calling: aws…"]  │ "Found 3…"     ║
║                                                          ║
║   TTL = 1 hour  →  auto-deleted, no cleanup needed       ║
╚══════════════════════════════════════════════════════════╝
```

---

## Why Async?

API Gateway has a **29-second timeout**. A full agent scan takes **60–120 seconds**.

The solution:

```
Client  ──POST /chat──►  Dispatcher  ──► returns jobId in <1s
                              │
                              └──► triggers Agent Lambda async
                                        (runs in background, up to 15 min)

Client  ──GET /result/{id}──►  Poller  ──► reads DynamoDB  ──► returns status
         (every 3 seconds)
```

---

## AWS Resources Per Agent

| Resource | Name (example: eoa) |
|---|---|
| API Gateway | `eoa-api` |
| Lambda — Dispatcher | `eoa-dispatcher` |
| Lambda — Agent | `eoa-agent` |
| Lambda — Poller | `eoa-poller` |
| DynamoDB | `eoa-jobs` |
| IAM Role | `eoa-lambda-role` |
| Bearer Token | Secrets Manager: `eoa/bearer-token` |

All four agents (`s3soa`, `soa`, `eoa`, `poa`) are fully independent — separate endpoints, separate tokens, separate AWS resources.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent framework | [Strands Agents SDK](https://github.com/strands-agents/sdk-python) (AWS open source) |
| LLM | Claude Sonnet 4 via Amazon Bedrock |
| AWS API access | [AWS MCP Server](https://aws.amazon.com/blogs/aws/the-aws-mcp-server-is-now-generally-available/) (managed remote, SigV4) |
| Compute | AWS Lambda (Python 3.12) |
| API | API Gateway HTTP API |
| State | DynamoDB (TTL = 1 hour) |
| Auth | Bearer token in Secrets Manager |
| IaC | CloudFormation |
