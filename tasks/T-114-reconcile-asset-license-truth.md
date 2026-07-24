# T-114: Reconcile asset-license truth

---
id: T-114
status: done
depends_on: []
invariant: "ADR-0028 — the repository is licensed Apache-2.0 as a whole while third-party material retains its own license terms"
---

## Objective

Make the generated asset-provenance ledger state the accepted Apache-2.0 project license
without changing any asset, hash, or third-party license claim.

## Why

ADR-0028 records the owner-ratified Apache-2.0 outbound license `[DD]`, and
`LICENSING.md`, `LICENSE`, and `NOTICE` publish that current posture `[VF]`. The asset
generator and its machine-readable registry still describe project-original assets as
unlicensed pending ADR-0014, so their generated public ledger contradicts the accepted
decision.

## Context — read these first

- `AGENTS.md`
- `docs/decisions/0028-apache-2-license.md`
- `docs/decisions/0014-licensing.md`
- `LICENSING.md`
- `LICENSE`
- `NOTICE`
- `scripts/build-assets-registry.py`
- `scripts/assets-registry.json`
- `ASSETS.md`
- `site/ASSETS.md`
- `Makefile` (`assets` and `check`)

## Scope

**Allowed to write:** `tasks/T-114-reconcile-asset-license-truth.md`,
`scripts/build-assets-registry.py`, `scripts/assets-registry.json`, generated
`ASSETS.md`, `site/ASSETS.md` only if its pointer text is found to be stale, and
`tests/scripts/test_asset_license_truth.py`.

**Forbidden:** changing the outbound license choice; `LICENSE`, `NOTICE`,
`LICENSING.md`, accepted ADRs, contribution policy, trademarks, package metadata,
third-party license claims, SVGs, images, fonts, other assets, asset hashes,
deployment, publication, or any human-gated mechanism. Anything not listed as allowed
is out of scope.

## Acceptance criteria

- [x] `python3 scripts/build-assets-registry.py --check` exits 0 and reports the generated
      ledger in sync with every swept asset registered.
- [x] The generated ledger contains no statement that the repository has no license and
      no project-original row marked as pending ADR-0014.
- [x] The narrow regression proves project-original rows use Apache-2.0 while the IBM Plex
      and MSW third-party rows retain OFL-1.1 and MIT respectively.
- [x] Regeneration changes no registered path or asset hash.
- [x] `make assets` and `make check` pass.

## Required validation

```text
uv run pytest tests/scripts/test_asset_license_truth.py -p no:cacheprovider
python3 scripts/build-assets-registry.py --check
make assets
make check
git diff --check
```

## Documentation updates

Regenerate root `ASSETS.md` mechanically. Leave `site/ASSETS.md` unchanged unless its
pointer is stale.

## Human review triggers — stop and ask if:

- Correcting the stale copy would require choosing or changing a license.
- A third-party license claim appears incorrect or ambiguous.
- Any registered path, asset byte, or asset hash would change.
- The work would require contribution, trademark, packaging, deployment, publication, or
  another human-gated mechanism.

## Definition of done

All criteria are checked; validation results are recorded below; no asset or hash changes;
no writes outside the allowed scope; status is `done`.

## Validation results

- `uv run pytest tests/scripts/test_asset_license_truth.py -p no:cacheprovider` — 3 passed.
- `python3 scripts/build-assets-registry.py --check` — registry in sync; every swept asset
  registered.
- `make assets` — passed with the same registry-in-sync result.
- Compared all generated `files (sha256)` lines against `HEAD` — no differences.
- `make check` — passed all validation gates.
- `git diff --check` — passed.
