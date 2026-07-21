#!/bin/bash
# Frozen/append-only diff gate (run via `make frozen`).
#
# Two modes:
#   CI:    BASE_REF=<ref> (the PR base, e.g. origin/main) - checks merge-base..HEAD,
#          so a PR cannot merge changes that violate the freeze rules.
#   Local: no BASE_REF - checks the STAGED diff (what the next commit would contain);
#          uncommitted/unstaged exploration is never blocked.
#
# Rules (design: append-only and frozen artifacts per AGENTS.md):
#   1. docs/master-doc.md may change only together with scripts/master-doc.sha256
#      (the human amendment re-pin path). The hash pin in check-integrity.sh stays
#      the primary, state-based control; this adds per-diff precision.
#   2. docs/review-queue.md is append-only: any deleted line fails — EXCEPT in a
#      human ratification integration, where the same range must carry the rule-1
#      amendment re-pin (docs/master-doc.md + scripts/master-doc.sha256 together)
#      AND the queue's added lines must record the ratifying amendment
#      (an added line carrying both an AM-<n> id and RATIFIED). Resolution stays
#      human-only: the re-pin is the in-diff act only a ratifying human performs.
#   3. Accepted ADRs are append-only: the only sanctioned edit is the status: line
#      (supersession). Acceptance is read from the BASE version, so flipping the
#      status in the same diff cannot unlock the file.
#   4. docs/benchmark-preregistration.md: no diff hunk may touch a section whose
#      heading carries the FROZEN marker. Section ranges come from the BASE version,
#      so moving the marker cannot unfreeze content retroactively.
#
# Needs only git + awk/grep/sed. State-based checks live in check-integrity.sh;
# this script is deliberately ref-relative (see docs/ci.md).
set -u
cd "$(dirname "$0")/.." || exit 1
fail=0

if [ -n "${BASE_REF:-}" ]; then
  MODE="range"
  BASE=$(git merge-base "$BASE_REF" HEAD) || {
    echo "frozen: FAIL - cannot resolve merge-base of BASE_REF=$BASE_REF and HEAD"
    echo "frozen: (in CI, checkout with fetch-depth: 0 so the base ref exists)"
    exit 1
  }
  diff_names()   { git diff --name-only "$BASE" HEAD; }
  diff_numstat() { git diff --numstat "$BASE" HEAD -- "$1"; }
  diff_hunks()   { git diff -U0 "$BASE" HEAD -- "$1"; }
  show_base()    { git show "$BASE:$1" 2>/dev/null; }
  show_current() { git show "HEAD:$1" 2>/dev/null; }
else
  MODE="staged"
  BASE="HEAD"
  diff_names()   { git diff --cached --name-only; }
  diff_numstat() { git diff --cached --numstat -- "$1"; }
  diff_hunks()   { git diff --cached -U0 -- "$1"; }
  show_base()    { git show "HEAD:$1" 2>/dev/null; }
  show_current() { git show ":$1" 2>/dev/null; }
fi

changed=$(diff_names)
if [ -z "$changed" ]; then
  echo "frozen: no ${MODE} changes - nothing to check"
  exit 0
fi

# -- Rule 1: master doc changes require the re-pinned hash in the same range -----
if printf '%s\n' "$changed" | grep -qx 'docs/master-doc.md'; then
  if printf '%s\n' "$changed" | grep -qx 'scripts/master-doc.sha256'; then
    echo "frozen: master-doc changed together with its hash pin (amendment path) - OK"
  else
    echo "frozen: FAIL - docs/master-doc.md changed without scripts/master-doc.sha256"
    echo "  The master doc is amended only by a human-ratified review-queue item that re-pins the hash."
    fail=1
  fi
fi

# -- Rule 2: review queue is append-only (ratification-integration exception) -----
if printf '%s\n' "$changed" | grep -qx 'docs/review-queue.md'; then
  deletions=$(diff_numstat docs/review-queue.md | awk '{print $2}')
  if [ -n "$deletions" ] && [ "$deletions" != "0" ] && [ "$deletions" != "-" ]; then
    # Exception: a human ratification integration may restructure the queue to
    # record ratification outcomes. Evidence required IN THE SAME RANGE:
    #   (a) the amendment re-pin — master doc AND its hash pin both changed
    #       (rule 1's amendment path; re-pinning is a human-only act), and
    #   (b) the queue's ADDED lines record the ratifying amendment: at least one
    #       added line carries an AM-<n> id together with the word RATIFIED.
    # Deletions without both pieces of evidence still fail.
    repin=0
    if printf '%s\n' "$changed" | grep -qx 'docs/master-doc.md' \
       && printf '%s\n' "$changed" | grep -qx 'scripts/master-doc.sha256'; then
      repin=1
    fi
    ratified=0
    if diff_hunks docs/review-queue.md | grep -E '^[+][^+]' \
         | grep -E 'AM-[0-9]+' | grep -q 'RATIFIED'; then
      ratified=1
    fi
    if [ "$repin" -eq 1 ] && [ "$ratified" -eq 1 ]; then
      echo "frozen: review-queue has $deletions deletion(s) WITH the amendment re-pin and a recorded RATIFIED AM-<n> - OK (ratification integration)"
    else
      echo "frozen: FAIL - docs/review-queue.md has $deletions deleted line(s); it is append-only"
      echo "  Deletions are allowed only in a human ratification integration: the same range"
      echo "  must re-pin the master doc (docs/master-doc.md + scripts/master-doc.sha256) AND"
      echo "  the queue's added lines must record the ratifying amendment (AM-<n> ... RATIFIED)."
      fail=1
    fi
  else
    echo "frozen: review-queue append-only OK"
  fi
fi

# -- Rule 3: accepted ADRs allow only status-line edits ---------------------------
while IFS= read -r f; do
  case "$f" in docs/decisions/[0-9][0-9][0-9][0-9]-*.md) ;; *) continue ;; esac
  base_content=$(show_base "$f") || continue   # new ADR file: not frozen
  [ -z "$base_content" ] && continue
  base_status=$(printf '%s\n' "$base_content" | sed -n 's/^status:[[:space:]]*//p' | sed -n 1p)
  case "$base_status" in
    accepted*|Accepted*|ACCEPTED*) ;;
    *) continue ;;                             # open/proposed ADRs are normal edits
  esac
  cur_content=$(show_current "$f")
  if [ -z "$cur_content" ]; then
    echo "frozen: FAIL - accepted ADR $f was deleted; accepted ADRs are append-only"
    fail=1
    continue
  fi
  if diff <(printf '%s\n' "$base_content" | grep -v '^status:') \
          <(printf '%s\n' "$cur_content"  | grep -v '^status:') >/dev/null; then
    echo "frozen: accepted ADR $f - only status line changed - OK"
  else
    echo "frozen: FAIL - accepted ADR $f modified beyond its status: line"
    echo "  Supersede with a new ADR instead; decision text is append-only."
    fail=1
  fi
done <<< "$changed"

# -- Rule 4: preregistration FROZEN sections are untouchable ----------------------
PREREG="docs/benchmark-preregistration.md"
if printf '%s\n' "$changed" | grep -qx "$PREREG"; then
  base_prereg=$(show_base "$PREREG")
  if [ -n "$base_prereg" ]; then
    # FROZEN section line ranges, computed from the BASE version: a section spans
    # from its heading to the next heading of the same or higher level (or EOF).
    frozen_ranges=$(printf '%s\n' "$base_prereg" | awk '
      /^#/ {
        match($0, /^#+/)
        level = RLENGTH
        if (substr($0, level + 1, 1) != " ") next
        if (open && level <= open_level) { print open_start "-" (NR - 1); open = 0 }
        if (!open && index($0, "FROZEN") > 0) { open = 1; open_level = level; open_start = NR }
      }
      END { if (open) print open_start "-" NR }')
    if [ -n "$frozen_ranges" ]; then
      # Old-file line ranges touched by the diff, from -U0 hunk headers.
      hunks=$(diff_hunks "$PREREG" | sed -n 's/^@@ -\([0-9]*\)\(,\([0-9]*\)\)\{0,1\} .*/\1 \3/p')
      while IFS= read -r range; do
        s=${range%-*}; e=${range#*-}
        while IFS=' ' read -r a b; do
          [ -z "$a" ] && continue
          [ -z "$b" ] && b=1
          [ "$b" = "0" ] && b=1   # pure insertion: treat the anchor line as touched
          h_end=$((a + b - 1))
          if [ "$a" -le "$e" ] && [ "$h_end" -ge "$s" ]; then
            echo "frozen: FAIL - $PREREG diff touches FROZEN section (base lines $s-$e)"
            echo "  FROZEN sections change only via numbered amendments per the document's section 0."
            fail=1
          fi
        done <<< "$hunks"
      done <<< "$frozen_ranges"
      [ "$fail" -eq 0 ] && echo "frozen: preregistration diff avoids all FROZEN sections - OK"
    else
      echo "frozen: preregistration has no FROZEN sections at base - OK"
    fi
  fi
fi

[ "$fail" -eq 0 ] && echo "frozen: all checks passed (${MODE} mode)"
exit "$fail"
