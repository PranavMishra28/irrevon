"""Truth checks for authority and destructive-recovery onboarding guidance."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_readme_discloses_doctor_rolled_back_write_authority() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "non-destructive but not strictly read-only" in readme
    assert "rolled-back temporary-table write probe" in readme
    assert "using the runtime/operator role" in readme


def test_stale_volume_recipe_is_destructive_and_restarts_postgres() -> None:
    guide = (ROOT / "site" / "src" / "content" / "guides" / "getting-started.md").read_text(
        encoding="utf-8"
    )

    assert "reset deletes the disposable local PostgreSQL volume" in guide
    assert ("docker compose down -v\ndocker compose up -d --wait\nuv run irrevon init") in guide
    assert "Do not use this destructive reset against a volume" in guide


def test_distribution_smoke_supplies_separate_demo_migration_authority() -> None:
    smoke = (ROOT / "scripts" / "dist-smoke-inner.sh").read_text(encoding="utf-8")

    assert 'IRREVON_MIGRATION_DSN="$ADMIN_DSN" \\\n  "$IRV" demo' in smoke


def test_containerized_vrt_does_not_replace_host_node_modules() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert '-v "$$PWD":/work -v /work/node_modules -w /work' in makefile
