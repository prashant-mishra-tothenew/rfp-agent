"""TTN proposal PPTX template rendering.

The template at templates/proposal-template.pptx is the base deck for every RFP.
Commercial Summary and Success Stories slides are preserved unchanged.
All other mapped slides are filled from generated proposal content.
"""

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Pt

from app.config import settings

# 0-based slide indices that must never be modified.
FIXED_SLIDE_INDICES: frozenset[int] = frozenset(
    {
        20,
        21,  # Commercial Summary (engagement model + payment milestones)
        23,
        24,
        25,  # Success Stories
    }
)

# 0-based slide index -> proposal content key.
SLIDE_CONTENT_MAP: dict[int, str] = {
    2: "executiveSummary",
    3: "relevantExperience",
    4: "understandingOfRequirements",
    5: "proposedSolution",
    6: "technicalApproach",
    7: "securityCompliance",
    8: "assumptions",
    9: "assumptions",
    11: "proposedSolution",
    12: "technicalApproach",
    13: "technicalApproach",
    14: "technicalApproach",
    16: "implementationMethodology",
    17: "supportAndSla",
    18: "implementationMethodology",
    26: "executiveSummary",
}

SKIP_TEXT = frozenset({"‹#›", "Commercial Summary", "Success Stories", "Agenda"})
FOOTER_TOP_EMU = 4_000_000
FOOTNOTE_TOP_EMU = 4_000_000
CHARS_PER_INCH_WIDTH = 11
LINES_PER_INCH_HEIGHT = 4.5
BODY_FONT_PT = 10
MIN_SHAPE_WIDTH_IN = 0.8
MIN_SHAPE_HEIGHT_IN = 0.5
EMU_PER_INCH = 914_400


def resolve_pptx_template_path() -> Path:
    configured = Path(settings.pptx_template_path)
    if configured.exists():
        return configured

    repo_fallback = (
        Path(__file__).resolve().parents[3] / "templates" / "proposal-template.pptx"
    )
    if repo_fallback.exists():
        return repo_fallback

    return configured


def _coerce_text(value: Any, max_len: int | None = None) -> str:
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    elif isinstance(value, list):
        text = "\n".join(_coerce_text(item) for item in value if item)
    elif isinstance(value, dict):
        for key in ("text", "content", "body", "paragraph", "summary", "value"):
            if key in value:
                text = _coerce_text(value[key])
                break
        else:
            text = "\n".join(_coerce_text(item) for item in value.values() if item)
    else:
        text = str(value)

    return text[:max_len] if max_len is not None else text


def _iter_text_shapes(slide: Any) -> Iterator[Any]:
    for shape in slide.shapes:
        if hasattr(shape, "text_frame"):
            yield shape
        elif hasattr(shape, "shapes"):
            for child in shape.shapes:
                if hasattr(child, "text_frame"):
                    yield child


def _shape_area(shape: Any) -> int:
    return int(getattr(shape, "width", 0)) * int(getattr(shape, "height", 0))


def _is_footer_shape(shape: Any) -> bool:
    text = shape.text.strip() if hasattr(shape, "text") else ""
    if text in SKIP_TEXT:
        return True

    top = getattr(shape, "top", 0)
    width_in, _ = _shape_size_inches(shape)
    return top > 4_700_000 and width_in < 1.5


def _find_title_shape(shapes: list[Any]) -> Any | None:
    candidates: list[tuple[int, Any]] = []
    for shape in shapes:
        text = shape.text.strip()
        if not text or _is_footer_shape(shape):
            continue
        candidates.append((getattr(shape, "top", 0), shape))

    if not candidates:
        return None

    return min(candidates, key=lambda item: item[0])[1]


def _shape_size_inches(shape: Any) -> tuple[float, float]:
    return (
        getattr(shape, "width", 0) / EMU_PER_INCH,
        getattr(shape, "height", 0) / EMU_PER_INCH,
    )


def _shape_char_capacity(shape: Any) -> int:
    width_in, height_in = _shape_size_inches(shape)
    if width_in < MIN_SHAPE_WIDTH_IN or height_in < MIN_SHAPE_HEIGHT_IN:
        return 0

    chars_per_line = max(12, int(width_in * CHARS_PER_INCH_WIDTH))
    max_lines = max(2, int(height_in * LINES_PER_INCH_HEIGHT))
    return chars_per_line * max_lines


def _truncate_text(text: str, max_chars: int) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if max_chars <= 0:
        return ""
    if len(cleaned) <= max_chars:
        return cleaned

    trimmed = cleaned[:max_chars].rstrip()
    for separator in (". ", "; ", ", ", " "):
        split_at = trimmed.rfind(separator)
        if split_at >= int(max_chars * 0.55):
            return trimmed[: split_at + (1 if separator == ". " else 0)].strip()

    return trimmed.rstrip(" ,;.") + "…"


def _apply_body_font(text_frame: Any) -> None:
    text_frame.word_wrap = True
    for paragraph in text_frame.paragraphs:
        paragraph.space_after = Pt(2)
        for run in paragraph.runs:
            run.font.size = Pt(BODY_FONT_PT)


def _set_text_frame(
    text_frame: Any,
    text: str,
    shape: Any | None = None,
    max_bullets: int = 12,
) -> None:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs:
        return

    capacity = _shape_char_capacity(shape) if shape is not None else 800
    if capacity <= 0:
        capacity = 120

    fitted: list[str] = []
    used = 0
    for paragraph in paragraphs[:max_bullets]:
        remaining = capacity - used
        if remaining <= 0:
            break
        line = _truncate_text(paragraph, remaining)
        if not line:
            break
        fitted.append(line)
        used += len(line) + 1

    if not fitted:
        fitted = [_truncate_text(paragraphs[0], capacity)]

    text_frame.clear()
    text_frame.text = fitted[0]
    for paragraph in fitted[1:]:
        bullet = text_frame.add_paragraph()
        bullet.text = paragraph
        bullet.level = 0

    _apply_body_font(text_frame)


def _content_to_lines(text: str) -> list[str]:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if len(lines) <= 1 and len(text) > 120:
        lines = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    return lines


def _split_table_line(line: str, max_left: int = 80, max_right: int = 180) -> tuple[str, str]:
    for separator in (" | ", " - ", ": "):
        if separator in line:
            left, right = line.split(separator, 1)
            return _truncate_text(left, max_left), _truncate_text(right, max_right)
    if len(line) > max_left:
        return _truncate_text(line, max_left), _truncate_text(line, max_right)
    return line, line


def _is_footnote_shape(shape: Any) -> bool:
    top = getattr(shape, "top", 0)
    _, height_in = _shape_size_inches(shape)
    width_in, _ = _shape_size_inches(shape)
    return top > FOOTNOTE_TOP_EMU or (height_in < 0.75 and width_in > 6)


def _clear_footnotes(slide: Any, title_shape: Any | None) -> None:
    for shape in _iter_text_shapes(slide):
        if shape is title_shape or _is_footer_shape(shape):
            continue
        if shape.shape_type == MSO_SHAPE_TYPE.TABLE:
            continue
        if _is_footnote_shape(shape):
            shape.text_frame.clear()


def _update_slide_table(slide: Any, text: str) -> bool:
    tables = [shape for shape in slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.TABLE]
    if not tables:
        return False

    table = tables[0].table
    lines = _content_to_lines(text)
    for row_index in range(1, len(table.rows)):
        line_index = row_index - 1
        if line_index < len(lines):
            left, right = _split_table_line(lines[line_index])
            table.cell(row_index, 0).text = left
            if len(table.columns) > 1:
                table.cell(row_index, 1).text = right
        else:
            table.cell(row_index, 0).text = ""
            if len(table.columns) > 1:
                table.cell(row_index, 1).text = ""
    return True


def _is_multi_card_layout(body_shapes: list[Any]) -> bool:
    cards = [shape for shape in body_shapes if _shape_char_capacity(shape) >= 100]
    if len(cards) < 3:
        return False

    areas = [_shape_area(shape) for shape in cards]
    average = sum(areas) / len(areas)
    if average <= 0:
        return False

    return all(abs(area - average) / average < 0.3 for area in areas)


def _update_multi_card_slide(body_shapes: list[Any], text: str) -> None:
    cards = sorted(
        [shape for shape in body_shapes if _shape_char_capacity(shape) >= 100],
        key=lambda shape: (shape.top, shape.left),
    )
    lines = _content_to_lines(text)

    for index, shape in enumerate(cards):
        if index < len(lines):
            _set_text_frame(shape.text_frame, lines[index], shape, max_bullets=4)
        else:
            shape.text_frame.clear()


def _update_slide_body(slide: Any, text: str) -> None:
    if not text.strip():
        return

    text_shapes = list(_iter_text_shapes(slide))
    title_shape = _find_title_shape(text_shapes)
    body_shapes: list[Any] = []

    for shape in text_shapes:
        if _is_footer_shape(shape) or shape is title_shape:
            continue
        if _shape_char_capacity(shape) <= 0:
            continue
        body_shapes.append(shape)

    if not body_shapes:
        return

    if _is_multi_card_layout(body_shapes):
        cards = [
            shape for shape in body_shapes if _shape_char_capacity(shape) >= 100
        ]
        for shape in body_shapes:
            if shape not in cards:
                shape.text_frame.clear()
        _update_multi_card_slide(body_shapes, text)
        return

    primary_shape = max(body_shapes, key=_shape_area)
    for shape in body_shapes:
        if shape is not primary_shape:
            shape.text_frame.clear()

    _set_text_frame(primary_shape.text_frame, text, primary_shape)


def _update_slide_content(slide: Any, text: str) -> None:
    title_shape = _find_title_shape(list(_iter_text_shapes(slide)))

    if _update_slide_table(slide, text):
        _clear_footnotes(slide, title_shape)
        return

    _update_slide_body(slide, text)


def _update_cover_slide(slide: Any, proposal: dict[str, Any], rfp_id: str) -> None:
    customer = _coerce_text(proposal.get("customer", "Client"))
    date_str = datetime.now().strftime("%d %b %Y")

    for shape in slide.shapes:
        if not hasattr(shape, "text"):
            continue
        if "Proposal" in shape.text or "Date" in shape.text:
            shape.text = f"TTN Proposal | {customer}\nDate : {date_str}\nRef : {rfp_id}"


def render_pptx_from_template(
    proposal: dict[str, Any],
    output_path: str,
    rfp_id: str,
) -> str:
    template_path = resolve_pptx_template_path()
    if not template_path.exists():
        raise FileNotFoundError(
            f"PPTX template not found at {template_path}. "
            "Place proposal-template.pptx in templates/."
        )

    os_dir = Path(output_path).parent
    os_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template_path, output_path)

    prs = Presentation(output_path)

    for index, slide in enumerate(prs.slides):
        if index in FIXED_SLIDE_INDICES:
            continue

        if index == 0:
            _update_cover_slide(slide, proposal, rfp_id)
            continue

        content_key = SLIDE_CONTENT_MAP.get(index)
        if not content_key:
            continue

        content = _coerce_text(proposal.get(content_key, ""))
        if content:
            _update_slide_content(slide, content)

    prs.save(output_path)
    return output_path
