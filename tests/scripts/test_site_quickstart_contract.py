from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]
SEQUENCE = (
    "uv sync --locked",
    "uv run irrevon init",
    "cp .env.example .env",
    "set -a && . ./.env && set +a",
    "docker compose up -d --wait",
    "uv run irrevon init",
    "uv run irrevon doctor",
    "uv run irrevon demo",
)
PUBLIC_QUICKSTARTS = (
    ROOT / "README.md",
    ROOT / "site" / "src" / "pages" / "index.astro",
    ROOT / "site" / "src" / "pages" / "install.astro",
    ROOT / "site" / "src" / "content" / "guides" / "getting-started.md",
)


def test_public_source_quickstarts_preserve_the_two_phase_migration_order() -> None:
    for path in PUBLIC_QUICKSTARTS:
        source = path.read_text(encoding="utf-8")
        cursor = source.find(SEQUENCE[0])
        assert cursor >= 0, f"{path} is missing the locked sync command"
        for command in SEQUENCE[1:]:
            cursor = source.find(command, cursor + 1)
            assert cursor >= 0, f"{path} is missing or misorders {command!r}"
