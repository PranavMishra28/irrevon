# Release process and artifact verification

Irrevon has not been published. This guide prepares a future human-approved
`0.1.0` release; running the dry run never creates a tag, release, attestation,
deployment, or package-index upload.

## Local dry run

```bash
make dist-smoke
IRREVON_ALLOW_RELEASE_VERSION=1 make release-dry-run
```

The process builds the Workbench before the wheel/sdist, enforces exact archive
contents, writes `dist/SHA256SUMS`, and creates a deterministic SPDX 2.3 JSON
SBOM. The Workbench build refuses every Node major except the repository's
declared Node 24 line. Twine 6.2.0, `check-jsonschema`, PyPA `pip-audit`
2.10.1, and SPDX Tools are exact-constrained in the `release-validation`
dependency group and resolved transitively by `uv.lock`; the workflow invokes
that group through `uv run --locked`. The launch audit checks a hash-bearing
frozen export of only the production dependency graph without dependency
resolution. Twine's strict PyPI long-description check fails on every warning,
and the dry run requires identical wheel/sdist hashes before and after Twine
before rechecking the archive manifests. `dist-smoke` installs both artifacts
in clean Python containers and runs the packaged CLI, schemas, migrations, and
Workbench.

The explicit environment flag permits validation of the final `0.1.0` version.
It does not enable a publishing command: the dry-run script has no upload,
release, tag, signing, or deployment path.

## Human one-time setup

Before the first release, the repository owner must:

1. register a **pending Trusted Publisher** for the not-yet-created PyPI
   `irrevon` project, bound to this repository,
   `.github/workflows/release.yml`, and the `release` environment; the first
   trusted publication creates the project, and the pending publisher does not
   reserve the name beforehand;
2. protect that environment with a required reviewer;
3. enable immutable GitHub releases and the repository security settings in
   [docs/ci.md](ci.md);
4. complete external clearance, provider, scientific, and release gates in
   [docs/execution-plan.md](execution-plan.md);
5. review the prepared `0.1.0` package metadata, changelog, and citation file,
   then merge a green release PR.

No PyPI API token or long-lived signing key is used.

## Release execution

The owner creates and pushes an annotated `v0.1.0` tag from the reviewed
default-branch commit. Only an annotated, version-shaped tag whose peeled
commit, checked-out `HEAD`, and current `origin/main` are identical can enter
the publish job; an older commit that is merely reachable from `main` is
refused. The workflow verifies a clean checkout, exact tag/package equality,
the full launch gate, archive contents and renderer hash invariance, clean
installs, strict PyPI README rendering, checksums, SBOM, and GitHub artifact
attestations. The protected `release` environment is the final human approval
boundary.

The workflow refuses untagged refs, forks, version mismatches, dirty trees, and
failed validation. Pull requests and manual dispatches run only the
non-publishing dry-run job.

## User verification

Download release artifacts and `SHA256SUMS` from the same GitHub release:

```bash
sha256sum --check SHA256SUMS
gh attestation verify irrevon-0.1.0-py3-none-any.whl \
  --repo PranavMishra28/irrevon
gh attestation verify irrevon-0.1.0.tar.gz \
  --repo PranavMishra28/irrevon
```

Inspect the SBOM before installation:

```bash
python -m json.tool irrevon.spdx.json >/dev/null
```

Install into a clean environment and verify the reported version:

```bash
python -m venv verify-env
verify-env/bin/pip install ./irrevon-0.1.0-py3-none-any.whl
verify-env/bin/irrevon --version
```

GitHub artifact attestations provide cryptographically signed provenance in the
public Sigstore transparency log. This is distinct from claiming that the Git
tag itself has a cryptographic signature: the required tag is annotated, while
the release artifacts are attested. The project will describe the achieved SLSA
posture only after a real release produces verifiable provenance; this
preparation alone does not claim a SLSA level.
