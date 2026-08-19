# AgntSpark Templates

Pre-built AI agent templates for common business use cases. Deploy in minutes, customize as needed.

## Available Templates

| Template | Use Case | LLM Provider | Framework |
|----------|----------|-------------|-----------|
| [Customer Support](templates/customer-support/) | Handle customer inquiries, route tickets, answer FAQs | OpenAI GPT-4o | AgntSpark Core |
| [Code Reviewer](templates/code-reviewer/) | Review PRs, find bugs, check security, enforce style | Anthropic Claude | AgntSpark Core |
| [Data Analyst](templates/data-analyst/) | Query databases, generate insights, visual reports | OpenAI GPT-4o | AgntSpark Core |
| [Content Writer](templates/content-writer/) | Research, draft, and SEO-optimize long-form content | Anthropic Claude | AgntSpark Core |

## Quick Start

```bash
# Install AgntSpark SDK
pip install agntspark

# Use a template
agntspark init --template customer-support my-support-agent
cd my-support-agent
agntspark deploy
```

## Template Structure

```
templates/
├── customer-support/
│   └── agent.py          # Agent definition with tools
├── code-reviewer/
│   └── agent.py
├── data-analyst/
│   └── agent.py
└── content-writer/
    └── agent.py
```

## Customization

Each template is a starting point. You can:
- Swap the LLM provider (OpenAI ↔ Anthropic ↔ Google)
- Add custom tools via the `@agent.tool()` decorator
- Adjust temperature and token limits
- Enable/disable conversation memory
- Set memory TTL for context retention

## Contributing

To contribute a new template:

1. Create a directory under `templates/`
2. Add an `agent.py` with the agent definition
3. Add a `README.md` describing the use case
4. Submit a PR

## License

MIT — © 2026 AgntSpark LLC
