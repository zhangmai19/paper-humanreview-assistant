"""
Paper Reader — load, parse, and extract plain text from academic papers.

Supports LaTeX (.tex), Markdown (.md), and plain text (.txt).
Deliberately does NOT include save, diff, or revision logic —
this tool annotates papers, it does not modify them.
"""

import os
import re
import hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class PaperSection:
    """A section of the paper with location info."""
    heading: str                # section heading (e.g., "Introduction", "Methodology")
    level: int                  # 0 = title, 1 = section, 2 = subsection, 3 = subsubsection
    content: str                # full text content of this section
    start_line: int
    end_line: int


@dataclass
class Paper:
    """An academic paper in LaTeX or Markdown format."""
    file_path: str
    format: str                 # "latex", "markdown", or "text"
    raw_text: str
    sections: list[PaperSection] = field(default_factory=list)
    preamble: str = ""          # LaTeX preamble (everything before \begin{document})
    body: str = ""              # main body content
    metadata: dict = field(default_factory=dict)


class PaperReader:
    """Handles paper loading, parsing, and plain-text extraction.

    Does NOT save, diff, or modify papers — this tool annotates, not rewrites.
    """

    SUPPORTED_FORMATS = [".tex", ".ltx", ".latex", ".md", ".markdown", ".txt"]

    @staticmethod
    def detect_format(file_path: str) -> str:
        """Detect paper format from file extension."""
        ext = Path(file_path).suffix.lower()
        if ext in [".tex", ".ltx", ".latex"]:
            return "latex"
        elif ext in [".md", ".markdown"]:
            return "markdown"
        else:
            return "text"

    @staticmethod
    def load(file_path: str) -> Paper:
        """Load a paper from file, auto-detecting format."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Paper not found: {file_path}")

        fmt = PaperReader.detect_format(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        paper = Paper(
            file_path=file_path,
            format=fmt,
            raw_text=raw_text,
            metadata={
                "filename": os.path.basename(file_path),
                "size_bytes": os.path.getsize(file_path),
                "load_time": datetime.now().isoformat(),
                "hash": hashlib.sha256(raw_text.encode()).hexdigest()[:16],
            },
        )

        if fmt == "latex":
            PaperReader._parse_latex(paper)
        else:
            PaperReader._parse_markdown(paper)

        return paper

    @staticmethod
    def _parse_latex(paper: Paper):
        """Parse LaTeX document into preamble, body, and sections."""
        text = paper.raw_text

        doc_begin = re.search(r'\\begin\{document\}', text)
        doc_end = re.search(r'\\end\{document\}', text)

        if doc_begin:
            paper.preamble = text[:doc_begin.start()]
            body_start = doc_begin.end()
            paper.body = text[body_start:doc_end.start()] if doc_end else text[body_start:]
        else:
            paper.preamble = ""
            paper.body = text

        # Parse sections from body
        section_pattern = re.compile(
            r'\\(section|subsection|subsubsection|chapter|part)\{([^}]*)\}',
            re.MULTILINE,
        )

        level_map = {
            "part": 0, "chapter": 0,
            "section": 1, "subsection": 2, "subsubsection": 3,
        }

        section_matches = list(section_pattern.finditer(paper.body))

        for idx, match in enumerate(section_matches):
            cmd = match.group(1)
            title = match.group(2)
            start = match.start()
            end = (
                section_matches[idx + 1].start()
                if idx + 1 < len(section_matches)
                else len(paper.body)
            )

            start_line = paper.body[:start].count("\n") + 1
            end_line = paper.body[:end].count("\n") + 1

            paper.sections.append(PaperSection(
                heading=title.strip(),
                level=level_map.get(cmd, 1),
                content=paper.body[start:end].strip(),
                start_line=start_line,
                end_line=end_line,
            ))

    @staticmethod
    def _parse_markdown(paper: Paper):
        """Parse Markdown document into sections."""
        text = paper.raw_text
        section_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        section_matches = list(section_pattern.finditer(text))

        for idx, match in enumerate(section_matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            start = match.start()
            end = (
                section_matches[idx + 1].start()
                if idx + 1 < len(section_matches)
                else len(text)
            )

            start_line = text[:start].count("\n") + 1
            end_line = text[:end].count("\n") + 1

            paper.sections.append(PaperSection(
                heading=title,
                level=min(level, 3),
                content=text[start:end].strip(),
                start_line=start_line,
                end_line=end_line,
            ))

        paper.body = text

    @staticmethod
    def get_plain_text(paper: Paper) -> str:
        """Extract plain text from a paper for review purposes.

        Strips LaTeX commands to produce readable text while preserving
        structure (sections, paragraphs). Math is replaced with placeholders
        since its correctness is checked separately.
        """
        text = paper.body if paper.body else paper.raw_text

        if paper.format == "latex":
            # Replace math environments BEFORE stripping LaTeX commands
            text = re.sub(r'\\begin\{equation\}.*?\\end\{equation\}', '[公式]', text, flags=re.DOTALL)
            text = re.sub(r'\\begin\{equation\*\}.*?\\end\{equation\*\}', '[公式]', text, flags=re.DOTALL)
            text = re.sub(r'\\begin\{align\}.*?\\end\{align\}', '[公式]', text, flags=re.DOTALL)
            text = re.sub(r'\\begin\{align\*\}.*?\\end\{align\*\}', '[公式]', text, flags=re.DOTALL)
            text = re.sub(r'\\begin\{eqnarray\}.*?\\end\{eqnarray\}', '[公式]', text, flags=re.DOTALL)
            text = re.sub(r'\$\$[^$]*\$\$', '[公式块]', text)     # display math
            text = re.sub(r'\$[^$]*\$', '[公式]', text)           # inline math → placeholder
            # Strip remaining LaTeX commands
            text = re.sub(r'\\\w+\{([^}]*)\}', r'\1', text)   # \cmd{arg} → arg
            text = re.sub(r'\\\w+', '', text)                   # \cmd
            text = re.sub(r'\\begin\{[^}]*\}', '', text)        # \begin{env}
            text = re.sub(r'\\end\{[^}]*\}', '', text)          # \end{env}
            text = re.sub(r'%.*$', '', text, flags=re.MULTILINE)  # comments
            text = re.sub(r'\n\s*\n', '\n\n', text)              # collapse blank lines

        return text.strip()

    @staticmethod
    def get_section_text(paper: Paper, heading: str) -> str | None:
        """Get the text content of a section by heading name."""
        for section in paper.sections:
            if section.heading.lower() == heading.lower():
                return section.content
        return None

    @staticmethod
    def get_line_context(text: str, line_number: int, window: int = 3) -> str:
        """Get surrounding lines for context around a line number."""
        lines = text.split("\n")
        start = max(0, line_number - window - 1)
        end = min(len(lines), line_number + window)
        return "\n".join(lines[start:end])
