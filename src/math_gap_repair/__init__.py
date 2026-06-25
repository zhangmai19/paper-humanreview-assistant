"""
Repair templates — generate LaTeX code for Lemma/Proposition/Appendix
that repair a mathematical gap identified by the math reviewer.

These are TEMPLATES that get filled with derived content.
The human reviews the output before inserting into the paper.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RepairResult:
    """Complete output of a math gap repair attempt."""

    # What gap was being repaired
    gap_title: str
    gap_what: str

    # Step 1: Numerical verification
    numerical_verified: bool = False
    numerical_detail: str = ""
    numerical_failures: list[str] = field(default_factory=list)

    # Step 2: Symbolic derivation
    symbolic_success: bool = False
    symbolic_expression: str = ""
    symbolic_factorization: str = ""
    symbolic_conditions: list[str] = field(default_factory=list)
    symbolic_detail: str = ""

    # Step 3: LaTeX output
    lemma_latex: str = ""
    appendix_latex: str = ""

    # Warnings for human review
    warnings: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        """Whether the repair produced a usable result."""
        return self.numerical_verified and self.symbolic_success


# ── LaTeX Templates ──

LEMMA_TEMPLATE = r"""\begin{{lemma}}\label{{{label}}}
{statement}
\end{{lemma}}

\begin{{proof}}
{proof_body}
\end{{proof}}"""


APPENDIX_SECTION_TEMPLATE = r"""\section{{{title}}}\label{{{label}}}

{body}
"""


def build_lemma_latex(
    label: str,
    statement: str,
    proof_body: str,
) -> str:
    """Build a Lemma + Proof LaTeX block."""
    return LEMMA_TEMPLATE.format(
        label=label,
        statement=statement,
        proof_body=proof_body,
    )


def build_appendix_latex(
    title: str,
    label: str,
    body: str,
) -> str:
    """Build a full appendix section."""
    return APPENDIX_SECTION_TEMPLATE.format(
        title=title,
        label=label,
        body=body,
    )


def build_repair_markdown(result: RepairResult) -> str:
    """Generate a Markdown report for a repair attempt.

    This is the human-readable output. The human reviews and decides
    whether to accept the suggested Lemma/Appendix.
    """
    lines = [
        f"## 🔧 Math Gap Repair: {result.gap_title}",
        "",
        f"**Original finding:** {result.gap_what}",
        "",
        "---",
        "",
    ]

    # Step 1
    lines.append("### Step 1 — Numerical Verification")
    lines.append("")
    if result.numerical_verified:
        lines.append("✅ **Verified:** the assertion holds across all parameter ranges tested.")
    else:
        lines.append("❌ **Not verified:** counterexamples or failures found.")
    lines.append("")
    lines.append(result.numerical_detail)
    lines.append("")
    if result.numerical_failures:
        lines.append("**Potential counterexample regions:**")
        for f in result.numerical_failures:
            lines.append(f"- {f}")
        lines.append("")

    # Step 2
    lines.append("### Step 2 — Symbolic Derivation")
    lines.append("")
    if result.symbolic_success:
        lines.append("✅ **Symbolic derivation succeeded.**")
        lines.append("")
        if result.symbolic_expression:
            lines.append("**Analyzed expression:**")
            lines.append("```")
            lines.append(result.symbolic_expression)
            lines.append("```")
            lines.append("")
        if result.symbolic_factorization:
            lines.append("**Factorization:**")
            lines.append("```")
            lines.append(result.symbolic_factorization)
            lines.append("```")
            lines.append("")
        if result.symbolic_conditions:
            lines.append("**Sufficient conditions for the assertion to hold:**")
            for c in result.symbolic_conditions:
                lines.append(f"- {c}")
            lines.append("")
    else:
        lines.append("⚠️ **Symbolic derivation incomplete** — requires human intervention.")
        lines.append("")
        lines.append(result.symbolic_detail)
        lines.append("")

    # Step 3
    lines.append("### Step 3 — Suggested LaTeX")
    lines.append("")
    if result.lemma_latex:
        lines.append("#### Lemma (for the main text)")
        lines.append("")
        lines.append("```latex")
        lines.append(result.lemma_latex)
        lines.append("```")
        lines.append("")
    if result.appendix_latex:
        lines.append("#### Appendix (for the supporting derivation)")
        lines.append("")
        lines.append("```latex")
        lines.append(result.appendix_latex)
        lines.append("```")
        lines.append("")

    if result.warnings:
        lines.append("### ⚠️ Warnings")
        lines.append("")
        for w in result.warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("---")
    lines.append("*This repair suggestion was auto-generated. The human must review and decide whether to accept it.*")
    lines.append("")

    return "\n".join(lines)
