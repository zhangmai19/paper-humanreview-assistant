#!/usr/bin/env python3
"""
Paper Human-Review Assistant — AI-assisted academic paper review tool.

AI annotates, humans decide. Produces structured Markdown reports
that help human reviewers read more efficiently.

Usage:
    python main.py paper.tex
    python main.py paper.tex --dimensions format,ai_patterns,logic
    python main.py paper.tex --output-dir reviews/ --model claude-opus-4-8
    python main.py paper.tex --math --repair
"""

import sys
import os
from pathlib import Path

import click

from src.utils import load_config, create_llm_client, print_banner, console

@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("paper", type=click.Path(exists=True), required=True)
@click.option(
    "--dimensions", "-d", default=None, type=str,
    help="Review dimensions, comma-separated: format,language,ai_patterns,math,logic,significance",
)
@click.option(
    "--output-dir", "-o", default=None, type=str,
    help="Output directory (default: output/)",
)
@click.option(
    "--model", "-m", default=None, type=str,
    help="Model name (e.g., claude-sonnet-4-6, claude-opus-4-8)",
)
@click.option(
    "--provider", "-p", default=None, type=str,
    help="LLM provider: anthropic (default) or deepseek",
)
@click.option(
    "--no-parallel", "serial", is_flag=True, default=False,
    help="Run reviews sequentially instead of in parallel",
)
@click.option(
    "--api-key", default=None, type=str,
    help="API key (or set ANTHROPIC_API_KEY / DEEPSEEK_API_KEY env var)",
)
@click.option(
    "--config", "config_path", default="config.yaml",
    help="Config file path (default: config.yaml)",
)
@click.option(
    "--verbose", "-v", is_flag=True, default=False,
    help="Verbose output",
)
@click.option(
    "--repair", is_flag=True, default=False,
    help="Enable math gap repair: numerical verification + symbolic derivation "
         "for math annotations. Generates repair reports with Lemma/Appendix suggestions.",
)
def main(
    paper: str,
    dimensions: str | None,
    output_dir: str | None,
    model: str | None,
    provider: str | None,
    serial: bool,
    api_key: str | None,
    config_path: str,
    verbose: bool,
    repair: bool,
):
    """
    Review an academic paper across multiple dimensions.

    PAPER: path to .tex, .md, or .txt file.
    Produces a structured Markdown review report — AI annotates, you decide.

    With --repair, also runs numerical verification + symbolic derivation
    on math annotations and generates repair reports.
    """
    # --- Load config ---
    if os.path.exists(config_path):
        config = load_config(config_path)
    else:
        config = load_config("nonexistent")

    final_provider = provider or config.get("provider", "anthropic")
    final_model = model or config.get("model", "claude-sonnet-4-6")
    final_output_dir = output_dir or config.get("output_dir", "output")

    # Parse dimensions
    if dimensions:
        final_dimensions = [d.strip() for d in dimensions.split(",")]
    else:
        final_dimensions = config.get("dimensions", None)

    # API key resolution
    env_key = (
        os.environ.get("DEEPSEEK_API_KEY")
        if final_provider == "deepseek"
        else (
            os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        )
    )
    final_api_key = api_key or config.get("api_key") or env_key
    if not final_api_key:
        key_vars = (
            "DEEPSEEK_API_KEY" if final_provider == "deepseek"
            else "ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN"
        )
        console.print(f"\n[bold red]Error: No {final_provider.upper()} API key[/bold red]")
        console.print(f"Set via: env var {key_vars}, --api-key, or config.yaml")
        sys.exit(1)

    config["provider"] = final_provider
    config["api_key"] = final_api_key

    # --- Validate paper ---
    paper_path = Path(paper).resolve()
    if not paper_path.exists():
        console.print(f"[bold red]Error: paper not found: {paper}[/bold red]")
        sys.exit(1)

    print_banner()

    # --- Initialize LLM client ---
    llm = create_llm_client(config)

    # --- Load paper ---
    console.print(f"[dim]Loading paper...[/dim]")
    from src.paper_reader import PaperReader
    paper_obj = PaperReader.load(str(paper_path))
    console.print(
        f"[dim]Format: {paper_obj.format} | "
        f"Sections: {len(paper_obj.sections)} | "
        f"Size: {paper_obj.metadata.get('size_bytes', 0)} bytes[/dim]"
    )

    # --- Run review ---
    from src.orchestrator import run_review
    report = run_review(
        paper=paper_obj,
        dimensions=final_dimensions or [
            "format", "language", "ai_patterns", "math", "logic", "significance"
        ],
        llm=llm,
        model=final_model,
        parallel=not serial,
    )

    # --- Print summary ---
    from src.utils import print_review_table
    print_review_table(report)

    # --- Write report ---
    from src.report_writer import write_report
    output_path = write_report(report, output_dir=final_output_dir)
    console.print(f"\n[bold green]📄 Report saved:[/bold green] {output_path}")

    # --- Math gap repair ---
    if repair and paper_obj.format == "latex":
        math_annotations = report.by_dimension("math")
        gap_annotations = [
            a for a in math_annotations
            if a.category in ("assumption", "derivation-gap", "completeness")
            and a.severity.value in ("high", "medium")
        ]
        if gap_annotations:
            console.print(f"\n[bold cyan]🔧 Math Gap Repair[/bold cyan]")
            console.print(
                f"[dim]  {len(gap_annotations)} repairable math gaps found "
                f"({len(math_annotations)} total math annotations)[/dim]\n"
            )
            from src.math_gap_repair.engine import repair_math_gap
            for i, ann in enumerate(gap_annotations):
                console.print(
                    f"  [{i+1}/{len(gap_annotations)}] "
                    f"Repairing: [cyan]{ann.title}[/cyan]..."
                )
                repair_path = repair_math_gap(
                    paper=paper_obj,
                    annotation=ann,
                    output_dir=final_output_dir,
                )
                if repair_path:
                    console.print(f"    [green]→[/green] {repair_path}")
                else:
                    console.print(f"    [dim]→ skipped (could not extract expression)[/dim]")
        else:
            console.print(f"\n[dim]🔧 No repairable math gaps found (need HIGH/MEDIUM "
                         f"assumptions or derivation-gaps)[/dim]")
    elif repair and paper_obj.format != "latex":
        console.print(
            f"\n[yellow]⚠ --repair only supports LaTeX papers, "
            f"got {paper_obj.format}[/yellow]"
        )


if __name__ == "__main__":
    main()
