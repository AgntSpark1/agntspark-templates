"""
AgntSpark Code Reviewer Agent

Reviews GitHub pull requests, detects bugs and security issues,
and suggests improvements with actionable feedback.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("code-reviewer")


class Severity(str, Enum):
    BLOCKING = "blocking"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    INFO = "info"


class IssueType(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    QUALITY = "quality"
    STYLE = "style"
    TEST = "test"
    DOCS = "docs"


@dataclass
class ReviewIssue:
    file: str
    line: int
    severity: Severity
    issue_type: IssueType
    message: str
    suggestion: str = ""
    rule_id: str = ""


@dataclass
class ReviewResult:
    pr_number: int
    repository: str
    summary: str
    issues: list[ReviewIssue] = field(default_factory=list)
    blocking_count: int = 0
    warning_count: int = 0
    suggestion_count: int = 0
    files_reviewed: int = 0
    lines_reviewed: int = 0
    approved: bool = False

    def to_dict(self) -> dict:
        return {
            "pr_number": self.pr_number,
            "repository": self.repository,
            "summary": self.summary,
            "issues": [
                {
                    "file": i.file, "line": i.line, "severity": i.severity.value,
                    "type": i.issue_type.value, "message": i.message,
                    "suggestion": i.suggestion, "rule_id": i.rule_id,
                }
                for i in self.issues
            ],
            "blocking_count": self.blocking_count,
            "warning_count": self.warning_count,
            "suggestion_count": self.suggestion_count,
            "files_reviewed": self.files_reviewed,
            "lines_reviewed": self.lines_reviewed,
            "approved": self.approved,
        }


# Security patterns to detect
SECURITY_PATTERNS = [
    (r'eval\s*\(', "SEC001", "Use of eval() can lead to code injection", Severity.BLOCKING),
    (r'exec\s*\(', "SEC002", "Use of exec() can lead to code injection", Severity.BLOCKING),
    (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', "SEC003", "shell=True in subprocess can lead to command injection", Severity.BLOCKING),
    (r'os\.system\s*\(', "SEC004", "os.system() can lead to command injection", Severity.BLOCKING),
    (r'pickle\.loads?\s*\(', "SEC005", "pickle.load/loads can execute arbitrary code", Severity.BLOCKING),
    (r'yaml\.load\s*\([^)]*\)\s*(?!#\s*safe)', "SEC006", "Use yaml.safe_load instead of yaml.load", Severity.WARNING),
    (r'(?:password|passwd|secret|api_key|token)\s*=\s*["\'][^"\']{8,}["\']', "SEC007", "Hardcoded secret/credential detected", Severity.BLOCKING),
    (r'SELECT\s+.*\s+FROM\s+.*\+.*["\']', "SEC008", "Potential SQL injection via string concatenation", Severity.BLOCKING),
    (r'verify\s*=\s*False', "SEC009", "SSL verification disabled", Severity.BLOCKING),
    (r'innerHTML\s*=', "SEC010", "Direct innerHTML assignment may cause XSS", Severity.WARNING),
]

# Bug patterns
BUG_PATTERNS = [
    (r'except\s*:', "BUG001", "Bare except catches all exceptions including SystemExit/KeyboardInterrupt", Severity.WARNING),
    (r'except\s+Exception\s*:\s*\n\s*pass', "BUG002", "Silent exception swallowing (except: pass)", Severity.WARNING),
    (r'==\s*(?:None|True|False)', "BUG003", "Use 'is' for comparisons with None/True/False", Severity.SUGGESTION),
    (r'open\s*\([^)]*\)(?!\s*with)', "BUG004", "File opened without 'with' statement (resource leak risk)", Severity.WARNING),
    (r'mutabl.*default.*=\s*\[\]', "BUG005", "Mutable default argument (list) will be shared across calls", Severity.WARNING),
    (r'def\s+\w+\([^)]*=\s*\{\}\s*\)', "BUG006", "Mutable default argument (dict) will be shared across calls", Severity.WARNING),
    (r'assert\s+.*\s*==', "BUG007", "Assert used for validation (disabled with -O flag)", Severity.SUGGESTION),
]

# Quality patterns
QUALITY_PATTERNS = [
    (r'print\s*\(', "QLT001", "print statement in production code (use logging)", Severity.SUGGESTION),
    (r'^\s*\#\s*TODO', "QLT002", "TODO comment found", Severity.INFO),
    (r'^\s*\#\s*FIXME', "QLT003", "FIXME comment found", Severity.WARNING),
    (r'^\s*\#\s*HACK', "QLT004", "HACK comment found", Severity.WARNING),
]


class CodeReviewerAgent:
    """Main agent class for automated code review."""

    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

    # --- Tool: fetch_pr_diff ---

    def fetch_pr_diff(self, repo: str, pr_number: int) -> dict:
        """Fetch the diff of a pull request from GitHub."""
        url = f"{self.api_base}/repos/{repo}/pulls/{pr_number}"
        logger.info(f"Fetching PR #{pr_number} from {repo}")
        try:
            resp = requests.get(url, headers={**self.headers, "Accept": "application/vnd.github.v3.diff"}, timeout=30)
            resp.raise_for_status()
            diff_text = resp.text

            # Also fetch metadata
            meta_resp = requests.get(url, headers=self.headers, timeout=30)
            meta_resp.raise_for_status()
            metadata = meta_resp.json()

            files = self._parse_diff(diff_text)
            return {
                "repo": repo,
                "pr_number": pr_number,
                "title": metadata.get("title", ""),
                "body": metadata.get("body", ""),
                "author": metadata.get("user", {}).get("login", ""),
                "base_branch": metadata.get("base", {}).get("ref", ""),
                "head_branch": metadata.get("head", {}).get("ref", ""),
                "files": files,
                "diff_raw": diff_text,
            }
        except requests.RequestException as e:
            logger.error(f"Failed to fetch PR: {e}")
            return {"error": str(e), "repo": repo, "pr_number": pr_number}

    def _parse_diff(self, diff_text: str) -> list[dict]:
        """Parse a unified diff into structured file data."""
        files = []
        current_file = None
        current_line = 0
        for line in diff_text.split("\n"):
            if line.startswith("diff --git"):
                if current_file:
                    files.append(current_file)
                current_file = {"path": "", "added": [], "removed": [], "context": []}
            elif line.startswith("+++ b/"):
                if current_file:
                    current_file["path"] = line[6:]
            elif line.startswith("+++") or line.startswith("---"):
                continue
            elif line.startswith("+") and not line.startswith("+++"):
                if current_file:
                    current_line += 1
                    current_file["added"].append({"line_num": current_line, "content": line[1:]})
            elif line.startswith("-") and not line.startswith("---"):
                if current_file:
                    current_file["removed"].append({"content": line[1:]})
            elif line.startswith("@@"):
                m = re.match(r'@@ -\d+,\d+ \+(\d+),(\d+) @@', line)
                if m:
                    current_line = int(m.group(1)) - 1
        if current_file:
            files.append(current_file)
        return files

    # --- Tool: analyze_code ---

    def analyze_code(self, files: list[dict]) -> list[ReviewIssue]:
        """Analyze parsed diff files for bugs, security issues, and improvements."""
        issues: list[ReviewIssue] = []
        for f in files:
            filepath = f.get("path", "unknown")
            for line_info in f.get("added", []):
                line_num = line_info["line_num"]
                content = line_info["content"]
                for pattern, rule_id, msg, severity in SECURITY_PATTERNS:
                    if re.search(pattern, content, re.IGNORECASE):
                        issues.append(ReviewIssue(
                            file=filepath, line=line_num, severity=severity,
                            issue_type=IssueType.SECURITY, message=msg,
                            suggestion=self._get_suggestion(rule_id, content),
                            rule_id=rule_id,
                        ))
                for pattern, rule_id, msg, severity in BUG_PATTERNS:
                    if re.search(pattern, content, re.IGNORECASE):
                        issues.append(ReviewIssue(
                            file=filepath, line=line_num, severity=severity,
                            issue_type=IssueType.BUG, message=msg,
                            suggestion=self._get_suggestion(rule_id, content),
                            rule_id=rule_id,
                        ))
                for pattern, rule_id, msg, severity in QUALITY_PATTERNS:
                    if re.search(pattern, content):
                        issues.append(ReviewIssue(
                            file=filepath, line=line_num, severity=severity,
                            issue_type=IssueType.QUALITY, message=msg,
                            rule_id=rule_id,
                        ))

        # Deduplicate
        seen = set()
        unique = []
        for i in issues:
            key = (i.file, i.line, i.rule_id)
            if key not in seen:
                seen.add(key)
                unique.append(i)
        logger.info(f"Found {len(unique)} issues across {len(files)} files")
        return unique

    def _get_suggestion(self, rule_id: str, content: str) -> str:
        """Get a fix suggestion for a rule."""
        suggestions = {
            "SEC001": "Replace eval() with ast.literal_eval() for literal parsing, or restructure the logic.",
            "SEC002": "Remove exec() usage. If dynamic code execution is required, consider a safe sandbox.",
            "SEC003": "Use subprocess.run() with shell=False and pass arguments as a list.",
            "SEC004": "Use subprocess.run() instead of os.system() for better security and control.",
            "SEC005": "Avoid pickle for untrusted data. Use JSON or a safe serialization format.",
            "SEC006": "Replace yaml.load() with yaml.safe_load().",
            "SEC007": "Move secrets to environment variables or a secrets manager. Never hardcode credentials.",
            "SEC008": "Use parameterized queries: cursor.execute(sql, params) instead of string concatenation.",
            "SEC009": "Remove verify=False. Fix the certificate chain instead of disabling verification.",
            "SEC010": "Use textContent or properly sanitize/escape user input before DOM insertion.",
            "BUG001": "Use 'except Exception as e:' to catch specific exceptions.",
            "BUG002": "Log or handle the exception instead of silently passing.",
            "BUG003": "Use 'is None', 'is True', 'is False' for identity comparisons.",
            "BUG004": "Use a 'with open(...) as f:' context manager to ensure file handles are closed.",
            "BUG005": "Use 'None' as default and initialize inside the function: 'items = items or []'",
            "BUG006": "Use 'None' as default and initialize inside the function: 'config = config or {}'",
            "BUG007": "Use 'if not condition: raise ValueError(...)' instead of assert for validation.",
        }
        return suggestions.get(rule_id, "")

    # --- Tool: check_security ---

    def check_security(self, files: list[dict]) -> dict:
        """Run security-focused analysis on the diff files."""
        issues = self.analyze_code(files)
        sec_issues = [i for i in issues if i.issue_type == IssueType.SECURITY]
        blocking = [i for i in sec_issues if i.severity == Severity.BLOCKING]
        warnings = [i for i in sec_issues if i.severity == Severity.WARNING]
        return {
            "total_security_issues": len(sec_issues),
            "blocking": len(blocking),
            "warnings": len(warnings),
            "details": [
                {"file": i.file, "line": i.line, "rule": i.rule_id, "message": i.message}
                for i in sec_issues
            ],
        }

    # --- Tool: check_test_coverage ---

    def check_test_coverage(self, files: list[dict]) -> dict:
        """Check if changed source files have corresponding test files."""
        test_files_found = []
        source_files_without_tests = []
        all_paths = [f["path"] for f in files]

        for f in files:
            path = f["path"]
            # Skip test files themselves
            if "test" in path.lower() or "spec" in path.lower():
                test_files_found.append(path)
                continue
            # Skip non-Python files
            if not path.endswith(".py"):
                continue
            # Check if a test file exists for this source file
            basename = path.rsplit("/", 1)[-1].replace(".py", "")
            test_patterns = [f"test_{basename}.py", f"{basename}_test.py", f"test_{basename}.py"]
            found = any(tp in all_paths for tp in test_patterns)
            if not found:
                source_files_without_tests.append(path)

        return {
            "test_files_changed": len(test_files_found),
            "source_files_without_tests": source_files_without_tests,
            "coverage_gap": len(source_files_without_tests),
        }

    # --- Tool: post_review ---

    def post_review(self, repo: str, pr_number: int, review: ReviewResult) -> dict:
        """Post a review comment on the GitHub PR."""
        event = "REQUEST_CHANGES" if review.blocking_count > 0 else "APPROVE" if review.warning_count == 0 else "COMMENT"

        body = self._format_review_body(review)
        payload = {
            "body": body,
            "event": event,
            "comments": [
                {
                    "path": issue.file,
                    "line": issue.line,
                    "body": f"**[{issue.severity.value.upper()}] {issue.rule_id}**: {issue.message}\n\n{suggestion}" if (suggestion := issue.suggestion) else f"**[{issue.severity.value.upper()}] {issue.rule_id}**: {issue.message}",
                }
                for issue in review.issues
                if issue.severity in (Severity.BLOCKING, Severity.WARNING)
            ],
        }

        url = f"{self.api_base}/repos/{repo}/pulls/{pr_number}/reviews"
        try:
            resp = requests.post(url, json=payload, headers=self.headers, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            logger.info(f"Review posted on PR #{pr_number}: {event}")
            return {"posted": True, "event": event, "review_id": result.get("id"), "url": result.get("html_url", "")}
        except requests.RequestException as e:
            logger.error(f"Failed to post review: {e}")
            return {"posted": False, "error": str(e), "body": body}

    def _format_review_body(self, review: ReviewResult) -> str:
        """Format the review summary as markdown."""
        lines = [
            f"## 🤖 Automated Code Review",
            f"\n**Files reviewed:** {review.files_reviewed} | **Lines reviewed:** {review.lines_reviewed}",
            f"\n| Severity | Count |",
            f"|---|---|",
            f"| 🔴 Blocking | {review.blocking_count} |",
            f"| 🟡 Warning | {review.warning_count} |",
            f"| 🔵 Suggestion | {review.suggestion_count} |",
        ]
        if review.summary:
            lines.append(f"\n### Summary\n\n{review.summary}")
        if review.blocking_count > 0:
            lines.append(f"\n### ⚠️ Blocking Issues\n")
            for i in review.issues:
                if i.severity == Severity.BLOCKING:
                    lines.append(f"- **{i.file}:{i.line}** [{i.rule_id}] {i.message}")
        if review.warning_count > 0:
            lines.append(f"\n### Warnings\n")
            for i in review.issues:
                if i.severity == Severity.WARNING:
                    lines.append(f"- **{i.file}:{i.line}** [{i.rule_id}] {i.message}")
        lines.append(f"\n---\n*Review by AgntSpark Code Reviewer Agent*")
        return "\n".join(lines)

    # --- Core: review_pr ---

    def review_pr(self, repo: str, pr_number: int) -> dict:
        """Full PR review pipeline: fetch diff → analyze → post review."""
        # Fetch diff
        pr_data = self.fetch_pr_diff(repo, pr_number)
        if "error" in pr_data:
            return pr_data

        files = pr_data["files"]
        issues = self.analyze_code(files)
        sec_check = self.check_security(files)
        coverage = self.check_test_coverage(files)

        # Build review result
        result = ReviewResult(
            pr_number=pr_number,
            repository=repo,
            summary=f"Reviewed {len(files)} files. Found {len(issues)} issues "
                    f"({sec_check['blocking']} blocking security, {coverage['coverage_gap']} files without tests).",
            issues=issues,
            blocking_count=sum(1 for i in issues if i.severity == Severity.BLOCKING),
            warning_count=sum(1 for i in issues if i.severity == Severity.WARNING),
            suggestion_count=sum(1 for i in issues if i.severity == Severity.SUGGESTION),
            files_reviewed=len(files),
            lines_reviewed=sum(len(f.get("added", [])) for f in files),
            approved=len(issues) == 0 or all(i.severity != Severity.BLOCKING for i in issues),
        )
        result_dict = result.to_dict()
        result_dict["security_check"] = sec_check
        result_dict["test_coverage"] = coverage
        return result_dict


def main():
    """Run the agent in test mode with sample code diffs."""
    agent = CodeReviewerAgent()

    # Sample diff for testing (simulating a PR with issues)
    sample_diff = """diff --git a/app/auth.py b/app/auth.py
new file mode 100644
--- /dev/null
+++ b/app/auth.py
@@ -0,0 +1,15 @@
+import os
+import subprocess
+
+def authenticate(username, password):
+    # TODO: add rate limiting
+    api_key = "sk-1234567890abcdef"
+    query = "SELECT * FROM users WHERE name='" + username + "'"
+    result = os.system("echo " + username)
+    eval(username)
+    return result
+
+def process_payment(amount, config={}):
+    pass
+    print("processing")
"""

    print("=" * 60)
    print("Code Reviewer Agent — Test Mode")
    print("=" * 60)

    # Parse the sample diff
    files = agent._parse_diff(sample_diff)
    print(f"\nParsed {len(files)} file(s) from diff:")
    for f in files:
        print(f"  {f['path']}: {len(f['added'])} lines added")

    # Analyze code
    print(f"\n{'─' * 60}")
    print("Analyzing code...")
    issues = agent.analyze_code(files)
    for i in issues:
        print(f"  [{i.severity.value.upper():10}] {i.rule_id:8} {i.file}:{i.line} — {i.message}")
        if i.suggestion:
            print(f"            → {i.suggestion[:100]}")

    # Security check
    print(f"\n{'─' * 60}")
    print("Security analysis:")
    sec = agent.check_security(files)
    print(f"  Total security issues: {sec['total_security_issues']}")
    print(f"  Blocking: {sec['blocking']}")
    print(f"  Warnings: {sec['warnings']}")

    # Test coverage check
    print(f"\n{'─' * 60}")
    print("Test coverage analysis:")
    cov = agent.check_test_coverage(files)
    print(f"  Test files changed: {cov['test_files_changed']}")
    print(f"  Source files without tests: {cov['coverage_gap']}")
    for sf in cov["source_files_without_tests"]:
        print(f"    - {sf}")

    # Build review result
    print(f"\n{'─' * 60}")
    print("Review summary:")
    result = ReviewResult(
        pr_number=0, repository="test/repo",
        summary=f"Found {len(issues)} issues in {len(files)} files.",
        issues=issues,
        blocking_count=sum(1 for i in issues if i.severity == Severity.BLOCKING),
        warning_count=sum(1 for i in issues if i.severity == Severity.WARNING),
        suggestion_count=sum(1 for i in issues if i.severity == Severity.SUGGESTION),
        files_reviewed=len(files),
        lines_reviewed=sum(len(f.get("added", [])) for f in files),
    )
    print(f"  Blocking: {result.blocking_count}")
    print(f"  Warnings: {result.warning_count}")
    print(f"  Suggestions: {result.suggestion_count}")
    print(f"  Approved: {result.approved}")

    # Show formatted review body
    print(f"\n{'─' * 60}")
    print("Formatted review:")
    print(agent._format_review_body(result))

    print(f"\n{'=' * 60}")
    print("Test complete ✓")


if __name__ == "__main__":
    main()
