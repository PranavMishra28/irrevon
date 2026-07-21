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
