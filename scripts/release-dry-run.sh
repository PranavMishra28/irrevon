#!/usr/bin/env bash
# Build and verify release artifacts without publishing, tagging, or signing.
set -euo pipefail

version=$(uv run python -c 'import irrevon; print(irrevon.__version__)')
if [ "${IRREVON_ALLOW_RELEASE_VERSION:-0}" != "1" ]; then
  case "$version" in
    *dev*) ;;
    *) echo "release-dry-run: expected an unpublished development version, got $version" >&2; exit 1 ;;
  esac
fi

make dist
python3 scripts/build-third-party-license-pack.py --check
sdist=$(find dist -maxdepth 1 -type f -name '*.tar.gz' -print -quit)
wheel=$(find dist -maxdepth 1 -type f -name '*.whl' -print -quit)
[ -n "$sdist" ] && [ -n "$wheel" ]
python3 scripts/check-dist-contents.py "$sdist" "$wheel"

python3 scripts/build-sbom.py --version "$version" --output dist/irrevon.spdx.json
uv run pyspdxtools -i dist/irrevon.spdx.json
(
  cd dist
  sha256sum -- *.tar.gz *.whl irrevon.spdx.json > SHA256SUMS
)

python3 - <<'PY'
import json
from pathlib import Path
doc = json.loads(Path("dist/irrevon.spdx.json").read_text())
assert doc["spdxVersion"] == "SPDX-2.3"
assert doc["packages"][0]["licenseDeclared"] == "Apache-2.0"
assert Path("dist/SHA256SUMS").stat().st_size > 0
print("release-dry-run: checksums and SPDX SBOM structure verified")
PY

echo "release-dry-run: complete; nothing was uploaded, signed, tagged, or published"
