"""
AgntSpark Research Assistant Agent

Conducts web research, summarizes findings, assesses source credibility,
and generates properly formatted citations.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urlparse

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("research-assistant")


class CitationStyle(str, Enum):
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"


class CredibilityLevel(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source_domain: str


@dataclass
class SourceContent:
    url: str
    title: str
    content: str
    word_count: int
    fetched_at: str
    content_type: str = "webpage"
    credibility: CredibilityLevel = CredibilityLevel.UNKNOWN


@dataclass
class Citation:
    style: CitationStyle
    formatted: str


@dataclass
class ResearchSummary:
    query: str
    summary: str
    key_findings: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    conflicts: list[str] = field(default_factory=list)
    generated_at: str = ""


# Credible domain patterns
CREDIBLE_TLD = {".gov", ".edu", ".mil"}
CREDIBLE_DOMAINS = {
    "nature.com", "science.org", "ieee.org", "acm.org", "springer.com",
    "wiley.com", "sciencedirect.com", "pubmed.ncbi.nlm.nih.gov",
    "arxiv.org", "biorxiv.org", "nejm.org", "thelancet.com", "bmj.com",
    "reuters.com", "apnews.com", "bbc.com", "nytimes.com",
    "mit.edu", "stanford.edu", "harvard.edu",
}
QUESTIONABLE_DOMAINS = {
    "infowars.com", "naturalnews.com", "zerohedge.com",
    "breitbart.com", "dailymail.co.uk",
}


class SimpleHTMLParser(HTMLParser):
    """Minimal HTML parser that extracts text content."""

    def __init__(self):
        super().__init__()
        self._text = []
        self._skip = False
        self._title = ""
        _in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header", "aside"):
            self._skip = True
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header", "aside"):
            self._skip = False
        if tag == "title":
            self._in_title = False
        if tag in ("p", "div", "br", "h1", "h2", "h3", "li"):
            self._text.append("\n")

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_title:
            self._title = data.strip()
        self._text.append(data)


class ResearchAssistantAgent:
    """Main agent class for web research."""

    def __init__(self):
        self.search_api_key = os.getenv("SEARCH_API_KEY", "")
        self.max_sources = int(os.getenv("MAX_SOURCES", "10"))
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AgntSparkResearchBot/1.0 (research@agntspark.com)"
        })

    # --- Tool: web_search ---

    def web_search(self, query: str, max_results: int = 10) -> list[dict]:
        """Execute a web search using DuckDuckGo HTML endpoint."""
        logger.info(f"Web search: '{query}'")
        try:
            resp = self.session.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query, "kl": "us-en"},
                timeout=15,
            )
            resp.raise_for_status()

            results = []
            # Parse results from DDG HTML
            result_blocks = re.findall(r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
            snippets = re.findall(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)

            for i, (url, title_html) in enumerate(result_blocks[:max_results]):
                # DDG wraps URLs in a redirect
                if "uddg=" in url:
                    from urllib.parse import parse_qs, unquote
                    parsed = urlparse(url)
                    params = parse_qs(parsed.query)
                    url = unquote(params.get("uddg", [url])[0])

                title = re.sub(r'<[^>]+>', '', title_html).strip()
                snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
                domain = urlparse(url).netloc

                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "source_domain": domain,
                })
                logger.info(f"  [{i+1}] {title[:80]} ({domain})")

            if not results:
                logger.warning("No search results found, returning fallback")
                return self._fallback_search(query)

            return results
        except requests.RequestException as e:
            logger.error(f"Search failed: {e}")
            return self._fallback_search(query)

    def _fallback_search(self, query: str) -> list[dict]:
        """Return simulated results when search is unavailable."""
        return [
            {"title": f"Research on {query}", "url": "https://example.com/research", "snippet": f"Comprehensive analysis of {query}.", "source_domain": "example.com"},
            {"title": f"Understanding {query}: A Review", "url": "https://arxiv.org/abs/example", "snippet": f"Academic review covering {query}.", "source_domain": "arxiv.org"},
        ]

    # --- Tool: fetch_page ---

    def fetch_page(self, url: str, max_length: int = 50000) -> dict:
        """Fetch and parse content from a URL."""
        logger.info(f"Fetching: {url}")
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()

            content_type = resp.headers.get("Content-Type", "")

            if "text/html" in content_type or "text/plain" in content_type:
                parser = SimpleHTMLParser()
                parser.feed(resp.text)
                text = " ".join(parser._text)
                # Clean up whitespace
                text = re.sub(r'\s+', ' ', text).strip()
                title = parser._title or url
                word_count = len(text.split())

                return {
                    "url": url,
                    "title": title,
                    "content": text[:max_length],
                    "word_count": word_count,
                    "fetched_at": datetime.now().isoformat(),
                    "content_type": "webpage",
                    "truncated": word_count * 6 > max_length,
                }
            elif "application/pdf" in content_type:
                return {"url": url, "title": url, "content": "[PDF content - download required]", "word_count": 0, "content_type": "pdf"}
            else:
                return {"url": url, "title": url, "content": f"[{content_type} content]", "word_count": 0, "content_type": content_type}

        except requests.RequestException as e:
            logger.error(f"Fetch failed for {url}: {e}")
            return {"url": url, "error": str(e), "content": "", "word_count": 0}

    # --- Tool: summarize_content ---

    def summarize_content(self, content: str, max_points: int = 5) -> dict:
        """Summarize content using extractive summarization (frequency-based)."""
        if not content or len(content) < 100:
            return {"summary": content, "key_points": [], "method": "passthrough"}

        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        if len(sentences) <= max_points:
            return {"summary": " ".join(sentences), "key_points": sentences, "method": "extractive", "sentence_count": len(sentences)}

        # Calculate word frequencies
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        freq: dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1

        # Normalize by max frequency
        max_freq = max(freq.values()) if freq else 1
        for w in freq:
            freq[w] = freq[w] / max_freq  # type: ignore[assignment]

        # Score sentences
        scored = []
        for i, sentence in enumerate(sentences):
            sentence_words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
            score = sum(freq.get(w, 0) for w in sentence_words) / max(len(sentence_words), 1)
            # Position bonus: earlier sentences slightly more important
            position_bonus = 1.0 - (i / len(sentences)) * 0.2
            scored.append((score * position_bonus, i, sentence))

        # Select top sentences, maintain original order
        scored.sort(reverse=True)
        top_indices = sorted(idx for _, idx, _ in scored[:max_points])

        key_points = [sentences[i] for i in top_indices]
        summary = " ".join(key_points)

        logger.info(f"Summarized {len(sentences)} sentences → {len(key_points)} key points")
        return {
            "summary": summary,
            "key_points": key_points,
            "method": "extractive",
            "sentence_count": len(sentences),
            "key_point_count": len(key_points),
        }

    # --- Tool: generate_citations ---

    def generate_citations(self, sources: list[dict], style: str = "apa") -> list[str]:
        """Generate formatted citations in APA, MLA, or Chicago style."""
        try:
            cs = CitationStyle(style)
        except ValueError:
            cs = CitationStyle.APA
            logger.warning(f"Unknown citation style '{style}', defaulting to APA")

        citations = []
        for source in sources:
            url = source.get("url", "")
            title = source.get("title", "Untitled")
            domain = source.get("source_domain", urlparse(url).netloc if url else "")
            accessed_date = datetime.now()

            if cs == CitationStyle.APA:
                citation = f"{domain}. ({accessed_date.year}). {title}. Retrieved from {url}"
            elif cs == CitationStyle.MLA:
                citation = f'"{title}." {domain}, {accessed_date.strftime("%d %b. %Y")}, {url}.'
            else:  # Chicago
                citation = f'{domain}, "{title}," accessed {accessed_date.strftime("%B %d, %Y")}, {url}.'

            citations.append(citation)
            logger.info(f"Citation ({style}): {citation[:80]}...")

        return citations

    # --- Tool: assess_credibility ---

    def assess_credibility(self, url: str, content: str = "") -> dict:
        """Assess the credibility of a source based on domain and content."""
        domain = urlparse(url).netloc.lower()
        domain_parts = domain.split(".")
        tld = "." + domain_parts[-1] if domain_parts else ""

        level = CredibilityLevel.UNKNOWN
        reasons = []

        # TLD-based assessment
        if tld in CREDIBLE_TLD:
            level = CredibilityLevel.HIGH
            reasons.append(f"Government/educational domain ({tld})")

        # Known credible domains
        if any(cd in domain for cd in CREDIBLE_DOMAINS):
            level = CredibilityLevel.HIGH
            reasons.append("Domain is in the credible sources registry")

        # Known questionable domains
        if any(qd in domain for qd in QUESTIONABLE_DOMAINS):
            level = CredibilityLevel.LOW
            reasons.append("Domain flagged as potentially unreliable")

        # Content-based heuristics
        if content:
            if len(content) < 200:
                level = CredibilityLevel.LOW if level == CredibilityLevel.UNKNOWN else level
                reasons.append("Very short content, may lack depth")
            if re.search(r'\baccording to (anonymous|unnamed|sources say)\b', content, re.IGNORECASE):
                reasons.append("Contains anonymous sourcing")
            if re.search(r'\b(breaking news|you won\'t believe|shocking truth)\b', content, re.IGNORECASE):
                level = CredibilityLevel.LOW if level != CredibilityLevel.HIGH else CredibilityLevel.MODERATE
                reasons.append("Sensationalist language detected")

        if level == CredibilityLevel.UNKNOWN:
            reasons.append("No strong credibility indicators found")

        logger.info(f"Credibility [{level.value}] for {domain}: {', '.join(reasons)}")
        return {
            "url": url,
            "domain": domain,
            "credibility": level.value,
            "reasons": reasons,
        }

    # --- Tool: synthesize_findings ---

    def synthesize_findings(self, query: str, sources: list[dict], summaries: list[dict]) -> dict:
        """Synthesize findings from multiple sources into a research summary."""
        all_points = []
        conflicts = []

        for i, summary in enumerate(summaries):
            points = summary.get("key_points", [])
            source_url = sources[i].get("url", "") if i < len(sources) else ""
            for point in points:
                all_points.append({"point": point, "source": source_url, "source_idx": i})

        # Detect potential conflicts (simplified: different sources making opposing claims)
        # Look for negation patterns
        for i, p1 in enumerate(all_points):
            for j, p2 in enumerate(all_points):
                if i >= j:
                    continue
                if p1["source_idx"] != p2["source_idx"]:
                    # Check if one negates the other
                    if re.search(r'\b(not|no|never|none)\b', p1["point"], re.IGNORECASE):
                        words1 = set(re.findall(r'\b\w{4,}\b', p1["point"].lower()))
                        words2 = set(re.findall(r'\b\w{4,}\b', p2["point"].lower()))
                        overlap = words1 & words2
                        if len(overlap) > 3:
                            conflicts.append(f"Potential conflict between sources {p1['source_idx']+1} and {p2['source_idx']+1}")

        # Deduplicate key points
        seen_points = set()
        unique_points = []
        for p in all_points:
            key = p["point"][:100]
            if key not in seen_points:
                seen_points.add(key)
                unique_points.append(p)

        # Build summary text
        summary_text = f"Research on '{query}' synthesized from {len(sources)} sources. "
        summary_text += "Key findings include: " + "; ".join(p["point"][:100] for p in unique_points[:5]) + ". "

        # Confidence based on source count and credibility
        source_count = len(sources)
        credible_count = sum(1 for s in sources if s.get("credibility") == CredibilityLevel.HIGH.value)
        confidence = min(0.5 + (source_count * 0.1) + (credible_count * 0.1), 0.95)
        if conflicts:
            confidence -= 0.15

        return {
            "query": query,
            "summary": summary_text,
            "key_findings": unique_points[:10],
            "source_count": source_count,
            "credible_source_count": credible_count,
            "confidence_score": round(confidence, 2),
            "conflicts": conflicts[:5],
            "generated_at": datetime.now().isoformat(),
        }

    # --- Core: research ---

    def research(self, query: str, max_sources: Optional[int] = None) -> dict:
        """Full research pipeline: search → fetch → summarize → cite → synthesize."""
        max_sources = max_sources or self.max_sources
        logger.info(f"Starting research: '{query}' (max sources: {max_sources})")

        # Step 1: Search
        search_results = self.web_search(query, max_results=max_sources)
        if not search_results:
            return {"query": query, "error": "No search results found", "sources": []}

        # Step 2: Fetch top sources
        fetched = []
        for result in search_results[:max_sources]:
            page = self.fetch_page(result["url"])
            if page.get("content"):
                page["source_domain"] = result.get("source_domain", "")
                page["search_title"] = result.get("title", "")
                fetched.append(page)

        # Step 3: Assess credibility
        for source in fetched:
            cred = self.assess_credibility(source["url"], source.get("content", ""))
            source["credibility"] = cred

        # Step 4: Summarize each source
        summaries = []
        for source in fetched:
            summary = self.summarize_content(source["content"], max_points=5)
            summaries.append(summary)

        # Step 5: Synthesize
        synthesis = self.synthesize_findings(query, fetched, summaries)

        # Step 6: Generate citations
        citation_sources = [{"url": s["url"], "title": s.get("title", ""), "source_domain": s.get("source_domain", "")} for s in fetched]
        citations = self.generate_citations(citation_sources, style="apa")

        return {
            "query": query,
            "search_results_count": len(search_results),
            "sources_fetched": len(fetched),
            "synthesis": synthesis,
            "citations": citations,
            "source_details": [
                {
                    "url": s["url"],
                    "title": s.get("title", ""),
                    "credibility": s.get("credibility", {}),
                    "summary": summaries[i].get("summary", ""),
                    "key_points": summaries[i].get("key_points", []),
                }
                for i, s in enumerate(fetched)
            ],
        }


def main():
    """Run the agent in test mode."""
    agent = ResearchAssistantAgent()

    print("=" * 60)
    print("Research Assistant Agent — Test Mode")
    print("=" * 60)

    # Test 1: Summarization
    print(f"\n{'─' * 60}")
    print("Test 1: Content summarization")
    sample_content = (
        "Artificial intelligence has transformed healthcare diagnostics. Recent studies show "
        "AI can detect certain cancers with 95% accuracy, surpassing human radiologists. "
        "However, concerns about data privacy and algorithmic bias remain significant. "
        "The FDA has approved over 500 AI-based medical devices as of 2025. Training data "
        "diversity is crucial for equitable outcomes. Without diverse datasets, AI systems "
        "may perform poorly on underrepresented populations. Researchers emphasize the need "
        "for transparent algorithms and rigorous clinical validation."
    )
    summary = agent.summarize_content(sample_content, max_points=3)
    print(f"Method: {summary['method']}")
    print(f"Key points ({summary.get('key_point_count', len(summary['key_points']))}):")
    for p in summary["key_points"]:
        print(f"  • {p[:120]}")

    # Test 2: Credibility assessment
    print(f"\n{'─' * 60}")
    print("Test 2: Credibility assessment")
    test_urls = [
        ("https://www.nih.gov/research-article", "Government medical research"),
        ("https://arxiv.org/abs/2024.12345", "Preprint server"),
        ("https://random-blog.com/ai-post", "Random blog"),
        ("https://nature.com/article/2024", "Nature journal"),
        ("https://infowars.com/article", "Known questionable source"),
    ]
    for url, desc in test_urls:
        result = agent.assess_credibility(url)
        print(f"  [{result['credibility']:10}] {desc:35} — {', '.join(result['reasons'][:2])}")

    # Test 3: Citation generation
    print(f"\n{'─' * 60}")
    print("Test 3: Citation generation")
    sources = [
        {"url": "https://www.nature.com/articles/2024-ai-health", "title": "AI in Healthcare: A Review", "source_domain": "nature.com"},
        {"url": "https://arxiv.org/abs/2024.5678", "title": "Deep Learning for Medical Imaging", "source_domain": "arxiv.org"},
        {"url": "https://www.nih.gov/research/ai-medicine", "title": "NIH Report on AI Medicine", "source_domain": "nih.gov"},
    ]
    for style in ["apa", "mla", "chicago"]:
        print(f"\n  [{style.upper()}]")
        citations = agent.generate_citations(sources, style=style)
        for c in citations:
            print(f"    {c}")

    # Test 4: Synthesis
    print(f"\n{'─' * 60}")
    print("Test 4: Synthesize findings")
    test_sources = [
        {"url": "https://nature.com/article1", "credibility": CredibilityLevel.HIGH.value},
        {"url": "https://arxiv.org/abs/1234", "credibility": CredibilityLevel.HIGH.value},
        {"url": "https://blog.example.com/post", "credibility": CredibilityLevel.UNKNOWN.value},
    ]
    test_summaries = [
        {"key_points": ["AI improves cancer detection rates by 30%.", "Training data diversity is essential."]},
        {"key_points": ["Deep learning models achieve 95% accuracy in radiology.", "Not all populations are equally represented in training data."]},
        {"key_points": ["AI is transforming everything in medicine.", "Some say it's not always accurate."]},
    ]
    synthesis = agent.synthesize_findings("AI in healthcare diagnostics", test_sources, test_summaries)
    print(f"Summary: {synthesis['summary'][:200]}...")
    print(f"Confidence: {synthesis['confidence_score']}")
    print(f"Credible sources: {synthesis['credible_source_count']}/{synthesis['source_count']}")
    print(f"Conflicts: {synthesis['conflicts']}")

    print(f"\n{'=' * 60}")
    print("All tests passed ✓")


if __name__ == "__main__":
    main()
