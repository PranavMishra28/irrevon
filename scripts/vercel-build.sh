#!/usr/bin/env bash
# Vercel Git build contract: production website builds come only from main.
set -euo pipefail

repository_root=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repository_root"

node_major=$(node -p "process.versions.node.split('.')[0]")
if [ "$node_major" != "24" ]; then
  echo "vercel-build: Node 24.x is required, found $(node --version)" >&2
  exit 1
fi

if [ "${VERCEL:-}" = "1" ]; then
  if [ "${VERCEL_ENV:-}" != "production" ]; then
    echo "vercel-build: automatic builds require VERCEL_ENV=production" >&2
    exit 1
  fi
  if [ "${VERCEL_GIT_COMMIT_REF:-}" != "main" ]; then
    echo "vercel-build: automatic builds require VERCEL_GIT_COMMIT_REF=main" >&2
    exit 1
  fi
  if [[ ! "${VERCEL_GIT_COMMIT_SHA:-}" =~ ^[0-9a-f]{40}$ ]]; then
    echo "vercel-build: automatic builds require a full VERCEL_GIT_COMMIT_SHA" >&2
    exit 1
  fi
fi

pnpm --dir site build
