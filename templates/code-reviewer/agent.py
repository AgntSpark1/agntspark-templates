"""
AgntSpark Template: Code Reviewer Agent
An AI agent that reviews pull requests, identifies bugs,
and suggests improvements with actionable feedback.
"""
from agntspark_core.agent import Agent, AgentConfig
from agntspark_core.config import LLMProvider

config = AgentConfig(
    name="code-reviewer-agent",
    description="Reviews code for bugs, security issues, and best practices",
    llm_provider=LLMProvider.ANTHROPIC,
    model="claude-sonnet-4-20250514",
    system_prompt="""You are an expert code reviewer with deep knowledge of
software engineering best practices, security vulnerabilities, and performance optimization.

Review guidelines:
- Identify potential bugs and logic errors
- Check for security vulnerabilities (OWASP Top 10)
- Suggest performance improvements
- Enforce style guide compliance
- Provide actionable, specific feedback with code examples
- Rate severity: critical, warning, suggestion
- Always explain WHY something is an issue, not just WHAT""",
    temperature=0.1,
    max_tokens=4096,
    memory_enabled=False,
)

agent = Agent(config=config)


@agent.tool(name="get_pr_diff", description="Fetch the pull request diff from GitHub")
async def get_pr_diff(pr_number: int, repo: str) -> str:
    """Fetch PR diff from GitHub API."""
    return f"Fetching diff for PR #{pr_number} in {repo}"


@agent.tool(name="run_linter", description="Run code linter on changed files")
async def run_linter(files: list[str]) -> dict:
    """Run linter and return issues."""
    return {"files_checked": len(files), "issues_found": 0}


@agent.tool(name="check_deps", description="Check for vulnerable dependencies")
async def check_deps(requirements_file: str) -> dict:
    """Check dependencies against vulnerability database."""
    return {"vulnerable_packages": [], "total_scanned": 42}


if __name__ == "__main__":
    import asyncio
    asyncio.run(agent.run("Review PR #42 in repo agntspark-core"))
