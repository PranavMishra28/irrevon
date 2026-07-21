#!/bin/bash
# Repository integrity checks (run via `make integrity`):
#   1. docs/master-doc.md matches the pinned sha256 (byte-identity guard)
#   2. ADR ids are unique (no duplicate NNNN prefixes; frontmatter id matches filename)
#   3. .cursor JSON configs are syntactically valid
#   4. Optional tripword scan: if an untracked .tripwords file exists (one term per line),
#      no term may appear (case-insensitive) in any repo file outside .scratch/.
#      The tripword list itself is never committed (see .gitignore).
set -u
cd "$(dirname "$0")/.." || exit 1
fail=0

# ── 1. master-doc hash pin ────────────────────────────────────────────────────
pinned=$(tr -d '[:space:]' < scripts/master-doc.sha256)
actual=$(shasum -a 256 docs/master-doc.md | awk '{print $1}')
if [ "$pinned" = "$actual" ]; then
  echo "integrity: master-doc hash OK"
else
  echo "integrity: FAIL - docs/master-doc.md does not match pinned hash"
  echo "  pinned: $pinned"
  echo "  actual: $actual"
  echo "  The master doc is byte-identical by policy; only a ratified amendment re-pins it."
  fail=1
fi

# ── 2. ADR id uniqueness + frontmatter consistency ────────────────────────────
ids=$(find docs/decisions -name '[0-9][0-9][0-9][0-9]-*.md' -exec basename {} \; | cut -c1-4 | sort)
dupes=$(printf '%s\n' "$ids" | uniq -d)
if [ -n "$dupes" ]; then
  echo "integrity: FAIL - duplicate ADR ids: $dupes"
  fail=1
else
  echo "integrity: ADR ids unique"
fi
while IFS= read -r f; do
  fname_id=$(basename "$f" | cut -c1-4)
  fm_id=$(sed -n 's/^id:[[:space:]]*ADR-\([0-9]\{4\}\).*/\1/p' "$f" | sed -n 1p)
  if [ "$fname_id" != "$fm_id" ]; then
    echo "integrity: FAIL - $f frontmatter id (ADR-$fm_id) != filename id ($fname_id)"
    fail=1
  fi
done < <(find docs/decisions -name '[0-9][0-9][0-9][0-9]-*.md')

# ── 3. .cursor JSON syntax ────────────────────────────────────────────────────
for j in .cursor/cli.json .cursor/hooks.json; do
  if [ -f "$j" ]; then
    if jq empty "$j" 2>/dev/null; then
      echo "integrity: $j syntax OK"
    else
      echo "integrity: FAIL - $j is not valid JSON"
      fail=1
    fi
  fi
done

# ── 4. Optional tripword scan (untracked local list) ──────────────────────────
if [ -f .tripwords ]; then
  hits=0
  while IFS= read -r word; do
    [ -z "$word" ] && continue
    if grep -riIl --exclude-dir=.scratch --exclude-dir=.git --exclude=.tripwords -e "$word" . >/dev/null 2>&1; then
      echo "integrity: FAIL - tripword found in repo files (term withheld; see local .tripwords)"
      grep -riIl --exclude-dir=.scratch --exclude-dir=.git --exclude=.tripwords -e "$word" . | sed 's/^/  /'
      hits=1
    fi
  done < .tripwords
  [ "$hits" -eq 1 ] && fail=1 || echo "integrity: tripword scan clean"
else
  echo "integrity: no local .tripwords file - tripword scan skipped"
fi

[ "$fail" -eq 0 ] && echo "integrity: all checks passed"
exit "$fail"
