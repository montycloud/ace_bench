# Testing Guide — AWS Bedrock Agents

This guide is for teams testing the agents via API. No special tools or SDKs needed — just curl, Python, or Postman.

---

## What you need

The team that deployed the agents will give you two values per agent:

| Value | Example |
|-------|---------|
| `AGENT_URL` | `https://abc123.lambda-url.us-east-1.on.aws/` |
| `AGENT_TOKEN` | `xK9mP2qR...` |

Each agent has its own URL and token. Keep the token private — it's the only thing protecting the endpoint.

---

## The four agents

| Agent | What to ask it |
|-------|---------------|
| **S3SOA** — S3 Security | Scan S3 buckets for public access, encryption, logging, ACL issues |
| **SOA** — Storage | Find unattached EBS volumes, stale snapshots, orphaned AMIs with cost estimates |
| **EOA** — EC2 Optimization | Analyze CPU utilization, identify underutilized instances, recommend right-sizing |
| **POA** — Processor | Inventory Intel/AMD/Graviton instances, recommend Graviton migration with savings |

Each agent is scoped — S3SOA only does S3 security, SOA only does storage, etc. Asking an agent to do something outside its scope will get a polite decline.

---

## How the API works

Every agent uses the same format.

**Request:**
```
POST <AGENT_URL>
Authorization: Bearer <AGENT_TOKEN>
Content-Type: application/json

{
  "prompt":   "your question or instruction",
  "messages": []
}
```

**Response** — a stream of newline-delimited JSON, one event per line:

```
{"type": "tool",  "name": "call_aws"}
{"type": "tool",  "name": "call_aws"}
{"type": "text",  "text": "I found 2 issues in your account:\n\n"}
{"type": "text",  "text": "| ID | Resource | Issue | Severity |\n"}
{"type": "text",  "text": "|----|-----------..."}
{"type": "done",  "elapsed": 42.1, "messages": [...]}
```

- `tool` events appear while the agent is calling AWS APIs — this is live progress
- `text` events are Claude's response, one token at a time — concatenate them for the full text
- `done` signals the agent is finished — the `messages` array is the conversation history
- `error` means something went wrong

---

## Quick start — curl

Set your credentials:
```bash
export AGENT_URL="https://abc123.lambda-url.us-east-1.on.aws/"
export AGENT_TOKEN="xK9mP2qR..."
```

Send a prompt:
```bash
curl -X POST "$AGENT_URL" \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "scan my account", "messages": []}' \
  --no-buffer
```

> `--no-buffer` is required — without it curl buffers the response and you won't see streaming.

---

## Prompts to try per agent

### S3SOA — S3 Security Optimization

```bash
# Full security scan
curl -X POST "$AGENT_URL" \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Scan all my S3 buckets for security issues. Show a findings table with ID, bucket name, issue, severity, and recommended fix.", "messages": []}' \
  --no-buffer

# Specific check
curl -X POST "$AGENT_URL" \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Which S3 buckets have public access block settings disabled?", "messages": []}' \
  --no-buffer

# Scope test — should decline
curl -X POST "$AGENT_URL" \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Resize my EC2 instances to save cost.", "messages": []}' \
  --no-buffer
```

### SOA — Storage Optimization

```bash
# Full storage scan
curl -X POST "$AGENT_URL" \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Scan my account for storage waste: unattached EBS volumes, stale snapshots older than 90 days, and orphaned AMIs. Show estimated monthly cost for each.", "messages": []}' \
  --no-buffer

# Cost focus
curl -X POST "$AGENT_URL" \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "How much am I spending on unattached EBS volumes each month?", "messages": []}' \
  --no-buffer
```

### EOA — EC2 Optimization

```bash
# Full utilization analysis
curl -X POST "$AGENT_URL" \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Analyze all running EC2 instances over the last 14 days. Identify underutilized ones (avg CPU below 10%) and recommend right-sized alternatives with projected monthly savings.", "messages": []}' \
  --no-buffer

# Stopped instances
curl -X POST "$AGENT_URL" \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "List all stopped EC2 instances that have been stopped for more than 30 days.", "messages": []}' \
  --no-buffer
```

### POA — Processor Optimization

```bash
# Full processor inventory
curl -X POST "$AGENT_URL" \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Inventory all running EC2 instances by processor architecture (Intel, AMD, Graviton). Which ones are eligible for Graviton migration and what would I save?", "messages": []}' \
  --no-buffer

# Architecture breakdown
curl -X POST "$AGENT_URL" \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What percentage of my EC2 instances are already on Graviton?", "messages": []}' \
  --no-buffer
```

---

## Multi-turn conversations

Pass the `messages` array from the `done` event back in your next request to continue the conversation. The agent remembers everything from the previous turn.

**Python example (easiest way to handle multi-turn):**

```python
import json
import requests

AGENT_URL   = "https://abc123.lambda-url.us-east-1.on.aws/"
AGENT_TOKEN = "xK9mP2qR..."

def ask(prompt, messages=[]):
    """Send a prompt, print the response live, return updated messages."""
    updated_messages = messages

    with requests.post(
        AGENT_URL,
        headers={
            "Authorization": f"Bearer {AGENT_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"prompt": prompt, "messages": messages},
        stream=True,
        timeout=(30, 900),
    ) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            event = json.loads(line)
            if event["type"] == "text":
                print(event["text"], end="", flush=True)
            elif event["type"] == "tool":
                print(f"\n  [calling {event['name']}...]", flush=True)
            elif event["type"] == "done":
                updated_messages = event.get("messages", messages)
                print(f"\n\n  [{event['elapsed']}s]\n")
            elif event["type"] == "error":
                print(f"\nError: {event['message']}")

    return updated_messages


# Turn 1 — scan
messages = ask("scan my account for security issues")

# Turn 2 — follow up (agent remembers the scan results)
messages = ask("which finding is most critical?", messages)

# Turn 3 — ask for remediation
messages = ask("fix the most critical finding", messages)
```

---

## Testing with Postman

1. Create a new **POST** request
2. **URL:** your `AGENT_URL`
3. **Headers:**
   - `Authorization` → `Bearer xK9mP2qR...`
   - `Content-Type` → `application/json`
4. **Body** → **raw** → **JSON:**
   ```json
   {
     "prompt": "scan my account for security issues",
     "messages": []
   }
   ```
5. Click **Send**

The response body will contain the stream of JSON events. Postman shows them all at once after the response completes (it doesn't render streaming line by line, but all events will be there).

---

## What a good response looks like

**1. Tool calls appear first** — confirms the agent is actually calling AWS APIs:
```json
{"type": "tool", "name": "call_aws"}
{"type": "tool", "name": "call_aws"}
{"type": "tool", "name": "call_aws"}
```

**2. A findings table in the text response:**
```
| ID     | Resource           | Issue                        | Severity | Recommended Fix              |
|--------|--------------------|------------------------------|----------|------------------------------|
| S3-001 | my-old-bucket      | Public access block disabled | HIGH     | Enable all 4 block settings  |
| S3-002 | logs-bucket        | Server-side encryption off   | MEDIUM   | Enable AES-256 encryption    |
```

**3. Scope enforcement** — asking S3SOA to do EC2 work:
```
I'm scoped to S3 security tasks only and can't help with EC2 resizing.
Would you like me to scan your S3 buckets for security issues instead?
```

**4. Confirmation before changes** — if you ask it to fix something:
```
I will make the following change:
  Resource: my-old-bucket
  API call: aws s3api put-public-access-block
  Change:   Enable BlockPublicAcls, IgnorePublicAcls, BlockPublicPolicy, RestrictPublicBuckets
  Effect:   All public access will be blocked on this bucket

Please confirm with yes/ok/proceed to continue.
```

---

## Response timing

| Agent | Typical scan time | Why |
|-------|------------------|-----|
| S3SOA | 30-90 seconds | Checks every bucket across all regions |
| SOA | 30-60 seconds | Describes all snapshots, volumes, AMIs |
| EOA | 60-120 seconds | Pulls CloudWatch metrics per instance |
| POA | 30-60 seconds | Describes instance types and pricing |

You should see `tool` events streaming in throughout — if you see nothing for 30+ seconds, the connection may have dropped. Retry.

---

## Troubleshooting

**`{"type":"error","message":"Unauthorized"}`**

Your token is wrong or expired. Ask the deploying team to re-run `./deploy.sh --agent <name>` and share the new token.

**No events appear / empty response**

- curl: make sure `--no-buffer` is included
- Python: make sure `stream=True` is set in `requests.post()`
- Postman: the response will appear all at once after completion — this is normal

**Response takes longer than 2 minutes**

Something may have gone wrong. Check with the deploying team — they can check Lambda logs:
```bash
aws logs tail /aws/lambda/s3soa-agent --follow --region us-east-1
```

**`{"type":"error","message":"No MCP tools loaded"}`**

The Lambda package needs to be redeployed. Ask the deploying team to run `./deploy.sh --agent <name>`.
