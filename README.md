# AgntSpark Templates

Official agent templates for the AgntSpark platform. Each is a small
directory — a manifest, a few tool functions and a README — that runs on the
platform's agent runtime image and gets its own HTTPS URL.

| Template | What it does | Default model |
|---|---|---|
| [customer-support](templates/customer-support/) | Answers from a knowledge base, notices frustration, opens tickets | `gpt-4o` |
| [code-reviewer](templates/code-reviewer/) | Reviews GitHub pull requests and pasted code | `claude-sonnet-4-5` |

Any model works: choose one when you deploy and pass that provider's key.

## Deploy a template

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

The response's `url` is the agent, and `access_key` is its first access key
(new agents are private; the key is only returned here). Talk to it:

```bash
curl -X POST https://<your-agent>.run.agntspark.com/invoke \
  -H "Authorization: Bearer <access_key>" \
  -H 'content-type: application/json' -d '{"input": "How do I reset my password?"}'
```

## How templates run

Every hosted agent speaks runtime contract v1 — `GET /health`,
`POST /invoke {"input", "session_id"?}` — served by
[agntspark-core](https://github.com/AgntSpark1/agntspark-core)'s
`agntspark/agent-runtime` image (see its README for the full contract). A
template adds only what makes the agent useful:

```
templates/<name>/
├── agent.yaml         # prompt, default model, tools, env vars (template.schema.json)
├── tools.py           # tool functions: called with keyword args, return text/JSON
├── requirements.txt   # extra pip packages, if any
└── README.md
```

The [`Dockerfile`](Dockerfile) builds `agntspark/template-<name>` on top of the
runtime image by copying the directory to `/template`.

## Develop

```bash
pip install "agntspark-core[llm,server] @ git+https://github.com/AgntSpark1/agntspark-core.git" \
  jsonschema pyyaml pytest
pytest

# Run a template locally
AGNTSPARK_TEMPLATE_DIR=templates/customer-support OPENAI_API_KEY=... \
  python -m agntspark_core serve --port 8080

# Build images (runtime image first, from an agntspark-core checkout)
docker build -t agntspark/agent-runtime:latest ../agntspark-core
docker build --build-arg TEMPLATE=customer-support -t agntspark/template-customer-support:latest .
```

## Adding a template

1. Create `templates/<name>/` with `agent.yaml`, `tools.py`, `requirements.txt`
   and `README.md`; `name` in the manifest must match the directory.
2. Keep tools deterministic and safe to call repeatedly; return JSON strings
   and report failures in the result instead of raising.
3. Add offline tests for the tools in `tests/`.
4. `pytest` must pass; CI also builds every template image.

The earlier data-analyst, content-generator and research-assistant drafts
predate the runtime contract and were removed; they remain in git history
(commit `8ac5cad`) for porting.

## License

MIT — © 2026 AgntSpark LLC
