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
    "irrevon-0.1.0.dist-info/entry_points.txt",
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


def _write_wheel(path: Path, members: set[str] = VALID_WHEEL_MEMBERS) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for member in sorted(members):
            archive.writestr(member, "test\n")


def _prepare_contract_root(tmp_path: Path) -> Path:
    contract_root = tmp_path / "contract"
    for relative in sorted(VALID_SDIST_MEMBERS - {"PKG-INFO"}):
        target = contract_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("test\n")
    return contract_root


def _run_checker(tmp_path: Path, sdist_members: set[str]) -> subprocess.CompletedProcess[str]:
    sdist = tmp_path / "irrevon-0.1.0.tar.gz"
    wheel = tmp_path / "irrevon-0.1.0-py3-none-any.whl"
    contract_root = _prepare_contract_root(tmp_path)
    _write_sdist(sdist, sdist_members)
    _write_wheel(wheel)
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            str(sdist),
            str(wheel),
            "--contract-root",
            str(contract_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_accepts_the_declared_artifact_surface(tmp_path: Path) -> None:
    result = _run_checker(tmp_path, VALID_SDIST_MEMBERS)

    assert result.returncode == 0, result.stderr
    assert "sdist exact content contract OK" in result.stdout
    assert "wheel exact content contract OK" in result.stdout


@pytest.mark.parametrize("leaked_tree", ["bench", "docs", "site", "tasks", "tests", "web"])
def test_rejects_every_unexpected_repository_tree(tmp_path: Path, leaked_tree: str) -> None:
    result = _run_checker(
        tmp_path,
        VALID_SDIST_MEMBERS | {f"{leaked_tree}/should-not-ship.txt"},
    )

    assert result.returncode == 1
    assert "artifact-content contract failed" in result.stderr
    assert f"{leaked_tree}/should-not-ship.txt" in result.stderr


@pytest.mark.parametrize(
    "member",
    [
        "src/irrevon/unreviewed.py",
        "schemas/unreviewed.schema.json",
        "migrations/9999_unreviewed.sql",
    ],
)
def test_rejects_unexpected_files_inside_allowed_trees(
    tmp_path: Path, member: str
) -> None:
    result = _run_checker(tmp_path, VALID_SDIST_MEMBERS | {member})

    assert result.returncode == 1
    assert member in result.stderr


def test_rejects_sdist_links(tmp_path: Path) -> None:
    sdist = tmp_path / "irrevon-0.1.0.tar.gz"
    wheel = tmp_path / "irrevon-0.1.0-py3-none-any.whl"
    contract_root = tmp_path / "contract"
    contract_root.mkdir()
    with tarfile.open(sdist, "w:gz") as archive:
        info = tarfile.TarInfo(f"{ARCHIVE_ROOT}/LICENSE")
        info.type = tarfile.SYMTYPE
        info.linkname = "../../outside"
        archive.addfile(info)
    _write_wheel(wheel)
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            str(sdist),
            str(wheel),
            "--contract-root",
            str(contract_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "non-regular members" in result.stderr


def test_rejects_wheel_symlinks(tmp_path: Path) -> None:
    sdist = tmp_path / "irrevon-0.1.0.tar.gz"
    wheel = tmp_path / "irrevon-0.1.0-py3-none-any.whl"
    contract_root = _prepare_contract_root(tmp_path)
    _write_sdist(sdist, VALID_SDIST_MEMBERS)
    with zipfile.ZipFile(wheel, "w") as archive:
        link = zipfile.ZipInfo("irrevon/link")
        link.create_system = 3
        link.external_attr = (0o120777 << 16)
        archive.writestr(link, "../../outside")
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            str(sdist),
            str(wheel),
            "--contract-root",
            str(contract_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "symbolic links" in result.stderr
