"""Checks every official template against the manifest schema and against the
runtime that hosts it (agntspark_core.server), plus offline tool tests.
"""

from __future__ import annotations

import importlib.util
import json
import re
import textwrap
from pathlib import Path
from types import ModuleType

import jsonschema
import pytest
import yaml
from agntspark_core.server import load_settings

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = sorted(p for p in (ROOT / "templates").iterdir() if (p / "agent.yaml").is_file())
SCHEMA = json.loads((ROOT / "template.schema.json").read_text())


def _manifest(template: Path) -> dict:
    return yaml.safe_load((template / "agent.yaml").read_text())


def _tools(name: str) -> ModuleType:
    path = ROOT / "templates" / name / "tools.py"
    spec = importlib.util.spec_from_file_location(f"{name.replace('-', '_')}_tools", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_official_templates_present() -> None:
    assert {p.name for p in TEMPLATES} >= {"customer-support", "code-reviewer"}


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.name)
class TestEveryTemplate:
    def test_manifest_matches_schema(self, template: Path) -> None:
        jsonschema.validate(_manifest(template), SCHEMA)

    def test_directory_matches_name(self, template: Path) -> None:
        assert _manifest(template)["name"] == template.name

    def test_loads_in_runtime(self, template: Path) -> None:
        settings = load_settings({"AGNTSPARK_TEMPLATE_DIR": str(template)})
        assert settings.template == template.name
        assert [t.name for t in settings.tools] == [t["name"] for t in _manifest(template)["tools"]]

    def test_has_readme_and_requirements(self, template: Path) -> None:
        assert (template / "README.md").is_file()
        assert (template / "requirements.txt").is_file()


class TestCustomerSupport:
    @pytest.fixture(autouse=True)
    def _no_integrations(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for var in ("KNOWLEDGE_BASE_URL", "KNOWLEDGE_BASE_API_KEY", "TICKET_WEBHOOK_URL"):
            monkeypatch.delenv(var, raising=False)

    def test_sample_knowledge_base(self) -> None:
        result = json.loads(_tools("customer-support").search_knowledge_base(query="How do I reset my password?"))
        assert result["source"] == "sample"
        assert result["articles"][0]["article_id"] == "KB-001"

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            ("This is ridiculous, you charged me twice AGAIN!!!", "frustrated"),
            ("Thanks, that article was really helpful", "positive"),
            ("Where can I download last month's invoice", "neutral"),
        ],
    )
    def test_sentiment(self, message: str, expected: str) -> None:
        assert json.loads(_tools("customer-support").analyze_sentiment(message=message))["sentiment"] == expected

    def test_ticket_without_webhook_is_not_delivered(self) -> None:
        result = json.loads(
            _tools("customer-support").create_ticket(subject="Double charge", category="Billing", priority="urgent")
        )
        assert result["delivered"] is False
        assert result["ticket"]["team"] == "billing"
        assert result["ticket"]["priority"] == "urgent"
        assert re.fullmatch(r"TKT-[0-9A-F]{8}", result["ticket"]["ticket_id"])

    def test_ticket_is_posted_to_webhook(self, monkeypatch: pytest.MonkeyPatch) -> None:
        tools = _tools("customer-support")
        sent: list[tuple[str, dict]] = []
        monkeypatch.setenv("TICKET_WEBHOOK_URL", "https://hooks.example.com/tickets")
        monkeypatch.setattr(tools, "_post_json", lambda url, payload, headers: sent.append((url, payload)) or {})

        result = json.loads(tools.create_ticket(subject="Login broken", category="nonsense"))

        assert result["delivered"] is True
        assert result["ticket"]["category"] == "general"
        assert sent == [("https://hooks.example.com/tickets", result["ticket"])]


SAMPLE_DIFF = textwrap.dedent(
    """\
    diff --git a/app/db.py b/app/db.py
    index 1111111..2222222 100644
    --- a/app/db.py
    +++ b/app/db.py
    @@ -10,3 +10,4 @@ def load(path):
         data = read(path)
    -    return data
    +    result = eval(data)
    +    return result
         # end
    diff --git a/README.md b/README.md
    --- a/README.md
    +++ b/README.md
    @@ -1 +1 @@
    -old
    +Never call eval(x) on input.
    """
)


class TestCodeReviewer:
    def test_parse_diff_numbers_lines_in_new_file(self) -> None:
        files = _tools("code-reviewer").parse_diff(SAMPLE_DIFF)
        assert [f["path"] for f in files] == ["app/db.py", "README.md"]
        assert files[0]["added"] == [(11, "    result = eval(data)"), (12, "    return result")]
        assert files[0]["removed"] == 1

    def test_findings_point_at_code_lines_and_skip_docs(self) -> None:
        tools = _tools("code-reviewer")
        findings = tools.scan_files(tools.parse_diff(SAMPLE_DIFF))
        assert [(f["file"], f["line"], f["rule"]) for f in findings] == [("app/db.py", 11, "SEC001")]

    def test_scan_code_avoids_common_false_positives(self) -> None:
        code = "\n".join(
            [
                "with open('a') as f:",
                "    value = ast.literal_eval(f.read())",
                "handle = open('b')",
                "subprocess.run(cmd, shell=True)",
            ]
        )
        found = {(f["line"], f["rule"]) for f in json.loads(_tools("code-reviewer").scan_code(code=code))["findings"]}
        assert found == {(3, "BUG003"), (4, "SEC003")}

    def test_rejects_malformed_repo_without_calling_github(self) -> None:
        result = json.loads(_tools("code-reviewer").review_pull_request(repo="not a repo", pr_number=1))
        assert "owner/name" in result["error"]
