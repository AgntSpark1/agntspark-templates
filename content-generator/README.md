# Content Generator Agent Template

An AI agent that generates blog posts, social media content, and marketing copy with configurable brand voice.

## Features

- **Blog Post Generation** — Creates full blog posts in multiple styles (how-to, listicle, analysis) with SEO metadata including meta descriptions, keywords, and estimated read time.
- **Multi-Platform Social Content** — Generates platform-specific posts for Twitter/X, LinkedIn, Instagram, and Facebook with automatic character limit enforcement.
- **Marketing Copy** — Creates landing page copy, email campaigns, and ad copy with audience targeting.
- **A/B Variations** — Generates multiple content variations in different tones (energetic, concise, formal) for A/B testing.
- **Brand Voice Engine** — Configurable brand voice with tone, vocabulary level, emoji usage, hashtag style, CTA style, and forbidden/preferred phrase lists.
- **Smart Truncation** — Truncates content at sentence boundaries to respect platform character limits.

## Configuration

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key for LLM calls | Required in production |
| `BRAND_CONFIG_PATH` | Path to brand voice JSON config file | (empty = defaults) |
| `MAX_CONTENT_LENGTH` | Maximum content length in characters | `10000` |

### Brand Voice Configuration

Create a JSON file (e.g., `brand.json`) and point `BRAND_CONFIG_PATH` to it:

```json
{
  "name": "my-brand",
  "tone": "casual",
  "personality": ["friendly", "witty", "knowledgeable"],
  "vocabulary_level": "simple",
  "emoji_usage": "moderate",
  "hashtag_style": "moderate",
  "cta_style": "question",
  "forbidden_phrases": ["synergy", "leverage"],
  "preferred_phrases": ["collaborate", "use"]
}
```

### LLM Settings

- **Provider:** OpenAI
- **Model:** gpt-4o
- **Temperature:** 0.8 (high, for creative variety)
- **Max Tokens:** 8192

## Usage

### Run in Test Mode

```bash
python agent.py
```

Runs all content generation capabilities with sample topics and prints results.

### Deploy with AgntSpark

```bash
agntspark deploy --template ./content-generator
```

### Programmatic Usage

```python
from agent import ContentGeneratorAgent

agent = ContentGeneratorAgent()
blog = agent.generate_blog_post("AI in Healthcare", style="how_to", keywords=["AI", "healthcare"])
tweet = agent.generate_social_post("productivity tips", platform="twitter")
```

## Tools

| Tool | Description |
|---|---|
| `generate_blog_post` | Create SEO-optimized blog posts (how_to, listicle, analysis) |
| `generate_social_post` | Create platform-specific social media content |
| `generate_marketing_copy` | Create landing page, email, or ad copy |
| `generate_variations` | Generate A/B test variations with different tones |
| `apply_brand_voice` | Apply brand voice rules to any content |

## Platform Limits

| Platform | Char Limit | Max Hashtags | Emoji Level |
|---|---|---|---|
| Twitter/X | 280 | 3 | Moderate |
| LinkedIn | 3,000 | 5 | Minimal |
| Instagram | 2,200 | 30 | Heavy |
| Facebook | 5,000 | 2 | Moderate |
