"""
Utility functions — config loading, LLM client factory, console output.
"""

import os
import sys
from rich.console import Console
from rich.table import Table

console = Console()


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file, with env var fallback for API key."""
    import yaml

    config: dict = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # Set defaults
    config.setdefault("provider", "anthropic")
    config.setdefault("parallel_reviews", True)
    config.setdefault("output_dir", "output")
    config.setdefault("dimensions", [
        "format", "language", "ai_patterns", "math", "logic", "significance",
    ])

    # Model defaults per provider
    provider = config.get("provider", "anthropic")
    if provider == "deepseek":
        config.setdefault("model", "deepseek-v4-pro")
        env_key = os.environ.get("DEEPSEEK_API_KEY")
    else:
        config.setdefault("model", "claude-sonnet-4-6")
        env_key = os.environ.get("ANTHROPIC_API_KEY")

    if env_key:
        config["api_key"] = env_key

    return config


def create_llm_client(config: dict) -> tuple[str, object]:
    """Create an LLM client based on provider config.

    Returns (provider_type, client) tuple.
    provider_type is "openai" for DeepSeek or "anthropic" for Anthropic.
    """
    from anthropic import Anthropic
    from openai import OpenAI

    provider = config.get("provider", "anthropic")
    api_key = config.get("api_key", "")

    if provider == "deepseek":
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        return ("openai", client)
    else:
        client = Anthropic(api_key=api_key)
        return ("anthropic", client)


def llm_chat(
    llm: tuple[str, object],
    model: str,
    system: str,
    user_message: str,
    max_tokens: int = 8192,
    temperature: float = 0.3,
) -> str:
    """Unified chat call — works with both Anthropic and OpenAI clients.

    Args:
        llm: (provider_type, client) tuple from create_llm_client()
        model: Model name
        system: System prompt
        user_message: User message content
        max_tokens: Max output tokens
        temperature: Sampling temperature

    Returns:
        Text response string
    """
    provider_type, client = llm

    if provider_type == "openai":
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
    else:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        for block in response.content:
            if hasattr(block, "text") and block.type == "text":
                return block.text
        for block in response.content:
            if hasattr(block, "text"):
                return getattr(block, "text", "")
        return ""


def print_banner():
    """Print the tool banner."""
    banner = """
[bold cyan]╔════════════════════════════════════════════════════╗
║  📄  Paper Human-Review Assistant  📄               ║
║  AI annotates, humans decide.                        ║
╚════════════════════════════════════════════════════╝[/bold cyan]
"""
    console.print(banner)


def print_review_table(report) -> None:
    """Print a formatted review summary table."""
    from src.annotation import Severity

    table = Table(title="📋 Review Report — Annotations Summary")
    table.add_column("Dimension", style="cyan", width=20)
    table.add_column("Count", style="white", width=8)
    table.add_column("🔴 High", style="red", width=10)
    table.add_column("🟡 Medium", style="yellow", width=10)
    table.add_column("🟢 Low", style="green", width=10)

    counts = report.count_by_dimension()

    for dim in report.dimensions_reviewed:
        dim_annotations = report.by_dimension(dim)
        high = sum(1 for a in dim_annotations if a.severity == Severity.HIGH)
        med = sum(1 for a in dim_annotations if a.severity == Severity.MEDIUM)
        low = sum(1 for a in dim_annotations if a.severity == Severity.LOW)
        table.add_row(dim, str(len(dim_annotations)), str(high), str(med), str(low))

    table.add_row("", "", "", "", "")
    totals = report.count_by_severity()
    table.add_row(
        "[bold]Total[/bold]",
        str(report.total_annotations),
        str(totals.get("high", 0)),
        str(totals.get("medium", 0)),
        str(totals.get("low", 0)),
    )

    console.print(table)
