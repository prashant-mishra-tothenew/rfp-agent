from unittest.mock import AsyncMock, patch

import pytest

from app.api.main import _collect_analysis_sources
from app.documents.website_crawler import CrawlResult, CrawledPage


@pytest.mark.asyncio
async def test_collect_analysis_sources_rejects_empty_input():
    with pytest.raises(ValueError, match="Provide a document or a website URL"):
        await _collect_analysis_sources(None, None)


@pytest.mark.asyncio
async def test_collect_analysis_sources_supports_document_only():
    parsed = {
        "filename": "requirements.pdf",
        "format": "pdf",
        "text": "The vendor must provide search.",
    }
    with patch("app.api.main._parse_uploaded_document", return_value=parsed):
        text, metadata = await _collect_analysis_sources("/uploads/file.pdf", None)

    assert "UPLOADED DOCUMENT" in text
    assert "must provide search" in text
    assert metadata["document"]["filename"] == "requirements.pdf"
    assert "website" not in metadata


@pytest.mark.asyncio
async def test_collect_analysis_sources_supports_website_only():
    crawled = CrawlResult(
        start_url="https://example.com/",
        pages=[
            CrawledPage(
                url="https://example.com/features",
                text="The website provides product search.",
            )
        ],
        warnings=[],
    )
    with patch(
        "app.api.main.crawl_website",
        new_callable=AsyncMock,
        return_value=crawled,
    ):
        text, metadata = await _collect_analysis_sources(
            None, "https://example.com/"
        )

    assert "WEBSITE SOURCE" in text
    assert "product search" in text
    assert metadata["website"]["pages_crawled"] == 1
    assert "document" not in metadata


@pytest.mark.asyncio
async def test_collect_analysis_sources_combines_document_and_website():
    parsed = {
        "filename": "requirements.docx",
        "format": "docx",
        "text": "Document requirement.",
    }
    crawled = CrawlResult(
        start_url="https://example.com/",
        pages=[CrawledPage(url="https://example.com/", text="Website feature.")],
        warnings=[],
    )
    with patch("app.api.main._parse_uploaded_document", return_value=parsed), patch(
        "app.api.main.crawl_website",
        new_callable=AsyncMock,
        return_value=crawled,
    ):
        text, metadata = await _collect_analysis_sources(
            "/uploads/file.docx", "https://example.com/"
        )

    assert "Document requirement." in text
    assert "Website feature." in text
    assert set(metadata) == {"document", "website"}
