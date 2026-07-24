"""Truth contract for pre-freeze benchmark-development observations.

The benchmark has no live-sandbox or confirmatory evidence, but it is not
pre-observation: synthetic S-REF smoke pilots are part of the development
record. Public copy must preserve both halves of that statement.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_canonical_draft_inventories_known_developmental_observations() -> None:
    prereg = _read("docs/benchmark-preregistration.md")
    guide = _read("docs/benchmark.md")

    for text in (prereg, guide):
        normalized = " ".join(text.lower().replace(">", " ").split())
        assert "Developmental" in text
        assert "488" in text
        assert "144" in text
        assert "S-REF" in text
        assert "non-confirmatory" in text
        assert "no live-sandbox" in normalized
        assert "no" in normalized and "confirmatory run" in normalized

    assert "cannot honestly be described as pristine" in prereg
    assert "not because no observation has occurred" in prereg


def test_human_ruling_remains_open_and_master_document_is_not_silently_rewritten() -> None:
    queue = _read("docs/review-queue.md")

    assert "| AM-25 | §8.1, §8.5, §12.2 |" in queue
    assert "PROPOSED — human scientific-integrity ruling required" in queue
    assert "| 41 | **Developmental benchmark exposure ruling" in queue
    assert "OPEN (appended 2026-07-23 by T-111; human-only ruling)" in queue


def test_public_surfaces_do_not_restore_categorical_no_observation_claims() -> None:
    public_paths = (
        "site/src/data/claims.ts",
        "site/src/pages/benchmark.astro",
        "site/src/pages/index.astro",
        "site/src/pages/roadmap.astro",
        "site/src/pages/platform.astro",
        "site/src/content/research/preregistering-a-benchmark.md",
        "site/src/content/guides/benchmark-reproduction.md",
        "web/src/app/routes/index.tsx",
    )
    forbidden = (
        "No benchmark has been run",
        "no benchmark run has occurred",
        "no benchmark run, sandbox spike",
        "No benchmark run contract or artifact exists",
        "before a single run",
        "nothing runs before the preregistration freeze",
        "preregisters hypotheses/metrics/analysis before any run",
        "Stage-A freeze precedes all observation",
    )

    for relative in public_paths:
        text = _read(relative)
        for stale_claim in forbidden:
            assert stale_claim not in text, f"{relative} restored stale claim: {stale_claim}"

    claims = _read("site/src/data/claims.ts")
    assert '"developmental-pilot-disclosure"' in claims
    assert "No scientific or confirmatory benchmark result exists" in claims
