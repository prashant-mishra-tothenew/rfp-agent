import tempfile
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from app.proposal.pptx_template import (
    FIXED_SLIDE_INDICES,
    SUCCESS_STORY_SLIDE_INDICES,
    WHY_TTN_SLIDE_INDEX,
    _shape_char_capacity,
    _truncate_text,
    render_pptx_from_template,
    resolve_pptx_template_path,
)


def _slide_text(slide) -> str:
    parts = []
    for shape in slide.shapes:
        if hasattr(shape, "text") and shape.text.strip():
            parts.append(shape.text)
    return "\n".join(parts)


def test_template_path_exists():
    assert resolve_pptx_template_path().exists()


def test_render_preserves_why_ttn_and_success_slides():
    template_path = resolve_pptx_template_path()
    template_prs = Presentation(str(template_path))
    why_ttn_before = _slide_text(template_prs.slides[WHY_TTN_SLIDE_INDEX])
    success_index = min(SUCCESS_STORY_SLIDE_INDICES)
    success_before = _slide_text(template_prs.slides[success_index])

    with tempfile.TemporaryDirectory() as tmp:
        output = str(Path(tmp) / "proposal.pptx")
        render_pptx_from_template(
            {
                "customer": "Acme Corp",
                "projectTitle": "Acme Mobile Platform",
                "executiveSummary": "Custom executive summary for Acme.",
                "understandingOfRequirements": "Custom requirements understanding.",
                "proposedSolution": "Custom proposed solution for Acme retail platform.",
                "technicalApproach": "API-first architecture | Microservices on AWS EKS",
                "engagementModel": "Iterative agile delivery with fortnightly demos.",
                "inScope": "Mobile app delivery\nAPI integration",
                "outOfScope": "Hardware procurement\nThird-party license costs",
            },
            output,
            "rfp-test-001",
        )

        result_prs = Presentation(output)
        assert _slide_text(result_prs.slides[WHY_TTN_SLIDE_INDEX]) == why_ttn_before
        assert _slide_text(result_prs.slides[success_index]) == success_before
        cover = _slide_text(result_prs.slides[0])
        assert "Acme Mobile Platform" in cover
        assert "Racing Queensland" not in cover
        assert "Custom executive summary" in _slide_text(result_prs.slides[2])
        slide5_text = _slide_text(result_prs.slides[5])
        assert "Custom proposed solution" in slide5_text
        assert "Races & Profiles" not in slide5_text
        scope_text = _slide_text(result_prs.slides[9])
        assert "Mobile app delivery" in scope_text
        assert "Hardware procurement" in scope_text
        assert "Procurement & Maintenance of Infrastructure" not in scope_text
        engagement_text = _slide_text(result_prs.slides[20])
        assert "Iterative agile delivery" in engagement_text
        assert "AUD 78,727" not in engagement_text


def test_truncate_text_respects_limit():
    long_text = (
        "Our proposed solution combines a Next.js/React frontend with REST/GraphQL APIs "
        "for a decoupled architecture. We integrate headless CMS platforms like Sanity."
    )
    truncated = _truncate_text(long_text, 90)
    assert len(truncated) <= 90
    assert len(truncated) > 40


def test_render_distributes_solution_cards_without_template_overflow():
    template_path = resolve_pptx_template_path()
    long_solution = "\n".join(
        [
            "Drupal Commerce core platform with multi-store support.",
            "Solr-powered faceted search for 100,000+ SKUs.",
            "Headless Next.js storefront with SSR for SEO.",
            "SAP ERP integration for inventory and orders.",
            "Stripe and PayPal checkout with PCI-DSS flows.",
            "WCAG 2.1 AA accessible customer journeys.",
        ]
    )

    with tempfile.TemporaryDirectory() as tmp:
        output = str(Path(tmp) / "proposal.pptx")
        render_pptx_from_template(
            {
                "customer": "Acme Corp",
                "proposedSolution": long_solution,
            },
            output,
            "rfp-test-002",
        )

        slide = Presentation(output).slides[5]
        card_capacities = [
            _shape_char_capacity(shape)
            for shape in slide.shapes
            if hasattr(shape, "text_frame") and _shape_char_capacity(shape) >= 100
        ]
        assert len(card_capacities) >= 3

        for shape in slide.shapes:
            if not hasattr(shape, "text_frame"):
                continue
            capacity = _shape_char_capacity(shape)
            if capacity < 100:
                continue
            assert len(shape.text) <= capacity + 5
            assert "Races & Profiles" not in shape.text


def test_architecture_slide_does_not_overlay_diagram_text():
    with tempfile.TemporaryDirectory() as tmp:
        output = str(Path(tmp) / "proposal.pptx")
        render_pptx_from_template(
            {
                "customer": "Acme Corp",
                "technicalApproach": "API Gateway | Federated GraphQL layer\nCDN | Global edge caching",
            },
            output,
            "rfp-test-arch",
        )
        slide = Presentation(output).slides[12]
        overlay = [
            shape.text
            for shape in slide.shapes
            if hasattr(shape, "text_frame")
            and getattr(shape, "width", 0) > 3_500_000
            and len(shape.text.strip()) > 40
        ]
        assert overlay == []
        assert _slide_text(slide).startswith("Proposed High Level Architecture")


def test_table_slides_keep_titles_after_footnote_clear():
    with tempfile.TemporaryDirectory() as tmp:
        output = str(Path(tmp) / "proposal.pptx")
        render_pptx_from_template(
            {
                "customer": "Acme Corp",
                "technicalApproach": "API Gateway | GraphQL federation layer",
            },
            output,
            "rfp-test-titles",
        )
        prs = Presentation(output)
        for index, expected in (
            (13, "Architecture Considerations"),
            (14, "Mobile Development Platform - Comparison"),
        ):
            titles = [
                shape.text.strip()
                for shape in prs.slides[index].shapes
                if hasattr(shape, "text_frame")
                and shape.top < 900_000
                and shape.text.strip()
            ]
            assert expected in titles


def test_render_clears_table_footnote():
    with tempfile.TemporaryDirectory() as tmp:
        output = str(Path(tmp) / "proposal.pptx")
        render_pptx_from_template(
            {
                "customer": "Acme Corp",
                "technicalApproach": "API Gateway | GraphQL federation layer",
            },
            output,
            "rfp-test-003",
        )

        slide = Presentation(output).slides[13]
        footnotes = [
            shape.text
            for shape in slide.shapes
            if hasattr(shape, "text_frame")
            and shape.top > 4_000_000
            and shape.text.strip()
            and shape.text.strip() != "‹#›"
        ]
        assert footnotes == []
        table_shapes = [
            shape for shape in slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.TABLE
        ]
        assert table_shapes
        table = table_shapes[0].table
        assert "API Gateway" in table.cell(1, 0).text


def test_fixed_slide_indices_cover_why_ttn_and_success_sections():
    assert WHY_TTN_SLIDE_INDEX in FIXED_SLIDE_INDICES
    assert SUCCESS_STORY_SLIDE_INDICES <= FIXED_SLIDE_INDICES
    assert 9 not in FIXED_SLIDE_INDICES
    assert 20 not in FIXED_SLIDE_INDICES
