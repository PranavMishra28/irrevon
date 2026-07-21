# Detent validation gates. `make check` is the only command anyone (human or agent)
# needs to remember; it must pass before any commit.
# Tested tool versions (update deliberately): lychee 0.24.x, check-jsonschema 0.37.x,
# gitleaks 8.x. One-time install: `make tools`.

SHELL := /bin/bash
.DEFAULT_GOAL := check

.PHONY: check links schemas secrets integrity tools

check: links schemas secrets integrity
	@echo "OK: all validation gates passed"

# Internal links + heading anchors across tracked markdown. --offline checks only
# local file links, so the gate is deterministic and network-free; external URLs
# are deliberately not checked here.
links:
	lychee --offline --include-fragments --no-progress --root-dir "$(CURDIR)" .

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
