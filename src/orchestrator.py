"""
Orchestrator — coordinates review across dimensions.

Runs rule-based scanners and LLM-based reviewers (parallel or sequential),
collects all annotations into a single ReviewReport.
"""

import concurrent.futures

from src.annotation import Annotation, ReviewReport
from src.paper_reader import PaperReader, Paper
from src.reviewers import (
    LLM_REVIEWERS,
    DIMENSION_NAMES,
    scan_ai_patterns,
)
from src.reviewers.base import _extract_json
from src.utils import console, llm_chat


def run_review(
    paper: Paper,
    dimensions: list[str],
    llm: tuple[str, object],
    model: str,
    parallel: bool = True,
) -> ReviewReport:
    """Run a complete review across all specified dimensions.

    Args:
        paper: Loaded Paper object
        dimensions: List of dimension keys to review
        llm: (provider_type, client) tuple
        model: Model name
        parallel: Run LLM reviewers in parallel

    Returns:
        ReviewReport with all annotations collected
    """
    report = ReviewReport(
        paper_path=paper.file_path,
        paper_title=paper.metadata.get("filename", ""),
        dimensions_reviewed=list(dimensions),
    )

    plain_text = PaperReader.get_plain_text(paper)
    all_annotations: list[Annotation] = []
    ai_rule_annotations: list[Annotation] = []

    # Validate dimensions
    valid_dims = [d for d in dimensions if d in LLM_REVIEWERS]
    invalid = set(dimensions) - set(valid_dims)
    if invalid:
        console.print(f"  [yellow]⚠ Unknown dimensions skipped: {invalid}[/yellow]")

    if not valid_dims:
        console.print("[red]No valid review dimensions specified.[/red]")
        return report

    console.print(f"\n[bold]🔍 Starting review — {len(valid_dims)} dimensions[/bold]")
    if parallel and len(valid_dims) > 1:
        console.print("[dim]Parallel mode[/dim]\n")
    else:
        console.print("[dim]Sequential mode[/dim]\n")

    # ── Phase 1: Rule-based scanning (ai_patterns) ──
    if "ai_patterns" in valid_dims:
        console.print("  [cyan]🔬 Running rule-based AI pattern scan...[/cyan]")
        ai_rule_annotations = scan_ai_patterns(plain_text)
        all_annotations.extend(ai_rule_annotations)
        report.metadata["ai_pattern_rule_count"] = len(ai_rule_annotations)
        console.print(
            f"  [dim]   → {len(ai_rule_annotations)} rule-based AI pattern annotations[/dim]"
        )

    # ── Phase 2: LLM-based reviewers ──
    def make_prompt(dim: str) -> str:
        """Build the user prompt for a dimension, with extra context if needed."""
        reviewer_cls = LLM_REVIEWERS[dim]
        template = reviewer_cls.user_prompt_template

        if dim == "ai_patterns" and ai_rule_annotations:
            rule_summary = "\n".join(
                f"[Line {a.location.line_start}] {a.severity.value}: {a.what}"
                for a in ai_rule_annotations[:20]
            )
            extra = (
                f"### Rule-based pre-scan results (verify these, add any missed patterns):\n"
                f"{rule_summary}\n\n"
                f"### Paper text:\n"
            )
            return template.replace("{paper_content}", extra + plain_text)
        else:
            return template.replace("{paper_content}", plain_text)

    def call_llm_reviewer(dim: str) -> list[Annotation]:
        """Instantiate a reviewer and run it on the paper."""
        reviewer_cls = LLM_REVIEWERS[dim]
        reviewer = reviewer_cls(llm=llm, model=model)
        prompt = make_prompt(dim)

        # AI patterns reviewer needs more tokens for long papers
        max_tokens = 16384 if dim == "ai_patterns" else 8192

        try:
            result_text = llm_chat(
                reviewer.llm, reviewer.model,
                reviewer.system_prompt, prompt,
                max_tokens=max_tokens, temperature=0.3,
            )
            parsed = _extract_json(result_text)
            if parsed:
                return reviewer._parse_response(parsed)
            else:
                return [reviewer._fallback_annotation(result_text)]
        except Exception as e:
            return [reviewer._error_annotation(str(e))]

    # ── Run (parallel or sequential) ──
    if parallel and len(valid_dims) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(valid_dims)) as executor:
            futures = {executor.submit(call_llm_reviewer, dim): dim for dim in valid_dims}
            for future in concurrent.futures.as_completed(futures):
                dim = futures[future]
                dim_name = DIMENSION_NAMES.get(dim, dim)
                try:
                    anns = future.result()
                    all_annotations.extend(anns)
                    icon = "✓" if anns else "—"
                    console.print(
                        f"  [green]{icon}[/green] {dim_name}: {len(anns)} findings"
                    )
                except Exception as e:
                    console.print(f"  [red]✗[/red] {dim_name}: {e}")
    else:
        for dim in valid_dims:
            dim_name = DIMENSION_NAMES.get(dim, dim)
            anns = call_llm_reviewer(dim)
            all_annotations.extend(anns)
            icon = "✓" if anns else "—"
            console.print(f"  [green]{icon}[/green] {dim_name}: {len(anns)} findings")

    report.annotations = all_annotations

    # ── Summary ──
    console.print(f"\n[bold]Total: {report.total_annotations} annotations found[/bold]")
    if report.high_severity_count:
        console.print(f"[red]  {report.high_severity_count} high severity[/red]")
    console.print()

    return report
