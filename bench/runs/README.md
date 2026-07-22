# bench/runs/ — append-only registered-run store

Empty until runs are deliberately registered. The permanent record of
benchmark runs is THIS store (plus release/archival deposits), never expiring
CI artifacts (preregistration §8).

- One directory per run: `run-manifest.json` (write-ahead, first),
  `environment.json`, `journal.jsonl`, `result.json` (last, hash-referencing
  everything).
- Append-only: INVALID runs are retained and marked, never deleted or
  rewritten. Replacements reference the run they replace
  (`replaces_run_id`), at most two per replicate slot (preregistration §6).
- Local development smoke runs do NOT belong here — they default to
  `.bench-smoke-runs/` (gitignored). Committing into this directory is a
  deliberate, reviewed act.
