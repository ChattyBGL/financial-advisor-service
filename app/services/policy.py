"""Context source: sections of the risk & compliance policy PDF.

The PDF is split into sections on its own headings. Each section starts with a
line `SECTION NN` followed by a title line `NN. Title`. A prompt is matched
against section titles by keyword; every matching section is returned whole.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pypdf import PdfReader

from app.core.config import get_settings

MAX_SECTIONS = 3  # cap on whole sections sent to the LLM per prompt

_SECTION_START = re.compile(r"^SECTION\s+(\d+)\s*$", re.MULTILINE)
# Page furniture to drop: the "SECTION NN  CONTINUED" header plus its repeated
# title line, and the three-line footer at the bottom of every page.
_CONTINUED = re.compile(r"^SECTION\s+\d+\W*CONTINUED[^\n]*\n[^\n]*\n", re.MULTILINE)
_FOOTER = re.compile(
    r"^RISK & COMPLIANCE POLICY[^\n]*\n^CONFIDENTIAL[^\n]*\n^Page \d+ of \d+[^\n]*\n?",
    re.MULTILINE,
)
_WORD = re.compile(r"[a-z]{4,}")
_STOP = {"what", "when", "where", "which", "does", "should", "about", "with", "from", "this"}


@dataclass(frozen=True)
class Section:
    number: int
    title: str
    body: str

    def as_text(self) -> str:
        return f"{self.number}. {self.title}\n{self.body}"


def parse_sections(text: str) -> list[Section]:
    """Split the full policy text into sections on the `SECTION NN` heading lines."""
    text = _FOOTER.sub("", _CONTINUED.sub("", text))
    matches = list(_SECTION_START.finditer(text))
    sections = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.end() : end].strip()
        title_line, _, body = block.partition("\n")
        title = re.sub(r"^\d+\.\s*", "", title_line).strip()
        sections.append(Section(number=int(m.group(1)), title=title, body=body.strip()))
    return sections


@lru_cache
def load_sections(pdf_path: Path | None = None) -> list[Section]:
    """Read and parse the PDF once; later calls return the cached list."""
    path = pdf_path or get_settings().policy_pdf
    reader = PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    return parse_sections(text)


def find_policy_context(prompt: str, sections: list[Section] | None = None) -> str:
    """Whole text of the first MAX_SECTIONS sections whose title shares a word with the prompt."""
    words = {w for w in _WORD.findall(prompt.lower()) if w not in _STOP}
    if not words:
        return ""
    sections = load_sections() if sections is None else sections
    hits = [s for s in sections if words & set(_WORD.findall(s.title.lower()))]
    return "\n\n".join(s.as_text() for s in hits[:MAX_SECTIONS])
