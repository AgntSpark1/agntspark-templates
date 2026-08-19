# Code Reviewer Agent Template

An AI agent that reviews GitHub pull requests, detects bugs and security vulnerabilities, and posts actionable feedback.

## Features

- **PR Diff Fetching** — Fetches and parses pull request diffs from the GitHub API, extracting added/removed lines per file.
- **Bug Detection** — Pattern-based detection of common bugs: bare excepts, silent exception swallowing, `== None` comparisons, file handle leaks, mutable default arguments.
- **Security Scanning** — Detects security vulnerabilities: `eval()`, `exec()`, shell injection, hardcoded secrets, SQL injection via string concatenation, disabled SSL verification, XSS vectors.
- **Code Quality Checks** — Flags print statements in production, TODO/FIXME/HACK comments.
- **Test Coverage Gap** — Identifies changed source files without corresponding test files.
- **GitHub Review Posting** — Posts structured reviews to GitHub PRs with inline comments, approve/request changes events, and a formatted markdown summary table.

## Configuration

### Environment Variables

| Variable | Description | Required |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key for LLM calls | Yes (production) |
| `GITHUB_TOKEN` | GitHub personal access token for API calls | Yes |
| `GITHUB_WEBHOOK_SECRET` | Webhook secret for verifying GitHub events | Optional |

### LLM Settings

- **Provider:** OpenAI
- **Model:** gpt-4o
- **Temperature:** 0.1 (very low, for consistent reviews)
- **Max Tokens:** 8192

## Usage

### Run in Test Mode

```bash
pip install -r requirements.txt
python agent.py
```

Runs the agent against a sample code diff containing intentional bugs and security issues, demonstrating all detection rules.

### Deploy with AgntSpark

```bash
agntspark deploy --template ./code-reviewer
```

### Programmatic Usage

```python
from agent import CodeReviewerAgent

agent = CodeReviewerAgent()
result = agent.review_pr("owner/repo", 142)
print(f"Blocking: {result['blocking_count']}, Warnings: {result['warning_count']}")
```

## Detection Rules

### Security Rules

| Rule ID | Description | Severity |
|---|---|---|
| SEC001 | `eval()` usage | Blocking |
| SEC002 | `exec()` usage | Blocking |
| SEC003 | `subprocess` with `shell=True` | Blocking |
| SEC004 | `os.system()` usage | Blocking |
| SEC005 | `pickle.load/loads()` on untrusted data | Blocking |
| SEC006 | `yaml.load()` instead of `safe_load()` | Warning |
| SEC007 | Hardcoded secrets/credentials | Blocking |
| SEC008 | SQL injection via string concatenation | Blocking |
| SEC009 | SSL verification disabled | Blocking |
| SEC010 | Direct `innerHTML` assignment (XSS) | Warning |

### Bug Rules

| Rule ID | Description | Severity |
|---|---|---|
| BUG001 | Bare `except:` clause | Warning |
| BUG002 | Silent exception swallowing | Warning |
| BUG003 | `== None/True/False` instead of `is` | Suggestion |
| BUG004 | File opened without `with` | Warning |
| BUG005/006 | Mutable default arguments | Warning |
| BUG007 | Assert used for validation | Suggestion |
