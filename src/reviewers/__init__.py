"""
Reviewers — dimension-specific review modules.

Each reviewer produces Annotation objects that identify, locate, and explain
potential issues. None of them suggest fixes — the human decides.
"""

from src.reviewers.format_reviewer import FormatReviewer
from src.reviewers.language_reviewer import LanguageReviewer
from src.reviewers.ai_pattern_scanner import scan as scan_ai_patterns
from src.reviewers.ai_pattern_scanner import compute_ai_score
from src.reviewers.ai_reviewer import AIReviewer
from src.reviewers.math_reviewer import MathReviewer
from src.reviewers.logic_reviewer import LogicReviewer
from src.reviewers.significance_reviewer import SignificanceReviewer

# Map dimension keys to reviewer classes (LLM-based reviewers)
LLM_REVIEWERS = {
    "format": FormatReviewer,
    "language": LanguageReviewer,
    "ai_patterns": AIReviewer,
    "math": MathReviewer,
    "logic": LogicReviewer,
    "significance": SignificanceReviewer,
}

# Human-readable dimension names
DIMENSION_NAMES = {
    "format": "Format & Structure",
    "language": "Language & Terminology",
    "ai_patterns": "AI Writing Patterns",
    "math": "Mathematical Derivation",
    "logic": "Logical Flow",
    "significance": "Research Significance",
}

# Review order: rule-based first, then LLM-assisted
RULE_BASED_DIMS = {"ai_patterns"}   # dimensions with rule-based pre-scanning
LLM_DIMS = set(LLM_REVIEWERS.keys())

__all__ = [
    "FormatReviewer", "LanguageReviewer", "AIReviewer",
    "MathReviewer", "LogicReviewer", "SignificanceReviewer",
    "scan_ai_patterns", "compute_ai_score",
    "LLM_REVIEWERS", "DIMENSION_NAMES",
    "RULE_BASED_DIMS", "LLM_DIMS",
]
