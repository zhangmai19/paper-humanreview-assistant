# Project Journal — Example / Template

> Real project journals are saved locally and gitignored.  
> This file shows the format — actual journals track specific paper reviews and tool iterations.

## Session Summary

Describe the day's work in one paragraph: what paper was under review, what the main goals were, any notable findings.

## Paper Edits (version label, N changes)

| # | What | Category |
|---|------|----------|
| 1 | `delivers` → `provides` | AI vocabulary (Tier 1 HARD) |
| 2 | Gendered pronoun elimination (×N) | Language convention |
| 3 | Unified terminology across paper | Terminology |
| … | … | … |

## New Patterns Discovered (Feed into Project)

### For `ai_pattern_scanner.py` (rule-based)
- **Pattern name** — description, example, why it matters
- *Example:* **Article-agreement breakage** — after global `agent`→`participant`, `an participant` remains. Scanner should check `a [vowel-start]` and `an [consonant-start]`.

### For `format_reviewer.py` / `language_reviewer.py` / `math_reviewer.py` (LLM prompts)
- **Check item** — added to the reviewer's "What to look for" list
- *Example:* **`\tag{...}` in equation environments** — should use numeric labels

## Key Insight

Document any meta-observations about the workflow or methodology that could improve the tool.

## Next Steps (Project)

- Bullet list of concrete project improvements to pursue
