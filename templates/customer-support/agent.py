"""
AgntSpark Template: Customer Support Agent
A conversational AI agent for handling customer inquiries,
ticket routing, and FAQ responses.
"""
from agntspark_core.agent import Agent, AgentConfig
from agntspark_core.config import LLMProvider

config = AgentConfig(
    name="customer-support-agent",
    description="Handles customer inquiries with empathy and accuracy",
    llm_provider=LLMProvider.OPENAI,
    model="gpt-4o",
    system_prompt="""You are a customer support agent for a SaaS platform.
Your goal is to resolve customer issues efficiently while maintaining
a friendly and professional tone.

Guidelines:
- Always acknowledge the customer's concern first
- Ask clarifying questions if the issue is ambiguous
- Provide step-by-step solutions when applicable
- Escalate to human agents for billing or security issues
- Never make up information — if unsure, say so""",
    temperature=0.3,
    max_tokens=2048,
    memory_enabled=True,
    memory_ttl=3600,
)

agent = Agent(config=config)


@agent.tool(name="search_kb", description="Search the knowledge base for relevant articles")
async def search_kb(query: str) -> str:
    """Search knowledge base and return matching articles."""
    return f"Found 3 articles matching: {query}"


@agent.tool(name="create_ticket", description="Create a support ticket for human escalation")
async def create_ticket(subject: str, priority: str, description: str) -> dict:
    """Create a support ticket in the ticketing system."""
    return {"ticket_id": "TKT-00001", "status": "open", "priority": priority}


@agent.tool(name="check_account", description="Check customer account status")
async def check_account(email: str) -> dict:
    """Retrieve customer account information."""
    return {"email": email, "plan": "pro", "status": "active"}


if __name__ == "__main__":
    import asyncio
    asyncio.run(agent.run("Hi, I'm having trouble logging into my account"))
