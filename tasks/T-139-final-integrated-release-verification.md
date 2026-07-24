# T-139: Final integrated repository-local release verification

---
id: T-139
status: done
depends_on: [T-126, T-127, T-128, T-129, T-130, T-131, T-132, T-133, T-134, T-135, T-136, T-137, T-138]
invariant: "verification is nonpublishing, repository-local, secret-safe, and may not weaken or edit implementation"
---

## Objective

Run the complete nonpublishing validation ladder over the integrated launch
diff using Node 24 exactly, and record reproducible pass/failure evidence plus
any exact repository-local blockers.

## Scope

**Allowed to write:** this task file and ignored build, test, audit, and scratch
outputs created by the existing repository validation commands.

**Forbidden:** implementation or documentation edits outside this task;
weakening any test, benchmark, audit, or validation gate; publishing;
deployment; provider calls; repository-setting changes; secrets or sensitive
values in output; history rewriting; and commits.

## Required verification

- [x] Confirm Node major version 24 for all Node-based commands.
- [x] `make check` and `python3 scripts/check-public-truth.py`.
- [x] `make check-all`, including PostgreSQL integration, crash/process, and
      benchmark gates reached by the target.
- [x] `make web-vrt`.
- [x] `make site-check site-build site-test site-vrt`.
- [x] Production site build and smoke with explicit current `HEAD` and
      `https://irrevon.vercel.app`.
- [x] `make dist-smoke`.
- [x] `IRREVON_ALLOW_RELEASE_VERSION=1 make release-dry-run`.
- [x] `IRREVON_ALLOW_RELEASE_VERSION=1 make launch-audit`.
- [x] `actionlint` across every workflow.
- [x] `zizmor` pedantic offline.
- [x] `gitleaks` over reachable history plus current/generated/artifact
      surfaces.
- [x] Public-data scan including generated outputs.
- [x] Locked Python production dependency audit using the release-validation
      `pip-audit` and a hash-bearing frozen export.
- [x] Web and site production dependency audits.
- [x] Exact archive/checksum inspection.
- [x] Generated-content drift checks and `git diff --check`.

## Execution notes

- Use current repository `HEAD` as the explicit production-build provenance
  value; do not infer a deployed commit.
- Run only existing local targets/scripts or read-only inspection commands.
- Redact or avoid output that could contain secrets.
- If a command fails, preserve the exact command, exit result, and concise
  non-sensitive failure cause; do not patch around it.

## Definition of done

Every repository-local gate above has passed under Node 24 and this task is set
to `done`, or the task remains incomplete with precise blockers recorded. No
external mutation, publication, deployment, implementation edit, or commit is
performed.

## Completion evidence

- Node `24.18.0` was used for the integrated Node-based ladder.
- `make check` and the standalone public-truth gate passed.
- The final integrated `make check-all` passed after all local corrections and
  task evidence: 539 nonintegration Python tests, 258 PostgreSQL
  integration/crash/process tests, Workbench suites of 92, 80, and 133 tests,
  and the benchmark smoke gate all passed.
- Workbench container VRT passed all 98 comparisons.
- The marketing-site ladder passed 388 checks and 697 screenshot cases.
- The production site artifact build/smoke passed against the exact current
  `HEAD` and canonical origin `https://irrevon.vercel.app`.
- `make dist-smoke` passed after the migration-authority correction, and the
  nonpublishing release dry run completed with valid distributions, strict
  rendering, SPDX SBOM, and checksums.
- The complete nonpublishing launch audit reached `completed` after the VRT
  dependency-isolation correction, with 539 nonintegration and 258 integration
  Python tests in that post-fix run.
- `actionlint`, offline pedantic `zizmor`, reachable-history/current/generated/
  artifact `gitleaks`, include-generated public-data scanning, locked
  hash-bearing Python `pip-audit`, web/site production dependency audits,
  archive/checksum inspection, generated drift checks, and `git diff --check`
  all passed.
- The public-data result covers defined patterns and allowlisted reachable
  history; it is explicitly not an exhaustive historical-PII audit.
- No external service or repository setting was mutated; nothing was
  published, deployed, committed, tagged, signed, or uploaded.
