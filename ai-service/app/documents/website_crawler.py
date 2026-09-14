import asyncio
import heapq
import ipaddress
import re
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Awaitable, Callable
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.config import settings


class WebsiteCrawlError(ValueError):
    pass


@dataclass
class CrawledPage:
    url: str
    text: str


@dataclass
class CrawlResult:
    start_url: str
    pages: list[CrawledPage]
    warnings: list[str]

    @property
    def text(self) -> str:
        return "\n\n".join(
            f"--- WEBSITE PAGE: {page.url} ---\n{page.text}" for page in self.pages
        )


UrlValidator = Callable[[str, str | None], Awaitable[str]]

_SKIPPED_EXTENSIONS = {
    ".7z",
    ".avi",
    ".css",
    ".csv",
    ".doc",
    ".docx",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".rar",
    ".svg",
    ".tar",
    ".webp",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
}
_TECHNICAL_SCRIPT_HINTS = (
    "analytics",
    "appinsights",
    "clarity",
    "crashlytics",
    "firebase",
    "gtag",
    "googletagmanager",
    "hotjar",
    "newrelic",
    "sentry",
)
_CORE_FEATURE_PATHS = {
    "/animal-welfare",
    "/about",
    "/careers-training",
    "/infrastructure",
    "/my-account",
    "/news",
    "/newsletters",
    "/ownership",
    "/racing",
    "/racing/clubs",
    "/racing/events",
    "/racing/featured-events",
    "/racing/form-analysis",
    "/racing/full-calendar",
    "/racing/premierships",
    "/racing/profiles",
    "/racing/race-day-stewards-reports",
    "/racing/race-planner",
    "/racing/recent-race-results",
    "/racing/recent-results",
    "/racing/replays",
    "/register",
    "/search",
    "/sign-in",
}
_USEFUL_DETAIL_PREFIXES = (
    "/my-account/",
    "/racing/profiles/",
    "/racing/replays/",
)


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.text_parts: list[str] = []
        self.links: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = {key: value for key, value in attrs if value}
        if tag in {"script", "style", "noscript", "svg", "template"}:
            if tag == "script" and (src := attributes.get("src")):
                if any(hint in src.lower() for hint in _TECHNICAL_SCRIPT_HINTS):
                    self.text_parts.append(f"[Detected integration script: {src}]")
            self._skip_depth += 1
            return
        if tag == "a" and self._skip_depth == 0:
            href = attributes.get("href")
            if href:
                self.links.append(href)
        if self._skip_depth:
            return

        if tag in {"input", "select", "textarea"}:
            details = [
                f"{key}={attributes[key]}"
                for key in ("type", "name", "placeholder", "aria-label")
                if key in attributes
            ]
            self.text_parts.append(
                f"[UI {tag} control{': ' + ', '.join(details) if details else ''}]"
            )
        elif tag in {"video", "audio"}:
            self.text_parts.append(f"[UI {tag} player]")
        elif tag == "iframe":
            label = attributes.get("title") or attributes.get("aria-label") or "embedded content"
            self.text_parts.append(f"[UI embedded frame: {label}]")
        elif tag == "button":
            label = attributes.get("aria-label") or attributes.get("title")
            if label:
                self.text_parts.append(f"[UI button: {label}]")
        elif tag == "form":
            action = attributes.get("action")
            self.text_parts.append(f"[UI form{': ' + action if action else ''}]")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg", "template"}:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = re.sub(r"\s+", " ", data).strip()
        if text and (not self.text_parts or self.text_parts[-1] != text):
            self.text_parts.append(text)


def _is_public_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


async def validate_public_url(url: str, allowed_host: str | None = None) -> str:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise WebsiteCrawlError("Website URL is invalid") from exc

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise WebsiteCrawlError("Website URL must use HTTP or HTTPS")
    if parsed.username or parsed.password:
        raise WebsiteCrawlError("Website URL must not contain credentials")

    expected_port = 443 if parsed.scheme == "https" else 80
    if port is not None and port != expected_port:
        raise WebsiteCrawlError("Website URL must use the standard HTTP or HTTPS port")

    hostname = parsed.hostname.rstrip(".").lower()
    if allowed_host and hostname != allowed_host:
        raise WebsiteCrawlError("Website crawl cannot leave the original host")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise WebsiteCrawlError("Local and private website addresses are not allowed")

    try:
        literal = ipaddress.ip_address(hostname)
        addresses = [str(literal)]
    except ValueError:
        try:
            records = await asyncio.to_thread(
                socket.getaddrinfo,
                hostname,
                expected_port,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise WebsiteCrawlError(f"Could not resolve website host: {hostname}") from exc
        addresses = list({record[4][0] for record in records})

    if not addresses or not all(_is_public_ip(address) for address in addresses):
        raise WebsiteCrawlError("Local and private website addresses are not allowed")

    path = parsed.path or "/"
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, ""))


def _parse_html(html: str) -> tuple[str, list[str]]:
    parser = _PageParser()
    parser.feed(html)
    return "\n".join(parser.text_parts), parser.links


def _normalize_link(href: str, current_url: str, allowed_host: str) -> str | None:
    if href.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return None
    try:
        parsed = urlsplit(urljoin(current_url, href))
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"}:
        return None
    if not parsed.hostname or parsed.hostname.rstrip(".").lower() != allowed_host:
        return None
    expected_port = 443 if parsed.scheme == "https" else 80
    if port is not None and port != expected_port:
        return None
    path = parsed.path or "/"
    if any(path.lower().endswith(extension) for extension in _SKIPPED_EXTENSIONS):
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _link_priority(url: str) -> tuple[int, int, str]:
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/").lower() or "/"
    segments = [segment for segment in path.split("/") if segment]

    if path in _CORE_FEATURE_PATHS:
        rank = 0
    elif "/meeting/" in path or "/race-player/" in path or "/stewards-player/" in path:
        rank = 1
    elif (
        "club-details" in path
        or (path.startswith("/news/") and len(segments) > 1)
        or any(re.fullmatch(r"20\d{2}", segment) for segment in segments)
        or re.search(r"/\d{8}(?:/|$)", path)
    ):
        rank = 4
    elif path.startswith(_USEFUL_DETAIL_PREFIXES):
        rank = 1
    elif len(segments) <= 2:
        rank = 2
    else:
        rank = 3

    return (rank, len(segments), url)


def _dynamic_feature_family(url: str) -> str | None:
    path = urlsplit(url).path.lower()
    for marker in ("/meeting/", "/race-player/", "/stewards-player/"):
        if marker in path:
            prefix, suffix = path.split(marker, 1)
            if marker == "/meeting/":
                family_type = prefix.rstrip("/").rsplit("/", 1)[-1]
            else:
                family_type = suffix.split("/", 1)[0]
            return f"{marker}{family_type}"
    if "club-details" in path:
        return "club-details"
    if path.startswith("/news/") and len([part for part in path.split("/") if part]) > 1:
        return "news-detail"
    return None


def _deduplicate_page_text(text: str, seen_lines: set[str]) -> str:
    unique_lines: list[str] = []
    for line in text.splitlines():
        normalized = re.sub(r"\s+", " ", line).strip()
        key = normalized.casefold()
        if len(key) < 2 or key in seen_lines:
            continue
        seen_lines.add(key)
        unique_lines.append(normalized)
    return "\n".join(unique_lines)


async def _read_response(
    client: httpx.AsyncClient,
    url: str,
    allowed_host: str,
    validator: UrlValidator,
) -> tuple[httpx.Response, bytes, str, bool]:
    current_url = url
    for _ in range(settings.website_crawl_max_redirects + 1):
        current_url = await validator(current_url, allowed_host)
        async with client.stream("GET", current_url, follow_redirects=False) as response:
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise WebsiteCrawlError("Website returned an invalid redirect")
                current_url = urljoin(current_url, location)
                continue

            chunks: list[bytes] = []
            size = 0
            truncated = False
            async for chunk in response.aiter_bytes():
                remaining = settings.website_crawl_max_page_bytes - size
                if remaining <= 0:
                    truncated = True
                    break
                if len(chunk) > remaining:
                    chunks.append(chunk[:remaining])
                    size += remaining
                    truncated = True
                    break
                chunks.append(chunk)
                size += len(chunk)
            return response, b"".join(chunks), current_url, truncated

    raise WebsiteCrawlError("Website exceeded the redirect limit")


async def _load_robots(
    client: httpx.AsyncClient,
    start_url: str,
    allowed_host: str,
    validator: UrlValidator,
) -> RobotFileParser | None:
    parsed = urlsplit(start_url)
    robots_url = urlunsplit((parsed.scheme, parsed.netloc, "/robots.txt", "", ""))
    try:
        response, body, _, _ = await _read_response(
            client, robots_url, allowed_host, validator
        )
        if response.status_code != 200:
            return None
        robots = RobotFileParser()
        robots.parse(body.decode(response.encoding or "utf-8", errors="replace").splitlines())
        return robots
    except (httpx.HTTPError, WebsiteCrawlError, UnicodeError, ValueError):
        return None


async def crawl_website(
    start_url: str,
    *,
    client: httpx.AsyncClient | None = None,
    validator: UrlValidator = validate_public_url,
) -> CrawlResult:
    normalized_start = await validator(start_url, None)
    allowed_host = urlsplit(normalized_start).hostname
    if not allowed_host:
        raise WebsiteCrawlError("Website URL is invalid")
    allowed_host = allowed_host.rstrip(".").lower()

    owns_client = client is None
    if client is None:
        timeout = httpx.Timeout(settings.website_crawl_timeout_seconds, connect=5.0)
        client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": settings.website_crawl_user_agent,
                "Accept": "text/html,application/xhtml+xml",
            },
        )

    pages: list[CrawledPage] = []
    warnings: list[str] = []
    queue: list[tuple[int, int, int, str]] = [(0, 0, 0, normalized_start)]
    seen: set[str] = set()
    queued_families: set[str] = set()
    seen_text_lines: set[str] = set()
    total_chars = 0

    try:
        robots = await _load_robots(client, normalized_start, allowed_host, validator)
        while queue and len(pages) < settings.website_crawl_max_pages:
            _, _, depth, url = heapq.heappop(queue)
            if url in seen:
                continue
            seen.add(url)

            if robots and not robots.can_fetch(settings.website_crawl_user_agent, url):
                warnings.append(f"Skipped by robots.txt: {url}")
                continue

            try:
                response, body, final_url, truncated = await _read_response(
                    client, url, allowed_host, validator
                )
                response.raise_for_status()
                if truncated:
                    warnings.append(
                        f"Page content reached the size limit and was truncated: {final_url}"
                    )
                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    warnings.append(f"Skipped non-HTML page: {final_url}")
                    continue

                html = body.decode(response.encoding or "utf-8", errors="replace")
                text, links = _parse_html(html)
                text = _deduplicate_page_text(text, seen_text_lines)
                text = text[: settings.website_crawl_max_page_chars]
                remaining = settings.website_crawl_max_total_chars - total_chars
                if remaining <= 0:
                    break
                text = text[:remaining]
                if text:
                    pages.append(CrawledPage(url=final_url, text=text))
                    total_chars += len(text)

                if depth < settings.website_crawl_max_depth:
                    normalized_links = {
                        link
                        for href in links
                        if (link := _normalize_link(href, final_url, allowed_host))
                        and link not in seen
                    }
                    for link in sorted(normalized_links, key=_link_priority):
                        family = _dynamic_feature_family(link)
                        if family and family in queued_families:
                            continue
                        if family:
                            queued_families.add(family)
                        rank, path_depth, _ = _link_priority(link)
                        heapq.heappush(
                            queue, (rank, path_depth, depth + 1, link)
                        )
            except (httpx.HTTPError, WebsiteCrawlError, UnicodeError, ValueError) as exc:
                warnings.append(f"Could not crawl {url}: {exc}")
    finally:
        if owns_client:
            await client.aclose()

    if not pages:
        detail = warnings[0] if warnings else "No readable HTML pages were found"
        raise WebsiteCrawlError(f"Website could not be analyzed. {detail}")

    return CrawlResult(start_url=normalized_start, pages=pages, warnings=warnings)
