# Customer Support Agent Template

An AI-powered customer support agent that handles customer inquiries with knowledge base lookup, intelligent ticket routing, and real-time sentiment analysis.

## Features

- **Knowledge Base Search** — Searches an internal KB API for relevant articles before responding. Falls back to a built-in keyword-based search if the KB API is unavailable.
- **Sentiment Analysis** — Analyzes customer messages for sentiment (positive, neutral, negative, frustrated) using keyword matching, punctuation analysis, and caps-ratio detection.
- **Ticket Creation & Routing** — Automatically creates support tickets for issues that can't be resolved from the knowledge base or when the customer is frustrated. Routes tickets to the appropriate team (technical, billing, account, product, general).
- **Conversation Context** — Maintains conversation history for context-aware responses and handoff summaries.
- **Graceful Degradation** — All external API calls have fallback logic so the agent continues functioning even if backend services are down.

## Configuration

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key for LLM calls | Required in production |
| `KNOWLEDGE_BASE_URL` | Knowledge base API URL | `http://localhost:8001` |
| `KNOWLEDGE_BASE_API_KEY` | KB API authentication key | `dev-key` |
| `TICKETING_SYSTEM_URL` | Ticketing system API URL | `http://localhost:8002` |
| `TICKETING_API_KEY` | Ticketing API key | `dev-key` |
| `CUSTOMER_DB_URL` | Customer database API URL | `http://localhost:8003` |

### LLM Settings

- **Provider:** OpenAI
- **Model:** gpt-4o
- **Temperature:** 0.3 (low, for consistent support responses)
- **Max Tokens:** 4096

## Usage

### Run in Test Mode

```bash
pip install -r requirements.txt
python agent.py
```

This runs the agent with sample customer interactions and prints responses, sentiment analysis, and ticket creation results.

### Deploy with AgntSpark

```bash
agntspark deploy --template ./customer-support
```

### Programmatic Usage

```python
from agent import CustomerSupportAgent

agent = CustomerSupportAgent()
result = agent.handle_message("CUST-001", "I can't reset my password!")
print(result["response"])
print(result["sentiment"])
```

## Tools

| Tool | Description |
|---|---|
| `search_knowledge_base` | Search internal KB for articles matching a query |
| `analyze_sentiment` | Analyze message sentiment (positive/neutral/negative/frustrated) |
| `create_ticket` | Create a support ticket with category and priority |
| `route_ticket` | Route ticket to appropriate team based on category |
| `get_customer_history` | Retrieve customer interaction history |

## Ticket Categories

| Category | Trigger Keywords |
|---|---|
| Technical | api, bug, error, crash, timeout, integration |
| Billing | bill, invoice, charge, refund, payment, subscription |
| Account | login, password, access, account, 2fa |
| Product | feature, request, roadmap, enhancement |
| General | (fallback) |
