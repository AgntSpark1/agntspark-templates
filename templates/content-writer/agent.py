"""
AgntSpark Template: Content Writer Agent
An AI agent that researches topics, drafts articles,
and optimizes content for SEO and engagement.
"""
from agntspark_core.agent import Agent, AgentConfig
from agntspark_core.config import LLMProvider

config = AgentConfig(
    name="content-writer-agent",
    description="Researches, drafts, and optimizes long-form content",
    llm_provider=LLMProvider.ANTHROPIC,
    model="claude-sonnet-4-20250514",
    system_prompt="""You are an expert content writer and SEO strategist.

Your capabilities:
- Research topics thoroughly using available tools
- Write engaging, well-structured long-form content
- Optimize for target keywords and search intent
- Maintain consistent brand voice and style
- Include relevant internal and external links
- Write compelling meta descriptions and titles
- Always fact-check claims before publishing""",
    temperature=0.7,
    max_tokens=8192,
    memory_enabled=True,
    memory_ttl=14400,
)

agent = Agent(config=config)


@agent.tool(name="search_web", description="Search the web for research")
async def search_web(query: str, num_results: int = 5) -> list[dict]:
    """Search web and return top results."""
    return [{"title": "", "url": "", "snippet": ""} for _ in range(num_results)]


@agent.tool(name="analyze_seo", description="Analyze content for SEO score")
async def analyze_seo(content: str, target_keyword: str) -> dict:
    """Analyze content SEO and return score with recommendations."""
    return {"seo_score": 85, "word_count": 1500, "recommendations": []}


@agent.tool(name="extract_keywords", description="Extract related keywords for topic")
async def extract_keywords(topic: str, limit: int = 10) -> list[str]:
    """Extract related keywords for content planning."""
    return [f"keyword_{i}" for i in range(limit)]


if __name__ == "__main__":
    import asyncio
    asyncio.run(agent.run("Write a 2000-word article about AI agent orchestration"))
