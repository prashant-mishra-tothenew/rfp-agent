import tempfile
from pathlib import Path

from pptx import Presentation

from app.proposal.pptx_template import (
    FIXED_SLIDE_INDICES,
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


def test_render_preserves_fixed_commercial_and_success_slides():
    template_path = resolve_pptx_template_path()
    template_prs = Presentation(str(template_path))
    commercial_before = _slide_text(template_prs.slides[20])
    success_before = _slide_text(template_prs.slides[23])

    with tempfile.TemporaryDirectory() as tmp:
        output = str(Path(tmp) / "proposal.pptx")
        render_pptx_from_template(
            {
                "customer": "Acme Corp",
                "executiveSummary": "Custom executive summary for Acme.",
                "understandingOfRequirements": "Custom requirements understanding.",
                "proposedSolution": "Custom proposed solution for Acme retail platform.",
                "technicalApproach": "API-first architecture | Microservices on AWS EKS",
                "relevantExperience": "TTN has delivered 50+ commerce platforms globally.",
            },
            output,
            "rfp-test-001",
        )

        result_prs = Presentation(output)
        assert len(result_prs.slides) == len(template_prs.slides)
        assert _slide_text(result_prs.slides[20]) == commercial_before
        assert _slide_text(result_prs.slides[23]) == success_before
        assert "Acme Corp" in _slide_text(result_prs.slides[0])
        assert "Custom executive summary" in _slide_text(result_prs.slides[2])
        slide5_text = _slide_text(result_prs.slides[5])
        assert "Custom proposed solution" in slide5_text
        assert "Races & Profiles" not in slide5_text
        assert "TTN has delivered 50+ commerce platforms" in _slide_text(result_prs.slides[3])


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

        slide = Presentation(output).slides[14]
        footnotes = [
            shape.text
            for shape in slide.shapes
            if hasattr(shape, "text_frame")
            and shape.top > 4_000_000
            and shape.text.strip()
            and shape.text.strip() != "‹#›"
        ]
        assert footnotes == []
        assert "Both Flutter and React Native" not in _slide_text(slide)


def test_fixed_slide_indices_cover_commercial_and_success_sections():
    assert 20 in FIXED_SLIDE_INDICES
    assert 21 in FIXED_SLIDE_INDICES
    assert 23 in FIXED_SLIDE_INDICES
    assert 24 in FIXED_SLIDE_INDICES
    assert 25 in FIXED_SLIDE_INDICES
