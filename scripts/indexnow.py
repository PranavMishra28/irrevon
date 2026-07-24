#!/usr/bin/env python3
"""Validate and optionally submit canonical post-deployment URLs to IndexNow.

Dry-run is the default. Network access and the external submission side effect
require both --submit and an exact --confirm-host value.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import math
import os
import re
import ssl
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
KEY_PATTERN = re.compile(r"^[A-Za-z0-9-]{8,128}$")
DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
SAFE_PATH = re.compile(r"^/(?:[A-Za-z0-9_~-]+/)*$")
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
MAX_SITEMAP_BYTES = 2 * 1024 * 1024
MAX_URL_FILE_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_INDEXNOW_URLS = 10_000
EXCLUDED_PREFIXES = ("/_astro/", "/_vercel/", "/pagefind/")
EXCLUDED_PATHS = {
    "/404.html",
    "/docs/search/",
    "/indexnow-key.txt",
    "/llms.txt",
    "/robots.txt",
    "/research/rss.xml",
    "/sitemap-0.xml",
    "/sitemap-index.xml",
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


class _MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.canonicals: list[str] = []
        self.robots: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        rel = {token.lower() for token in values.get("rel", "").split()}
        if tag.lower() == "link" and "canonical" in rel:
            self.canonicals.append(values.get("href", ""))
        if tag.lower() == "meta" and values.get("name", "").lower() in {"robots", "bingbot"}:
            self.robots.append(values.get("content", "").lower())


@dataclass(frozen=True)
class Submission:
    origin: str
    live: tuple[str, ...]
    deleted: tuple[str, ...]

    @property
    def urls(self) -> tuple[str, ...]:
        return tuple(sorted({*self.live, *self.deleted}))


def validate_origin(raw: str) -> str:
    if raw != raw.strip() or any(ord(character) < 0x20 for character in raw):
        raise ValueError("origin must not contain whitespace or control characters")
    parsed = urlsplit(raw)
    try:
        explicit_port = parsed.port
    except ValueError as error:
        raise ValueError("origin contains an invalid port") from error
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or explicit_port is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise ValueError("origin must be a credential-free HTTPS origin without a port")
    try:
        parsed.hostname.encode("ascii")
    except UnicodeEncodeError as error:
        raise ValueError("origin host must be ASCII") from error
    host = parsed.hostname.lower()
    labels = host.split(".")
    if (
        host.endswith(".")
        or len(labels) < 2
        or any(not DNS_LABEL.fullmatch(label) for label in labels)
        or host == "localhost"
        or host.endswith((".localhost", ".local", ".internal"))
        or (host.endswith(".vercel.app") and host != "irrevon.vercel.app")
    ):
        raise ValueError("origin must be a canonical public production hostname")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP literals are never IndexNow origins")
    if parsed.netloc != host:
        raise ValueError("origin hostname must use its lowercase canonical spelling")
    return f"https://{host}"


def validate_canonical_url(raw: str, origin: str) -> str:
    canonical_origin = validate_origin(origin)
    if raw != raw.strip() or any(ord(character) < 0x20 for character in raw):
        raise ValueError(f"noncanonical or foreign URL: {raw!r}")
    parsed = urlsplit(raw)
    expected = urlsplit(canonical_origin)
    try:
        explicit_port = parsed.port
    except ValueError as error:
        raise ValueError(f"noncanonical or foreign URL: {raw}") from error
    if (
        parsed.scheme != "https"
        or parsed.netloc != expected.netloc
        or parsed.username
        or parsed.password
        or explicit_port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"noncanonical or foreign URL: {raw}")
    if (
        not parsed.path
        or "\\" in parsed.path
        or "%" in parsed.path
        or "//" in parsed.path
        or not SAFE_PATH.fullmatch(parsed.path)
        or any(parsed.path.startswith(prefix) for prefix in EXCLUDED_PREFIXES)
    ):
        raise ValueError(f"excluded URL path: {raw}")
    if parsed.path in EXCLUDED_PATHS or "." in parsed.path.rsplit("/", 1)[-1]:
        raise ValueError(f"non-HTML URL path: {raw}")
    if parsed.path != "/" and not parsed.path.endswith("/"):
        raise ValueError(f"canonical URL must end in '/': {raw}")
    return raw


def parse_sitemap(path: Path, origin: str) -> set[str]:
    raw = path.read_bytes()
    if len(raw) > MAX_SITEMAP_BYTES:
        raise ValueError("sitemap exceeds the local safety limit")
    if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)\b", raw, flags=re.IGNORECASE):
        raise ValueError("sitemap declarations and entities are not accepted")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as error:
        raise ValueError("sitemap is not well-formed XML") from error
    if root.tag != f"{{{SITEMAP_NAMESPACE}}}urlset":
        raise ValueError("sitemap root must be a standard urlset")
    locations: list[str] = []
    for entry in root.findall(f"{{{SITEMAP_NAMESPACE}}}url"):
        nodes = entry.findall(f"{{{SITEMAP_NAMESPACE}}}loc")
        if len(nodes) != 1 or not (nodes[0].text or "").strip():
            raise ValueError("every sitemap URL entry must contain exactly one loc")
        locations.append((nodes[0].text or "").strip())
    if not locations:
        raise ValueError("sitemap contains no URLs")
    if len(set(locations)) != len(locations):
        raise ValueError("sitemap contains duplicate URLs")
    return {validate_canonical_url(url, origin) for url in locations}


def read_url_file(path: Path | None) -> set[str]:
    if path is None:
        return set()
    raw = path.read_bytes()
    if len(raw) > MAX_URL_FILE_BYTES:
        raise ValueError("URL list exceeds the local safety limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("URL list must be UTF-8") from error
    urls = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(set(urls)) != len(urls):
        raise ValueError("URL list contains duplicate URLs")
    return set(urls)


def build_submission(
    *,
    origin: str,
    current: set[str],
    changed: set[str] | None = None,
    deleted: set[str] | None = None,
    previous: set[str] | None = None,
    cap: int = 250,
) -> Submission:
    canonical_origin = validate_origin(origin)
    if origin != canonical_origin:
        raise ValueError("origin must use its canonical spelling")
    if cap < 1 or cap > MAX_INDEXNOW_URLS:
        raise ValueError(f"submission cap must be between 1 and {MAX_INDEXNOW_URLS}")
    live = current if changed is None else changed
    deleted = deleted or set()
    previous = previous or set()
    for url in current | live | deleted | previous:
        validate_canonical_url(url, origin)
    missing = live - current
    if missing:
        raise ValueError(f"live URLs are absent from the current sitemap: {sorted(missing)!r}")
    invalid_deleted = deleted - previous
    if invalid_deleted:
        raise ValueError(
            f"deleted URLs are absent from the previous sitemap: {sorted(invalid_deleted)!r}"
        )
    if deleted & current:
        raise ValueError("deleted URLs still exist in the current sitemap")
    submission = Submission(origin=origin, live=tuple(sorted(live)), deleted=tuple(sorted(deleted)))
    if not submission.urls or len(submission.urls) > cap:
        raise ValueError("submission must contain between 1 and the configured URL cap")
    return submission


def _opener() -> urllib.request.OpenerDirector:
    context = ssl.create_default_context()
    return urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=context))


def _validate_key(key: str) -> None:
    if not KEY_PATTERN.fullmatch(key):
        raise ValueError("IndexNow key must be 8-128 ASCII letters, digits, or hyphens")


def _validate_submission(submission: Submission) -> None:
    if submission.origin != validate_origin(submission.origin):
        raise ValueError("submission origin is not canonical")
    if (
        not submission.urls
        or len(submission.urls) > MAX_INDEXNOW_URLS
        or set(submission.live) & set(submission.deleted)
        or len(set(submission.live)) != len(submission.live)
        or len(set(submission.deleted)) != len(submission.deleted)
    ):
        raise ValueError("submission URL set is empty, duplicated, overlapping, or oversized")
    for url in submission.urls:
        validate_canonical_url(url, submission.origin)


def _read_limited(response, limit: int = MAX_RESPONSE_BYTES) -> bytes:  # type: ignore[no-untyped-def]
    body = response.read(limit + 1)
    if len(body) > limit:
        raise RuntimeError("remote response exceeds the local safety limit")
    return body


def _has_noindex(directives: list[str]) -> bool:
    return any(
        token.strip().lower() == "noindex"
        for directive in directives
        for token in directive.split(",")
    )


def verify_deployed(submission: Submission, key: str, timeout: float = 10.0) -> None:
    _validate_submission(submission)
    _validate_key(key)
    if not math.isfinite(timeout) or timeout <= 0 or timeout > 60:
        raise ValueError("timeout must be greater than zero and at most 60 seconds")
    opener = _opener()
    key_url = f"{submission.origin}/indexnow-key.txt"
    try:
        with opener.open(key_url, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if (
                response.status != 200
                or response.geturl() != key_url
                or "text/plain" not in content_type
                or _read_limited(response, 512).decode("ascii").strip() != key
            ):
                raise RuntimeError("deployed IndexNow key file is unavailable or does not match")
    except (UnicodeDecodeError, urllib.error.URLError) as error:
        raise RuntimeError("deployed IndexNow key file could not be verified") from error
    for url in submission.live:
        try:
            with opener.open(url, timeout=timeout) as response:
                if (
                    response.status != 200
                    or response.geturl() != url
                    or "text/html" not in response.headers.get("Content-Type", "").lower()
                ):
                    raise RuntimeError(f"live URL is not a direct 200 HTML page: {url}")
                parser = _MetadataParser()
                parser.feed(_read_limited(response).decode("utf-8"))
                header_directives = response.headers.get_all("X-Robots-Tag", [])
                if (
                    parser.canonicals != [url]
                    or _has_noindex(parser.robots)
                    or _has_noindex(header_directives)
                ):
                    raise RuntimeError(f"live URL is noncanonical or noindex: {url}")
        except (UnicodeDecodeError, urllib.error.URLError) as error:
            raise RuntimeError(f"live URL could not be verified: {url}") from error
    for url in submission.deleted:
        try:
            with opener.open(url, timeout=timeout):
                pass
        except urllib.error.HTTPError as error:
            if error.code in {404, 410}:
                continue
            raise RuntimeError(
                f"deleted URL returned {error.code}, expected 404/410: {url}"
            ) from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"deleted URL could not be verified: {url}") from error
        raise RuntimeError(f"deleted URL still returns success: {url}")


def submit_indexnow(submission: Submission, key: str, timeout: float = 10.0) -> int:
    _validate_submission(submission)
    _validate_key(key)
    if not math.isfinite(timeout) or timeout <= 0 or timeout > 60:
        raise ValueError("timeout must be greater than zero and at most 60 seconds")
    payload = json.dumps(
        {
            "host": urlsplit(submission.origin).hostname,
            "key": key,
            "keyLocation": f"{submission.origin}/indexnow-key.txt",
            "urlList": list(submission.urls),
        },
        separators=(",", ":"),
    ).encode("utf-8")
    request = urllib.request.Request(
        INDEXNOW_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with _opener().open(request, timeout=timeout) as response:
            if response.status not in {200, 202}:
                raise RuntimeError(f"IndexNow returned unexpected status {response.status}")
            return response.status
    except urllib.error.HTTPError as error:
        if error.code == 429:
            raise RuntimeError("IndexNow rate limited the request (429); retry later") from error
        raise RuntimeError(f"IndexNow submission failed with status {error.code}") from error
    except urllib.error.URLError as error:
        raise RuntimeError("IndexNow submission failed before receiving a response") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument(
        "--sitemap", type=Path, required=True, help="current canonical sitemap-0.xml"
    )
    parser.add_argument(
        "--changed",
        type=Path,
        help="changed canonical URLs, one per line; omit for initial launch",
    )
    parser.add_argument("--deleted", type=Path, help="deleted canonical URLs, one per line")
    parser.add_argument("--previous-sitemap", type=Path)
    parser.add_argument("--cap", type=int, default=250)
    parser.add_argument("--submit", action="store_true")
    parser.add_argument(
        "--confirm-host",
        help="must exactly match the production host when --submit is used",
    )
    args = parser.parse_args()

    origin = validate_origin(args.origin)
    current = parse_sitemap(args.sitemap, origin)
    previous = parse_sitemap(args.previous_sitemap, origin) if args.previous_sitemap else set()
    submission = build_submission(
        origin=origin,
        current=current,
        changed=read_url_file(args.changed) if args.changed else None,
        deleted=read_url_file(args.deleted),
        previous=previous,
        cap=args.cap,
    )
    if not args.submit:
        print(
            f"IndexNow dry run: {len(submission.live)} live, "
            f"{len(submission.deleted)} deleted canonical URLs"
        )
        return 0

    host = urlsplit(origin).hostname
    if args.confirm_host != host:
        raise SystemExit("--confirm-host must exactly match the production host")
    key = os.environ.get("INDEXNOW_KEY", "")
    if not KEY_PATTERN.fullmatch(key):
        raise SystemExit("INDEXNOW_KEY is missing or invalid")
    verify_deployed(submission, key)
    status = submit_indexnow(submission, key)
    print(
        f"IndexNow accepted {len(submission.urls)} URLs with status {status}; "
        "indexing is not guaranteed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
