from __future__ import annotations

import io
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check-dist-contents.py"
ARCHIVE_ROOT = "irrevon-0.1.0"

VALID_SDIST_MEMBERS = {
    ".gitignore",
    "LICENSE",
    "LICENSING.md",
    "NOTICE",
    "PKG-INFO",
    "PACKAGE_README.md",
    "README.md",
    "ASSETS.md",
    "CHANGELOG.md",
    "THIRD-PARTY-NOTICES.md",
    "THIRD-PARTY-LICENSES.md",
    "hatch_build.py",
    "pyproject.toml",
    "migrations/0005_read_role.sql",
    "schemas/capability-declaration.schema.json",
    "src/irrevon/__init__.py",
    "src/irrevon/_web/index.html",
}

VALID_WHEEL_MEMBERS = {
    "irrevon/__init__.py",
    "irrevon/_web/index.html",
    "irrevon/_migrations/0005_read_role.sql",
    "irrevon/_schemas/capability-declaration.schema.json",
    "irrevon/_legal/ASSETS.md",
    "irrevon/_legal/THIRD-PARTY-NOTICES.md",
    "irrevon/_legal/THIRD-PARTY-LICENSES.md",
    "irrevon-0.1.0.dist-info/METADATA",
    "irrevon-0.1.0.dist-info/WHEEL",
    "irrevon-0.1.0.dist-info/RECORD",
    "irrevon-0.1.0.dist-info/licenses/LICENSE",
    "irrevon-0.1.0.dist-info/licenses/NOTICE",
}


def _write_sdist(path: Path, members: set[str]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for relative in sorted(members):
            payload = b"test\n"
            info = tarfile.TarInfo(f"{ARCHIVE_ROOT}/{relative}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))


def _write_wheel(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for member in sorted(VALID_WHEEL_MEMBERS):
            archive.writestr(member, "test\n")


def _run_checker(tmp_path: Path, sdist_members: set[str]) -> subprocess.CompletedProcess[str]:
    sdist = tmp_path / "irrevon-0.1.0.tar.gz"
    wheel = tmp_path / "irrevon-0.1.0-py3-none-any.whl"
    _write_sdist(sdist, sdist_members)
    _write_wheel(wheel)
    return subprocess.run(
        [sys.executable, str(CHECKER), str(sdist), str(wheel)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_accepts_the_declared_artifact_surface(tmp_path: Path) -> None:
    result = _run_checker(tmp_path, VALID_SDIST_MEMBERS)

    assert result.returncode == 0, result.stderr
    assert "sdist content contract OK" in result.stdout
    assert "wheel content contract OK" in result.stdout


@pytest.mark.parametrize("leaked_tree", ["bench", "docs", "site", "tasks", "tests", "web"])
def test_rejects_every_unexpected_repository_tree(tmp_path: Path, leaked_tree: str) -> None:
    result = _run_checker(
        tmp_path,
        VALID_SDIST_MEMBERS | {f"{leaked_tree}/should-not-ship.txt"},
    )

    assert result.returncode == 1
    assert "artifact-content contract failed" in result.stderr
    assert f"unexpected=['{leaked_tree}']" in result.stderr
