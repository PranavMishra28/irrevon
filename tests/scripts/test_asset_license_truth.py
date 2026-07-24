"""Regression checks for the generated asset ledger's license distinctions."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "scripts" / "assets-registry.json"
GENERATOR_PATH = ROOT / "scripts" / "build-assets-registry.py"
OUTPUT_PATH = ROOT / "ASSETS.md"


def _registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text())


def test_project_assets_follow_accepted_apache_license() -> None:
    rows = _registry()["rows"]
    project_rows = [row for row in rows if row["origin"] in {"original", "self-generated"}]

    assert project_rows
    assert {row["license"] for row in project_rows} == {"Apache-2.0"}


def test_stale_unlicensed_posture_cannot_return() -> None:
    corpus = "\n".join(
        (
            GENERATOR_PATH.read_text(),
            REGISTRY_PATH.read_text(),
            OUTPUT_PATH.read_text(),
        )
    ).casefold()

    assert "no license" not in corpus
    assert "pending adr-0014" not in corpus


def test_third_party_asset_licenses_remain_distinct() -> None:
    rows = {row["asset"]: row for row in _registry()["rows"]}

    assert rows["IBM Plex Sans / Mono woff2 subsets + OFL license text"]["origin"] == (
        "third-party-verbatim"
    )
    assert rows["IBM Plex Sans / Mono woff2 subsets + OFL license text"]["license"] == (
        "OFL-1.1"
    )
    assert rows["MSW service worker (generated vendor file)"]["origin"] == (
        "third-party-verbatim"
    )
    assert rows["MSW service worker (generated vendor file)"]["license"] == "MIT"
