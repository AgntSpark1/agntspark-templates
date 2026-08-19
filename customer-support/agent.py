"""
AgntSpark Customer Support Agent

Provides AI-powered customer support with knowledge base lookup,
intelligent ticket routing, and sentiment analysis.
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
logger = logging.getLogger("customer-support")


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    FRUSTRATED = "frustrated"


class TicketCategory(str, Enum):
    TECHNICAL = "technical"
    BILLING = "billing"
    ACCOUNT = "account"
    PRODUCT = "product"
    GENERAL = "general"


@dataclass
class KnowledgeArticle:
    article_id: str
    title: str
    content: str
    relevance: float
    url: str = ""


@dataclass
class Ticket:
    ticket_id: str
    customer_id: str
    subject: str
    category: TicketCategory
    priority: str
    sentiment: Sentiment
    status: str = "open"
    assigned_team: str = ""


@dataclass
class CustomerContext:
    customer_id: str
    name: str = ""
    email: str = ""
    tier: str = "standard"
    history: list = field(default_factory=list)
    open_tickets: list = field(default_factory=list)


class CustomerSupportAgent:
    """Main agent class orchestrating support interactions."""

    def __init__(self):
        self.kb_url = os.getenv("KNOWLEDGE_BASE_URL", "http://localhost:8001")
        self.kb_api_key = os.getenv("KNOWLEDGE_BASE_API_KEY", "dev-key")
        self.ticketing_url = os.getenv("TICKETING_SYSTEM_URL", "http://localhost:8002")
        self.ticketing_api_key = os.getenv("TICKETING_API_KEY", "dev-key")
        self.customer_db_url = os.getenv("CUSTOMER_DB_URL", "http://localhost:8003")
        self.conversation_history: list[dict] = []

        # Sentiment keywords for lightweight local analysis
        self._sentiment_keywords = {
            Sentiment.POSITIVE: ["thank", "great", "awesome", "perfect", "love", "excellent", "appreciate"],
            Sentiment.NEGATIVE: ["broken", "error", "wrong", "bad", "terrible", "hate", "fail"],
            Sentiment.FRUSTRATED: ["angry", "frustrated", "unacceptable", "ridiculous", "furious", "terrible service", "not working again", "third time"],
        }

    # --- Tool: search_knowledge_base ---

    def search_knowledge_base(self, query: str, max_results: int = 5) -> list[dict]:
        """Search the knowledge base for articles matching the query."""
        logger.info(f"KB search: '{query}'")
        try:
            resp = requests.post(
                f"{self.kb_url}/api/v1/search",
                json={"query": query, "max_results": max_results, "min_relevance": 0.7},
                headers={"Authorization": f"Bearer {self.kb_api_key}"},
                timeout=15,
            )
            resp.raise_for_status()
            articles = resp.json().get("results", [])
            logger.info(f"KB returned {len(articles)} articles")
            return articles
        except requests.RequestException as e:
            logger.warning(f"KB search failed, using fallback: {e}")
            return self._fallback_kb_search(query, max_results)

    def _fallback_kb_search(self, query: str, max_results: int) -> list[dict]:
        """Simple keyword-based fallback when KB API is unavailable."""
        fallback_articles = [
            {"article_id": "KB-001", "title": "Password Reset Guide", "content": "To reset your password, go to Settings > Security > Reset Password. Follow the email link within 15 minutes.", "relevance": 0.85},
            {"article_id": "KB-002", "title": "API Authentication", "content": "Use Bearer token authentication. Generate tokens in Dashboard > API > Create Token.", "relevance": 0.80},
            {"article_id": "KB-003", "title": "Billing and Invoices", "content": "View invoices in Account > Billing. Download PDF invoices for any billing period.", "relevance": 0.75},
            {"article_id": "KB-004", "title": "Account Deletion", "content": "Delete your account in Settings > Account > Delete. This action is irreversible within 30 days.", "relevance": 0.70},
            {"article_id": "KB-005", "title": "Two-Factor Authentication", "content": "Enable 2FA in Settings > Security. Supports TOTP apps and SMS codes.", "relevance": 0.68},
        ]
        query_lower = query.lower()
        scored = []
        for article in fallback_articles:
            score = sum(1 for word in query_lower.split() if word in article["title"].lower() or word in article["content"].lower())
            if score > 0:
                article["relevance"] = min(0.5 + score * 0.15, 1.0)
                scored.append(article)
        scored.sort(key=lambda x: x["relevance"], reverse=True)
        return scored[:max_results]

    # --- Tool: analyze_sentiment ---

    def analyze_sentiment(self, message: str) -> dict:
        """Analyze customer message sentiment."""
        message_lower = message.lower()
        scores: dict[Sentiment, int] = {s: 0 for s in Sentiment}

        for sentiment, keywords in self._sentiment_keywords.items():
            for kw in keywords:
                if kw in message_lower:
                    scores[sentiment] += 1

        # Punctuation-based frustration boost
        exclamation_count = message.count("!")
        caps_ratio = sum(1 for c in message if c.isupper()) / max(len(message), 1)
        if exclamation_count >= 3 or caps_ratio > 0.3:
            scores[Sentiment.FRUSTRATED] += 2

        best = max(scores, key=lambda s: scores[s]) if any(scores.values()) else Sentiment.NEUTRAL
        result = {
            "sentiment": best.value,
            "scores": {s.value: c for s, c in scores.items()},
            "exclamation_count": exclamation_count,
            "caps_ratio": round(caps_ratio, 2),
        }
        logger.info(f"Sentiment: {result['sentiment']} for message: '{message[:80]}...'")
        return result

    # --- Tool: create_ticket ---

    def create_ticket(self, customer_id: str, subject: str, category: str, priority: str = "normal") -> dict:
        """Create a support ticket in the ticketing system."""
        sentiment = self.analyze_sentiment(subject)
        ticket_data = {
            "customer_id": customer_id,
            "subject": subject,
            "category": category,
            "priority": priority,
            "sentiment": sentiment["sentiment"],
            "source": "ai-agent",
        }
        try:
            resp = requests.post(
                f"{self.ticketing_url}/api/v1/tickets",
                json=ticket_data,
                headers={"Authorization": f"Bearer {self.ticketing_api_key}"},
                timeout=15,
            )
            resp.raise_for_status()
            ticket = resp.json()
            logger.info(f"Ticket created: {ticket.get('ticket_id', 'unknown')}")
            return ticket
        except requests.RequestException as e:
            logger.warning(f"Ticket API failed, generating local ticket: {e}")
            ticket_id = f"TKT-{abs(hash(customer_id + subject)) % 100000:05d}"
            return {"ticket_id": ticket_id, **ticket_data, "status": "open", "fallback": True}

    # --- Tool: route_ticket ---

    def route_ticket(self, ticket_id: str, category: str) -> dict:
        """Route a ticket to the appropriate team based on category."""
        team_mapping = {
            TicketCategory.TECHNICAL: "technical-team",
            TicketCategory.BILLING: "billing-team",
            TicketCategory.ACCOUNT: "account-team",
            TicketCategory.PRODUCT: "product-team",
            TicketCategory.GENERAL: "general-support",
        }
        try:
            cat = TicketCategory(category)
        except ValueError:
            cat = TicketCategory.GENERAL
            logger.warning(f"Unknown category '{category}', defaulting to general")

        team = team_mapping.get(cat, "general-support")
        try:
            resp = requests.post(
                f"{self.ticketing_url}/api/v1/tickets/{ticket_id}/route",
                json={"team": team, "category": cat.value},
                headers={"Authorization": f"Bearer {self.ticketing_api_key}"},
                timeout=15,
            )
            resp.raise_for_status()
            result = resp.json()
        except requests.RequestException as e:
            logger.warning(f"Route API failed: {e}")
            result = {"ticket_id": ticket_id, "team": team, "status": "routed", "fallback": True}

        logger.info(f"Routed ticket {ticket_id} to {team}")
        return result

    # --- Tool: get_customer_history ---

    def get_customer_history(self, customer_id: str) -> dict:
        """Retrieve customer interaction history."""
        try:
            resp = requests.get(
                f"{self.customer_db_url}/api/v1/customers/{customer_id}",
                headers={"Authorization": f"Bearer {self.kb_api_key}"},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.warning(f"Customer DB unavailable: {e}")
            return {"customer_id": customer_id, "history": [], "fallback": True}

    # --- Core: handle_message ---

    def handle_message(self, customer_id: str, message: str) -> dict:
        """Process an incoming customer message and generate a response."""
        self.conversation_history.append({"role": "customer", "content": message, "customer_id": customer_id})

        # Step 1: Analyze sentiment
        sentiment = self.analyze_sentiment(message)

        # Step 2: Search knowledge base
        kb_results = self.search_knowledge_base(message)

        # Step 3: Determine if we need to create a ticket
        needs_ticket = sentiment["sentiment"] in ("frustrated", "negative") or not kb_results
        ticket = None
        if needs_ticket:
            category = self._classify_issue(message)
            priority = "high" if sentiment["sentiment"] == "frustrated" else "normal"
            ticket = self.create_ticket(customer_id, message[:200], category, priority)
            self.route_ticket(ticket.get("ticket_id", ""), category)

        # Step 4: Compose response
        response = self._compose_response(message, sentiment, kb_results, ticket)

        self.conversation_history.append({"role": "agent", "content": response})
        return {
            "response": response,
            "sentiment": sentiment,
            "kb_articles_used": [a.get("article_id") for a in kb_results],
            "ticket_created": ticket is not None,
            "ticket_id": ticket.get("ticket_id") if ticket else None,
        }

    def _classify_issue(self, message: str) -> str:
        """Classify the issue into a ticket category based on keywords."""
        message_lower = message.lower()
        if any(w in message_lower for w in ["api", "bug", "error", "crash", "500", "timeout", "integration"]):
            return TicketCategory.TECHNICAL.value
        if any(w in message_lower for w in ["bill", "invoice", "charge", "refund", "payment", "subscription"]):
            return TicketCategory.BILLING.value
        if any(w in message_lower for w in ["login", "password", "access", "account", "2fa", "delete account"]):
            return TicketCategory.ACCOUNT.value
        if any(w in message_lower for w in ["feature", "request", "roadmap", "enhancement", "suggestion"]):
            return TicketCategory.PRODUCT.value
        return TicketCategory.GENERAL.value

    def _compose_response(self, message: str, sentiment: dict, kb_results: list, ticket: Optional[dict]) -> str:
        """Compose a natural language response based on available data."""
        parts = []

        # Sentiment-aware opening
        if sentiment["sentiment"] == "frustrated":
            parts.append("I completely understand your frustration, and I want to help resolve this as quickly as possible.")
        elif sentiment["sentiment"] == "negative":
            parts.append("I'm sorry you're experiencing this issue. Let me look into it right away.")
        else:
            parts.append("Thanks for reaching out! Let me help you with that.")

        # Include KB answers
        if kb_results:
            parts.append("Based on our knowledge base:")
            for article in kb_results[:3]:
                aid = article.get("article_id", "N/A")
                content = article.get("content", "")[:300]
                parts.append(f"  [Ref: {aid}] {content}")
        else:
            parts.append("I wasn't able to find a specific article for this issue in our knowledge base.")

        # Ticket notification
        if ticket:
            parts.append(f"I've created ticket {ticket.get('ticket_id', 'N/A')} and routed it to the appropriate team. You'll receive updates via email.")

        return "\n\n".join(parts)

    def summarize_conversation(self) -> dict:
        """Summarize the current conversation for handoff or logging."""
        if not self.conversation_history:
            return {"summary": "No conversation history.", "message_count": 0}

        customer_messages = [m for m in self.conversation_history if m["role"] == "customer"]
        agent_messages = [m for m in self.conversation_history if m["role"] == "agent"]
        return {
            "message_count": len(self.conversation_history),
            "customer_messages": len(customer_messages),
            "agent_messages": len(agent_messages),
            "summary": " | ".join(m["content"][:100] for m in customer_messages),
        }


def main():
    """Run the agent in test mode with sample interactions."""
    agent = CustomerSupportAgent()

    test_interactions = [
        ("CUST-001", "I can't log into my account, it keeps saying invalid credentials even though I'm using the right password!"),
        ("CUST-002", "Hey, I was charged twice for my subscription this month. This is ridiculous!"),
        ("CUST-003", "Thanks, the API documentation was really helpful. Great work!"),
    ]

    print("=" * 60)
    print("Customer Support Agent — Test Mode")
    print("=" * 60)

    for customer_id, message in test_interactions:
        print(f"\n{'─' * 60}")
        print(f"Customer [{customer_id}]: {message}")
        result = agent.handle_message(customer_id, message)
        print(f"\nAgent Response:\n{result['response']}")
        print(f"\n[Sentiment: {result['sentiment']['sentiment']}]")
        print(f"[KB Articles: {result['kb_articles_used']}]")
        print(f"[Ticket: {result.get('ticket_id', 'None')}]")

    print(f"\n{'─' * 60}")
    summary = agent.summarize_conversation()
    print(f"Conversation Summary:\n{json.dumps(summary, indent=2)}")
    print(f"\n{'=' * 60}")
    print("Test complete ✓")


if __name__ == "__main__":
    main()
