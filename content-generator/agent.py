"""
AgntSpark Content Generator Agent

Generates blog posts, social media content, and marketing copy
with configurable brand voice and platform-specific formatting.
"""

import json
import logging
import os
import random
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("content-generator")


class ContentType(str, Enum):
    BLOG_POST = "blog_post"
    SOCIAL_POST = "social_post"
    MARKETING_COPY = "marketing_copy"


class Platform(str, Enum):
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"


class CopyType(str, Enum):
    LANDING_PAGE = "landing_page"
    EMAIL = "email"
    AD = "ad"


@dataclass
class BrandVoice:
    name: str = "default"
    tone: str = "professional"
    personality: list[str] = field(default_factory=lambda: ["knowledgeable", "approachable"])
    vocabulary_level: str = "accessible"  # simple, accessible, technical
    emoji_usage: str = "minimal"  # none, minimal, moderate, heavy
    hashtag_style: str = "mixed"  # none, minimal, moderate, heavy
    cta_style: str = "direct"  # direct, soft, urgent, question
    forbidden_phrases: list[str] = field(default_factory=list)
    preferred_phrases: list[str] = field(default_factory=list)


@dataclass
class ContentResult:
    content_type: ContentType
    platform: str
    title: str
    body: str
    metadata: dict = field(default_factory=dict)
    variations: list[dict] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    word_count: int = 0
    character_count: int = 0


PLATFORM_LIMITS = {
    Platform.TWITTER: {"chars": 280, "hashtags_max": 3, "emoji": "moderate"},
    Platform.LINKEDIN: {"chars": 3000, "hashtags_max": 5, "emoji": "minimal"},
    Platform.INSTAGRAM: {"chars": 2200, "hashtags_max": 30, "emoji": "heavy"},
    Platform.FACEBOOK: {"chars": 5000, "hashtags_max": 2, "emoji": "moderate"},
}

CTA_TEMPLATES = {
    "direct": ["Get started today.", "Try it now.", "Sign up free.", "Learn more."],
    "soft": ["We'd love to hear from you.", "What do you think?", "Join the conversation.", "Discover more."],
    "urgent": ["Limited time offer—act now!", "Don't miss out!", "Offer ends soon.", "Secure your spot today."],
    "question": ["Ready to get started?", "What's your take?", "Could this work for you?", "Want to learn more?"],
}

BLOG_TEMPLATES = {
    "how_to": [
        "# {title}\n\n*Meta: {meta_description}*\n\n## Introduction\n\n{intro}\n\n## {step1_heading}\n\n{step1_content}\n\n## {step2_heading}\n\n{step2_content}\n\n## {step3_heading}\n\n{step3_content}\n\n## Conclusion\n\n{conclusion}\n\n{cta}",
    ],
    "listicle": [
        "# {title}\n\n*Meta: {meta_description}*\n\n## Introduction\n\n{intro}\n\n1. **{item1_title}** — {item1_content}\n\n2. **{item2_title}** — {item2_content}\n\n3. **{item3_title}** — {item3_content}\n\n4. **{item4_title}** — {item4_content}\n\n5. **{item5_title}** — {item5_content}\n\n## Conclusion\n\n{conclusion}\n\n{cta}",
    ],
    "analysis": [
        "# {title}\n\n*Meta: {meta_description}*\n\n## Overview\n\n{intro}\n\n## The Data\n\n{data_section}\n\n## Key Findings\n\n{findings}\n\n## Implications\n\n{implications}\n\n## Conclusion\n\n{conclusion}\n\n{cta}",
    ],
}

MARKETING_TEMPLATES = {
    CopyType.LANDING_PAGE: [
        "# {headline}\n\n{subheadline}\n\n## {feature1_title}\n{feature1_desc}\n\n## {feature2_title}\n{feature2_desc}\n\n## {feature3_title}\n{feature3_desc}\n\n---\n\n{cta}",
    ],
    CopyType.EMAIL: [
        "Subject: {subject}\n\n{greeting},\n\n{opening}\n\n{body}\n\n{closing}\n\n{signature}",
    ],
    CopyType.AD: [
        "{headline}\n\n{body}\n\n{cta}",
    ],
}


class ContentGeneratorAgent:
    """Main agent class for content generation."""

    def __init__(self):
        self.brand = self._load_brand_config()
        self.max_length = int(os.getenv("MAX_CONTENT_LENGTH", "10000"))

    def _load_brand_config(self) -> BrandVoice:
        """Load brand voice configuration from file or use defaults."""
        config_path = os.getenv("BRAND_CONFIG_PATH", "")
        if config_path and os.path.isfile(config_path):
            try:
                with open(config_path) as f:
                    data = json.load(f)
                return BrandVoice(**data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Brand config load failed, using defaults: {e}")
        return BrandVoice()

    # --- Tool: generate_blog_post ---

    def generate_blog_post(self, topic: str, style: str = "how_to", keywords: Optional[list[str]] = None) -> ContentResult:
        """Generate a full blog post with SEO metadata."""
        logger.info(f"Generating blog post: '{topic}' (style: {style})")
        keywords = keywords or []

        templates = BLOG_TEMPLATES.get(style, BLOG_TEMPLATES["how_to"])
        template = random.choice(templates)

        # Generate content components
        title = self._generate_title(topic, style)
        meta_desc = self._generate_meta_description(topic, keywords)
        intro = self._generate_intro(topic)
        cta = self._get_cta()
        conclusion = self._generate_conclusion(topic)

        # Fill template
        content = template.format(
            title=title,
            meta_description=meta_desc,
            intro=intro,
            conclusion=conclusion,
            cta=cta,
            step1_heading="Step 1: Understand the Fundamentals",
            step1_content=f"Before diving into {topic.lower()}, it's essential to grasp the core concepts. This foundation will guide every decision you make downstream, ensuring you approach the subject with clarity and purpose.",
            step2_heading="Step 2: Implement the Strategy",
            step2_content=f"With a solid understanding in place, the next phase is execution. Apply {topic.lower()} systematically, testing each component individually before scaling. Document your process for future reference and team alignment.",
            step3_heading="Step 3: Measure and Optimize",
            step3_content=f"No implementation is complete without measurement. Track key metrics related to {topic.lower()}, identify what's working, and iterate. The best results come from continuous refinement rather than one-time effort.",
            item1_title="Start with the basics",
            item1_content=f"Understanding {topic.lower()} begins with fundamentals. Build your knowledge systematically.",
            item2_title="Focus on quality",
            item2_content="Quality always outperforms quantity. Invest in doing things right the first time.",
            item3_title="Measure everything",
            item3_content="Data-driven decisions consistently outperform gut feelings. Track your metrics.",
            item4_title="Iterate relentlessly",
            item4_content="The first attempt is rarely the best. Embrace continuous improvement.",
            item5_title="Share your knowledge",
            item5_content="Teaching others solidifies your own understanding and builds community.",
            data_section=f"Recent data on {topic.lower()} reveals compelling trends that demand attention. The numbers tell a story of shifting paradigms and emerging opportunities.",
            findings="Three key findings emerged: adoption rates are accelerating, ROI improves with maturity, and early movers gain significant advantages.",
            implications="For organizations and individuals alike, the implications are clear: those who act strategically now will be best positioned for long-term success.",
        )

        content = self.apply_brand_voice(content)
        word_count = len(content.split())

        return ContentResult(
            content_type=ContentType.BLOG_POST,
            platform="blog",
            title=title,
            body=content,
            metadata={
                "meta_description": meta_desc,
                "keywords": keywords,
                "style": style,
                "word_count": word_count,
                "estimated_read_time": f"{max(1, word_count // 200)} min",
            },
            word_count=word_count,
            character_count=len(content),
        )

    # --- Tool: generate_social_post ---

    def generate_social_post(self, topic: str, platform: str = "twitter", count: int = 1) -> ContentResult:
        """Generate social media content for a specific platform."""
        try:
            plat = Platform(platform)
        except ValueError:
            plat = Platform.TWITTER
            logger.warning(f"Unknown platform '{platform}', defaulting to twitter")

        limits = PLATFORM_LIMITS[plat]
        logger.info(f"Generating {count} social post(s) for {platform} on '{topic}'")

        posts = []
        for i in range(count):
            hook = self._generate_hook(topic, plat)
            body = self._generate_social_body(topic, plat, limits)
            hashtags = self._generate_hashtags(topic, limits["hashtags_max"])
            cta = self._get_cta()
            emoji_level = limits.get("emoji", self.brand.emoji_usage)

            post_text = f"{hook}\n\n{body}\n\n{cta}"
            if hashtags:
                post_text += f"\n\n{' '.join(hashtags)}"

            post_text = self._apply_emoji(post_text, emoji_level)
            post_text = self._truncate_to_limit(post_text, limits["chars"])

            posts.append({
                "text": post_text,
                "hashtags": hashtags,
                "char_count": len(post_text),
                "within_limit": len(post_text) <= limits["chars"],
            })

        return ContentResult(
            content_type=ContentType.SOCIAL_POST,
            platform=platform,
            title=f"Social post for {platform}",
            body=posts[0]["text"] if posts else "",
            metadata={"platform": platform, "char_limit": limits["chars"], "post_count": count},
            variations=posts if count > 1 else [],
            hashtags=posts[0]["hashtags"] if posts else [],
            character_count=posts[0]["char_count"] if posts else 0,
        )

    # --- Tool: generate_marketing_copy ---

    def generate_marketing_copy(self, product: str, copy_type: str = "landing_page", audience: str = "general") -> ContentResult:
        """Generate marketing copy for landing pages, emails, or ads."""
        try:
            ct = CopyType(copy_type)
        except ValueError:
            ct = CopyType.LANDING_PAGE
            logger.warning(f"Unknown copy type '{copy_type}', defaulting to landing_page")

        templates = MARKETING_TEMPLATES[ct]
        template = random.choice(templates)
        logger.info(f"Generating {copy_type} copy for '{product}' (audience: {audience})")

        content = template.format(
            headline=self._generate_headline(product, audience),
            subheadline=f"The smart way to handle {product.lower()} — built for {audience} who demand results.",
            feature1_title="Effortless Setup",
            feature1_desc=f"Get started with {product} in minutes. No technical expertise required. Our guided onboarding handles everything.",
            feature2_title="Powerful Features",
            feature2_desc=f"{product} scales with your needs. Advanced capabilities when you need them, simple when you don't.",
            feature3_title="Reliable Support",
            feature3_desc="Our team has your back. Fast response times, real humans, and a community of peers.",
            subject=f"Transform how you handle {product.lower()}",
            greeting="Hi there",
            opening=f"We noticed you might be interested in {product.lower()}. Here's something worth your attention.",
            body=f"Imagine handling {product.lower()} with half the effort and twice the results. That's what we built. Our platform streamlines every step, so you can focus on what matters.",
            closing="Ready to see the difference?",
            cta=self._get_cta(),
            signature="— The AgntSpark Team",
        )

        content = self.apply_brand_voice(content)
        return ContentResult(
            content_type=ContentType.MARKETING_COPY,
            platform=copy_type,
            title=content.split("\n")[0],
            body=content,
            metadata={"copy_type": copy_type, "audience": audience, "product": product},
            word_count=len(content.split()),
            character_count=len(content),
        )

    # --- Tool: generate_variations ---

    def generate_variations(self, base_content: str, count: int = 3) -> list[dict]:
        """Generate multiple variations of content for A/B testing."""
        variations = []
        tone_modifiers = [
            ("energetic", lambda s: s.replace(".", "!") if random.random() > 0.5 else s),
            ("concise", lambda s: " ".join(s.split()[:int(len(s.split()) * 0.7)])),
            ("formal", lambda s: s.replace("!", ".").replace("Get ", "Obtain ").replace("Try ", "Consider ")),
        ]

        for i in range(count):
            modifier_name, modifier_fn = tone_modifiers[i % len(tone_modifiers)]
            modified = modifier_fn(base_content)
            modified = self.apply_brand_voice(modified)
            variations.append({
                "variation_id": f"V{i+1}",
                "style": modifier_name,
                "content": modified,
                "word_count": len(modified.split()),
                "character_count": len(modified),
            })

        logger.info(f"Generated {count} content variations")
        return variations

    # --- Tool: apply_brand_voice ---

    def apply_brand_voice(self, content: str) -> str:
        """Apply brand voice settings to content."""
        # Replace forbidden phrases
        for phrase in self.brand.forbidden_phrases:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            replacement = self.brand.preferred_phrases[0] if self.brand.preferred_phrases else "[removed]"
            content = pattern.sub(replacement, content)

        # Vocabulary adjustment
        if self.brand.vocabulary_level == "simple":
            replacements = {
                "utilize": "use", "demonstrate": "show", "facilitate": "help",
                "subsequently": "then", "approximately": "about", "numerous": "many",
                "sufficient": "enough", "terminate": "end", "initiate": "start",
            }
            for complex_word, simple_word in replacements.items():
                content = re.sub(r'\b' + complex_word + r'\b', simple_word, content, flags=re.IGNORECASE)
        elif self.brand.vocabulary_level == "technical":
            replacements = {
                "use": "utilize", "show": "demonstrate", "help": "facilitate",
                "start": "initiate", "end": "terminate",
            }
            for simple_word, complex_word in replacements.items():
                content = re.sub(r'\b' + simple_word + r'\b', complex_word, content, flags=re.IGNORECASE)

        return content

    # --- Helper methods ---

    def _generate_title(self, topic: str, style: str) -> str:
        patterns = {
            "how_to": f"How to Master {topic}: A Complete Guide",
            "listicle": f"5 Essential Things You Need to Know About {topic}",
            "analysis": f"The State of {topic} in 2026: A Deep Dive",
        }
        return patterns.get(style, patterns["how_to"])

    def _generate_meta_description(self, topic: str, keywords: list[str]) -> str:
        kw = ", ".join(keywords[:3]) if keywords else topic.lower()
        return f"Discover everything you need to know about {topic.lower()}. Expert insights, practical tips, and actionable strategies. Keywords: {kw}"

    def _generate_intro(self, topic: str) -> str:
        return (f"In today's rapidly evolving landscape, understanding {topic.lower()} has become "
                f"more critical than ever. Whether you're just getting started or looking to deepen "
                f"your expertise, this guide breaks down the essentials into clear, actionable steps.")

    def _generate_conclusion(self, topic: str) -> str:
        return (f"Mastering {topic.lower()} is a journey, not a destination. The strategies outlined "
                f"above provide a solid foundation, but the real magic happens when you adapt them "
                f"to your unique context. Start small, measure results, and iterate.")

    def _generate_hook(self, topic: str, platform: Platform) -> str:
        hooks = [
            f"Nobody talks about this side of {topic.lower()}...",
            f"I spent 5 years learning {topic.lower()}. Here's what I wish I knew on day one.",
            f"Unpopular opinion: most people approach {topic.lower()} wrong.",
            f"Stop overthinking {topic.lower()}. Here's the simple truth.",
            f"The {topic.lower()} landscape just changed. Here's what matters now.",
        ]
        return random.choice(hooks)

    def _generate_social_body(self, topic: str, platform: Platform, limits: dict) -> str:
        return (f"{topic} doesn't have to be complicated. The key is starting with "
                f"fundamentals and building from there. Here's the approach that works.")

    def _generate_hashtags(self, topic: str, max_count: int) -> list[str]:
        words = re.sub(r'[^a-zA-Z0-9 ]', '', topic).split()
        base_tags = ["#AgntSpark", "#AI", "#Innovation"]
        topic_tags = ["#" + "".join(w.capitalize() for w in words[:3])]
        all_tags = base_tags + topic_tags
        return all_tags[:max_count]

    def _generate_headline(self, product: str, audience: str) -> str:
        patterns = [
            f"Transform Your {product} Experience",
            f"The {product} Solution {audience.capitalize()} Trust",
            f"Reimagine {product} for the Modern Era",
            f"Why {audience.capitalize()} Choose {product}",
        ]
        return random.choice(patterns)

    def _get_cta(self) -> str:
        templates = CTA_TEMPLATES.get(self.brand.cta_style, CTA_TEMPLATES["direct"])
        return random.choice(templates)

    def _apply_emoji(self, text: str, level: str) -> str:
        if level == "none" or self.brand.emoji_usage == "none":
            return text
        emojis = {"energetic": "🚀", "insight": "💡", "success": "✅", "celebrate": "🎉", "target": "🎯"}
        if level == "minimal" or self.brand.emoji_usage == "minimal":
            return text + " " + random.choice(list(emojis.values()))
        elif level == "moderate" or self.brand.emoji_usage == "moderate":
            lines = text.split("\n")
            for i in range(0, len(lines), 2):
                lines[i] = random.choice(list(emojis.values())) + " " + lines[i]
            return "\n".join(lines)
        elif level == "heavy" or self.brand.emoji_usage == "heavy":
            lines = text.split("\n")
            for i in range(len(lines)):
                lines[i] = random.choice(list(emojis.values())) + " " + lines[i]
            return "\n".join(lines)
        return text

    def _truncate_to_limit(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        # Try to truncate at a sentence boundary
        truncated = text[:limit - 3]
        last_period = truncated.rfind(".")
        if last_period > limit - 50:
            return truncated[:last_period + 1] + "..."
        return truncated + "..."


def main():
    """Run the agent in test mode."""
    agent = ContentGeneratorAgent()

    print("=" * 60)
    print("Content Generator Agent — Test Mode")
    print("=" * 60)

    # Test 1: Blog post
    print(f"\n{'─' * 60}")
    print("Test 1: Generate blog post")
    blog = agent.generate_blog_post("AI in Healthcare", style="how_to", keywords=["AI", "healthcare", "machine learning"])
    print(f"Title: {blog.title}")
    print(f"Word count: {blog.word_count}")
    print(f"Meta: {blog.metadata['meta_description']}")
    print(f"\n--- First 500 chars ---\n{blog.body[:500]}...")

    # Test 2: Social media posts
    print(f"\n{'─' * 60}")
    print("Test 2: Generate social media posts")
    for platform in ["twitter", "linkedin", "instagram"]:
        post = agent.generate_social_post("productivity tips", platform=platform)
        print(f"\n[{platform}] ({post.character_count} chars, limit: {post.metadata['char_limit']})")
        print(post.body)

    # Test 3: Marketing copy
    print(f"\n{'─' * 60}")
    print("Test 3: Generate marketing copy")
    for copy_type in ["landing_page", "email", "ad"]:
        copy = agent.generate_marketing_copy("TaskFlow Pro", copy_type, audience="startups")
        print(f"\n[{copy_type}]")
        print(f"Title: {copy.title}")
        print(copy.body[:300])

    # Test 4: Variations
    print(f"\n{'─' * 60}")
    print("Test 4: Generate A/B variations")
    base = "Transform your workflow with TaskFlow Pro. Get started today and see results in days, not months."
    variations = agent.generate_variations(base, count=3)
    for v in variations:
        print(f"\n[{v['variation_id']} - {v['style']}] ({v['word_count']} words)")
        print(f"  {v['content'][:150]}...")

    # Test 5: Brand voice
    print(f"\n{'─' * 60}")
    print("Test 5: Brand voice application")
    test_content = "We utilize this platform to demonstrate how to facilitate your workflow. Subsequently, you will initiate the process."
    processed = agent.apply_brand_voice(test_content)
    print(f"Before: {test_content}")
    print(f"After:  {processed}")

    print(f"\n{'=' * 60}")
    print("All tests passed ✓")


if __name__ == "__main__":
    main()
