#!/usr/bin/env python3
"""Fail-closed verification for a built Irrevon production-site artifact."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from xml.etree import ElementTree

REQUIRED_HTML = (
    "index.html",
    "platform/index.html",
    "how-it-works/index.html",
    "demo/index.html",
    "benchmark/index.html",
    "docs/index.html",
    "install/index.html",
    "contributing/index.html",
)
REQUIRED_ASSETS = (
    "favicon.svg",
    "og/og-default.png",
    "images/workbench-effects-light.png",
    "images/workbench-effects-dark.png",
)
EXPECTED_NAVIGATION = (
    "Product",
    "How it works",
    "Demo",
    "Benchmark",
    "Docs",
    "Install",
    "Contribute",
    "Community",
    "GitHub",
)
REQUIRED_FOOTER_LINKS = (
    "Product",
    "Documentation",
    "Demo",
    "Community",
    "GitHub",
    "Security",
    "Privacy",
    "License",
)
VERSION_FIELDS = {
    "release_version",
    "release_status",
    "commit_sha",
    "built_at",
    "benchmark_harness_version",
    "schema_version",
    "environment",
}
GLOBAL_HEADERS = {
    "content-security-policy": "frame-ancestors 'none'",
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
    "cross-origin-opener-policy": "same-origin",
    "x-frame-options": "DENY",
    "cache-control": "public, max-age=600, stale-while-revalidate=86400",
}
ROUTE_HEADERS = {
    "/_astro/(.*)": {
        "cache-control": "public, max-age=31536000, immutable",
    },
    "/robots.txt": {
        "cache-control": "public, max-age=300, must-revalidate",
    },
    "/version.json": {
        "content-type": "application/json; charset=utf-8",
        "x-robots-tag": "noindex",
        "cache-control": "public, max-age=0, must-revalidate",
    },
}

VERCEL_BUILD_CONTRACT = {
    "framework": "astro",
    "ignoreCommand": 'test "${VERCEL_GIT_COMMIT_REF:-}" != main',
    "installCommand": "corepack enable && cd site && corepack pnpm install --frozen-lockfile",
    "buildCommand": "bash scripts/vercel-build.sh",
    "outputDirectory": "site/dist",
}
VERCEL_GIT_CONTRACT = {"*": False, "main": True}
LEGACY_HOME_MARKERS = (
    "benchmark draft, S-REF pilots disclosed",
    "B5 baseline leg",
    "A developmental file-journal B5 stand-in",
    "No advantage on C1 —",
    "C3 is an impossibility boundary",
    "Synthetic S-REF development",
    "Pre-release",
    "not on any package index",
    "Discussions is currently disabled",
    "counsel trademark screen",
    "Scientific results are not claimed",
    "Research-preview status",
    "Apache-2.0 source",
    "Read the master document",
)


class SmokeFailure(ValueError):
    """The production artifact is incomplete or does not match its intended release."""


class _PageContractParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonicals: list[str] = []
        self.meta: dict[tuple[str, str], list[str]] = {}
        self.hrefs: list[str] = []
        self.primary_links: list[str] = []
        self._in_primary = False
        self._in_primary_link = False
        self._primary_link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key.lower(): value or "" for key, value in attrs_list}
        if tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonicals.append(attrs.get("href", ""))
        if tag == "a":
            self.hrefs.append(attrs.get("href", ""))
        if tag == "meta":
            for kind in ("property", "name", "http-equiv"):
                value = attrs.get(kind)
                if value:
                    self.meta.setdefault((kind, value.lower()), []).append(attrs.get("content", ""))
        if tag == "nav" and attrs.get("aria-label") == "Primary":
            self._in_primary = True
        elif tag == "a" and self._in_primary:
            self._in_primary_link = True
            self._primary_link_text = []

    def handle_data(self, data: str) -> None:
        if self._in_primary_link:
            self._primary_link_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_primary_link:
            self.primary_links.append(" ".join("".join(self._primary_link_text).split()))
            self._in_primary_link = False
            self._primary_link_text = []
        elif tag == "nav" and self._in_primary:
            self._in_primary = False


def _canonical_origin(raw: str) -> str:
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise SmokeFailure("expected origin is not a valid URL") from exc
    canonical = f"https://{parsed.netloc}"
    if (
        raw != canonical
        or parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or port is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.netloc != parsed.netloc.lower()
    ):
        raise SmokeFailure(
            "expected origin must be an exact lowercase credential-free HTTPS origin "
            "with no port, path, query, fragment, or trailing slash"
        )
    return canonical


def _page_url(origin: str, relative: str) -> str:
    if relative == "index.html":
        return f"{origin}/"
    return f"{origin}/{relative.removesuffix('index.html')}"


def _parse_page(path: Path) -> tuple[str, _PageContractParser]:
    try:
        html = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SmokeFailure(f"cannot read built page {path}: {exc}") from exc
    parser = _PageContractParser()
    parser.feed(html)
    parser.close()
    return html, parser


def _one_meta(parser: _PageContractParser, kind: str, name: str, page: str) -> str:
    values = parser.meta.get((kind, name), [])
    if len(values) != 1:
        raise SmokeFailure(f"{page} must contain exactly one {kind}={name}")
    return values[0]


def _validate_pages(dist: Path, origin: str, expected_commit: str) -> None:
    for relative in REQUIRED_HTML:
        html, parser = _parse_page(dist / relative)
        expected_url = _page_url(origin, relative)
        if parser.canonicals != [expected_url]:
            raise SmokeFailure(
                f"{relative} canonical is {parser.canonicals!r}, expected {expected_url!r}"
            )
        if _one_meta(parser, "property", "og:url", relative) != expected_url:
            raise SmokeFailure(f"{relative} Open Graph URL does not match its canonical")
        og_image = _one_meta(parser, "property", "og:image", relative)
        parsed_image = urlsplit(og_image)
        image_relative = parsed_image.path.removeprefix("/")
        if (
            f"{parsed_image.scheme}://{parsed_image.netloc}" != origin
            or not parsed_image.path.startswith("/")
            or parsed_image.path.startswith("//")
            or ".." in Path(image_relative).parts
            or parsed_image.query
            or parsed_image.fragment
        ):
            raise SmokeFailure(f"{relative} Open Graph image is outside the canonical origin")
        if not (dist / image_relative).is_file():
            raise SmokeFailure(f"{relative} Open Graph image is missing from the artifact")

        csp = _one_meta(parser, "http-equiv", "content-security-policy", relative)
        for directive in (
            "default-src 'none'",
            "base-uri 'none'",
            "form-action 'self'",
            "script-src 'self'",
            "connect-src 'self'",
        ):
            if directive not in csp:
                raise SmokeFailure(f"{relative} meta CSP is missing {directive!r}")

        if relative == "index.html":
            if tuple(parser.primary_links) != EXPECTED_NAVIGATION:
                raise SmokeFailure(
                    "home primary navigation does not match the launch contract: "
                    + ", ".join(parser.primary_links)
                )
            footer_match = re.search(
                r'<footer class="site-footer">(?P<footer>.*?)</footer>',
                html,
                flags=re.DOTALL,
            )
            if footer_match is None:
                raise SmokeFailure("home page is missing the global product footer")
            footer = footer_match.group("footer")
            for label in REQUIRED_FOOTER_LINKS:
                if not re.search(rf">\s*{re.escape(label)}\s*</a>", footer):
                    raise SmokeFailure(f"home footer is missing {label!r}")
            for forbidden in (
                "Scientific results are not claimed",
                "Research-preview status",
                "Apache-2.0 source",
                "version.json",
                "Status and provenance",
            ):
                if forbidden in footer:
                    raise SmokeFailure(f"home footer retains launch clutter: {forbidden}")
            for marker in LEGACY_HOME_MARKERS:
                if marker in html:
                    raise SmokeFailure(f"home page retains legacy launch wording: {marker}")
            legacy_patterns = (
                r'<a[^>]+href="/platform/"[^>]*>\s*Engine\s*</a>',
                r'<a[^>]+href="/research/"[^>]*>\s*Research\s*</a>',
                r'<h2[^>]*class="footer-head"[^>]*>\s*Policies\s*</h2>',
                r"<a[^>]*>\s*Repository\s*</a>",
            )
            for pattern in legacy_patterns:
                if re.search(pattern, html):
                    raise SmokeFailure("home page retains legacy navigation or footer markup")


def _validate_sitemap_and_robots(dist: Path, origin: str) -> None:
    index_path = dist / "sitemap-index.xml"
    sitemap_path = dist / "sitemap-0.xml"
    robots_path = dist / "robots.txt"
    try:
        index_root = ElementTree.parse(index_path).getroot()
        sitemap_root = ElementTree.parse(sitemap_path).getroot()
        robots = robots_path.read_text(encoding="utf-8")
    except (OSError, ElementTree.ParseError) as exc:
        raise SmokeFailure(f"invalid sitemap or robots artifact: {exc}") from exc

    def locations(root: ElementTree.Element) -> list[str]:
        return [
            (element.text or "").strip()
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "loc"
        ]

    if locations(index_root) != [f"{origin}/sitemap-0.xml"]:
        raise SmokeFailure("sitemap index does not target the exact canonical origin")
    public_urls = locations(sitemap_root)
    required_urls = {_page_url(origin, relative) for relative in REQUIRED_HTML}
    if not required_urls.issubset(public_urls):
        raise SmokeFailure("sitemap is missing a required public launch page")
    if len(public_urls) != len(set(public_urls)) or any(
        not url.startswith(f"{origin}/") for url in public_urls
    ):
        raise SmokeFailure("sitemap contains duplicate or noncanonical destinations")
    sitemap_lines = [
        line.strip() for line in robots.splitlines() if line.strip().lower().startswith("sitemap:")
    ]
    if sitemap_lines != [f"Sitemap: {origin}/sitemap-index.xml"]:
        raise SmokeFailure("robots.txt does not identify the exact canonical sitemap")


def _headers_for(config: dict[str, Any], source: str) -> dict[str, str]:
    matches = [
        entry
        for entry in config.get("headers", [])
        if isinstance(entry, dict) and entry.get("source") == source
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("headers"), list):
        raise SmokeFailure(f"vercel.json must contain exactly one header rule for {source}")
    result: dict[str, str] = {}
    for header in matches[0]["headers"]:
        if not isinstance(header, dict):
            raise SmokeFailure(f"vercel.json has an invalid header in {source}")
        key = header.get("key")
        value = header.get("value")
        if not isinstance(key, str) or not isinstance(value, str) or key.lower() in result:
            raise SmokeFailure(f"vercel.json has an invalid or duplicate header in {source}")
        result[key.lower()] = value
    return result


def _validate_vercel_config(path: Path) -> None:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SmokeFailure(f"invalid Vercel configuration: {exc}") from exc
    if not isinstance(config, dict) or config.get("trailingSlash") is not True:
        raise SmokeFailure("vercel.json must preserve canonical trailing slashes")
    for key, value in VERCEL_BUILD_CONTRACT.items():
        if config.get(key) != value:
            raise SmokeFailure(f"vercel.json {key} does not match the production build contract")
    git = config.get("git")
    if not isinstance(git, dict) or git.get("deploymentEnabled") != VERCEL_GIT_CONTRACT:
        raise SmokeFailure("vercel.json must enable automatic deployment for main only")
    for key, value in GLOBAL_HEADERS.items():
        if _headers_for(config, "/(.*)").get(key) != value:
            raise SmokeFailure(f"vercel.json global {key} policy does not match the contract")
    for source, expected in ROUTE_HEADERS.items():
        actual = _headers_for(config, source)
        for key, value in expected.items():
            if actual.get(key) != value:
                raise SmokeFailure(f"vercel.json {source} {key} policy does not match the contract")


def validate_dist(
    dist: Path,
    expected_environment: str,
    expected_commit: str,
    expected_origin: str,
    vercel_config: Path,
) -> dict[str, Any]:
    if expected_environment not in {"production", "preview", "development"}:
        raise SmokeFailure(f"unsupported expected environment: {expected_environment}")
    if re.fullmatch(r"[0-9a-f]{40}", expected_commit) is None or expected_commit == "0" * 40:
        raise SmokeFailure("expected commit must be an exact non-placeholder 40-character SHA")
    origin = _canonical_origin(expected_origin)
    if not dist.is_dir():
        raise SmokeFailure(f"site artifact directory does not exist: {dist}")

    missing_pages = [relative for relative in REQUIRED_HTML if not (dist / relative).is_file()]
    missing_assets = [relative for relative in REQUIRED_ASSETS if not (dist / relative).is_file()]
    astro_assets = list((dist / "_astro").glob("*")) if (dist / "_astro").is_dir() else []
    if missing_pages:
        raise SmokeFailure("missing public pages: " + ", ".join(missing_pages))
    if missing_assets or not astro_assets:
        missing = [*missing_assets, *(["_astro/*"] if not astro_assets else [])]
        raise SmokeFailure("missing public assets: " + ", ".join(missing))

    manifest_path = dist / "version.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SmokeFailure(f"invalid version manifest: {exc}") from exc
    if not isinstance(manifest, dict) or set(manifest) != VERSION_FIELDS:
        raise SmokeFailure("version manifest fields do not match the public provenance contract")

    checks = {
        "release_version": r"\d+\.\d+\.\d+(?:[.+-][0-9A-Za-z.-]+)?",
        "release_status": r"(?:candidate|published)",
        "commit_sha": r"[0-9a-f]{40}",
        "built_at": r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
        "benchmark_harness_version": r"\d+\.\d+\.\d+",
        "schema_version": r"\d+",
    }
    for field, pattern in checks.items():
        value = manifest.get(field)
        if not isinstance(value, str) or re.fullmatch(pattern, value) is None:
            raise SmokeFailure(f"version manifest has invalid {field}")
    if manifest["commit_sha"] != expected_commit:
        raise SmokeFailure(
            f"version manifest commit does not match expected commit {expected_commit}"
        )
    if manifest.get("environment") != expected_environment:
        raise SmokeFailure(
            f"version manifest environment is {manifest.get('environment')!r}, "
            f"expected {expected_environment!r}"
        )

    _validate_pages(dist, origin, expected_commit)
    _validate_sitemap_and_robots(dist, origin)
    _validate_vercel_config(vercel_config)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("site/dist"))
    parser.add_argument("--vercel-config", type=Path, default=Path("vercel.json"))
    parser.add_argument(
        "--expect-environment",
        choices=("production", "preview", "development"),
        default="production",
    )
    parser.add_argument("--expect-commit", required=True)
    parser.add_argument("--expect-origin", required=True)
    args = parser.parse_args()
    try:
        manifest = validate_dist(
            args.dist,
            args.expect_environment,
            args.expect_commit,
            args.expect_origin,
            args.vercel_config,
        )
    except SmokeFailure as exc:
        print(f"site-production-smoke: FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "site-production-smoke: OK "
        f"{manifest['release_version']} {manifest['commit_sha'][:12]} "
        f"{manifest['environment']} {args.expect_origin}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
