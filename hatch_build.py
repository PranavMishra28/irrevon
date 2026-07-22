"""Build honesty hook (ADR-0018): refuse to build a distributable artifact
without the staged workbench.

``make dist`` sets ``IRREVON_REQUIRE_WEB=1`` after staging ``web/dist`` into
``src/irrevon/_web``; if the staged assets are missing (or the staging step
was skipped) the build FAILS instead of silently shipping a wheel whose
``irrevon serve`` has nothing to serve. Editable installs (``uv sync``) never
set the env var, so contributors without Node are unaffected — serve degrades
gracefully at runtime instead.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class WebAssetsHook(BuildHookInterface):  # type: ignore[type-arg]
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        web_index = Path(self.root, "src", "irrevon", "_web", "index.html")
        if os.environ.get("IRREVON_REQUIRE_WEB") == "1" and not web_index.is_file():
            raise RuntimeError(
                "web assets missing: run `make web-build dist-stage` before "
                "building a distributable artifact (ADR-0018: no install path "
                "requires Node)"
            )
