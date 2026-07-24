#!/usr/bin/env python3
"""Fail-closed content contract for Irrevon's Python distribution artifacts."""

from __future__ import annotations

import argparse
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

SDIST_TOP_LEVEL = {
    ".gitignore",
    "LICENSE",
    "LICENSING.md",
    "NOTICE",
    "PKG-INFO",
    "README.md",
    "hatch_build.py",
    "migrations",
    "pyproject.toml",
    "schemas",
    "src",
}


class ContractError(ValueError):
    """An artifact does not satisfy the declared distribution contract."""


def _safe_parts(name: str, *, artifact: str) -> tuple[str, ...]:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ContractError(f"{artifact} contains an unsafe path: {name!r}")
    return tuple(part for part in path.parts if part not in {"", "."})


def _require_members(names: set[str], required: set[str], *, artifact: str) -> None:
    missing = sorted(required - names)
    if missing:
        raise ContractError(f"{artifact} is missing required members: {missing}")


def _split_names(names: list[str], *, artifact: str) -> list[tuple[str, ...]]:
    result = []
    for name in names:
        parts = _safe_parts(name, artifact=artifact)
        if parts:
            result.append(parts)
    return result


def check_sdist(path: Path) -> None:
    with tarfile.open(path, mode="r:*") as archive:
        raw_names = archive.getnames()

    split_names = _split_names(raw_names, artifact="sdist")
    roots = {parts[0] for parts in split_names}
    if len(roots) != 1:
        raise ContractError(f"sdist must have exactly one archive root, found: {sorted(roots)}")
    root = next(iter(roots))
    relative_names = {"/".join(parts[1:]) for parts in split_names if len(parts) > 1}
    top_level = {parts[1] for parts in split_names if len(parts) > 1}
    unexpected = sorted(top_level - SDIST_TOP_LEVEL)
    missing = sorted(SDIST_TOP_LEVEL - top_level)
    if unexpected or missing:
        raise ContractError(
            "sdist top-level content differs from the allowlist: "
            f"unexpected={unexpected}, missing={missing}"
        )

    _require_members(
        relative_names,
        {
            ".gitignore",
            "LICENSE",
            "LICENSING.md",
            "NOTICE",
            "PKG-INFO",
            "README.md",
            "hatch_build.py",
            "pyproject.toml",
            "src/irrevon/__init__.py",
            "src/irrevon/_web/index.html",
            "migrations/0005_read_role.sql",
            "schemas/capability-declaration.schema.json",
        },
        artifact="sdist",
    )

    source_packages = {
        parts[2]
        for parts in split_names
        if len(parts) > 3 and parts[1] == "src"
    }
    if source_packages != {"irrevon"}:
        raise ContractError(
            "sdist src/ packages must be exactly ['irrevon'], "
            f"found: {sorted(source_packages)}"
        )
    stale = [
        "/".join(parts)
        for parts in split_names
        if "detent" in {part.lower() for part in parts}
    ]
    if stale:
        raise ContractError(f"sdist carries stale detent paths: {stale[:10]}")
    print(f"sdist content contract OK: root={root}, top-level={sorted(top_level)}")


def check_wheel(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        raw_names = archive.namelist()

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
    _require_members(
        names,
        {
            "irrevon/__init__.py",
            "irrevon/_web/index.html",
            "irrevon/_migrations/0005_read_role.sql",
            "irrevon/_schemas/capability-declaration.schema.json",
            f"{info_dir}/METADATA",
            f"{info_dir}/WHEEL",
            f"{info_dir}/RECORD",
            f"{info_dir}/licenses/LICENSE",
            f"{info_dir}/licenses/NOTICE",
        },
        artifact="wheel",
    )
    stale = [
        "/".join(parts)
        for parts in split_names
        if "detent" in {part.lower() for part in parts}
    ]
    if stale:
        raise ContractError(f"wheel carries stale detent paths: {stale[:10]}")
    print(
        "wheel content contract OK: "
        f"package=irrevon, dist-info={next(iter(dist_info))}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sdist", type=Path)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    try:
        check_sdist(args.sdist)
        check_wheel(args.wheel)
    except (ContractError, tarfile.TarError, zipfile.BadZipFile, OSError) as exc:
        print(f"artifact-content contract failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
