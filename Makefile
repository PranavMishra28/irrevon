# Irrevon validation gates. `make check` is the required local gate; it must pass
# before any commit (pre-commit additionally runs the secret scan on every commit).
# One-time install: `make tools` (installs, then verifies versions via tools-check).
# Local installs are version-pinned below, not checksum-pinned — the checksum-verified
# bootstrap lands with CI (see docs/security-policy.md, supply-chain section).

SHELL := /bin/bash
.DEFAULT_GOAL := check

# Tested tool versions (update deliberately, in one commit with any CI pin change):
LYCHEE_VERSION := 0.24.2
CHECK_JSONSCHEMA_VERSION := 0.37.4
GITLEAKS_VERSION := 8.30.1

.PHONY: check links links-online schemas secrets integrity tools tools-check

check: links schemas secrets integrity
	@echo "OK: all validation gates passed"

# Internal links + heading anchors across tracked markdown. --offline checks only
# local file links, so the gate is deterministic and network-free; external URLs
# are deliberately not checked here. The remaps encode Vite's public-dir serving
# semantics: web/ root-absolute asset URLs (/fonts/*, /brand/*) resolve to
# web/public/* at runtime — the remapped file must still exist, so the check
# stays strict.
links:
	lychee --offline --include-fragments --no-progress --root-dir "$(CURDIR)" \
	  $(LYCHEE_EXCLUDES) \
	  --remap "file://$(CURDIR)/fonts/ file://$(CURDIR)/web/public/fonts/" \
	  --remap "file://$(CURDIR)/brand/ file://$(CURDIR)/web/public/brand/" .

links-online:
	lychee --include-fragments --no-progress --root-dir "$(CURDIR)" \
	  $(LYCHEE_EXCLUDES) \
	  $(LYCHEE_ONLINE_EXCLUDES) \
	  --remap "file://$(CURDIR)/fonts/ file://$(CURDIR)/web/public/fonts/" \
	  --remap "file://$(CURDIR)/brand/ file://$(CURDIR)/web/public/brand/" .

# site/src/content/ is excluded as a SOURCE only: it holds byte-synced mirrors of
# repository docs (drift-gated by scripts/sync-docs.mjs --check) plus site-authored
# markdown whose repo-relative links are resolved at build time by
# site/scripts/satteri-repo-links.mjs. Their links cannot resolve at the mirror
# location by construction; the canonical files are checked above at their real
# paths, and the BUILT site's links are checked by the site Playwright link suite
# (make site-test). Nothing is exempted twice-unchecked.
links: LYCHEE_EXCLUDES := --exclude-path site/src/content
links-online: LYCHEE_EXCLUDES := --exclude-path site/src/content
# Placeholder hosts are deliberately non-resolving. The SEC order is an
# authoritative primary source that returns 403 to automated clients; exclude
# that exact resource rather than teaching the checker to accept arbitrary 4xx.
links-online: LYCHEE_ONLINE_EXCLUDES := \
	--exclude 'https://irrevon\.dev' \
	--exclude 'https://example\.com' \
	--exclude 'https://www\.sec\.gov/files/litigation/admin/2013/34-70694\.pdf'

# Every schema must be valid against its declared metaschema; every valid-*.json
# example must pass; every invalid-*.json example must be REJECTED (the invalid
# suite is the executable form of the Intent Registrar's rejection rules).
schemas:
	check-jsonschema --check-metaschema schemas/*.schema.json
	@set -e; for s in schemas/*.schema.json; do \
	  n=$$(basename $$s .schema.json); d=schemas/examples/$$n; \
	  check-jsonschema --schemafile $$s $$d/valid-*.json; \
	  for f in $$d/invalid-*.json; do \
	    if check-jsonschema --schemafile $$s "$$f" >/dev/null 2>&1; then \
	      echo "FAIL: $$f validated against $$s but is required to be invalid"; exit 1; \
	    fi; \
	  done; \
	  echo "schemas: $$n examples OK (valid pass, invalid fail)"; \
	done

# Secret scan over the working tree, plus commit history once a git repo exists.
# Rules/allowlist live in .gitleaks.toml (generic rules only).
secrets:
	gitleaks dir --no-banner --redact .
	@if [ -d .git ]; then gitleaks git --no-banner --redact .; \
	else echo "secrets: no .git yet - history scan skipped"; fi

# Master-doc hash pin, ADR id uniqueness, .cursor JSON syntax, optional local
# tripword scan (.tripwords is untracked; see scripts/check-integrity.sh).
integrity:
	bash scripts/check-integrity.sh

tools:
	brew install lychee check-jsonschema gitleaks pre-commit
	@$(MAKE) --no-print-directory tools-check

# Fails loudly when installed tool versions drift from the tested set above.
# Not part of `check` (state gates must not depend on tool-install state), but run
# it after any `make tools` or brew upgrade; update the pins deliberately.
tools-check:
	@set -e; fail=0; \
	v=$$(lychee --version 2>/dev/null | awk '{print $$2}'); \
	[ "$$v" = "$(LYCHEE_VERSION)" ] || { echo "tools-check: lychee $$v != tested $(LYCHEE_VERSION)"; fail=1; }; \
	v=$$(check-jsonschema --version 2>/dev/null | awk '{print $$3}'); \
	[ "$$v" = "$(CHECK_JSONSCHEMA_VERSION)" ] || { echo "tools-check: check-jsonschema $$v != tested $(CHECK_JSONSCHEMA_VERSION)"; fail=1; }; \
	v=$$(gitleaks version 2>/dev/null); \
	[ "$$v" = "$(GITLEAKS_VERSION)" ] || { echo "tools-check: gitleaks $$v != tested $(GITLEAKS_VERSION)"; fail=1; }; \
	[ "$$fail" -eq 0 ] && echo "tools-check: all tool versions match the tested set" || exit 1

# ══════════════════════════════════════════════════════════════════════════════
# Python engine targets (appended by T-101..T-104; taxonomy per ADR-0017).
# `check` above is untouched; `check-all` folds the Python gates in.
# ══════════════════════════════════════════════════════════════════════════════

.PHONY: py-check py-test py-test-integration py-db-up py-db-down check-all

# Static gates: lockfile-faithful sync, lint, strict types, import boundaries.
py-check:
	uv sync --locked --quiet
	uv run ruff check src tests
	uv run mypy
	uv run lint-imports

# Unit + property tests (no I/O). HYPOTHESIS_PROFILE=dev(100)|ci/conformance(1000+).
py-test:
	uv sync --locked --quiet
	uv run pytest -m "not integration" -p no:cacheprovider

# Integration tests need the digest-pinned local Postgres (docker-compose.yml).
# Mocks never replace Postgres transactional behavior (testing.md §2).
py-test-integration: py-db-up
	uv sync --locked --quiet
	uv run pytest -m integration -p no:cacheprovider

py-db-up:
	docker compose up -d --wait ledger-db-test

py-db-down:
	docker compose down -v

check-all: check py-check py-test py-test-integration
	@echo "OK: all validation gates passed (docs + python + web)"

# ── CI gates (appended block — keep contiguous; see docs/ci.md) ───────────────
# Tested tool versions (update deliberately, in one commit with the pin table in
# scripts/bootstrap-tools.sh): actionlint 1.7.12, zizmor 1.27.0.
# `actionslint` runs zizmor --offline for the same reason `links` runs lychee
# --offline: the local gate stays deterministic and network-free. The nightly
# workflow runs the online variants.
.PHONY: actionslint frozen tools-pinned
check: actionslint frozen
tools: tools-pinned

actionslint:
	@if [ -d .github/workflows ]; then \
	  actionlint; \
	  zizmor --offline --persona=pedantic .github/workflows/; \
	else echo "actionslint: no .github/workflows yet - skipped"; fi

# Diff-based freeze/append-only gate. In CI, BASE_REF is the PR base; locally it
# checks the staged diff and never blocks uncommitted work.
frozen:
	bash scripts/check-frozen.sh

# Checksum-verified pinned binaries (Linux x86_64 + macOS arm64) — the same pin
# table CI and cloud agents use. `make tools` keeps brew as macOS convenience.
tools-pinned:
	bash scripts/bootstrap-tools.sh

# ── Web workbench gates (appended at integration; taxonomy per ADR-0017) ──────
# Recipes cd into web/ so corepack resolves the pinned pnpm from web/package.json.
# `check` stays node-free by design (docs/ci.md tier table); `check-all` folds the
# web gates in below. web-vrt is authoritative only inside the pinned container.
.PHONY: web-check web-test web-e2e web-vrt
check-all: web-check web-test web-e2e

# F0 static: typecheck, lint, stylelint, format, codegen drift, fixture pins,
# font drift, unit tests (the `check` script bundles the unit project).
web-check:
	cd web && pnpm install --frozen-lockfile && pnpm run check

# F1/F2: unit + Storybook browser-mode story tests (axe violations are errors).
# The story project runs headless chromium via Playwright: install the chromium
# headless shell first (version comes from the locked @playwright/test pin;
# no-op when already cached, so the target stays idempotent locally and in CI).
web-test:
	cd web && pnpm install --frozen-lockfile \
	  && pnpm exec playwright install chromium --only-shell \
	  && pnpm run test && pnpm run test:stories

# F3: Playwright workflows + a11y against the built review app.
web-e2e:
	cd web && pnpm install --frozen-lockfile \
	  && pnpm exec playwright install chromium --only-shell \
	  && pnpm exec playwright test --project=e2e --project=a11y

# F4: pixel baselines — only meaningful inside the pinned Linux container
# (see web/README.md); a bare local run skips the vrt project by design.
web-vrt:
	cd web && docker run --rm --ipc=host -e CI=1 -v "$$PWD":/work -w /work \
	  mcr.microsoft.com/playwright:v1.61.1-noble \
	  bash -lc 'corepack enable && \
	            pnpm install --frozen-lockfile --store-dir /tmp/pnpm-store && \
	            IRREVON_VRT_CONTAINER=1 pnpm exec playwright test --project=vrt'

# ── Marketing site gates (appended by the site/ task; see site/README.md) ─────
# Self-contained Node package, same corepack/pnpm pattern as web/. Deploys are
# owner-directed Vercel static uploads of site/dist (ADR-0027), never CI-triggered.
.PHONY: site-check site-build site-test

# Static gates: astro check + vendored token/font drift + claims-registry drift.
site-check:
	cd site && pnpm install --frozen-lockfile && pnpm run check

site-build:
	cd site && pnpm install --frozen-lockfile && pnpm run build

# Playwright: axe (WCAG 2.2 AA, both themes, all pages), keyboard, no-JS render,
# internal links, JS budget + zero-external-request scan. Builds first.
site-test:
	cd site && pnpm install --frozen-lockfile \
	  && pnpm exec playwright install chromium --only-shell \
	  && pnpm run build && pnpm test

# ── Serve + distribution targets (appended by the BE serve task; ADR-0024 ─────
# proposed). `make dist` is THE ordering ADR-0018 requires: web assets are
# built FIRST (the only step that touches Node), staged into the package, and
# the honesty hook (hatch_build.py, IRREVON_REQUIRE_WEB=1) fails the build if
# they are missing or were never staged. dist-smoke proves the whole no-Node
# chain inside python:3.13-slim (scripts/dist-smoke.sh).
.PHONY: web-build dist-stage dist dist-smoke py-test-serve serve-live web-e2e-live

web-build:
	cd web && pnpm install --frozen-lockfile && pnpm run build

dist-stage:
	rm -rf src/irrevon/_web && mkdir -p src/irrevon/_web && cp -R web/dist/. src/irrevon/_web/

dist: web-build dist-stage
	rm -rf dist && IRREVON_REQUIRE_WEB=1 uv build
	@ls -l dist/

dist-smoke: dist py-db-up
	bash scripts/dist-smoke.sh

# Serve-layer suite only (unit + integration; the full ladder already includes
# it via py-test / py-test-integration).
py-test-serve: py-db-up
	uv sync --locked --quiet
	uv run pytest tests/serve -p no:cacheprovider

# ── Governance registries (appended at rebuild consolidation; N5 design) ──────
# Two committed, generated, drift-gated registries (the site/CLAIMS.md pattern):
#   ASSETS.md                — asset provenance (sha256 + coverage sweep)
#   THIRD-PARTY-NOTICES.md   — third-party inventory (direct-dep coverage)
# Both checks are stdlib-python3-only and read committed files exclusively, so
# `check` stays node-free and install-free. Regeneration is a normal commit.
.PHONY: assets third-party
check: assets third-party

assets:
	python3 scripts/build-assets-registry.py --check

third-party:
	python3 scripts/build-third-party-notices.py --check

# ── Benchmark integrity gates (appended by the bench foundation; ADR-0030 ─────
# proposed). bench-integrity is stdlib-python3-only over committed files
# (manifest drift, canary, holdout leakage, freeze honesty, oracle isolation)
# so `check` stays install-free; the encoder-exact fixture parity and the full
# harness suites run under py-test / py-test-integration. bench-smoke is the
# CLI-level end-to-end (conventional arms only — no DB) folded into check-all.
.PHONY: bench-integrity bench-smoke
check: bench-integrity

bench-integrity:
	python3 scripts/check-bench-integrity.py

bench-smoke:
	uv sync --locked --quiet
	rm -rf .scratch/bench-smoke-ci
	uv run irrevon bench smoke --fixtures bench/fixtures/dev \
	  --out .scratch/bench-smoke-ci \
	  --workloads wl_dev.c2.responselost.irre.r0,wl_dev.c2.semanticresynthesis.irre.r0 \
	  --arms B0,B1,B3,B5,B6,B5+B3+B6 >/dev/null

check-all: bench-smoke

# Live E2E foundation for the consolidator's `web-e2e-live` (WEB's Playwright
# suite consumes this). Invocation contract (tests/serve/live_server.py):
#   - seeds the test Postgres (127.0.0.1:54329, override IRREVON_TEST_ADMIN_DSN)
#     via `irrevon demo --keep --seed 42` — kept DB irrevon_demo_s42; flagship
#     effect id 0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5;
#     demo artifact at /tmp/irrevon-demo-artifact.json (IRREVON_LIVE_ARTIFACT)
#   - then starts `irrevon serve --json` on IRREVON_LIVE_PORT (default 0 =
#     ephemeral) and prints serve's single-line JSON ready document on stdout:
#     {"schema_version":"1","url":"http://127.0.0.1:<port>/","port":<port>,...}
#   - Playwright targets ready.url; stop with SIGINT/SIGTERM (exit 0).
# The same contract is available in-process as the `live_serve` pytest fixture
# (tests/serve/conftest.py) for Python-side E2E tests.
serve-live: py-db-up
	uv sync --locked --quiet
	uv run python tests/serve/live_server.py

# THE joint proof (consolidation ladder): real demo data → real `irrevon serve`
# serving the staged packaged workbench → Playwright (web/e2e/live-real/,
# config web/playwright.live.config.ts — the suite spawns serve-live itself so
# the SIGKILL-disconnect test kills the REAL engine process). The stub-backed
# live suite (web-e2e) stays the fast PR-side approximation; this is the
# integration truth.
web-e2e-live: py-db-up web-build dist-stage
	uv sync --locked --quiet
	cd web && pnpm install --frozen-lockfile \
	  && pnpm exec playwright install chromium --only-shell \
	  && pnpm exec playwright test --config=playwright.live.config.ts
