"""Static regression contracts for the scheduled nightly infrastructure.

These assertions intentionally inspect the committed orchestration text. The nightly
failures they pin occur outside pytest (GitHub-hosted Linux plus sibling containers), so
the local test protects the topology and parity decisions that make those environments
portable.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


def test_online_links_reuse_the_local_source_and_asset_rules() -> None:
    makefile = (ROOT / "Makefile").read_text()
    workflow = (ROOT / ".github/workflows/nightly.yml").read_text()

    assert "run: make links-online" in workflow
    assert "links-online: LYCHEE_EXCLUDES := --exclude-path site/src/content" in makefile
    assert "file://$(CURDIR)/web/public/fonts/" in makefile
    assert "file://$(CURDIR)/web/public/brand/" in makefile
    assert "file://$(CURDIR)/site/vercel.json file://$(CURDIR)/vercel.json" in makefile
    assert "34-70694" in makefile
    assert "--accept" not in makefile


def test_dist_smoke_joins_compose_network_without_widening_postgres() -> None:
    smoke = (ROOT / "scripts/dist-smoke.sh").read_text()
    compose = (ROOT / "docker-compose.yml").read_text()

    assert "docker compose ps -q ledger-db-test" in smoke
    assert '--network "$SMOKE_NETWORK"' in smoke
    assert "ledger-db-test" in smoke
    assert "host.docker.internal" not in smoke
    assert '"127.0.0.1:54329:5432"' in compose


def test_failure_reporter_needs_no_repository_label() -> None:
    workflow = (ROOT / ".github/workflows/nightly.yml").read_text()
    template = (ROOT / ".github/nightly-failure-body.md").read_text()

    assert 'ISSUE_TITLE="Nightly validation failure"' in workflow
    assert 'select(.title == "Nightly validation failure")' in workflow
    assert "--label nightly-failure" not in workflow
    assert ".github/nightly-failure-body.md" in workflow
    assert not (ROOT / ".github/ISSUE_TEMPLATE/nightly-failure.md").exists()
    assert not template.startswith("---")
