"""Tests for PaperReader — paper loading, parsing, plain-text extraction."""

import os
import pytest
from pathlib import Path

from src.paper_reader import PaperReader, Paper, PaperSection


PAPERS_DIR = Path(__file__).parent.parent / "papers"


class TestDetectFormat:
    def test_latex_extensions(self):
        assert PaperReader.detect_format("paper.tex") == "latex"
        assert PaperReader.detect_format("paper.ltx") == "latex"
        assert PaperReader.detect_format("paper.latex") == "latex"

    def test_markdown_extensions(self):
        assert PaperReader.detect_format("paper.md") == "markdown"
        assert PaperReader.detect_format("paper.markdown") == "markdown"

    def test_text_fallback(self):
        assert PaperReader.detect_format("paper.txt") == "text"
        assert PaperReader.detect_format("paper.unknown") == "text"


class TestLoadLatex:
    def test_load_sample_tex(self):
        path = str(PAPERS_DIR / "sample.tex")
        paper = PaperReader.load(path)

        assert paper.format == "latex"
        assert len(paper.raw_text) > 0
        assert paper.preamble != ""
        assert paper.body != ""
        # Should find sections
        assert len(paper.sections) > 0
        # Should find Introduction, Methodology, Results, Discussion, Conclusion
        headings = {s.heading.lower() for s in paper.sections}
        assert "introduction" in headings
        assert "methodology" in headings

    def test_metadata_populated(self):
        path = str(PAPERS_DIR / "sample.tex")
        paper = PaperReader.load(path)

        assert "filename" in paper.metadata
        assert paper.metadata["filename"] == "sample.tex"
        assert paper.metadata["size_bytes"] > 0
        assert "hash" in paper.metadata


class TestGetPlainText:
    def test_strips_latex_commands(self):
        path = str(PAPERS_DIR / "sample.tex")
        paper = PaperReader.load(path)
        plain = PaperReader.get_plain_text(paper)

        # Should not contain LaTeX commands
        assert "\\section" not in plain
        assert "\\begin" not in plain
        assert "\\documentclass" not in plain
        # Comments should be stripped
        assert "%" not in plain
        # Math should be replaced with placeholders
        assert "[公式]" in plain or "[公式块]" in plain
        # Real content should remain
        assert "Introduction" in plain
        assert "Methodology" in plain

    def test_keep_human_readable(self):
        path = str(PAPERS_DIR / "sample.tex")
        paper = PaperReader.load(path)
        plain = PaperReader.get_plain_text(paper)

        # The plain text should be readable
        assert len(plain) > 100
        assert "E = mc^2" not in plain  # math should be replaced


class TestGetSectionText:
    def test_finds_existing_section(self):
        path = str(PAPERS_DIR / "sample.tex")
        paper = PaperReader.load(path)
        text = PaperReader.get_section_text(paper, "Introduction")

        assert text is not None
        assert len(text) > 0
        assert "introduction section" in text.lower()


class TestGetLineContext:
    def test_returns_surrounding_lines(self):
        text = "line 1\nline 2\nline 3\nline 4\nline 5"
        ctx = PaperReader.get_line_context(text, 3, window=2)
        assert "line 1" in ctx
        assert "line 5" in ctx


class TestNonexistentFile:
    def test_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            PaperReader.load("/nonexistent/path/paper.tex")
