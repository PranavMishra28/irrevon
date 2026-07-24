from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path

import pytest
import scripts.indexnow as indexnow
from scripts.indexnow import (
    Submission,
    build_submission,
    parse_sitemap,
    read_url_file,
    submit_indexnow,
    validate_canonical_url,
    validate_origin,
    verify_deployed,
)

ORIGIN = "https://irrevon.example"


def write_sitemap(path: Path, urls: list[str]) -> Path:
    entries = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    path.write_text(
        f'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{entries}</urlset>',
        encoding="utf-8",
    )
    return path


def test_parse_sitemap_and_build_changed_deleted_submission(tmp_path: Path) -> None:
    current = parse_sitemap(
        write_sitemap(tmp_path / "current.xml", [f"{ORIGIN}/", f"{ORIGIN}/docs/"]),
        ORIGIN,
    )
    previous = parse_sitemap(
        write_sitemap(tmp_path / "previous.xml", [f"{ORIGIN}/", f"{ORIGIN}/old/"]),
        ORIGIN,
    )
    submission = build_submission(
        origin=ORIGIN,
        current=current,
        changed={f"{ORIGIN}/docs/"},
        deleted={f"{ORIGIN}/old/"},
        previous=previous,
    )
    assert submission.live == (f"{ORIGIN}/docs/",)
    assert submission.deleted == (f"{ORIGIN}/old/",)
    assert submission.urls == (f"{ORIGIN}/docs/", f"{ORIGIN}/old/")


def test_parse_sitemap_rejects_duplicate_or_non_urlset_input(tmp_path: Path) -> None:
    duplicate = write_sitemap(tmp_path / "duplicate.xml", [f"{ORIGIN}/", f"{ORIGIN}/"])
    with pytest.raises(ValueError, match="duplicate"):
        parse_sitemap(duplicate, ORIGIN)

    sitemap_index = tmp_path / "index.xml"
    sitemap_index.write_text(
        (
            '<?xml version="1.0"?>'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"<sitemap><loc>{ORIGIN}/sitemap-0.xml</loc></sitemap></sitemapindex>"
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="urlset"):
        parse_sitemap(sitemap_index, ORIGIN)


def test_parse_sitemap_rejects_declarations_and_oversized_input(tmp_path: Path) -> None:
    declared = tmp_path / "declared.xml"
    declared.write_text(
        '<!DOCTYPE urlset [<!ENTITY x "value">]>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{ORIGIN}/</loc></url></urlset>",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="declarations"):
        parse_sitemap(declared, ORIGIN)

    oversized = tmp_path / "oversized.xml"
    oversized.write_bytes(b"x" * (indexnow.MAX_SITEMAP_BYTES + 1))
    with pytest.raises(ValueError, match="safety limit"):
        parse_sitemap(oversized, ORIGIN)


def test_url_file_rejects_duplicates_and_non_utf8(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.txt"
    duplicate.write_text(f"{ORIGIN}/docs/\n{ORIGIN}/docs/\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        read_url_file(duplicate)

    invalid = tmp_path / "invalid.txt"
    invalid.write_bytes(b"\xff")
    with pytest.raises(ValueError, match="UTF-8"):
        read_url_file(invalid)


@pytest.mark.parametrize(
    "url",
    [
        "http://irrevon.example/docs/",
        "https://other.example/docs/",
        "https://IRREVON.example/docs/",
        "https://user@irrevon.example/docs/",
        "https://irrevon.example:443/docs/",
        "https://irrevon.example:8443/docs/",
        "https://irrevon.example/docs/?utm_source=x",
        "https://irrevon.example/docs/#section",
        "https://irrevon.example/docs",
        "https://irrevon.example",
        "https://irrevon.example/docs//guide/",
        "https://irrevon.example/docs/%2e%2e/private/",
        "https://irrevon.example/404.html",
        "https://irrevon.example/_astro/app.js",
        "https://irrevon.example/llms.txt",
    ],
)
def test_rejects_noncanonical_or_nonhtml_urls(url: str) -> None:
    with pytest.raises(ValueError):
        validate_canonical_url(url, ORIGIN)


@pytest.mark.parametrize(
    "origin",
    [
        "http://irrevon.example",
        "https://localhost",
        "https://127.0.0.1",
        "https://[2606:4700:4700::1111]",
        "https://irrevon.example:443",
        "https://irrevon.example:bad",
        "https://IRREVON.example",
        "https://irrevon.example.",
        "https://preview-123.vercel.app",
        "https://irrevon.local",
        "https://user@irrevon.example",
        "https://irrevon.example/path",
        " https://irrevon.example",
    ],
)
def test_rejects_unsafe_origin(origin: str) -> None:
    with pytest.raises(ValueError):
        validate_origin(origin)


def test_deleted_url_must_be_previous_and_absent_from_current() -> None:
    with pytest.raises(ValueError, match="previous sitemap"):
        build_submission(
            origin=ORIGIN,
            current={f"{ORIGIN}/"},
            deleted={f"{ORIGIN}/old/"},
            previous=set(),
        )
    with pytest.raises(ValueError, match="still exist"):
        build_submission(
            origin=ORIGIN,
            current={f"{ORIGIN}/", f"{ORIGIN}/old/"},
            deleted={f"{ORIGIN}/old/"},
            previous={f"{ORIGIN}/old/"},
        )


def test_submission_cap_fails_closed() -> None:
    urls = {f"{ORIGIN}/page-{index}/" for index in range(3)}
    with pytest.raises(ValueError, match="configured URL cap"):
        build_submission(origin=ORIGIN, current=urls, cap=2)
    with pytest.raises(ValueError, match="between 1"):
        build_submission(origin=ORIGIN, current={f"{ORIGIN}/"}, cap=0)


def test_build_submission_validates_non_submitted_sitemap_sets() -> None:
    with pytest.raises(ValueError, match="foreign"):
        build_submission(
            origin=ORIGIN,
            current={f"{ORIGIN}/"},
            changed={f"{ORIGIN}/"},
            previous={"https://other.example/old/"},
        )


class FakeResponse:
    def __init__(
        self,
        url: str,
        body: bytes,
        *,
        status: int = 200,
        content_type: str = "text/html; charset=utf-8",
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._url = url
        self._body = body
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        for key, value in (extra_headers or {}).items():
            self.headers[key] = value

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def geturl(self) -> str:
        return self._url

    def read(self, size: int = -1) -> bytes:
        return self._body if size < 0 else self._body[:size]


class FakeOpener:
    def __init__(self, responses: dict[str, FakeResponse | Exception]) -> None:
        self.responses = responses
        self.requests: list[urllib.request.Request | str] = []

    def open(
        self,
        request: urllib.request.Request | str,
        *,
        timeout: float,
    ) -> FakeResponse:
        del timeout
        self.requests.append(request)
        url = request.full_url if isinstance(request, urllib.request.Request) else request
        result = self.responses[url]
        if isinstance(result, Exception):
            raise result
        return result


def _submission(*, deleted: tuple[str, ...] = ()) -> Submission:
    return Submission(origin=ORIGIN, live=(f"{ORIGIN}/docs/",), deleted=deleted)


def test_verify_deployed_accepts_direct_html_and_proven_deleted_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = "indexnow-test-key"
    deleted = f"{ORIGIN}/old/"
    html = (
        f'<link rel="alternate canonical" href="{ORIGIN}/docs/">'
        '<meta name="robots" content="index,follow">'
    ).encode()
    gone = urllib.error.HTTPError(deleted, 410, "gone", {}, None)
    opener = FakeOpener(
        {
            f"{ORIGIN}/indexnow-key.txt": FakeResponse(
                f"{ORIGIN}/indexnow-key.txt",
                f"{key}\n".encode(),
                content_type="text/plain; charset=utf-8",
            ),
            f"{ORIGIN}/docs/": FakeResponse(f"{ORIGIN}/docs/", html),
            deleted: gone,
        }
    )
    monkeypatch.setattr(indexnow, "_opener", lambda: opener)

    verify_deployed(_submission(deleted=(deleted,)), key)


@pytest.mark.parametrize(
    ("html", "headers", "final_url"),
    [
        (
            (
                f'<link rel="canonical" href="{ORIGIN}/docs/">'
                f'<link rel="canonical" href="{ORIGIN}/docs/">'
            ),
            {},
            f"{ORIGIN}/docs/",
        ),
        (
            f'<link rel="canonical" href="{ORIGIN}/docs/">',
            {"X-Robots-Tag": "noindex"},
            f"{ORIGIN}/docs/",
        ),
        (
            f'<link rel="canonical" href="{ORIGIN}/docs/">',
            {},
            f"{ORIGIN}/elsewhere/",
        ),
    ],
)
def test_verify_deployed_rejects_duplicate_metadata_noindex_and_redirects(
    monkeypatch: pytest.MonkeyPatch,
    html: str,
    headers: dict[str, str],
    final_url: str,
) -> None:
    key = "indexnow-test-key"
    opener = FakeOpener(
        {
            f"{ORIGIN}/indexnow-key.txt": FakeResponse(
                f"{ORIGIN}/indexnow-key.txt",
                key.encode(),
                content_type="text/plain",
            ),
            f"{ORIGIN}/docs/": FakeResponse(
                final_url,
                html.encode(),
                extra_headers=headers,
            ),
        }
    )
    monkeypatch.setattr(indexnow, "_opener", lambda: opener)
    with pytest.raises(RuntimeError):
        verify_deployed(_submission(), key)


def test_verify_deployed_rejects_oversized_response(monkeypatch: pytest.MonkeyPatch) -> None:
    key = "indexnow-test-key"
    opener = FakeOpener(
        {
            f"{ORIGIN}/indexnow-key.txt": FakeResponse(
                f"{ORIGIN}/indexnow-key.txt",
                key.encode(),
                content_type="text/plain",
            ),
            f"{ORIGIN}/docs/": FakeResponse(
                f"{ORIGIN}/docs/",
                b"x" * (indexnow.MAX_RESPONSE_BYTES + 1),
            ),
        }
    )
    monkeypatch.setattr(indexnow, "_opener", lambda: opener)
    with pytest.raises(RuntimeError, match="safety limit"):
        verify_deployed(_submission(), key)


def test_submit_uses_fixed_endpoint_and_minimal_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    key = "indexnow-test-key"
    response = FakeResponse(indexnow.INDEXNOW_ENDPOINT, b"", status=202)
    opener = FakeOpener({indexnow.INDEXNOW_ENDPOINT: response})
    monkeypatch.setattr(indexnow, "_opener", lambda: opener)

    assert submit_indexnow(_submission(), key) == 202
    request = opener.requests[0]
    assert isinstance(request, urllib.request.Request)
    assert request.full_url == indexnow.INDEXNOW_ENDPOINT
    assert json.loads(request.data or b"") == {
        "host": "irrevon.example",
        "key": key,
        "keyLocation": f"{ORIGIN}/indexnow-key.txt",
        "urlList": [f"{ORIGIN}/docs/"],
    }


def test_direct_network_helpers_revalidate_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        indexnow,
        "_opener",
        lambda: pytest.fail("unsafe submission must fail before constructing an opener"),
    )
    unsafe = Submission(origin=ORIGIN, live=("https://other.example/",), deleted=())
    with pytest.raises(ValueError):
        submit_indexnow(unsafe, "indexnow-test-key")
    with pytest.raises(ValueError):
        verify_deployed(_submission(), "short")


def test_main_dry_run_never_constructs_network_opener(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sitemap = write_sitemap(tmp_path / "current.xml", [f"{ORIGIN}/"])
    monkeypatch.setattr(
        indexnow,
        "_opener",
        lambda: pytest.fail("dry run attempted network access"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["indexnow.py", "--origin", ORIGIN, "--sitemap", str(sitemap)],
    )
    assert indexnow.main() == 0
    assert "IndexNow dry run: 1 live, 0 deleted canonical URLs" in capsys.readouterr().out
