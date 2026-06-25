# Paper Human-Review Assistant

> **AI annotates, humans decide.** A tool that helps you read and review your own academic papers more efficiently.

## Why This Exists

AI tools that "review and revise" papers put the LLM in both roles — judge and executioner. Your paper gets "AI-fied" rather than improved, and you lose control of your own writing.

This tool does the opposite:

| ✅ AI Does | ❌ AI Doesn't |
|-----------|--------------|
| Scan for patterns across the full text | Rewrite or modify your paper |
| Flag potential issues with exact locations | Make judgments without showing evidence |
| Summarize sections for faster reading | Generate new content or "suggested fixes" |
| Compare against writing checklists | Decide what your paper should say |
| Highlight red flags in math and logic | Replace human judgment |

The AI is your **junior research assistant** — it finds things for you to look at, then gets out of the way.

## What It Checks

Six dimensions, each producing a self-contained section in the review report:

| # | Dimension | What It Looks For |
|---|-----------|-------------------|
| 1 | **Format & Structure** | Section numbering, figure/table captions, citation format, typography |
| 2 | **Language & Terminology** | Grammar, terminology consistency, academic register, precision |
| 3 | **AI Writing Patterns** | AI vocabulary, inflated claims, vague attributions, em-dash abuse, chatbot traces |
| 4 | **Mathematical Derivation** | Gaps in derivations, undefined symbols, missing assumptions, completeness |
| 5 | **Logical Flow** | Argument thread, paragraph coherence, evidence quality, overgeneralization |
| 6 | **Research Significance** | Novelty, motivation, literature positioning, claim honesty |

## Installation

```bash
git clone git@github.com:zhangmai19/paper-humanreview-assistant.git
cd paper-humanreview-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.yaml.example config.yaml
# Edit config.yaml with your API key, or set ANTHROPIC_API_KEY env var
```

## Usage

```bash
# Full review (all 6 dimensions)
python main.py paper.tex

# Specific dimensions only
python main.py paper.tex --dimensions format,logic,ai_patterns

# Custom output directory and model
python main.py paper.tex --output-dir reviews/ --model claude-opus-4-8

# Sequential mode (slower, easier to read progress)
python main.py paper.tex --no-parallel
```

### Supported Input Formats

- LaTeX (`.tex`, `.ltx`, `.latex`)
- Markdown (`.md`, `.markdown`)
- Plain text (`.txt`)

### Output

A Markdown report is saved to the `output/` directory (or `--output-dir`). Each finding follows this structure:

```markdown
### 🔍 [Dimension] Issue Title
- **Location:** Section 3.2, Paragraph 2 (lines 145-152)
- **Severity:** ⚠️ Medium
- **What:** The derivation jumps from A to B without showing the intermediate step.
- **Why it matters:** Readers unfamiliar with this technique may not follow the reasoning.
- **Context:** [Quoted text snippet showing the issue]
```

**No suggested fixes.** You decide what to change.

## Configuration

```yaml
# config.yaml
api_key: ""                              # or set ANTHROPIC_API_KEY env var
provider: "anthropic"                    # or "deepseek"
model: "claude-sonnet-4-6"              # any Claude or DeepSeek model
dimensions:                              # default dimensions to review
  - format
  - language
  - ai_patterns
  - math
  - logic
  - significance
parallel_reviews: true                   # run reviewers concurrently
output_dir: "output"                     # where reports are saved
```

## Project Structure

```
paper-humanreview-assistant/
├── main.py                              # CLI entry point
├── config.yaml.example
├── requirements.txt
├── README.md
├── CLAUDE.md                            # Project constitution & design rules
├── src/
│   ├── annotation.py                    # Data models (Annotation, ReviewReport)
│   ├── paper_reader.py                  # Paper loading & parsing
│   ├── orchestrator.py                  # Coordinates rule-based + LLM reviewers
│   ├── report_writer.py                 # Generates structured Markdown reports
│   ├── utils.py                         # Config loading, LLM client, console output
│   ├── math_gap_repair/                 # Math gap repair module
│   │   ├── __init__.py                  # Data models, LaTeX templates, report builder
│   │   ├── engine.py                    # Repair engine (expression → report)
│   │   └── analysis_script_template.py  # sympy+numpy analysis (subprocess)
│   └── reviewers/
│       ├── base.py                      # Abstract reviewer (enforces annotation contract)
│       ├── ai_pattern_scanner.py        # Rule-based AI writing detection (24+ patterns)
│       ├── format_reviewer.py           # Format & structure (LLM)
│       ├── language_reviewer.py         # Language & terminology (LLM)
│       ├── ai_reviewer.py               # AI patterns verification (LLM)
│       ├── math_reviewer.py             # Mathematical derivation (LLM)
│       ├── logic_reviewer.py            # Logical flow (LLM)
│       └── significance_reviewer.py     # Research significance (LLM)
├── tests/
│   ├── test_paper_reader.py
│   └── test_ai_pattern_scanner.py
└── papers/
    └── sample.tex
```

## AI Pattern Detection

The AI writing pattern scanner runs **locally** — no API calls, instant results. It detects 24+ patterns across 5 categories:

- **Content**: Inflated significance claims, vague attributions, superficial clauses, promotional language
- **Language**: AI vocabulary (3 tiers), copula avoidance, negative parallelism, elegant variation, false ranges
- **Editing Artifacts**: Article-noun agreement errors (e.g., "an participant" after bulk replace), capitalized word drift (both "Agent" and "Participant"), gendered pronoun usage
- **Style**: Em-dash overuse, Title Case headings, structured abstract sub-headings
- **Communication**: Chatbot artifacts, knowledge-cutoff declarations, ingratiating tone
- **Filler**: Excessive hedging, generic conclusions

Patterns are density-gated to avoid false positives — individual "hence" or "demonstrate" won't flag; only dense clusters trigger alerts.

## Math Gap Repair

When the math reviewer flags an unverified claim (e.g. "concavity assumed without proof"), `--repair` runs a three-stage pipeline to find the proof:

```
Numerical Exploration → Symbolic Derivation → Lemma + Appendix
```

### How It Works

1. **Numerical sweep** — Grid-scans the parameter space to test the claim. If violations are found, it reports exactly where. Includes assumption filtering (e.g. `n_H >= 2`).

2. **Symbolic analysis** — Expands the expression, groups terms by monomial degree, factors each group. Determines sign-definiteness from the factorization. Handles both `≤ 0` and `≥ 0` claims (auto-detected from context).

3. **LaTeX generation** — Produces a self-contained Lemma + Proof block and an Appendix section with the full algebraic decomposition. Ready for human review and insertion into the paper.

### Usage

```bash
python main.py paper.tex --math --repair
```

For programmatic use:

```python
from src.math_gap_repair.engine import repair_math_gap

repair_math_gap(
    expression="-gamma*a**4*n_H**3*sigma2_H*(n_H-1) - ...",
    claim="d2U_dalphaH2 <= 0 (U_H concave in alpha_H)",
    assumptions=["n_H >= 2", "sigma_H^2 >= sigma_L^2"],
)
```

### Methodology

This implements a general approach developed while repairing a real paper:

1. **Numerical exploration** — Write scripts to scan parameter space, verify the claim holds, locate counterexample regions
2. **Symbolic derivation** — Use sympy to get exact expressions, factor/expand/collect, pair terms, find sufficient conditions
3. **Paper integration** — Write the result as a Lemma + Appendix with clear conditions

The module generalizes this pattern to any mathematical claim as long as it can be expressed as a sympy expression.

## Workflow: Review, Then Edit One at a Time

The tool produces a review report. **How** you act on it matters:

| Batch Fever | Step-by-Step |
|------------|--------------|
| Get 40+ annotations at once | Pick one small, mechanical item |
| Feel overwhelmed, procrastinate | Make the edit, verify it worked |
| Fix a few randomly | Move to the next — each step has a win |

The review report doubles as a task list you can tick through. Each finding says **what** and **why** — never **how**. You decide the fix, and you decide what to skip.

The AI pattern scanner also catches editing artifacts: after global find-and-replace (`agent` → `participant`), it can flag article-noun mismatches (`an participant`), capitalized leftovers (`Agents` surviving the replace), and gendered pronouns you may want to neutralize.

## License

MIT
