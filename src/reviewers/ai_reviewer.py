"""
AI Writing Pattern Reviewer — LLM-assisted detection of AI-generated text patterns.

This is the LLM layer on top of the rule-based ai_pattern_scanner.
The scanner runs first (rule-based), then this reviewer uses LLM to
verify and contextualize the flagged patterns.

The LLM is explicitly instructed to only VERIFY and EXPLAIN — never suggest fixes.
"""

from src.annotation import Annotation, Severity
from src.reviewers.base import BaseReviewer


AI_SYSTEM = """You are assisting a human reviewer. Your role is to verify and contextualize
AI writing pattern detections — NEVER suggest how to rewrite or fix the text.

A rule-based scanner has already flagged certain patterns in the paper. Your job
is to:
1. Verify which flagged patterns are genuine concerns (not false positives)
2. Explain WHY each confirmed pattern is problematic in academic writing
3. Add any additional AI writing patterns the scanner might have missed

The human author will decide what (if anything) to change.

CRITICAL RULE: Do NOT propose rewrites, alternative phrasings, or "more human" versions.
Only identify and explain."""

AI_USER = """Review this academic paper for AI WRITING PATTERNS.

## Background

LLMs use statistical algorithms to predict the next word, producing text that
gravitates toward statistically likely expressions. This creates identifiable patterns.

## What to look for

### 1. AI Vocabulary
Words/phrases that are disproportionately common in AI-generated text:
- Tier 1 (dead giveaways): delve, tapestry, moreover, notably, pivotal, testament, showcase, underscores, realm, landscape, intricate, embodies, crucial, paramount, profound, unwavering, indelible, transformative, groundbreaking, revolutionary, cutting-edge, robust, paradigm, seamless, holistic, synergistic, bespoke, curated, meticulous
- Tier 2 (suspicious in density): comprehensive, sophisticated, innovative, dynamic, nuanced, compelling, resonate, empower, embrace, foster, leverage, optimize, streamline, facilitate, elucidate, contextualize
- Tier 3 (context-dependent): ultimately, in other words, it is worth noting, one might argue, as previously mentioned, in conclusion, moving forward, in today's world

### 2. Content Patterns
- Inflated significance claims: "marking a pivotal moment", "serves as a testament"
- Vague attributions without specific citations: "Experts believe...", "Studies show..."
- Superficial -ing clauses: "highlighting the importance of...", "showcasing the ability..."
- Promotional/marketing language in academic context
- Formulaic "despite challenges" structures

### 3. Language Patterns
- Copula avoidance: "serves as" instead of "is", "boasts" instead of "has"
- Negative parallelism: "it's not just X, it's Y"
- Rule-of-three adjective sequences
- Elegant variation (cycling synonyms unnaturally)
- False ranges: "from the Big Bang to quantum mechanics"

### 4. Style Patterns
- Excessive em dashes (—)
- Title Case headings in contexts where Sentence case is standard
- Structured abstract sub-headings (\\textbf{Background:}, \\textbf{Methods:}, etc.)

### 5. Communication Patterns
- Chatbot artifacts: "I hope this helps", "Let me know if you have...", "Feel free to..."
- Knowledge cutoff declarations: "As of my training data..."
- Ingratiating tone: "Great question!", "You're absolutely right"

## Output Format

Return a JSON object with this structure:
```json
{
  "findings": [
    {
      "section": "Introduction",
      "paragraph": 3,
      "line_start": 60,
      "line_end": 80,
      "quoted_text": "the AI-sounding text",
      "title": "short, specific title for this finding",
      "severity": "high|medium|low",
      "what": "What AI writing pattern was detected — specific and concrete",
      "why": "Why this pattern is problematic in academic writing",
      "category": "ai-vocabulary|inflated-claim|vague-attribution|superficial-ing|promotional|formulaic-challenge|copula-avoidance|negative-parallelism|rule-of-three|elegant-variation|false-range|em-dash|title-case|structured-abstract|chatbot-artifact|hedging-excess|generic-conclusion"
    }
  ]
}
```

IMPORTANT:
- The "what" field identifies the AI pattern, NOT how to rewrite
- The "why" field explains why this pattern undermines academic credibility
- Do NOT include a "suggestion", "fix", "rewrite", or "alternative" field
- If no issues found, return `{"findings": []}`

Paper content:
{paper_content}"""


class AIReviewer(BaseReviewer):
    dimension = "ai_patterns"
    dimension_name = "AI Writing Patterns"
    system_prompt = AI_SYSTEM
    user_prompt_template = AI_USER

    def _parse_response(self, parsed: dict) -> list[Annotation]:
        findings = parsed.get("findings", [])
        annotations: list[Annotation] = []
        for item in findings:
            annotations.append(Annotation(
                dimension=self.dimension,
                title=item.get("title", "AI pattern"),
                severity=self._parse_severity(item),
                location=self._make_location(item),
                what=item.get("what", ""),
                why=item.get("why", ""),
                category=item.get("category", "ai_patterns"),
            ))
        return annotations
