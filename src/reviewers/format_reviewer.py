"""
Format & Structure Reviewer — checks paper formatting conventions.

AI annotates structural and formatting issues. Never suggests fixes.
"""

from src.annotation import Annotation, Severity
from src.reviewers.base import BaseReviewer


FORMAT_SYSTEM = """You are assisting a human reviewer. Your role is to identify potential
formatting and structural issues in an academic paper — NEVER suggest how to fix them.

The human author is an expert in their field. You are their junior assistant,
helping them spot things they might miss during a careful read.

For every finding you MUST provide:
- Exact location: section name, paragraph number, line numbers, quoted text
- What the issue is (specific and concrete)
- Why it matters (evidence-based, grounded in academic writing conventions)
- Severity: high (seriously impacts readability/compliance), medium (noticeable), low (minor)

CRITICAL RULE: Do NOT propose corrections, rewrites, or "better" versions.
The human author will decide what (if anything) to change."""

FORMAT_USER = """Review the following academic paper for FORMATTING & STRUCTURE issues.

## What to look for

### 1. Section Structure
- Are sections numbered consistently and hierarchically?
- Are core sections (abstract, introduction, methods, results, discussion, conclusion) present?
- Are section titles clear, concise, and consistent in style?
- Does the paper follow the expected structure for its field?

### 2. Figures, Tables & Equations
- Do all figures and tables have clear, numbered captions?
- Are caption positions consistent (figures: below, tables: above)?
- Are all figures/tables referenced in the body text?
- Are equations numbered correctly and consecutively?
- Are symbols in equations defined in the surrounding text?
- Are there any `\\tag{...}` commands in equation environments? (should use numeric labels)
- Are there duplicate `\\label{...}` keys? (will cause LaTeX compilation errors)
- Do any labeled equations lack corresponding `\\eqref` / `\\ref` in the text?

### 3. Citations & References
- Is the in-text citation format consistent throughout?
- Do all cited works appear in the reference list (and vice versa)?
- Does the reference format follow the target venue's standard?

### 4. Typography & Layout
- Are fonts, spacing, and margins consistent?
- Are paragraph indents uniform?
- Is there appropriate whitespace around figures and tables?
- Are page breaks placed sensibly?

## Output Format

Return a JSON object with this structure:
```json
{
  "findings": [
    {
      "section": "Introduction",
      "paragraph": 2,
      "line_start": 45,
      "line_end": 52,
      "quoted_text": "the relevant excerpt from the paper",
      "title": "short, specific title for this finding",
      "severity": "high|medium|low",
      "what": "What the issue is — specific and concrete",
      "why": "Why this matters — evidence-based rationale",
      "category": "citation-format|figure-label|section-numbering|typography|reference-consistency|layout"
    }
  ]
}
```

IMPORTANT:
- The "what" field describes the issue, NOT the fix
- The "why" field explains why it's problematic, NOT what should be done
- Do NOT include a "suggestion", "fix", or "recommended_change" field
- If no issues found, return `{"findings": []}`

Paper content:
{paper_content}"""


class FormatReviewer(BaseReviewer):
    dimension = "format"
    dimension_name = "Format & Structure"
    system_prompt = FORMAT_SYSTEM
    user_prompt_template = FORMAT_USER

    def _parse_response(self, parsed: dict) -> list[Annotation]:
        findings = parsed.get("findings", [])
        annotations: list[Annotation] = []
        for item in findings:
            annotations.append(Annotation(
                dimension=self.dimension,
                title=item.get("title", "Format issue"),
                severity=self._parse_severity(item),
                location=self._make_location(item),
                what=item.get("what", ""),
                why=item.get("why", ""),
                category=item.get("category", "format"),
            ))
        return annotations
