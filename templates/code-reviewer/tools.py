"""Tools for the code-reviewer template.

Each tool returns a JSON string for the model. The pattern checks are
heuristics that point the model at suspicious lines — the model confirms or
discards them. Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

_GITHUB_API = "https://api.github.com"
_HTTP_TIMEOUT = 20
_MAX_DIFF_CHARS = 60_000
_MAX_FINDINGS = 60
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

# (rule, severity, pattern, message, suggestion)
_RULES = [
    ("SEC001", "blocking", r"(?<![\w.])eval\s*\(", "eval() can execute arbitrary code",
     "Use ast.literal_eval() for literals, or avoid dynamic evaluation."),
    ("SEC002", "blocking", r"(?<![\w.])exec\s*\(", "exec() can execute arbitrary code",
     "Avoid executing dynamically built code."),
    ("SEC003", "blocking", r"subprocess\.\w+\([^)]*shell\s*=\s*True", "shell=True allows command injection",
     "Pass the command as a list with shell=False."),
    ("SEC004", "blocking", r"\bos\.system\s*\(", "os.system() allows command injection",
     "Use subprocess.run() with a list of arguments."),
    ("SEC005", "blocking", r"\bpickle\.loads?\s*\(", "Unpickling untrusted data executes code",
     "Use JSON or another safe format for untrusted input."),
    ("SEC006", "warning", r"\byaml\.load\s*\((?![^)]*SafeLoader)", "yaml.load() without SafeLoader",
     "Use yaml.safe_load()."),
    ("SEC007", "blocking", r"(?i)\b(password|passwd|secret|api_key|apikey|token)\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']",
     "Possible hardcoded credential", "Load secrets from the environment or a secrets manager."),
    ("SEC008", "blocking",
     r"(?i)\b(select\b.+\bfrom|insert\s+into|update\s+\w+\s+set|delete\s+from)\b.*([\"']\s*\+|%\s*\(|\.format\(|\{\w+\})",
     "SQL built by string concatenation or formatting", "Use parameterized queries."),
    ("SEC009", "blocking", r"\bverify\s*=\s*False", "TLS certificate verification disabled",
     "Keep verification on and fix the certificate chain instead."),
    ("SEC010", "warning", r"\.innerHTML\s*=", "innerHTML assignment can introduce XSS",
     "Use textContent, or sanitize the HTML first."),
    ("BUG001", "warning", r"^\s*except\s*:", "Bare except also catches SystemExit and KeyboardInterrupt",
     "Catch specific exceptions."),
    ("BUG002", "suggestion", r"(==|!=)\s*None\b", "Comparison to None with == or !=",
     "Use `is None` / `is not None`."),
    ("BUG003", "warning", r"^(?!\s*with\b).*(?<![\w.])open\s*\(", "File opened outside a with-block may leak",
     "Use `with open(...) as f:`."),
    ("BUG004", "warning", r"\bdef\s+\w+\(.*=\s*(\[\]|\{\}|set\(\))", "Mutable default argument is shared between calls",
     "Default to None and create the object inside the function."),
    ("QLT001", "suggestion", r"^\s*print\s*\(", "print() left in the code", "Use logging."),
    ("QLT002", "info", r"#\s*(TODO|FIXME|HACK|XXX)\b", "Unresolved TODO/FIXME marker", ""),
]  # fmt: skip
_COMPILED = [(rule, sev, re.compile(pattern), msg, fix) for rule, sev, pattern, msg, fix in _RULES]
_SEVERITY_ORDER = {"blocking": 0, "warning": 1, "suggestion": 2, "info": 3}
_NON_CODE = (".md", ".rst", ".txt", ".json", ".lock", ".csv", ".svg", ".png", ".jpg", ".gif")
_SOURCE = (".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rb", ".java", ".kt", ".rs", ".php", ".cs")


def review_pull_request(repo: str, pr_number: int) -> str:
    repo = repo.strip().removeprefix("https://github.com/").strip("/")
    if not _REPO_RE.match(repo) or ".." in repo:
        return json.dumps({"error": f"repo must look like owner/name, got {repo!r}"})
    try:
        number = int(pr_number)
    except (TypeError, ValueError):
        return json.dumps({"error": f"pr_number must be a number, got {pr_number!r}"})

    path = f"/repos/{repo}/pulls/{number}"
    try:
        meta = json.loads(_github(path, "application/vnd.github+json"))
        diff = _github(path, "application/vnd.github.diff")
    except urllib.error.HTTPError as exc:
        hint = ""
        if exc.code in (401, 403, 404) and not os.environ.get("GITHUB_TOKEN"):
            hint = " If the repository is private, set GITHUB_TOKEN."
        return json.dumps({"error": f"GitHub returned HTTP {exc.code} for {repo}#{number}.{hint}"})
    except OSError as exc:
        return json.dumps({"error": f"Could not reach GitHub: {exc}"})

    files = parse_diff(diff)
    findings = scan_files(files)
    return json.dumps(
        {
            "repo": repo,
            "number": number,
            "title": meta.get("title", ""),
            "author": (meta.get("user") or {}).get("login", ""),
            "base": (meta.get("base") or {}).get("ref", ""),
            "head": (meta.get("head") or {}).get("ref", ""),
            "description": (meta.get("body") or "")[:4000],
            "files": [{"path": f["path"], "added": len(f["added"]), "removed": f["removed"]} for f in files],
            "findings": findings[:_MAX_FINDINGS],
            "findings_total": len(findings),
            "source_files_without_test_changes": untested_source_files(files),
            "diff": diff[:_MAX_DIFF_CHARS],
            "diff_truncated": len(diff) > _MAX_DIFF_CHARS,
        }
    )


def scan_code(code: str, filename: str = "snippet.py") -> str:
    lines = list(enumerate(code.splitlines(), start=1))
    findings = scan_files([{"path": filename, "added": lines, "removed": 0}])
    return json.dumps({"filename": filename, "findings": findings[:_MAX_FINDINGS], "findings_total": len(findings)})


def parse_diff(diff_text: str) -> list[dict]:
    """Split a unified diff into files with added lines numbered as in the new file."""
    files: list[dict] = []
    current: dict | None = None
    in_hunk = False
    new_line = 0
    for raw in diff_text.splitlines():
        if raw.startswith("diff --git "):
            current = {"path": raw.split(" b/", 1)[-1], "added": [], "removed": 0}
            files.append(current)
            in_hunk = False
        elif current is None:
            continue
        elif not in_hunk and raw.startswith("+++ "):
            target = raw[4:].strip()
            if target != "/dev/null":
                current["path"] = target.removeprefix("b/")
        elif raw.startswith("@@"):
            match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
            new_line = int(match.group(1)) if match else 0
            in_hunk = True
        elif not in_hunk:
            continue
        elif raw.startswith("+"):
            current["added"].append((new_line, raw[1:]))
            new_line += 1
        elif raw.startswith("-"):
            current["removed"] += 1
        elif not raw.startswith("\\"):
            new_line += 1
    return files


def scan_files(files: list[dict]) -> list[dict]:
    findings = []
    for f in files:
        if f["path"].lower().endswith(_NON_CODE):
            continue
        for line_no, content in f["added"]:
            for rule, severity, pattern, message, suggestion in _COMPILED:
                if pattern.search(content):
                    findings.append(
                        {
                            "file": f["path"],
                            "line": line_no,
                            "rule": rule,
                            "severity": severity,
                            "message": message,
                            "suggestion": suggestion,
                            "code": content.strip()[:200],
                        }
                    )
    findings.sort(key=lambda item: _SEVERITY_ORDER[item["severity"]])
    return findings


def untested_source_files(files: list[dict]) -> list[str]:
    paths = [f["path"] for f in files]
    tests = [p.rsplit("/", 1)[-1].lower() for p in paths if _is_test(p)]
    missing = []
    for path in paths:
        if _is_test(path) or not path.endswith(_SOURCE):
            continue
        stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
        if not any(stem in test for test in tests):
            missing.append(path)
    return missing


def _is_test(path: str) -> bool:
    lowered = f"/{path.lower()}"
    name = lowered.rsplit("/", 1)[-1]
    return (
        name.startswith("test_")
        or any(marker in name for marker in ("_test.", ".test.", ".spec."))
        or "/tests/" in lowered
        or "/__tests__/" in lowered
    )


def _github(path: str, accept: str) -> str:
    headers = {
        "Accept": accept,
        "User-Agent": "agntspark-code-reviewer",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(_GITHUB_API + path, headers=headers)
    with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT) as resp:
        return resp.read(5_000_000).decode("utf-8", errors="replace")
