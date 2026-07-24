#!/usr/bin/env python3
"""Build an artifact- and lock-aware SPDX 2.3 JSON SBOM.

The release wheel/sdist are hashed as SPDX files. Python runtime packages come
from uv's frozen production export; bundled Workbench packages come from
pnpm's installed production graph. Dev dependencies and the separate marketing
site are deliberately excluded from the Python distribution SBOM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    hasher.update(path.read_bytes())
    return hasher.hexdigest()


def spdx_id(ecosystem: str, name: str, version: str) -> str:
    raw = f"{ecosystem}-{name}-{version}"
    return "SPDXRef-Package-" + re.sub(r"[^A-Za-z0-9.-]", "-", raw)


def python_packages() -> list[tuple[str, str]]:
    exported = subprocess.check_output(
        [
            "uv",
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements-txt",
        ],
        cwd=ROOT,
        text=True,
    )
    packages: list[tuple[str, str]] = []
    for line in exported.splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s;\\]+)", line)
        if match:
            packages.append((match.group(1), match.group(2)))
    if not packages:
        raise RuntimeError("uv production export produced no packages")
    return sorted(set(packages))


def node_packages() -> list[tuple[str, str, str, str]]:
    raw = subprocess.check_output(
        ["pnpm", "list", "--prod", "--depth", "Infinity", "--json"],
        cwd=ROOT / "web",
        text=True,
    )
    root = json.loads(raw)[0]
    found: dict[tuple[str, str], tuple[str, str]] = {}

    def walk(dependencies: dict[str, Any]) -> None:
        for name, entry in dependencies.items():
            if not isinstance(entry, dict):
                continue
            version = entry.get("version")
            if not isinstance(version, str):
                continue
            resolved = entry.get("resolved")
            package_path = entry.get("path")
            license_value = "NOASSERTION"
            if isinstance(package_path, str):
                metadata = Path(package_path) / "package.json"
                try:
                    license_raw = json.loads(metadata.read_text()).get("license")
                    if isinstance(license_raw, str) and license_raw:
                        license_value = license_raw
                except (OSError, ValueError):
                    pass
            found[(name, version)] = (
                resolved if isinstance(resolved, str) else "NOASSERTION",
                license_value,
            )
            child = entry.get("dependencies")
            if isinstance(child, dict):
                walk(child)

    walk(root.get("dependencies", {}))
    if not found:
        raise RuntimeError("pnpm production graph produced no packages")
    return sorted(
        (name, version, location, license_value)
        for (name, version), (location, license_value) in found.items()
    )


def created_at() -> str:
    value = subprocess.check_output(
        ["git", "show", "-s", "--format=%cI", "HEAD"], cwd=ROOT, text=True
    ).strip()
    return (
        datetime.fromisoformat(value)
        .astimezone(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, default=Path("dist/irrevon.spdx.json"))
    args = parser.parse_args()

    artifacts = sorted(Path("dist").glob("*.whl")) + sorted(Path("dist").glob("*.tar.gz"))
    if len(artifacts) != 2:
        raise RuntimeError("expected exactly one wheel and one sdist before SBOM generation")

    root_id = "SPDXRef-Package-irrevon"
    packages: list[dict[str, Any]] = [
        {
            "SPDXID": root_id,
            "name": "irrevon",
            "versionInfo": args.version,
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": True,
            "licenseConcluded": "Apache-2.0",
            "licenseDeclared": "Apache-2.0",
            "copyrightText": "Copyright 2026 Irrevon contributors",
            "externalRefs": [
                {
                    "referenceCategory": "PACKAGE-MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": f"pkg:pypi/irrevon@{args.version}",
                }
            ],
        }
    ]
    relationships: list[dict[str, str]] = []

    for name, version in python_packages():
        package_id = spdx_id("pypi", name, version)
        packages.append(
            {
                "SPDXID": package_id,
                "name": name,
                "versionInfo": version,
                "downloadLocation": f"https://pypi.org/project/{name}/{version}/",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "copyrightText": "NOASSERTION",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": f"pkg:pypi/{name}@{version}",
                    }
                ],
            }
        )
        relationships.append(
            {
                "spdxElementId": root_id,
                "relationshipType": "DEPENDS_ON",
                "relatedSpdxElement": package_id,
            }
        )

    for name, version, location, license_value in node_packages():
        package_id = spdx_id("npm", name, version)
        packages.append(
            {
                "SPDXID": package_id,
                "name": name,
                "versionInfo": version,
                "downloadLocation": location,
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": license_value,
                "copyrightText": "NOASSERTION",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": f"pkg:npm/{name.replace('@', '%40')}@{version}",
                    }
                ],
            }
        )
        relationships.append(
            {
                "spdxElementId": root_id,
                "relationshipType": "CONTAINS",
                "relatedSpdxElement": package_id,
            }
        )

    artifact_sha1s = [digest(artifact, "sha1") for artifact in artifacts]
    packages[0]["packageVerificationCode"] = {
        "packageVerificationCodeValue": hashlib.sha1(
            "".join(sorted(artifact_sha1s)).encode()
        ).hexdigest()
    }
    files = [
        {
            "SPDXID": f"SPDXRef-File-{index}",
            "fileName": f"./{artifact.name}",
            "checksums": [
                {"algorithm": "SHA1", "checksumValue": digest(artifact, "sha1")},
                {"algorithm": "SHA256", "checksumValue": digest(artifact)},
            ],
            "licenseConcluded": "NOASSERTION",
            "copyrightText": "NOASSERTION",
        }
        for index, artifact in enumerate(artifacts, start=1)
    ]
    relationships.extend(
        {
            "spdxElementId": root_id,
            "relationshipType": "CONTAINS",
            "relatedSpdxElement": file["SPDXID"],
        }
        for file in files
    )

    namespace_seed = hashlib.sha256(
        json.dumps({"packages": packages, "files": files}, sort_keys=True).encode()
    ).hexdigest()
    document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"irrevon-{args.version}",
        "documentNamespace": (
            f"https://github.com/PranavMishra28/irrevon/sbom/{namespace_seed}"
        ),
        "creationInfo": {
            "created": created_at(),
            "creators": ["Tool: scripts/build-sbom.py"],
        },
        "documentDescribes": [root_id],
        "packages": packages,
        "files": files,
        "relationships": relationships,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(
        f"sbom: wrote {args.output} "
        f"({len(packages)} packages, {len(files)} release artifacts)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
