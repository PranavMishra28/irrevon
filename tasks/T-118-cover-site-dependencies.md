# T-118: Cover site dependencies with Dependabot

---
id: T-118
status: done
depends_on: []
invariant: "docs/master-doc.md §12.3 — dependency scans precede release"
---

## Objective

Add a noise-contained Dependabot lane for the independent `site/` pnpm project and make
that coverage a regression-tested CI contract.

## Why

`[VF]` The deployed marketing/documentation site has its own `package.json` and
`pnpm-lock.yaml`, while the current Dependabot configuration monitors only the root,
backend, and `web/` manifests. Leaving `site/` unlisted makes dependency and security-update
coverage silently incomplete.

## Context — read these first

- `AGENTS.md`
- `docs/ci.md`
- `.github/dependabot.yml`
- `site/package.json`
- `site/pnpm-lock.yaml`
- `site/pnpm-workspace.yaml`
- `site/README.md`
- `web/package.json`
- `web/pnpm-workspace.yaml`
- `web/README.md`
- GitHub Docs: Dependabot options reference and supported package ecosystems

## Scope

**Allowed to write:** `tasks/T-118-cover-site-dependencies.md`,
`.github/dependabot.yml`, `tests/scripts/test_dependabot_contract.py`, `docs/ci.md`,
`site/src/content/repo-docs/ci.md`.

**Forbidden:** every other path; dependency or lockfile updates; Docker update policy;
workflow code; GitHub settings, alert toggles, releases, publication, or deployment.

## Acceptance criteria

- [x] Dependabot has exactly four configured update lanes, including `npm` at `/web` and
      `npm` at `/site`; each lane is monthly, has a seven-day default cooldown, one open
      version-update PR maximum, the current owner assignment, and the established commit
      prefix.
- [x] The `/site` lane ignores major version updates, groups all minor/patch version
      updates, and separately groups security updates.
- [x] A narrow test fails if `/site` disappears or its low-noise/security policy drifts.
- [x] CI documentation and its generated site mirror describe four configured lanes and
      at most four scheduled version-update PRs per month.
- [x] Dependabot YAML parses and retains the required version-2 update structure.
- [x] `make check` passes.

## Required validation

```sh
uv run pytest tests/scripts/test_dependabot_contract.py -p no:cacheprovider
ruby -e 'require "yaml"; cfg=YAML.safe_load(File.read(".github/dependabot.yml")); abort unless cfg["version"] == 2 && cfg["updates"].is_a?(Array) && cfg["updates"].length == 4'
diff -u docs/ci.md <(tail -n +11 site/src/content/repo-docs/ci.md)
make check
git diff --check
```

## Documentation updates

Update `docs/ci.md` and its generated site mirror in lockstep.

## Human review triggers — stop and ask if:

- Coverage requires a GitHub setting or Dependabot alert/security-update toggle.
- The site needs a different upgrade policy from the already reviewed web policy.
- A dependency or lockfile must change to validate the configuration.

## Definition of done

All criteria checked; validation results reported; documentation mirrors synchronized; no
writes outside the allowed scope; status set to `done`.
