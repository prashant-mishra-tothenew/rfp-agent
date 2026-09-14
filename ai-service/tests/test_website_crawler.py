import httpx
import pytest

from app.config import settings
from app.documents.website_crawler import WebsiteCrawlError, crawl_website


@pytest.mark.asyncio
async def test_crawl_follows_same_host_html_links_only():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404, request=request)
        if request.url.path == "/":
            return httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                text="""
                    <html><body>
                      <h1>Commerce Platform</h1>
                      <a href="/features">Features</a>
                      <a href="/features#details">Duplicate</a>
                      <a href="https://example.org/external">External</a>
                      <a href="/manual.pdf">PDF</a>
                      <input type="search" placeholder="Find a race">
                      <video controls></video>
                      <script>secret()</script>
                    </body></html>
                """,
                request=request,
            )
        if request.url.path == "/features":
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<main>Customers can search products and manage their cart.</main>",
                request=request,
            )
        return httpx.Response(404, request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = await crawl_website("https://93.184.216.34/", client=client)

    assert [page.url for page in result.pages] == [
        "https://93.184.216.34/",
        "https://93.184.216.34/features",
    ]
    assert "Commerce Platform" in result.text
    assert "manage their cart" in result.text
    assert "UI input control" in result.text
    assert "UI video player" in result.text
    assert "secret()" not in result.text


@pytest.mark.asyncio
async def test_crawl_honors_page_limit(monkeypatch):
    monkeypatch.setattr(settings, "website_crawl_max_pages", 1)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404, request=request)
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text='<p>Home</p><a href="/one">One</a>',
            request=request,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = await crawl_website("https://93.184.216.34/", client=client)

    assert len(result.pages) == 1


@pytest.mark.asyncio
async def test_crawl_truncates_oversized_page_without_failing(monkeypatch):
    monkeypatch.setattr(settings, "website_crawl_max_page_bytes", 80)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404, request=request)
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"<h1>Visible feature</h1>" + (b"x" * 200),
            request=request,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = await crawl_website("https://93.184.216.34/", client=client)

    assert result.pages[0].text.startswith("Visible feature")
    assert any("was truncated" in warning for warning in result.warnings)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1",
        "file:///etc/passwd",
        "https://user:password@example.com",
        "https://93.184.216.34:8443",
    ],
)
async def test_crawl_rejects_unsafe_urls(url):
    with pytest.raises(WebsiteCrawlError):
        await crawl_website(url)


@pytest.mark.asyncio
async def test_crawl_revalidates_same_host_redirects():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404, request=request)
        if request.url.path == "/":
            return httpx.Response(
                302, headers={"location": "/home"}, request=request
            )
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<h1>Home feature</h1>",
            request=request,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = await crawl_website("https://93.184.216.34/", client=client)

    assert result.pages[0].url == "https://93.184.216.34/home"
