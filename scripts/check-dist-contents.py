#!/usr/bin/env python3
"""Fail-closed content contract for Irrevon's Python distribution artifacts."""

from __future__ import annotations

import argparse
import stat
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SDIST_ROOT_FILES = {
    ".gitignore",
    "LICENSE",
    "LICENSING.md",
    "NOTICE",
    "THIRD-PARTY-NOTICES.md",
    "THIRD-PARTY-LICENSES.md",
    "ASSETS.md",
    "CHANGELOG.md",
    "PKG-INFO",
    "PACKAGE_README.md",
    "README.md",
    "hatch_build.py",
    "pyproject.toml",
}
SOURCE_TREES = ("migrations", "schemas", "src")


class ContractError(ValueError):
    """An artifact does not satisfy the declared distribution contract."""


def _safe_parts(name: str, *, artifact: str) -> tuple[str, ...]:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ContractError(f"{artifact} contains an unsafe path: {name!r}")
    return tuple(part for part in path.parts if part not in {"", "."})


def _split_names(names: list[str], *, artifact: str) -> list[tuple[str, ...]]:
    result = []
    for name in names:
        parts = _safe_parts(name, artifact=artifact)
        if parts:
            result.append(parts)
    return result


def _source_files(root: Path, relative: str) -> set[str]:
    base = root / relative
    return {
        path.relative_to(root).as_posix()
        for path in base.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    }


def _expected_sdist(root: Path) -> set[str]:
    return SDIST_ROOT_FILES | set().union(
        *(_source_files(root, tree) for tree in SOURCE_TREES)
    )


def _expected_wheel(root: Path, info_dir: str) -> set[str]:
    package = {
        path.removeprefix("src/")
        for path in _source_files(root, "src/irrevon")
    }
    schemas = {
        f"irrevon/_schemas/{path.removeprefix('schemas/')}"
        for path in _source_files(root, "schemas")
    }
    migrations = {
        f"irrevon/_migrations/{path.removeprefix('migrations/')}"
        for path in _source_files(root, "migrations")
    }
    legal = {
        f"irrevon/_legal/{name}"
        for name in ("ASSETS.md", "THIRD-PARTY-LICENSES.md", "THIRD-PARTY-NOTICES.md")
    }
    metadata = {
        f"{info_dir}/METADATA",
        f"{info_dir}/WHEEL",
        f"{info_dir}/entry_points.txt",
        f"{info_dir}/licenses/LICENSE",
        f"{info_dir}/licenses/NOTICE",
        f"{info_dir}/RECORD",
    }
    return package | schemas | migrations | legal | metadata


def _require_exact(actual: set[str], expected: set[str], *, artifact: str) -> None:
    unexpected = sorted(actual - expected)
    missing = sorted(expected - actual)
    if unexpected or missing:
        raise ContractError(
            f"{artifact} content differs from the exact source manifest: "
            f"unexpected={unexpected[:20]}, missing={missing[:20]}"
        )


def check_sdist(path: Path, *, contract_root: Path = ROOT) -> None:
    with tarfile.open(path, mode="r:*") as archive:
        members = archive.getmembers()
    raw_names = [member.name for member in members]
    if len(raw_names) != len(set(raw_names)):
        raise ContractError("sdist contains duplicate member names")
    non_files = [member.name for member in members if not member.isfile()]
    if non_files:
        raise ContractError(f"sdist contains non-regular members: {non_files[:20]}")

    split_names = _split_names(raw_names, artifact="sdist")
    roots = {parts[0] for parts in split_names}
    if len(roots) != 1:
        raise ContractError(f"sdist must have exactly one archive root, found: {sorted(roots)}")
    root = next(iter(roots))
    relative_names = {"/".join(parts[1:]) for parts in split_names if len(parts) > 1}
    _require_exact(relative_names, _expected_sdist(contract_root), artifact="sdist")

    stale = [
        "/".join(parts)
        for parts in split_names
        if "detent" in {part.lower() for part in parts}
    ]
    if stale:
        raise ContractError(f"sdist carries stale detent paths: {stale[:10]}")
    print(f"sdist exact content contract OK: root={root}, files={len(relative_names)}")


def check_wheel(path: Path, *, contract_root: Path = ROOT) -> None:
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
    raw_names = [member.filename for member in members]
    if len(raw_names) != len(set(raw_names)):
        raise ContractError("wheel contains duplicate member names")
    links = [
        member.filename
        for member in members
        if stat.S_ISLNK((member.external_attr >> 16) & 0xFFFF)
    ]
    if links:
        raise ContractError(f"wheel contains symbolic links: {links[:20]}")

    split_names = _split_names(raw_names, artifact="wheel")
    names = {"/".join(parts) for parts in split_names}
    top_level = {parts[0] for parts in split_names}
    dist_info = {name for name in top_level if name.endswith(".dist-info")}
    unexpected = sorted(top_level - {"irrevon"} - dist_info)
    if unexpected or len(dist_info) != 1 or "irrevon" not in top_level:
        raise ContractError(
            "wheel top-level content differs from the allowlist: "
            f"unexpected={unexpected}, dist_info={sorted(dist_info)}, "
            f"package_present={'irrevon' in top_level}"
        )

    info_dir = next(iter(dist_info))
    _require_exact(names, _expected_wheel(contract_root, info_dir), artifact="wheel")
    stale = [
        "/".join(parts)
        for parts in split_names
        if "detent" in {part.lower() for part in parts}
    ]
    if stale:
        raise ContractError(f"wheel carries stale detent paths: {stale[:10]}")
    print(
        "wheel exact content contract OK: "
        f"package=irrevon, dist-info={next(iter(dist_info))}, files={len(names)}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sdist", type=Path)
    parser.add_argument("wheel", type=Path)
    parser.add_argument(
        "--contract-root",
        type=Path,
        default=ROOT,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()
    try:
        check_sdist(args.sdist, contract_root=args.contract_root)
        check_wheel(args.wheel, contract_root=args.contract_root)
    except (ContractError, tarfile.TarError, zipfile.BadZipFile, OSError) as exc:
        print(f"artifact-content contract failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
