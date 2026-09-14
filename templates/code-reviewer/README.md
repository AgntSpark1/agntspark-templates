# Code Reviewer

Reviews GitHub pull requests or pasted code: fetches the diff, runs quick
security / bug / quality checks, and writes a prioritized review with a
verdict.

| Tool | What it does |
|---|---|
| `review_pull_request` | Title, description, changed files, diff (first 60k characters) and automated findings for `owner/repo#number` |
| `scan_code` | The same checks on a pasted snippet |

The checks are regex heuristics (eval/exec, shell injection, hardcoded
secrets, SQL string building, disabled TLS verification, bare except, …);
the model is told to confirm each against the code rather than repeat them.

Set `GITHUB_TOKEN` (read access to pull requests) for private repositories.
Public repositories work without it, at GitHub's lower anonymous rate limit.

## Deploy

```bash
curl -X POST https://agntapi.agntspark.com/v1/agents \
  -H "Authorization: Bearer $AGNTSPARK_API_KEY" -H 'content-type: application/json' \
  -d '{
    "name": "reviewer",
    "model": "claude-sonnet-4-5",
    "api_key": "'"$ANTHROPIC_API_KEY"'",
    "deploy": {
      "image": "agntspark/template-code-reviewer:latest",
      "env": [{"key": "GITHUB_TOKEN", "value": "'"$GITHUB_TOKEN"'", "secret": true}]
    }
  }'
```

## Talk to it

```bash
curl -X POST https://<your-agent>.run.agntspark.com/invoke \
  -H 'content-type: application/json' \
  -d '{"input": "Review https://github.com/owner/repo/pull/123"}'
```
