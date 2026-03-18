from __future__ import annotations

import collections
import re
from io import BytesIO
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from pypdf import PdfReader


@dataclass
class Chapter:
    title: str
    text: str
    start_page: int
    end_page: int


@dataclass
class TocEntry:
    number: int
    title: str
    toc_page: int


def extract_pdf_text(file_bytes: bytes) -> List[str]:
    reader = PdfReader(BytesIO(file_bytes))
    pages: List[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return pages


def extract_chapters_from_pdf(
    file_bytes: bytes,
    heading_patterns: Sequence[str],
    min_chapter_chars: int,
) -> Tuple[List[Chapter], bool]:
    pages = extract_pdf_text(file_bytes)
    has_contents_page = _find_contents_page(pages) is not None
    if has_contents_page:
        toc_entries = parse_toc_entries(pages)
        if toc_entries:
            chapters = chapters_from_toc(pages, toc_entries, min_chapter_chars)
            if chapters:
                return chapters, True
        return [], True

    return split_into_chapters(pages, heading_patterns, min_chapter_chars), False


def parse_toc_entries(pages: Sequence[str]) -> List[TocEntry]:
    contents_page_idx = _find_contents_page(pages)
    if contents_page_idx is None:
        return []

    toc_entries: List[TocEntry] = []
    seen_numbers = set()
    max_scan = min(contents_page_idx + 30, len(pages))
    no_match_pages = 0

    for page_idx in range(contents_page_idx, max_scan):
        page_lines = [line.strip() for line in pages[page_idx].splitlines() if line.strip()]
        page_entries = _parse_toc_page_entries(page_lines)
        page_matches = 0
        for chapter_no, chapter_title, chapter_page in page_entries:
            if chapter_no in seen_numbers:
                continue
            seen_numbers.add(chapter_no)
            toc_entries.append(
                TocEntry(number=chapter_no, title=chapter_title, toc_page=chapter_page)
            )
            page_matches += 1

        if page_matches == 0:
            no_match_pages += 1
        else:
            no_match_pages = 0
        if no_match_pages >= 3 and toc_entries:
            break

    return sorted(toc_entries, key=lambda item: item.number)


def chapters_from_toc(
    pages: Sequence[str],
    toc_entries: Sequence[TocEntry],
    min_chapter_chars: int,
) -> List[Chapter]:
    if not toc_entries:
        return []

    offset = _infer_pdf_page_offset(pages, toc_entries)
    mapped_starts: List[Tuple[TocEntry, int]] = []
    for entry in toc_entries:
        start_idx = max(0, min(len(pages) - 1, entry.toc_page + offset - 1))
        mapped_starts.append((entry, start_idx))

    mapped_starts.sort(key=lambda x: x[1])
    chapters: List[Chapter] = []

    for i, (entry, start_idx) in enumerate(mapped_starts):
        if i + 1 < len(mapped_starts):
            end_idx = mapped_starts[i + 1][1] - 1
        else:
            end_idx = len(pages) - 1
        if end_idx < start_idx:
            continue

        chapter_text = "\n\n".join(pages[start_idx : end_idx + 1]).strip()
        if len(chapter_text) < min_chapter_chars:
            continue

        chapter_title = f"Chapter {entry.number}: {entry.title}"
        chapters.append(
            Chapter(
                title=chapter_title,
                text=chapter_text,
                start_page=start_idx + 1,
                end_page=end_idx + 1,
            )
        )

    return chapters


def split_into_chapters(
    pages: Sequence[str], heading_patterns: Sequence[str], min_chapter_chars: int
) -> List[Chapter]:
    full_text = "\n\n".join(pages).strip()
    if not full_text:
        return []

    heading_regexes = [re.compile(pattern) for pattern in heading_patterns]

    chapter_boundaries = []
    lines = full_text.splitlines()
    for i, line in enumerate(lines):
        if any(regex.match(line) for regex in heading_regexes):
            chapter_boundaries.append(i)

    if not chapter_boundaries:
        return _fallback_segments(full_text, min_chapter_chars)

    chapter_boundaries.append(len(lines))
    chapters: List[Chapter] = []

    for idx in range(len(chapter_boundaries) - 1):
        start = chapter_boundaries[idx]
        end = chapter_boundaries[idx + 1]

        chunk_lines = lines[start:end]
        chunk_text = "\n".join(chunk_lines).strip()
        if len(chunk_text) < min_chapter_chars:
            continue

        first_line = chunk_lines[0].strip() if chunk_lines else ""
        title = first_line if first_line else f"Chapter {len(chapters) + 1}"
        chapters.append(Chapter(title=title, text=chunk_text, start_page=0, end_page=0))

    if chapters:
        return chapters

    return _fallback_segments(full_text, min_chapter_chars)


def _fallback_segments(text: str, min_chapter_chars: int) -> List[Chapter]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chapters: List[Chapter] = []
    buffer = []
    current_len = 0

    for para in paragraphs:
        buffer.append(para)
        current_len += len(para)
        if current_len >= min_chapter_chars:
            chapter_text = "\n\n".join(buffer)
            chapters.append(
                Chapter(title=f"Segment {len(chapters) + 1}", text=chapter_text, start_page=0, end_page=0)
            )
            buffer = []
            current_len = 0

    if buffer:
        chapter_text = "\n\n".join(buffer)
        if chapter_text:
            chapters.append(
                Chapter(title=f"Segment {len(chapters) + 1}", text=chapter_text, start_page=0, end_page=0)
            )

    return chapters


def _find_contents_page(pages: Sequence[str]) -> int | None:
    for i, page_text in enumerate(pages[:40]):
        lowered = page_text.lower()
        if "table of contents" in lowered or re.search(r"(?im)^contents\s*$", page_text):
            return i
    return None


def _parse_toc_line(line: str) -> Tuple[int, str, int] | None:
    normalized = " ".join(line.strip().split())
    if not normalized:
        return None

    patterns = [
        r"^(?:chapter\s+)?(?P<num>\d{1,2})\s*[:.\-]?\s*(?P<title>.+?)\s*\.{2,}\s*(?P<page>\d{1,4})$",
        r"^(?:chapter\s+)?(?P<num>\d{1,2})\s*[:.\-]?\s*(?P<title>.+?)\s+(?P<page>\d{1,4})$",
    ]
    for pattern in patterns:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if not match:
            continue
        chapter_no = int(match.group("num"))
        chapter_title = match.group("title").strip(" .-")
        chapter_page = int(match.group("page"))
        if chapter_page <= 0 or not chapter_title:
            continue
        return chapter_no, chapter_title, chapter_page
    return None


def _parse_toc_page_entries(lines: Sequence[str]) -> List[Tuple[int, str, int]]:
    entries: List[Tuple[int, str, int]] = []
    i = 0
    while i < len(lines):
        line = " ".join(lines[i].split())
        parsed = _parse_toc_line(line)
        if parsed:
            entries.append(parsed)
            i += 1
            continue

        partial = _parse_toc_line_without_page(line)
        if not partial:
            i += 1
            continue

        chapter_no, chapter_title = partial
        page_no = None
        j = i + 1
        while j < len(lines) and j <= i + 4:
            next_line = " ".join(lines[j].split())

            if re.fullmatch(r"\d{1,4}", next_line):
                page_no = int(next_line)
                break

            if re.match(r"^(?:chapter\s+)?\d{1,2}\b", next_line, flags=re.IGNORECASE):
                break

            tail_with_page = re.match(r"^(?P<tail>.+?)\s+(?P<page>\d{1,4})$", next_line)
            if tail_with_page:
                chapter_title = f"{chapter_title} {tail_with_page.group('tail')}".strip()
                page_no = int(tail_with_page.group("page"))
                break

            chapter_title = f"{chapter_title} {next_line}".strip()
            j += 1

        if page_no is not None:
            entries.append((chapter_no, chapter_title.strip(" .-"), page_no))
            i = j + 1
        else:
            i += 1

    return entries


def _parse_toc_line_without_page(line: str) -> Tuple[int, str] | None:
    match = re.match(
        r"^(?:chapter\s+)?(?P<num>\d{1,2})\s*[:.\-]?\s*(?P<title>.+?)\s*\.{0,}$",
        line,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    chapter_no = int(match.group("num"))
    chapter_title = match.group("title").strip(" .-")
    if not chapter_title:
        return None
    return chapter_no, chapter_title


def _infer_pdf_page_offset(pages: Sequence[str], toc_entries: Sequence[TocEntry]) -> int:
    if not toc_entries:
        return 0

    diffs: List[int] = []
    sample_entries = toc_entries[: min(8, len(toc_entries))]
    for entry in sample_entries:
        expected = _normalize_for_search(entry.title)
        chapter_tag = f"chapter {entry.number}"
        for page_idx, page_text in enumerate(pages):
            normalized_page = _normalize_for_search(page_text)
            if not normalized_page:
                continue
            if chapter_tag in normalized_page and _title_keywords_present(expected, normalized_page):
                diffs.append((page_idx + 1) - entry.toc_page)
                break

    if not diffs:
        return 0
    return collections.Counter(diffs).most_common(1)[0][0]


def _normalize_for_search(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[^a-z0-9\s]+", " ", lowered)
    return " ".join(lowered.split())


def _title_keywords_present(title: str, page_text: str) -> bool:
    words = [word for word in title.split() if len(word) >= 4][:4]
    if not words:
        return True
    return all(word in page_text for word in words[:2])
