from __future__ import annotations

import pytest
from scripts.campaign_url import build_campaign_url


def test_campaign_url_has_fixed_lowercase_order_and_clean_canonical() -> None:
    assert build_campaign_url(
        "https://irrevon.vercel.app/docs",
        source="linkedin",
        medium="organic-social",
        campaign="oss-launch",
        content="technical-explainer",
    ) == (
        "https://irrevon.vercel.app/docs/?utm_source=linkedin&utm_medium=organic-social"
        "&utm_campaign=oss-launch&utm_content=technical-explainer"
    )


def test_campaign_url_normalizes_hostname_case() -> None:
    assert build_campaign_url(
        "https://IRREVON.example/",
        source="x",
        medium="organic-social",
        campaign="oss-launch",
        content="launch-post",
    ).startswith("https://irrevon.example/?")


@pytest.mark.parametrize(
    "base",
    [
        "http://irrevon.example/",
        "https://localhost/",
        "https://127.0.0.1/",
        "https://[2606:4700:4700::1111]/",
        "https://irrevon.example:443/",
        "https://irrevon.example:bad/",
        "https://secret@example.com/",
        "https://preview-123.vercel.app/",
        "https://irrevon.example./",
        "https://irrevon.local/",
        "https://irrevon.example/?token=secret",
        "https://irrevon.example/#fragment",
        "https://irrevon.example/docs//guide/",
        "https://irrevon.example/docs/%2e%2e/private/",
        "https://irrevon.example/asset.js",
        " https://irrevon.example/",
    ],
)
def test_campaign_url_rejects_unsafe_or_noncanonical_base(base: str) -> None:
    with pytest.raises(ValueError):
        build_campaign_url(
            base,
            source="x",
            medium="organic-social",
            campaign="oss-launch",
            content="launch-post",
        )


@pytest.mark.parametrize(
    "value",
    ["LinkedIn", "has space", "email@example.com", "../secret", "", "trailing-", "two..dots"],
)
def test_campaign_url_rejects_inconsistent_or_sensitive_values(value: str) -> None:
    with pytest.raises(ValueError):
        build_campaign_url(
            "https://irrevon.example/",
            source=value,
            medium="organic-social",
            campaign="oss-launch",
            content="launch-post",
        )
