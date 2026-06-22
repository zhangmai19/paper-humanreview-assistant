"""
Mathematical Derivation Reviewer — checks equation correctness and rigor.

AI annotates potential math issues. Never suggests corrections to derivations.
"""

from src.annotation import Annotation, Severity
from src.reviewers.base import BaseReviewer


MATH_SYSTEM = """You are assisting a human reviewer. Your role is to identify potential
mathematical and derivation issues in an academic paper — NEVER suggest corrections.

The human author is the expert in their mathematical domain. You are their junior
assistant, helping them spot potential gaps or inconsistencies in their derivations.

For every finding you MUST provide:
- Exact location: section name, equation number, line numbers, quoted text
- What the mathematical issue is (specific and concrete)
- Why it matters (e.g., missing step, undefined symbol, assumption not stated)
- Severity: high (derivation error or critical gap), medium (missing justification), low (minor)

CRITICAL RULE: Do NOT propose corrections, alternative derivations, or "fixed" equations.
The human author will decide what (if anything) to change."""

MATH_USER = """Review the following academic paper for MATHEMATICAL issues.

## What to look for

### 1. Derivation Correctness
- Does each step in a derivation follow logically from the previous step?
- Are there logical gaps or jumps in the derivation?
- Are key steps justified (with citations to theorems, lemmas, etc.)?
- Are approximations or simplifications reasonable and explicitly stated?

### 2. Notation Consistency
- Are mathematical symbols clearly defined before use?
- Are vectors, matrices, scalars consistently represented (bold, italic, etc.)?
- Are subscripts and superscripts used correctly and consistently?
- Are different variable types (random variables, constants, parameters) clearly distinguished?

### 3. Assumptions & Boundary Conditions
- Are all assumptions explicitly stated?
- Are assumptions reasonable and not hidden?
- Are boundary conditions handled correctly?
- Are the conditions for applying theorems/lemmas verified?

### 4. Completeness
- Are proofs complete with sufficient detail?
- Are there missing intermediate steps?
- Are "it is obvious that..." or "clearly..." claims actually justified?

### 5. Equation Presentation
- Are equations properly numbered?
- Do inline equations disrupt readability?
- Are displayed equations formatted clearly?

## Output Format

Return a JSON object with this structure:
```json
{
  "findings": [
    {
      "section": "3.2 Derivation",
      "equation_number": "(7)",
      "line_start": 200,
      "line_end": 215,
      "quoted_text": "the relevant excerpt or equation",
      "title": "short, specific title for this finding",
      "severity": "high|medium|low",
      "what": "What the mathematical issue is — specific and concrete",
      "why": "Why this matters for mathematical rigor",
      "category": "derivation-gap|notation|assumption|completeness|presentation"
    }
  ]
}
```

IMPORTANT:
- The "what" field identifies the issue, NOT the correction
- The "why" field explains the impact on mathematical soundness
- Do NOT include a "suggestion", "fix", "corrected_derivation", or "rewrite" field
- If no issues found, return `{"findings": []}`

Paper content:
{paper_content}"""


class MathReviewer(BaseReviewer):
    dimension = "math"
    dimension_name = "Mathematical Derivation"
    system_prompt = MATH_SYSTEM
    user_prompt_template = MATH_USER

    def _parse_response(self, parsed: dict) -> list[Annotation]:
        findings = parsed.get("findings", [])
        annotations: list[Annotation] = []
        for item in findings:
            # Include equation number in location context if present
            eq_num = item.get("equation_number", "")
            annotations.append(Annotation(
                dimension=self.dimension,
                title=item.get("title", "Math issue"),
                severity=self._parse_severity(item),
                location=self._make_location(item),
                what=item.get("what", ""),
                why=item.get("why", ""),
                category=item.get("category", "math"),
            ))
        return annotations
