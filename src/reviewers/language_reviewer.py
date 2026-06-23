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
- Are there signs of incomplete global find-replace (e.g., both "Agent" and "Participant" appearing)?

### 2. Grammar & Spelling
- Are there grammatical errors (subject-verb agreement, tense, voice)?
- Are there spelling mistakes or typos?
- Are punctuation marks used correctly?
- Are Chinese and English punctuation marks mixed inappropriately?
- Are there article-noun agreement errors (e.g., "an participant", "a equilibrium")?

### 3. Academic Register
- Does the language match formal academic writing standards?
- Are there colloquial expressions, slang, or overly casual phrasing?
- Are there overly ornate rhetorical flourishes or empty modifiers?
- Is the balance of passive and active voice appropriate for the field?
- Are gendered pronouns (he/she/his/her) used for generic participants? (neutral alternatives may be preferred)

### 4. Expression Precision
- Are there vague or ambiguous expressions?
- Are quantities, degrees, and ranges described precisely?
- Are causal relationships expressed clearly (not overusing "therefore", "thus")?

### 5. Sentence Structure
- Are sentences of reasonable length (not excessively long or short)?
- Are there run-on sentences or fragments?
- Is there evidence of translationese or non-native structuring?

### 6. AI-Generated Sentence Patterns
These are sentence-level patterns characteristic of LLM-generated academic prose.
They are subtle — unlike individual words ("delve", "tapestry"), these pass as acceptable
English but *feel* formulaic. Flag them for the human author to decide.

**Abstract elevation at sentence end**: sentences that conclude by inflating a specific
finding into an abstract claim using empty signifiers. Examples:
- "... emerges as a central dimension of P2P insurance design"
- "... serves as a cornerstone for future research"
- "... stands as a critical consideration for practitioners"
→ These end a sentence with a vague, grand claim. The preceding content is often fine;
the last clause overreaches.

**Nested subordinate clause chains**: one sentence that tries to say everything at once
by stacking clauses. Pattern: "X does Y, by Z-ing the W that P ignores, moving toward Q."
Each clause is grammatical, but the stacking is an AI hallmark. Break into two sentences.

**Dramatic verbs where plain ones work**: "reveals", "uncovers", "brings out", "unleashes",
"transforms" — especially when introducing findings. A finding can simply "show", "indicate",
or "suggest". (Note: "reveal" / "uncover" are distinct from the Tier 1 word list — those
catch marketing adjectives; this is about verb choice in academic argumentation.)

**"Not just X, but Y" / "Alongside X, Y emerges" cadence**: a two-part sentence structure
where the second part elevates. Examples:
- "... matters for P2P insurance design, not just the choice of sharing rule"
- "pool composition, alongside the sharing rule, shapes the viability..."
→ Often the first part is enough. The second part adds rhetorical weight, not information.

**Compressed multi‑claim sentences**: a single sentence that packs 2–3 separable claims
into one, often joined by "and" or a semicolon. If each claim could be its own sentence,
flag it. AI tends to compress; humans tend to separate.

For each flagged sentence, identify the pattern and quote the sentence. Explain *why*
it reads as AI-generated — be specific about which structural feature triggered the flag.
Do NOT propose a rewrite.

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
