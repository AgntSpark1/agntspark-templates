# Research Assistant Agent Template

An AI agent that conducts web research, summarizes findings, assesses source credibility, and generates formatted citations.

## Features

- **Web Search** — Executes searches via DuckDuckGo's HTML endpoint (no API key required). Falls back to simulated results if the search service is unavailable.
- **Page Fetching** — Fetches and parses web pages using a built-in HTML parser that strips scripts, styles, navigation, and footers. Extracts clean text content.
- **Extractive Summarization** — Frequency-based extractive summarization that identifies the most information-dense sentences. Provides configurable number of key points.
- **Source Credibility Assessment** — Evaluates source credibility based on TLD (.gov/.edu/.mil), known credible domains (Nature, Science, arXiv, NIH, etc.), questionable domain registry, and content heuristics (sensationalist language, anonymous sourcing, content length).
- **Citation Generation** — Generates formatted citations in APA, MLA, and Chicago styles with proper retrieval dates.
- **Finding Synthesis** — Combines findings from multiple sources into a unified summary with confidence scoring, conflict detection (negation-based), and source cross-referencing.

## Configuration

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key for LLM calls | Required in production |
| `SEARCH_API_KEY` | Optional search API key (uses DDG by default) | (empty) |
| `MAX_SOURCES` | Maximum number of sources to fetch per research | `10` |

### LLM Settings

- **Provider:** Anthropic
- **Model:** claude-sonnet-4-20250514
- **Temperature:** 0.3 (low, for factual accuracy)
- **Max Tokens:** 8192

## Usage

### Run in Test Mode

```bash
pip install -r requirements.txt
python agent.py
```

Tests summarization, credibility assessment, citation generation, and synthesis with sample content.

### Deploy with AgntSpark

```bash
agntspark deploy --template ./research-assistant
```

### Programmatic Usage

```python
from agent import ResearchAssistantAgent

agent = ResearchAssistantAgent()
result = agent.research("latest developments in quantum computing", max_sources=5)
print(result["synthesis"]["summary"])
print(result["citations"])
```

## Tools

| Tool | Description |
|---|---|
| `web_search` | Execute web search via DuckDuckGo |
| `fetch_page` | Fetch and parse content from a URL |
| `summarize_content` | Extractive summarization of web content |
| `generate_citations` | Generate APA/MLA/Chicago citations |
| `assess_credibility` | Evaluate source credibility |
| `synthesize_findings` | Combine findings from multiple sources |
| `research` | Full pipeline: search → fetch → summarize → cite → synthesize |

## Credibility Assessment

Sources are evaluated using:

- **TLD check**: .gov, .edu, .mil domains → High credibility
- **Known credible domains**: nature.com, science.org, arxiv.org, NIH, IEEE, etc.
- **Questionable domains**: Flagged domains known for unreliable content
- **Content heuristics**: Sensationalist language detection, anonymous sourcing, content length

## Citation Styles

| Style | Format Example |
|---|---|
| APA | `domain. (2026). Title. Retrieved from https://...` |
| MLA | `"Title." domain, 20 Aug. 2026, https://...` |
| Chicago | `domain, "Title," accessed August 20, 2026, https://...` |
