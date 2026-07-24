#!/usr/bin/env python3
"""Generate one canonical Irrevon launch URL with a bounded UTM taxonomy."""

from __future__ import annotations

import argparse
import ipaddress
import re
from urllib.parse import urlencode, urlsplit, urlunsplit

UTM_ORDER = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")
TOKEN = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
SAFE_PATH = re.compile(r"^/(?:[A-Za-z0-9_~-]+/)*$")


def _public_https_url(raw: str) -> tuple[str, str, str]:
    if raw != raw.strip() or any(ord(character) < 0x20 for character in raw):
        raise ValueError("base URL must not contain whitespace or control characters")
    parsed = urlsplit(raw)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("base URL must be credential-free HTTPS")
    try:
        explicit_port = parsed.port
    except ValueError as error:
        raise ValueError("base URL contains an invalid port") from error
    if explicit_port is not None or parsed.query or parsed.fragment:
        raise ValueError("base URL must not contain a port, query, or fragment")
    try:
        parsed.hostname.encode("ascii")
    except UnicodeEncodeError as error:
        raise ValueError("base URL host must be ASCII") from error
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
        raise ValueError("preview and local hosts are not campaign destinations")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP literals are not campaign destinations")
    path = parsed.path or "/"
    if (
        "\\" in path
        or "%" in path
        or "//" in path
        or not SAFE_PATH.fullmatch(path if path.endswith("/") else f"{path}/")
    ):
        raise ValueError("base URL path must be a clean ASCII HTML route")
    if not path.endswith("/"):
        path += "/"
    return parsed.scheme, host, path


def build_campaign_url(
    base_url: str,
    *,
    source: str,
    medium: str,
    campaign: str,
    content: str,
    term: str | None = None,
) -> str:
    values = {
        "utm_source": source,
        "utm_medium": medium,
        "utm_campaign": campaign,
        "utm_content": content,
    }
    if term is not None:
        values["utm_term"] = term
    for key, value in values.items():
        if len(value) > 64 or not TOKEN.fullmatch(value):
            raise ValueError(
                f"{key} must be 1-64 lowercase letters/digits separated by single dots or hyphens"
            )
    scheme, netloc, path = _public_https_url(base_url)
    query = urlencode([(key, values[key]) for key in UTM_ORDER if key in values])
    return urlunsplit((scheme, netloc, path, query, ""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url")
    parser.add_argument("--source", required=True)
    parser.add_argument("--medium", required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--term")
    args = parser.parse_args()
    print(
        build_campaign_url(
            args.base_url,
            source=args.source,
            medium=args.medium,
            campaign=args.campaign,
            content=args.content,
            term=args.term,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
