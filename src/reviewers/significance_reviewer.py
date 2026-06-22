"""
Research Significance Reviewer — assesses novelty, contribution, and impact.

AI annotates potential issues with how the research is positioned and evaluated.
Never suggests how to reframe or reposition the research.
"""

from src.annotation import Annotation, Severity
from src.reviewers.base import BaseReviewer


SIGNIFICANCE_SYSTEM = """You are assisting a human reviewer. Your role is to identify potential
issues with how a paper presents its research significance — NEVER suggest how to fix them.

The human author is the expert in their research domain. You are their junior
assistant, helping them spot potential weaknesses in how they position their contribution.

For every finding you MUST provide:
- Exact location: section name, paragraph number, line numbers, quoted text
- What the issue is (specific and concrete)
- Why it matters (e.g., overclaimed novelty, unclear contribution, weak motivation)
- Severity: high (seriously undermines the paper's perceived value), medium (noticeable), low (minor)

CRITICAL RULE: Do NOT propose how to reframe, reposition, or reword the contribution.
The human author will decide what (if anything) to change."""

SIGNIFICANCE_USER = """Review the following academic paper for RESEARCH SIGNIFICANCE issues.

## What to look for

### 1. Novelty
- Is the core innovation clearly stated?
- Compared to existing work, how significant is the novelty (incremental vs. breakthrough)?
- Is the novelty appropriately characterized (not overclaimed)?
- Are there overstatements like "first-ever", "completely new", "revolutionary"?

### 2. Research Motivation
- Is the motivation compelling and grounded in real problems?
- Is the importance of the research question convincingly argued?
- Is it clear why existing methods are insufficient?

### 3. Literature Positioning
- Does the paper correctly and comprehensively position itself in the literature?
- Is the comparison against the most relevant prior work adequate?
- Are there missing key references or related works?

### 4. Contribution Clarity
- Are the contributions listed clearly and specifically?
- Are contributions verifiable (not vague claims)?
- Is each claimed contribution supported by evidence in the paper?

### 5. Impact Assessment
- Does the research have practical, theoretical, or methodological value?
- Is the potential impact realistically assessed?
- Are the results generalizable?

### 6. Claim Honesty
- Do the claims match the experimental results?
- Are there unsupported claims of superiority?
- Is the scope of applicability accurately described?

## Output Format

Return a JSON object with this structure:
```json
{
  "findings": [
    {
      "section": "Introduction",
      "paragraph": 1,
      "line_start": 5,
      "line_end": 20,
      "quoted_text": "the relevant excerpt",
      "title": "short, specific title for this finding",
      "severity": "high|medium|low",
      "what": "What the issue is — specific and concrete",
      "why": "Why this matters for how readers will assess the paper",
      "category": "novelty|motivation|literature-gap|contribution-clarity|overclaim|impact-assessment"
    }
  ]
}
```

IMPORTANT:
- The "what" field identifies the issue, NOT how to reframe
- The "why" field explains the impact on the paper's perceived contribution
- Do NOT include a "suggestion", "fix", "rewrite", or "repositioning" field
- If no issues found, return `{"findings": []}`

Paper content:
{paper_content}"""


class SignificanceReviewer(BaseReviewer):
    dimension = "significance"
    dimension_name = "Research Significance"
    system_prompt = SIGNIFICANCE_SYSTEM
    user_prompt_template = SIGNIFICANCE_USER

    def _parse_response(self, parsed: dict) -> list[Annotation]:
        findings = parsed.get("findings", [])
        annotations: list[Annotation] = []
        for item in findings:
            annotations.append(Annotation(
                dimension=self.dimension,
                title=item.get("title", "Significance issue"),
                severity=self._parse_severity(item),
                location=self._make_location(item),
                what=item.get("what", ""),
                why=item.get("why", ""),
                category=item.get("category", "significance"),
            ))
        return annotations
