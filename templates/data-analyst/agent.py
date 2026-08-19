"""
AgntSpark Template: Data Analyst Agent
An AI agent that queries databases, generates insights,
and produces visual reports from business data.
"""
from agntspark_core.agent import Agent, AgentConfig
from agntspark_core.config import LLMProvider

config = AgentConfig(
    name="data-analyst-agent",
    description="Queries databases and generates business insights",
    llm_provider=LLMProvider.OPENAI,
    model="gpt-4o",
    system_prompt="""You are a senior data analyst with expertise in SQL,
Python (pandas), and data visualization.

Your responsibilities:
- Translate business questions into SQL queries
- Identify trends, anomalies, and opportunities in data
- Generate clear visual summaries
- Provide actionable business recommendations
- Always validate data quality before drawing conclusions
- Explain your analysis methodology clearly""",
    temperature=0.2,
    max_tokens=4096,
    memory_enabled=True,
    memory_ttl=7200,
)

agent = Agent(config=config)


@agent.tool(name="run_sql", description="Execute a read-only SQL query")
async def run_sql(query: str, database: str = "default") -> dict:
    """Execute SQL query and return results."""
    return {"rows": [], "columns": [], "row_count": 0}


@agent.tool(name="generate_chart", description="Generate a chart from data")
async def generate_chart(data: dict, chart_type: str = "bar") -> str:
    """Generate visualization and return image path."""
    return f"/tmp/chart_{chart_type}.png"


@agent.tool(name="export_report", description="Export analysis as PDF report")
async def export_report(title: str, sections: list[dict]) -> str:
    """Generate PDF report from analysis sections."""
    return f"/tmp/report_{title}.pdf"


if __name__ == "__main__":
    import asyncio
    asyncio.run(agent.run("Analyze sales trends for Q3 2026"))
