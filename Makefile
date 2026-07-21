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

.PHONY: check links schemas secrets integrity tools tools-check

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
	  --remap "file://$(CURDIR)/fonts/ file://$(CURDIR)/web/public/fonts/" \
	  --remap "file://$(CURDIR)/brand/ file://$(CURDIR)/web/public/brand/" .

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
check-all: web-check web-test

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
	cd web && pnpm install --frozen-lockfile && pnpm exec playwright test --project=e2e --project=a11y

# F4: pixel baselines — only meaningful inside the pinned Linux container
# (see web/README.md); a bare local run skips the vrt project by design.
web-vrt:
	cd web && docker run --rm --ipc=host -e CI=1 -v "$$PWD":/work -w /work \
	  mcr.microsoft.com/playwright:v1.61.1-noble \
	  bash -lc 'corepack enable && \
	            pnpm install --frozen-lockfile --store-dir /tmp/pnpm-store && \
	            IRREVON_VRT_CONTAINER=1 pnpm exec playwright test --project=vrt'

# ── Marketing site gates (appended by the site/ task; see site/README.md) ─────
# Self-contained Node package, same corepack/pnpm pattern as web/. Deploy stays
# gated and human-only: .github/workflows/site-deploy.yml (dispatch-only) documents it.
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
