# T-130: Hostile-review the release and supply-chain candidate

---
id: T-130
status: done
depends_on: [T-127]
invariant: "master doc §9 and §12.3; preserve secret safety, exact release identity, truthful provenance, and human-only publication"
---

## Objective

Adversarially review the integrated `0.1.0` release, package, provenance, and
Dependabot contracts and report only substantiated defects.

## Why

The release candidate now contains executable publication preparation and a
new multi-ecosystem dependency policy. A separate read-only pass must verify
that upstream semantics, permissions, artifacts, and public claims agree before
the owner considers any irreversible release action.

## Context — read these first

- `AGENTS.md`
- `docs/master-doc.md` §9 and §12.3
- `.github/workflows/release.yml`
- `.github/dependabot.yml`
- `scripts/release-dry-run.sh`
- `scripts/build-sbom.py`
- `scripts/check-dist-contents.py`
- `docs/release-process.md`
- `docs/ci.md`

## Scope

**Allowed to write:** this task file only.

**Forbidden:** every implementation, workflow, package, documentation, test, or
generated file; commits; tags; releases; uploads; deployments; provider calls;
repository settings; history changes; credentials; and sensitive-value output.

## Acceptance criteria

- [x] Review exact-version Twine execution, tag/main identity, workflow
      permissions, OIDC, attestations, archive/SBOM integrity, changelog/CFF
      truth, Dependabot semantics, and secret/log exposure.
- [x] Run focused non-publishing static and artifact checks.
- [x] Every finding names exact file/line evidence, impact, and the smallest
      safe correction; unsubstantiated concerns are excluded.
- [x] No implementation or external state changes.

## Required validation

```text
actionlint .github/workflows/release.yml
uv run --locked pytest -q tests/scripts/test_release_workflow_contract.py tests/scripts/test_dependabot_contract.py tests/scripts/test_dist_content_contract.py
IRREVON_ALLOW_RELEASE_VERSION=1 make release-dry-run
gitleaks dir --no-banner --redact dist
git diff --check
```

## Documentation updates

This task file records the review outcome; no public documentation changes are
authorized.

## Human review triggers — stop and ask if

- Verification would require publication, a tag, a credential, settings
  mutation, or inspection/output of a sensitive value.
- A defect requires implementation; report it rather than editing.

## Definition of done

The scoped surfaces have a hostile evidence-backed verdict, focused
non-publishing checks pass or their failures are recorded, findings include
minimal fixes, no forbidden file changes occur, and the task is marked done.

## Review outcome

Verdict: **three substantiated defects; publication should remain owner-blocked
until R1 and R2 are corrected.** The review changed no implementation or
external state.

### R1 — HIGH: release validators execute dependencies outside the project lock

**Evidence.**

- `scripts/release-dry-run.sh:24-27` selects `twine==6.2.0`, but invokes it with
  `uvx --from`; neither Twine nor its transitive dependencies occur in
  `uv.lock`.
- Twine runs after the exact archive-content check
  (`scripts/release-dry-run.sh:23`) and before the SBOM/checksums
  (`scripts/release-dry-run.sh:29-34`). A compromised dynamically resolved
  package could therefore alter the already-checked artifacts and have those
  altered bytes checksummed and later attested.
- `scripts/bootstrap-tools.sh:108-120` likewise installs
  `check-jsonschema==0.37.4` through pipx, uv tool, or pip without a transitive
  lock or distribution hashes. It is then executed by the release job through
  `make check` (`.github/workflows/release.yml:62-72,110-145`;
  `Makefile:17,59-70`).
- The release step names at `.github/workflows/release.yml:62,110` say
  “checksum-pinned validation tools,” and `docs/ci.md:144-147` calls the
  bootstrap table checksum-verified, although the bootstrap's
  `check-jsonschema` leg is only direct-version-pinned.

**Impact.** An upstream compromise or changed transitive resolution can execute
in the tagged build before artifact hashing. The job has no publication/OIDC
permission, which limits credential exposure, but the resulting bytes are the
inputs to the separate attestation and publishing jobs.

**Smallest safe correction.** Put Twine and `check-jsonschema` in a dedicated
exact-constrained release-validation dependency group covered by `uv.lock`;
invoke both through `uv run --locked` (and the schema Make target through that
locked command). Record the wheel/sdist hashes before Twine and require the
post-Twine hashes to match, so the renderer gate is provably non-mutating.
Until then, rename the bootstrap steps and documentation so they do not claim
that every installed validator is checksum-verified. A hash-locked dedicated
requirements/PEP 723 environment is an equivalent minimal design.

Upstream basis: uv documents that `uvx --from 'package==version'` selects the
direct package version, while project dependencies use the exact `uv.lock`
resolution; uv also documents that locking is needed to keep transitive
versions reproducible:

- <https://docs.astral.sh/uv/guides/tools/>
- <https://docs.astral.sh/uv/concepts/projects/sync/>
- <https://docs.astral.sh/uv/pip/compile/>

Twine 6.2.0 and `check --strict` are otherwise the correct current stable
renderer gate:

- <https://pypi.org/project/twine/6.2.0/>
- <https://twine.readthedocs.io/en/stable/index.html#twine-check>

### R2 — MEDIUM: the script binds the tag to main, but not the build checkout to the tag

**Evidence.** `.github/workflows/release.yml:126-132` computes the peeled tag
commit and current `origin/main`, compares those two values, then reads the
package version from the checked-out working tree. It never asserts that
`git rev-parse HEAD` equals the peeled tag commit. The clean-tree assertion at
line 117 detects file changes, not a different clean commit.

**Impact.** The invariant depends implicitly on `actions/checkout` ref
behavior. A ref race, checkout regression, or future checkout edit could build
a clean commit different from the commit whose tag/main equality was proven,
while still passing when both commits carry the same package version. The
attestation would faithfully sign those unintended bytes.

**Smallest safe correction.** After peeling the annotated tag, resolve
`checked_out_commit=$(git rev-parse HEAD)` and require it to equal both
`tagged_commit` and `reviewed_main`; add the three-way identity assertion to
`tests/scripts/test_release_workflow_contract.py`.

### R3 — LOW: the local release dry run does not enforce its declared Node range

**Evidence.** `web/package.json:7-10` requires Node `>=24.0.0 <25`, but
`Makefile:254-261` invokes pnpm/build without a Node-version preflight or strict
engine setting. The required local `IRREVON_ALLOW_RELEASE_VERSION=1 make
release-dry-run` completed successfully under an out-of-range Node 25 runtime
after pnpm emitted only an “Unsupported engine” warning. The tagged GitHub job
does pin Node from `web/.nvmrc`, so the public workflow path is not affected.

**Impact.** The documented local candidate gate can certify artifacts produced
by an unsupported build runtime, weakening local/CI parity and reproducibility.

**Smallest safe correction.** Add a fail-closed Node-major preflight to the
release/web-build path (or a pnpm engine-strict setting proven to reject the
root package) and cover the rejection with a focused contract test.

## Confirmed correct / no finding

- The annotated tag is required to peel exactly to current `origin/main`; older
  ancestors, lightweight tags, non-owner actors, forks, development/local
  versions, dirty trees, PRs, and manual dispatches cannot enter publication.
- Workflow permissions are separated correctly: repository code runs with
  `contents: read`; the attestation-only job has `contents: read`,
  `id-token: write`, and `attestations: write` and executes no repository code;
  PyPI has only `id-token: write`; GitHub release creation alone has
  `contents: write`. The full-SHA-pinned attestation wrapper remains supported,
  although GitHub now recommends `actions/attest` for new implementations.
- The protected `release` environment and PyPI workflow/environment binding
  match current Trusted Publisher guidance. Owner setup remains mandatory and
  no long-lived publishing credential is present.
- Archive manifests reject extra/missing/duplicate/unsafe sdist entries and
  wheel symlinks; the generated SPDX 2.3 document passed the official
  `pyspdxtools` validator; checksums cover the wheel, sdist, and SBOM; the
  attestation subjects also include `SHA256SUMS`.
- `CHANGELOG.md:11-29`, `CITATION.cff:5-11`,
  `PACKAGE_README.md:10-13`, and the public status surfaces consistently say
  `0.1.0` is an unpublished Alpha candidate with no confirmatory result.
- Dependabot's single monthly multi-ecosystem group, per-entry security groups,
  cooldown behavior, major-update ignores, assignee/label merging, and absence
  of auto-merge match current GitHub semantics. Security updates are not
  delayed by `cooldown`, and `version-update:semver-major` ignores do not
  suppress security updates.
- No secret or credential value is passed to or printed by the dry-run/build
  job; checkout credentials are not persisted; checksum and release commands
  print artifact names rather than credential material; the `dist/` scan found
  no leak.

Upstream references used for those conclusions:

- <https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations>
- <https://github.com/actions/attest-build-provenance>
- <https://docs.pypi.org/trusted-publishers/using-a-publisher/>
- <https://docs.github.com/en/code-security/concepts/supply-chain-security/multi-ecosystem-updates>
- <https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference>

## Validation record

All commands were non-publishing:

```text
PASS  actionlint .github/workflows/release.yml
PASS  zizmor --offline --persona=pedantic .github/workflows/release.yml
PASS  uv run --locked pytest -q tests/scripts/test_release_workflow_contract.py tests/scripts/test_dependabot_contract.py tests/scripts/test_dist_content_contract.py
      22 passed
PASS  IRREVON_ALLOW_RELEASE_VERSION=1 make release-dry-run
      exact wheel/sdist content, Twine strict rendering, SPDX validation,
      checksums; emitted the R3 unsupported-Node warning
PASS  gitleaks dir --no-banner --redact dist
      no leaks found
PASS  git diff --check
```
