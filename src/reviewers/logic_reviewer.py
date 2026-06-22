"""
Logical Flow Reviewer — checks argument coherence and reasoning quality.

AI annotates logic issues. Never suggests how to restructure arguments.
"""

from src.annotation import Annotation, Severity
from src.reviewers.base import BaseReviewer


LOGIC_SYSTEM = """You are assisting a human reviewer. Your role is to identify potential
logical and argumentation issues in an academic paper — NEVER suggest how to fix them.

The human author is the expert in their research domain. You are their junior
assistant, helping them spot potential weaknesses in their reasoning chain.

For every finding you MUST provide:
- Exact location: section name, paragraph number, line numbers, quoted text
- What the logical issue is (specific and concrete)
- Why it matters (e.g., weakens the argument, logical gap, unsupported claim)
- Severity: high (undermines a key argument), medium (noticeable weakness), low (minor)

CRITICAL RULE: Do NOT propose how to restructure, rewrite, or strengthen the argument.
The human author will decide what (if anything) to change."""

LOGIC_USER = """Review the following academic paper for LOGICAL FLOW & ARGUMENT issues.

## What to look for

### 1. Argument Thread
- Is there a clear, identifiable core thesis or research question?
- Do all sections contribute to answering the core question?
- Is there a clear logical chain: problem → approach → validation → conclusion?
- Are there sections or paragraphs that drift from the main argument?

### 2. Paragraph Coherence
- Does each paragraph have a clear topic sentence?
- Are sentences within each paragraph logically connected?
- Are transitions between paragraphs smooth and logical?
- Are there non-sequiturs or logical leaps between sentences?

### 3. Argument Quality
- Are conclusions adequately supported by evidence?
- Is there circular reasoning or tautology?
- Are correlation and causation correctly distinguished?
- Is there overgeneralization (broad conclusions from limited evidence)?
- Are there straw-man arguments (attacking positions no one holds)?
- Are important counter-arguments acknowledged and addressed?

### 4. Literature Review Logic
- Are related works correctly categorized and compared?
- Is the research gap convincingly argued?
- Are prior contributions and limitations fairly assessed?

### 5. Discussion & Conclusion Logic
- Does the discussion address the research questions posed in the introduction?
- Are conclusions proportional to the evidence presented?
- Are limitations honestly and fully discussed?
- Are future work suggestions grounded in actual findings?

## Output Format

Return a JSON object with this structure:
```json
{
  "findings": [
    {
      "section": "Discussion",
      "paragraph": 4,
      "line_start": 350,
      "line_end": 370,
      "quoted_text": "the relevant excerpt",
      "title": "short, specific title for this finding",
      "severity": "high|medium|low",
      "what": "What the logical issue is — specific and concrete",
      "why": "Why this matters for the argument's strength",
      "category": "argument-thread|coherence|evidence|overgeneralization|transition|counter-argument|conclusion-logic"
    }
  ]
}
```

IMPORTANT:
- The "what" field identifies the logical issue, NOT how to restructure
- The "why" field explains the impact on the paper's reasoning quality
- Do NOT include a "suggestion", "fix", "rewrite", or "restructure" field
- If no issues found, return `{"findings": []}`

Paper content:
{paper_content}"""


class LogicReviewer(BaseReviewer):
    dimension = "logic"
    dimension_name = "Logical Flow"
    system_prompt = LOGIC_SYSTEM
    user_prompt_template = LOGIC_USER

    def _parse_response(self, parsed: dict) -> list[Annotation]:
        findings = parsed.get("findings", [])
        annotations: list[Annotation] = []
        for item in findings:
            annotations.append(Annotation(
                dimension=self.dimension,
                title=item.get("title", "Logic issue"),
                severity=self._parse_severity(item),
                location=self._make_location(item),
                what=item.get("what", ""),
                why=item.get("why", ""),
                category=item.get("category", "logic"),
            ))
        return annotations
