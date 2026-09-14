"""Tools for the customer-support template.

Plain functions: the agent runtime calls them with keyword arguments and
sends the return value back to the model, so each returns a JSON string.
Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
import uuid
from datetime import datetime, timezone

_HTTP_TIMEOUT = 15

# Shown when no KNOWLEDGE_BASE_URL is configured, so the template works out of
# the box. Replace with your own knowledge base for real use.
_SAMPLE_ARTICLES = [
    {
        "article_id": "KB-001",
        "title": "Resetting your password",
        "content": "Go to Settings > Security > Reset password. "
        "The reset link we email you expires after 15 minutes.",
    },
    {
        "article_id": "KB-002",
        "title": "API authentication",
        "content": "Send your API key as a Bearer token in the Authorization header. "
        "Create keys under Dashboard > API keys.",
    },
    {
        "article_id": "KB-003",
        "title": "Billing, invoices and duplicate charges",
        "content": "Invoices for every billing period are under Account > Billing as PDF. "
        "Confirmed duplicate charges are refunded within 5-10 business days.",
    },
    {
        "article_id": "KB-004",
        "title": "Deleting your account",
        "content": "Delete your account under Settings > Account > Delete. "
        "It can be restored for 30 days; after that deletion is permanent.",
    },
    {
        "article_id": "KB-005",
        "title": "Two-factor authentication",
        "content": "Turn on 2FA under Settings > Security. "
        "Authenticator apps (TOTP) and SMS codes are supported.",
    },
]

_STOPWORDS = {
    "a", "an", "and", "are", "can", "do", "does", "for", "how", "i", "in", "is", "it",
    "me", "my", "of", "on", "or", "the", "to", "what", "when", "why", "with", "you", "your",
}  # fmt: skip

# Checked in this order, so ties favour the stronger signal.
_SENTIMENT_KEYWORDS = {
    "frustrated": (
        "angry", "frustrated", "unacceptable", "ridiculous", "furious", "fed up",
        "third time", "again", "still not",
    ),
    "negative": (
        "broken", "error", "wrong", "bad", "terrible", "fail", "not working",
        "doesn't work", "charged twice", "can't",
    ),
    "positive": ("thank", "great", "awesome", "perfect", "love", "excellent", "appreciate", "helpful"),
}  # fmt: skip

_TEAMS = {
    "technical": "technical-support",
    "billing": "billing",
    "account": "account-security",
    "product": "product",
    "general": "general-support",
}
_PRIORITIES = ("low", "normal", "high", "urgent")


def search_knowledge_base(query: str, max_results: int = 3) -> str:
    limit = max(1, min(int(max_results), 10))

    url = os.environ.get("KNOWLEDGE_BASE_URL", "").strip()
    if url:
        headers = {}
        token = os.environ.get("KNOWLEDGE_BASE_API_KEY", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            data = _post_json(url.rstrip("/") + "/search", {"query": query, "max_results": limit}, headers)
        except OSError as exc:
            return json.dumps({"source": "knowledge_base", "error": f"Knowledge base unavailable: {exc}"})
        return json.dumps({"source": "knowledge_base", "articles": list(data.get("results", []))[:limit]})

    words = _words(query)
    scored = []
    for article in _SAMPLE_ARTICLES:
        score = len(words & _words(f"{article['title']} {article['content']}"))
        if score:
            scored.append((score, article))
    scored.sort(key=lambda item: item[0], reverse=True)
    return json.dumps(
        {
            "source": "sample",
            "note": "Built-in sample articles; set KNOWLEDGE_BASE_URL to search your own.",
            "articles": [article for _, article in scored[:limit]],
        }
    )


def analyze_sentiment(message: str) -> str:
    text = message.lower()
    scores = {label: sum(kw in text for kw in keywords) for label, keywords in _SENTIMENT_KEYWORDS.items()}

    letters = [c for c in message if c.isalpha()]
    shouting = len(letters) >= 12 and sum(c.isupper() for c in letters) / len(letters) > 0.6
    if message.count("!") >= 3 or shouting:
        scores["frustrated"] += 2

    label = max(scores, key=scores.__getitem__) if any(scores.values()) else "neutral"
    return json.dumps({"sentiment": label, "scores": scores})


def create_ticket(
    subject: str, category: str = "general", priority: str = "normal", customer_email: str = ""
) -> str:
    category = category.strip().lower()
    if category not in _TEAMS:
        category = "general"
    priority = priority.strip().lower()
    if priority not in _PRIORITIES:
        priority = "normal"

    ticket = {
        "ticket_id": f"TKT-{uuid.uuid4().hex[:8].upper()}",
        "subject": subject.strip()[:200],
        "category": category,
        "team": _TEAMS[category],
        "priority": priority,
        "customer_email": customer_email.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "agntspark-customer-support",
    }

    webhook = os.environ.get("TICKET_WEBHOOK_URL", "").strip()
    if not webhook:
        return json.dumps(
            {
                "ticket": ticket,
                "delivered": False,
                "note": "No TICKET_WEBHOOK_URL is configured, so no team was notified.",
            }
        )
    try:
        _post_json(webhook, ticket, {})
    except OSError as exc:
        return json.dumps({"ticket": ticket, "delivered": False, "error": f"Ticket webhook failed: {exc}"})
    return json.dumps({"ticket": ticket, "delivered": True})


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS}


def _post_json(url: str, payload: dict, headers: dict[str, str]) -> dict:
    if not url.startswith(("https://", "http://")):
        raise OSError(f"unsupported URL {url!r}")
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "agntspark-template", **headers},
    )
    with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT) as resp:
        body = resp.read(1_000_000)
    try:
        data = json.loads(body or b"{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}
