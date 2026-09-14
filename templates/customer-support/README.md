# Customer Support

Answers customer questions from a knowledge base, notices frustration, and
opens tickets for anything it can't resolve.

| Tool | What it does |
|---|---|
| `search_knowledge_base` | Searches `KNOWLEDGE_BASE_URL`, or a built-in sample of five help articles |
| `analyze_sentiment` | Positive / neutral / negative / frustrated |
| `create_ticket` | Routes to a team and POSTs the ticket to `TICKET_WEBHOOK_URL` if set |

Works with no configuration beyond an LLM key. Optional environment variables
are described in [`agent.yaml`](agent.yaml).

## Deploy

```bash
curl -X POST https://agntapi.agntspark.com/v1/agents \
  -H "Authorization: Bearer $AGNTSPARK_API_KEY" -H 'content-type: application/json' \
  -d '{
    "name": "support",
    "model": "gpt-4o",
    "api_key": "'"$OPENAI_API_KEY"'",
    "deploy": {"image": "agntspark/template-customer-support:latest"}
  }'
```

The response's `url` is your agent. Any model works — pass the matching
provider's key as `api_key` (e.g. `claude-sonnet-4-5` with an Anthropic key).

## Talk to it

```bash
curl -X POST https://<your-agent>.run.agntspark.com/invoke \
  -H 'content-type: application/json' \
  -d '{"input": "I was charged twice for my subscription this month."}'
```

Send the returned `session_id` with the next message to continue the
conversation.
