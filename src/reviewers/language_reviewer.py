"""
Language & Terminology Reviewer — checks academic writing conventions.

AI annotates language issues. Never suggests rewrites.
"""

from src.annotation import Annotation, Severity
from src.reviewers.base import BaseReviewer


LANGUAGE_SYSTEM = """You are assisting a human reviewer. Your role is to identify potential
language and terminology issues in an academic paper — NEVER suggest rewrites or fixes.

The human author is an expert in their field. You are their junior assistant,
helping them spot language issues they might overlook during revision.

For every finding you MUST provide:
- Exact location: section name, paragraph number, line numbers, quoted text
- What the language issue is (specific and concrete)
- Why it matters (e.g., impairs clarity, inconsistent terminology, non-academic register)
- Severity: high (seriously impairs comprehension), medium (noticeable), low (minor)

CRITICAL RULE: Do NOT propose alternative wording, rewrites, or corrections.
The human author will decide what (if anything) to change."""

LANGUAGE_USER = """Review the following academic paper for LANGUAGE & TERMINOLOGY issues.

## What to look for

### 1. Terminology Consistency
- Are technical terms used consistently throughout the paper?
- Are abbreviations defined at first use and then used consistently?
- Is the same concept referred to by different terms (inconsistent terminology)?

### 2. Grammar & Spelling
- Are there grammatical errors (subject-verb agreement, tense, voice)?
- Are there spelling mistakes or typos?
- Are punctuation marks used correctly?
- Are Chinese and English punctuation marks mixed inappropriately?

### 3. Academic Register
- Does the language match formal academic writing standards?
- Are there colloquial expressions, slang, or overly casual phrasing?
- Are there overly ornate rhetorical flourishes or empty modifiers?
- Is the balance of passive and active voice appropriate for the field?

### 4. Expression Precision
- Are there vague or ambiguous expressions?
- Are quantities, degrees, and ranges described precisely?
- Are causal relationships expressed clearly (not overusing "therefore", "thus")?

### 5. Sentence Structure
- Are sentences of reasonable length (not excessively long or short)?
- Are there run-on sentences or fragments?
- Is there evidence of translationese or non-native structuring?

## Output Format

Return a JSON object with this structure:
```json
{
  "findings": [
    {
      "section": "Methodology",
      "paragraph": 3,
      "line_start": 120,
      "line_end": 135,
      "quoted_text": "the relevant excerpt showing the issue",
      "title": "short, specific title for this finding",
      "severity": "high|medium|low",
      "what": "What the language issue is — specific and concrete",
      "why": "Why this matters for academic writing quality",
      "category": "terminology|grammar|register|precision|sentence-structure"
    }
  ]
}
```

IMPORTANT:
- The "what" field describes the issue, NOT how to rewrite it
- The "why" field explains the impact on readability or academic quality
- Do NOT include a "suggestion", "fix", "rewrite", or "correction" field
- If no issues found, return `{"findings": []}`

Paper content:
{paper_content}"""


class LanguageReviewer(BaseReviewer):
    dimension = "language"
    dimension_name = "Language & Terminology"
    system_prompt = LANGUAGE_SYSTEM
    user_prompt_template = LANGUAGE_USER

    def _parse_response(self, parsed: dict) -> list[Annotation]:
        findings = parsed.get("findings", [])
        annotations: list[Annotation] = []
        for item in findings:
            annotations.append(Annotation(
                dimension=self.dimension,
                title=item.get("title", "Language issue"),
                severity=self._parse_severity(item),
                location=self._make_location(item),
                what=item.get("what", ""),
                why=item.get("why", ""),
                category=item.get("category", "language"),
            ))
        return annotations
