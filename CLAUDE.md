# CLAUDE.md — Paper Human-Review Assistant

> AI-assisted academic paper review tool. **AI annotates, humans decide.**

## Project Identity

- **Name:** Paper Human-Review Assistant
- **Repo:** `zhangmai19/paper-humanreview-assistant`
- **Language:** Python 3.11+
- **Interface:** CLI (click + rich), outputs structured Markdown reports
- **License:** MIT

## Core Philosophy

This tool is built on a fundamental belief about AI's role in academic writing:

> **AI should help humans read better, not write for them.**

The problem with most "AI paper review" tools is that they put AI in both the reviewer and reviser roles — AI finds problems, then AI fixes them. This creates an echo chamber where papers get "AI-fied" rather than improved. It also raises serious academic integrity concerns.

### What This Tool Does (and Doesn't Do)

| ✅ AI Does | ❌ AI Doesn't |
|-----------|--------------|
| Scan for patterns across the full text | Rewrite or modify the paper |
| Flag potential issues with location references | Make judgments without showing evidence |
| Summarize sections for faster human review | Generate new content or "suggested fixes" |
| Compare against writing convention checklists | Decide what the paper should say |
| Highlight statistical/methodological red flags | Replace human peer review |
| Present findings in a navigable, structured report | Operate in a fully-automated mode |

### Design Principles

1. **Annotation, not generation.** Every AI output references specific locations (section, paragraph, line). Findings are presented as "here's something to check" not "here's what to change."

2. **Verifiable, not trustable.** Every flag comes with a rationale the human can independently verify. The AI is a junior assistant, not an authority.

3. **Layered, not monolithic.** Reviews are organized into passes — the human chooses what to review and in what order. Format → Language → Logic → Math → AI patterns → Significance. Each pass is self-contained.

4. **Human-in-the-loop by design.** There is no `--no-human` flag. The tool produces reports for humans to read and act on. The human decides what matters and what to change.

5. **Toolchain-compatible.** Works with LaTeX (`.tex`) and Markdown (`.md`) papers. Output is standard Markdown that can be viewed in any editor. Designed to fit into existing academic workflows, not replace them.

## Architecture

### Directory Structure (Planned)

```
paper-humanreview-assistant/
├── main.py                      # CLI entry point
├── config.yaml.example          # Configuration template
├── requirements.txt
├── README.md
├── CLAUDE.md                    # This file
├── src/
│   ├── __init__.py
│   ├── paper_reader.py          # Paper loading, parsing, plain-text extraction
│   ├── annotation.py            # Annotation data models (location, severity, category)
│   ├── reviewers/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract reviewer interface
│   │   ├── format_reviewer.py   # Formatting & structure checks
│   │   ├── language_reviewer.py # Academic language conventions
│   │   ├── ai_pattern_scanner.py # AI writing pattern detection (rule-based)
│   │   ├── math_reviewer.py     # Mathematical derivation checks
│   │   ├── logic_reviewer.py    # Argument flow & logical coherence
│   │   └── significance_reviewer.py # Research contribution assessment
│   ├── summarizer.py            # Section/chapter summarization for human reading
│   ├── report_writer.py         # Generates structured Markdown reports
│   ├── diff_engine.py           # Compare paper versions, track changes
│   └── utils.py                 # Shared utilities, config loading, LLM client
├── tests/
│   ├── test_paper_reader.py
│   ├── test_ai_pattern_scanner.py
│   └── ...
└── papers/                      # Sample papers for testing
    └── sample.tex
```

### Key Differences from `paper-review-iterative`

This project is a spiritual successor to `paper-review-iterative` (the sibling project at `../paper-review-iterative`). That project does AI-driven review + AI-driven revision in a loop. This project deliberately breaks that loop:

| Aspect | paper-review-iterative | paper-humanreview-assistant |
|--------|----------------------|---------------------------|
| AI role | Reviewer + Reviser | Annotator + Summarizer |
| Output | Revised `.tex` files | Markdown review reports |
| Human role | Optional feedback between rounds | Central decision-maker |
| Automation | `--no-human` full-auto mode | No auto mode exists |
| Iteration | AI iterates until convergence | Human iterates at their own pace |
| Modification | AI modifies the paper | AI never touches the paper |

### Reusable Code from `paper-review-iterative`

The following modules can be adapted (not copied blindly — they need refactoring to match the new philosophy):

- `src/paper_manager.py` → `src/paper_reader.py` — Keep parsing logic, remove save/diff/revision logic (diff moves to separate module)
- `src/humanizer_patterns.py` → `src/reviewers/ai_pattern_scanner.py` — Keep the 24+ pattern detection rules, these are rule-based and don't generate content
- `src/utils.py` → `src/utils.py` — Keep config loading and LLM client factory
- `src/prompts/*.py` → Rewrite completely. Old prompts ask AI to "find problems and suggest fixes." New prompts must ask AI to "identify, locate, and explain — never suggest."

## Development Workflow

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.yaml.example config.yaml
# Edit config.yaml with your API key
```

### Running

```bash
# Review a paper on all dimensions
python main.py paper.tex

# Review specific dimensions only
python main.py paper.tex --dimensions format,ai_patterns,logic

# Output to specific directory
python main.py paper.tex --output-dir reviews/

# Specify model
python main.py paper.tex --model claude-opus-4-8
```

### Code Conventions

- **Language:** All source code, docstrings, and comments in English
- **Commit messages:** Conventional Commits in English (`feat:`, `fix:`, `refactor:`, `docs:`)
- **Formatting:** Follow PEP 8, use `ruff` for linting
- **Type hints:** Use modern Python type hints (`str | None` not `Optional[str]`)
- **Docstrings:** Google-style docstrings for public APIs
- **Dependencies:** `click` for CLI, `rich` for terminal output, `pyyaml` for config, `anthropic` (and optionally `openai` for DeepSeek) for LLM API

### Testing

- Use `pytest` for tests
- Test paper fixtures go in `papers/`
- Rule-based scanners (like AI pattern detection) must have unit tests
- LLM-based reviewers should have integration tests with mocked API responses

## Review Dimensions

Each dimension produces a self-contained section in the final report:

| # | Dimension | Key | What It Checks | Method |
|---|-----------|-----|----------------|--------|
| 1 | **Format & Structure** | `format` | Section hierarchy, figure/table numbering, citation format, layout consistency | LLM-assisted |
| 2 | **Language Conventions** | `language` | Terminology consistency, grammar, academic register, expression precision | LLM-assisted |
| 3 | **AI Writing Patterns** | `ai_patterns` | AI vocabulary, exaggerated claims, vague references, em-dash abuse, chatbot traces | Rule-based + LLM verification |
| 4 | **Mathematical Derivation** | `math` | Equation correctness, symbol consistency, assumption documentation, completeness | LLM-assisted |
| 5 | **Logical Flow** | `logic` | Argument thread, paragraph coherence, reasoning quality, transition naturalness | LLM-assisted |
| 6 | **Research Significance** | `significance` | Novelty, motivation, literature positioning, contribution clarity, impact | LLM-assisted |

### Annotation Output Format

Each finding follows this structure:

```markdown
### 🔍 [Dimension] Issue Title
- **Location:** Section 3.2, Paragraph 2 (lines 145-152)
- **Severity:** ⚠️ Medium
- **What:** The derivation in equation (7) jumps from assumption A to conclusion B without showing the intermediate step.
- **Why it matters:** Readers unfamiliar with this technique may not follow the reasoning.
- **Context:** [Quoted text snippet showing the issue]
```

Note: There is no "Suggested Fix" or "Recommended Change" field. The human decides what to do.

## Prompt Design Rules

When writing reviewer prompts, follow these rules strictly:

1. **Ask for identification, not correction.** "Find and locate instances of X" — not "Fix instances of X."
2. **Require location.** Every finding must include section/paragraph/line references.
3. **Require rationale.** Every finding must explain *why* it's a potential issue.
4. **Forbid suggestions.** Explicitly instruct: "Do NOT suggest how to fix this. Only identify and explain the issue."
5. **Be specific about what to look for.** Vague prompts produce vague results. Define concrete patterns, categories, and examples.

### Anti-Pattern Prompt (from old project — DO NOT USE)

```
You are a strict academic reviewer. Find issues in the paper and suggest specific fixes.
For each issue, provide:
- The problem
- Suggested correction
```

### Correct Prompt Pattern (for this project)

```
You are assisting a human reviewer. Your role is to identify potential issues
and explain why they matter — NEVER suggest how to fix them.

For each finding, provide:
- Exact location (section, paragraph number, quote the relevant text)
- Category of issue
- Why this might be problematic (evidence-based rationale)
- Severity assessment (low / medium / high)

IMPORTANT: Do NOT propose corrections, rewrites, or "better" versions.
The human author will decide what (if anything) to change.
```

## References & Prior Art

- `../paper-review-iterative` — Sibling project (AI-driven review + revision loop). Reference for paper parsing and AI pattern detection code.
- [blader/humanizer](https://github.com/blader/humanizer) (21k+ stars) — AI writing pattern reference
- [Wikipedia: Signs of AI Writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
- [Anthropic Claude API Docs](https://docs.anthropic.com/en/api)

## Git Conventions

- **Branch naming:** `feat/short-description`, `fix/short-description`, `refactor/short-description`
- **Commit format:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`)
- **Never commit:** `config.yaml` (contains API keys), `.venv/`, `__pycache__/`, `output/`
- **Before committing:** Ask the human for confirmation with a summary of changes.
- **Before pushing:** Ask the human for confirmation.
