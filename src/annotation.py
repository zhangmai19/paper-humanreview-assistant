"""
Annotation data models — the core output format for all reviewers.

Every AI finding is an Annotation: a located, explained observation.
Deliberately omits "suggested fix" — the human decides what to do.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    """How much attention this finding deserves."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Location:
    """Pinpoint where in the paper an issue was found."""
    section: str = ""           # e.g., "Introduction", "3.2. Methodology"
    paragraph: int = 0          # paragraph number within section (1-based)
    line_start: int = 0         # global line number in source file
    line_end: int = 0
    quoted_text: str = ""       # short excerpt showing the issue


@dataclass
class Annotation:
    """
    A single finding from a review dimension.

    An Annotation says "here's something to check" — never "here's how to fix it."
    """
    dimension: str              # which review dimension: format, language, ai_patterns, ...
    title: str                  # short, human-readable summary
    severity: Severity
    location: Location          # where in the paper
    what: str                   # what the issue is
    why: str                    # why it matters (evidence-based rationale)
    category: str = ""          # sub-category within the dimension (e.g., "citation-format")


@dataclass
class ReviewReport:
    """
    The complete output of a review session.

    Contains all annotations across all dimensions, plus paper metadata.
    """
    paper_path: str
    paper_title: str = ""
    dimensions_reviewed: list[str] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    summary: str = ""           # overall summary paragraph
    metadata: dict = field(default_factory=dict)

    def by_dimension(self, dimension: str) -> list[Annotation]:
        """Return annotations for a specific dimension."""
        return [a for a in self.annotations if a.dimension == dimension]

    def by_severity(self, severity: Severity) -> list[Annotation]:
        """Return annotations at a specific severity level."""
        return [a for a in self.annotations if a.severity == severity]

    def count_by_dimension(self) -> dict[str, int]:
        """Count annotations per dimension."""
        counts: dict[str, int] = {}
        for a in self.annotations:
            counts[a.dimension] = counts.get(a.dimension, 0) + 1
        return counts

    def count_by_severity(self) -> dict[str, int]:
        """Count annotations per severity level."""
        counts: dict[str, int] = {}
        for a in self.annotations:
            counts[a.severity.value] = counts.get(a.severity.value, 0) + 1
        return counts

    @property
    def total_annotations(self) -> int:
        return len(self.annotations)

    @property
    def high_severity_count(self) -> int:
        return sum(1 for a in self.annotations if a.severity == Severity.HIGH)
