#!/usr/bin/env bash
# Verify DCO 1.1 sign-off trailers for every commit in a pull-request range.
# Usage: scripts/check-dco.sh <base-ref> [head-ref]
set -euo pipefail

if [ "${1:-}" = "--self-test" ]; then
  good='Signed-off-by: Example Contributor <contributor@users.noreply.github.com>'
  bad='Signed off by Example Contributor'
  pattern='^Signed-off-by:[[:space:]]+.+[[:space:]]+<[^<>[:space:]@]+@[^<>[:space:]@]+>$'
  printf '%s\n' "$good" | grep -Eiq "$pattern"
  if printf '%s\n' "$bad" | grep -Eiq "$pattern"; then
    echo "dco: self-test accepted an invalid trailer" >&2
    exit 1
  fi
  echo "dco: self-test passed"
  exit 0
fi

base="${1:-}"
head="${2:-HEAD}"
if [ -z "$base" ]; then
  echo "usage: $0 <base-ref> [head-ref]" >&2
  exit 2
fi
git rev-parse --verify "${base}^{commit}" >/dev/null
git rev-parse --verify "${head}^{commit}" >/dev/null

pattern='^Signed-off-by:[[:space:]]+.+[[:space:]]+<[^<>[:space:]@]+@[^<>[:space:]@]+>$'
value_pattern='^.+[[:space:]]+<[^<>[:space:]@]+@[^<>[:space:]@]+>$'
fail=0
count=0
while IFS= read -r commit; do
  [ -n "$commit" ] || continue
  count=$((count + 1))
  author=$(git show -s --format='%an <%ae>' "$commit")
  if [ "$author" = "dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>" ]; then
    echo "dco: commit ${commit:0:12} is the narrowly exempt Dependabot bot"
    continue
  fi
  trailers=$(git show -s --format='%(trailers:key=Signed-off-by,valueonly)' "$commit")
  if ! printf '%s\n' "$trailers" | grep -Eiq "$value_pattern"; then
    echo "dco: commit ${commit:0:12} lacks a syntactically valid Signed-off-by trailer" >&2
    fail=1
  elif ! printf '%s\n' "$trailers" | grep -Fxiq "$author"; then
    echo "dco: commit ${commit:0:12} sign-off does not match author $author" >&2
    fail=1
  fi
done < <(git rev-list --reverse "${base}..${head}")

if [ "$count" -eq 0 ]; then
  echo "dco: no commits found in ${base}..${head}" >&2
  exit 1
fi
if [ "$fail" -ne 0 ]; then
  echo "dco: add the certification with 'git commit -s' and update the pull request" >&2
  exit 1
fi
echo "dco: ${count} commit(s) carry Signed-off-by trailers"
