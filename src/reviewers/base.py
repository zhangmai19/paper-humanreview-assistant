"""
Base reviewer interface — all dimension reviewers inherit from this.

The base class enforces the "annotate, never suggest" contract:
every reviewer produces Annotation objects that identify, locate, and explain
potential issues — they NEVER propose corrections.
"""

import json
import re
from abc import ABC, abstractmethod

from src.annotation import Annotation, Location, Severity
from src.utils import llm_chat, console


# ─────────────────────────────────────────────
# JSON extraction helper
# ─────────────────────────────────────────────

def _extract_json(text: str) -> dict | None:
    """Extract JSON from LLM response, handling markdown code blocks."""
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


# ─────────────────────────────────────────────
# Base Reviewer
# ─────────────────────────────────────────────

class BaseReviewer(ABC):
    """Abstract base for dimension-specific reviewers.

    Subclasses must define:
        - dimension: str          — dimension key (format, language, etc.)
        - dimension_name: str     — human-readable name
        - system_prompt: str      — system prompt for the LLM call
        - user_prompt_template: str — user prompt with {paper_content} placeholder
    """

    dimension: str
    dimension_name: str
    system_prompt: str
    user_prompt_template: str

    def __init__(self, llm: tuple[str, object], model: str):
        self.llm = llm
        self.model = model

    def review(self, paper_content: str) -> list[Annotation]:
        """Run the review and return a list of Annotations.

        Sends the paper to the LLM with dimension-specific prompts,
        then parses the structured JSON response into Annotation objects.
        """
        prompt = self.user_prompt_template.replace("{paper_content}", paper_content)

        try:
            result_text = llm_chat(
                self.llm, self.model,
                self.system_prompt, prompt,
                max_tokens=8192, temperature=0.3,
            )
            parsed = _extract_json(result_text)

            if parsed:
                return self._parse_response(parsed)
            else:
                console.print(
                    f"  [yellow]⚠ {self.dimension_name}: "
                    f"JSON parse failed, returning raw finding[/yellow]"
                )
                return [self._fallback_annotation(result_text)]

        except Exception as e:
            console.print(f"  [red]✗ {self.dimension_name}: {e}[/red]")
            return [self._error_annotation(str(e))]

    @abstractmethod
    def _parse_response(self, parsed: dict) -> list[Annotation]:
        """Convert the parsed LLM JSON response into Annotation objects.

        Each subclass implements dimension-specific JSON parsing logic.
        """
        ...

    def _fallback_annotation(self, raw_text: str) -> Annotation:
        """Produce a single annotation when JSON parsing fails."""
        return Annotation(
            dimension=self.dimension,
            title=f"{self.dimension_name} — raw output",
            severity=Severity.MEDIUM,
            location=Location(quoted_text=""),
            what="JSON解析失败，请查看详细输出",
            why="LLM返回的JSON格式无法解析",
            category="parse-error",
        )

    def _error_annotation(self, error_msg: str) -> Annotation:
        """Produce a single annotation when the API call itself fails."""
        return Annotation(
            dimension=self.dimension,
            title=f"{self.dimension_name} — API error",
            severity=Severity.LOW,
            location=Location(quoted_text=""),
            what=f"API调用失败: {error_msg}",
            why="本次评审未能完成",
            category="api-error",
        )

    # ── Shared helper for subclasses ──

    @staticmethod
    def _make_location(parsed_item: dict) -> Location:
        """Extract Location from a parsed JSON item."""
        return Location(
            section=parsed_item.get("section", ""),
            paragraph=parsed_item.get("paragraph", 0),
            line_start=parsed_item.get("line_start", 0),
            line_end=parsed_item.get("line_end", 0),
            quoted_text=parsed_item.get("quoted_text", ""),
        )

    @staticmethod
    def _parse_severity(parsed_item: dict) -> Severity:
        """Parse severity string to Severity enum."""
        sev = parsed_item.get("severity", "medium").lower()
        if sev in ("high", "critical", "major"):
            return Severity.HIGH
        elif sev in ("medium", "moderate"):
            return Severity.MEDIUM
        else:
            return Severity.LOW
