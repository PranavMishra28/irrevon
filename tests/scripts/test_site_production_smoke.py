from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "scripts" / "site-production-smoke.py"
SPEC = importlib.util.spec_from_file_location("site_production_smoke", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

COMMIT = "a" * 40
ORIGIN = "https://irrevon.example"
CSP = (
    "default-src 'none'; base-uri 'none'; form-action 'self'; "
    "script-src 'self' 'sha256-example'; connect-src 'self'"
)


def _route(relative: str) -> str:
    if relative == "index.html":
        return "/"
    return f"/{relative.removesuffix('index.html')}"


def _html(relative: str, *, origin: str = ORIGIN, commit: str = COMMIT) -> str:
    canonical = f"{origin}{_route(relative)}"
    nav = "".join(f"<a href='/'>{label}</a>" for label in MODULE.EXPECTED_NAVIGATION)
    return f"""<!doctype html>
<html><head>
<link rel="canonical" href="{canonical}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{origin}/og/og-default.png">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
</head><body>
<nav aria-label="Primary">{nav}</nav>
<footer><a href="https://github.com/example/irrevon/commit/{commit}"><code>{commit[:12]}</code></a></footer>
</body></html>
"""


def _vercel_config() -> dict[str, object]:
    return {
        **MODULE.VERCEL_BUILD_CONTRACT,
        "git": {"deploymentEnabled": MODULE.VERCEL_GIT_CONTRACT},
        "trailingSlash": True,
        "headers": [
            {
                "source": "/(.*)",
                "headers": [
                    {"key": key, "value": value}
                    for key, value in (
                        ("Content-Security-Policy", "frame-ancestors 'none'"),
                        (
                            "Strict-Transport-Security",
                            "max-age=31536000; includeSubDomains",
                        ),
                        ("X-Content-Type-Options", "nosniff"),
                        ("Referrer-Policy", "strict-origin-when-cross-origin"),
                        (
                            "Permissions-Policy",
                            "camera=(), microphone=(), geolocation=(), interest-cohort=()",
                        ),
                        ("Cross-Origin-Opener-Policy", "same-origin"),
                        ("X-Frame-Options", "DENY"),
                        (
                            "Cache-Control",
                            "public, max-age=600, stale-while-revalidate=86400",
                        ),
                    )
                ],
            },
            {
                "source": "/_astro/(.*)",
                "headers": [
                    {
                        "key": "Cache-Control",
                        "value": "public, max-age=31536000, immutable",
                    }
                ],
            },
            {
                "source": "/robots.txt",
                "headers": [
                    {
                        "key": "Cache-Control",
                        "value": "public, max-age=300, must-revalidate",
                    }
                ],
            },
            {
                "source": "/version.json",
                "headers": [
                    {
                        "key": "Content-Type",
                        "value": "application/json; charset=utf-8",
                    },
                    {"key": "X-Robots-Tag", "value": "noindex"},
                    {
                        "key": "Cache-Control",
                        "value": "public, max-age=0, must-revalidate",
                    },
                ],
            },
        ],
    }


def _artifact(tmp_path: Path, **manifest_overrides: str) -> tuple[Path, Path]:
    dist = tmp_path / "dist"
    for relative in MODULE.REQUIRED_HTML:
        page = dist / relative
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(_html(relative), encoding="utf-8")
    for relative in MODULE.REQUIRED_ASSETS:
        asset = dist / relative
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(b"fixture")
    astro_asset = dist / "_astro" / "site.css"
    astro_asset.parent.mkdir(parents=True, exist_ok=True)
    astro_asset.write_bytes(b"fixture")

    manifest = {
        "release_version": "0.1.0.dev0",
        "commit_sha": COMMIT,
        "built_at": "2026-07-24T12:00:00Z",
        "benchmark_harness_version": "0.1.0",
        "schema_version": "1",
        "environment": "production",
        **manifest_overrides,
    }
    (dist / "version.json").write_text(json.dumps(manifest), encoding="utf-8")
    (dist / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {ORIGIN}/sitemap-index.xml\n",
        encoding="utf-8",
    )
    (dist / "sitemap-index.xml").write_text(
        '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<sitemap><loc>{ORIGIN}/sitemap-0.xml</loc></sitemap></sitemapindex>",
        encoding="utf-8",
    )
    urls = "".join(
        f"<url><loc>{ORIGIN}{_route(relative)}</loc></url>"
        for relative in MODULE.REQUIRED_HTML
    )
    (dist / "sitemap-0.xml").write_text(
        '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{urls}</urlset>",
        encoding="utf-8",
    )
    vercel = tmp_path / "vercel.json"
    vercel.write_text(json.dumps(_vercel_config()), encoding="utf-8")
    return dist, vercel


def _validate(
    dist: Path,
    vercel: Path,
    *,
    commit: str = COMMIT,
    origin: str = ORIGIN,
) -> dict[str, str]:
    return cast(
        dict[str, str],
        MODULE.validate_dist(dist, "production", commit, origin, vercel),
    )


def test_accepts_complete_intended_production_artifact(tmp_path: Path) -> None:
    dist, vercel = _artifact(tmp_path)
    manifest = _validate(dist, vercel)
    assert manifest["commit_sha"] == COMMIT


@pytest.mark.parametrize(
    ("overrides", "expected_commit", "message"),
    [
        ({"commit_sha": "0" * 40}, COMMIT, "does not match expected commit"),
        ({"commit_sha": "unknown"}, COMMIT, "invalid commit_sha"),
        ({"commit_sha": "b" * 40}, COMMIT, "does not match expected commit"),
        ({"environment": "preview"}, COMMIT, "expected 'production'"),
    ],
)
def test_rejects_untrusted_manifest_provenance(
    tmp_path: Path,
    overrides: dict[str, str],
    expected_commit: str,
    message: str,
) -> None:
    dist, vercel = _artifact(tmp_path, **overrides)
    with pytest.raises(MODULE.SmokeFailure, match=message):
        _validate(dist, vercel, commit=expected_commit)


@pytest.mark.parametrize(
    "origin",
    [
        "http://irrevon.example",
        "https://IRREVON.example",
        "https://irrevon.example/",
        "https://irrevon.example:443",
        "https://user@irrevon.example",
        "https://irrevon.example/path",
        "https://irrevon.example?preview=1",
    ],
)
def test_rejects_noncanonical_expected_origin(tmp_path: Path, origin: str) -> None:
    dist, vercel = _artifact(tmp_path)
    with pytest.raises(MODULE.SmokeFailure, match="expected origin"):
        _validate(dist, vercel, origin=origin)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (
            f'<link rel="canonical" href="{ORIGIN}/">',
            '<link rel="canonical" href="https://wrong.example/">',
            "canonical",
        ),
        (
            f'<meta property="og:url" content="{ORIGIN}/">',
            '<meta property="og:url" content="https://wrong.example/">',
            "Open Graph URL",
        ),
    ],
)
def test_rejects_page_canonical_or_open_graph_drift(
    tmp_path: Path, old: str, new: str, message: str
) -> None:
    dist, vercel = _artifact(tmp_path)
    home = dist / "index.html"
    home.write_text(
        home.read_text(encoding="utf-8").replace(old, new),
        encoding="utf-8",
    )
    with pytest.raises(MODULE.SmokeFailure, match=message):
        _validate(dist, vercel)


@pytest.mark.parametrize(
    ("relative", "message"),
    [
        ("robots.txt", "sitemap or robots"),
        ("sitemap-0.xml", "sitemap or robots"),
        ("og/og-default.png", "missing public assets"),
        ("_astro/site.css", "missing public assets"),
    ],
)
def test_rejects_missing_discovery_or_asset_contract(
    tmp_path: Path, relative: str, message: str
) -> None:
    dist, vercel = _artifact(tmp_path)
    (dist / relative).unlink()
    with pytest.raises(MODULE.SmokeFailure, match=message):
        _validate(dist, vercel)


@pytest.mark.parametrize(
    ("relative", "old", "new", "message"),
    [
        (
            "sitemap-index.xml",
            f"{ORIGIN}/sitemap-0.xml",
            "https://wrong.example/sitemap-0.xml",
            "sitemap index",
        ),
        (
            "robots.txt",
            f"{ORIGIN}/sitemap-index.xml",
            "https://wrong.example/sitemap-index.xml",
            "robots.txt",
        ),
    ],
)
def test_rejects_noncanonical_discovery_destinations(
    tmp_path: Path, relative: str, old: str, new: str, message: str
) -> None:
    dist, vercel = _artifact(tmp_path)
    path = dist / relative
    path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    with pytest.raises(MODULE.SmokeFailure, match=message):
        _validate(dist, vercel)


@pytest.mark.parametrize("marker", MODULE.LEGACY_HOME_MARKERS)
def test_rejects_legacy_internal_launch_wording(tmp_path: Path, marker: str) -> None:
    dist, vercel = _artifact(tmp_path)
    home = dist / "index.html"
    home.write_text(home.read_text(encoding="utf-8") + marker, encoding="utf-8")
    with pytest.raises(MODULE.SmokeFailure, match="legacy launch wording"):
        _validate(dist, vercel)


def test_rejects_legacy_footer_markup(tmp_path: Path) -> None:
    dist, vercel = _artifact(tmp_path)
    home = dist / "index.html"
    home.write_text(
        home.read_text(encoding="utf-8")
        + '<h2 class="footer-head">Policies</h2>',
        encoding="utf-8",
    )
    with pytest.raises(MODULE.SmokeFailure, match="legacy navigation or footer"):
        _validate(dist, vercel)


def test_rejects_weakened_built_meta_csp(tmp_path: Path) -> None:
    dist, vercel = _artifact(tmp_path)
    home = dist / "index.html"
    home.write_text(
        home.read_text(encoding="utf-8").replace("form-action 'self'; ", ""),
        encoding="utf-8",
    )
    with pytest.raises(MODULE.SmokeFailure, match="meta CSP"):
        _validate(dist, vercel)


@pytest.mark.parametrize(
    ("source", "key", "message"),
    [
        ("/(.*)", "Content-Security-Policy", "global content-security-policy"),
        ("/(.*)", "Strict-Transport-Security", "global strict-transport-security"),
        ("/_astro/(.*)", "Cache-Control", r"/_astro/\(\.\*\) cache-control"),
        ("/version.json", "Cache-Control", "/version.json cache-control"),
        ("/version.json", "X-Robots-Tag", "/version.json x-robots-tag"),
        ("/version.json", "Content-Type", "/version.json content-type"),
    ],
)
def test_rejects_weakened_vercel_security_or_cache_policy(
    tmp_path: Path, source: str, key: str, message: str
) -> None:
    dist, vercel = _artifact(tmp_path)
    config = json.loads(vercel.read_text(encoding="utf-8"))
    rule = next(entry for entry in config["headers"] if entry["source"] == source)
    rule["headers"] = [header for header in rule["headers"] if header["key"] != key]
    vercel.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(MODULE.SmokeFailure, match=message):
        _validate(dist, vercel)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda config: config.update({"framework": "python"}),
            "framework does not match",
        ),
        (
            lambda config: config.update({"outputDirectory": "dist"}),
            "outputDirectory does not match",
        ),
        (
            lambda config: config["git"].update({"deploymentEnabled": True}),
            "main only",
        ),
        (
            lambda config: config["git"]["deploymentEnabled"].update(
                {"preview-*": True}
            ),
            "main only",
        ),
        (
            lambda config: config["git"]["deploymentEnabled"].pop("main"),
            "main only",
        ),
    ],
)
def test_rejects_weakened_vercel_build_or_branch_policy(
    tmp_path: Path,
    mutation: Callable[[dict[str, object]], object],
    message: str,
) -> None:
    dist, vercel = _artifact(tmp_path)
    config = json.loads(vercel.read_text(encoding="utf-8"))
    mutation(config)
    vercel.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(MODULE.SmokeFailure, match=message):
        _validate(dist, vercel)


def test_make_target_requires_explicit_expected_commit_and_origin() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    target = makefile.split("site-production-smoke:", 1)[1].split("\n\n", 1)[0]
    assert "SITE_EXPECT_COMMIT" in target
    assert "SITE_EXPECT_ORIGIN" in target
    assert "--expect-commit" in target
    assert "--expect-origin" in target
