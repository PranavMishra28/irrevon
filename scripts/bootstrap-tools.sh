#!/bin/bash
# Exact-version, checksum-verified install of Irrevon's validation tools.
# This is the ONE pin table — consumed by `make tools-pinned`, every CI job, and
# cloud-agent environments (.cursor/environment.json). Update pins deliberately and
# in one commit together with the Makefile header and any CI references.
#
# Versions + SHA-256 pins resolved from official release assets on 2026-07-21.
# zizmor upstream publishes no checksum manifest; its hashes were computed from the
# release tarballs fetched over TLS on the same date — re-verify on every bump.
#
# Idempotent: a tool already present at the pinned version is skipped, so re-runs
# (cloud-agent install snapshots, repeated CI steps) converge without side effects.
#
# Supported platforms: Linux x86_64 (CI runners, cloud agents) and macOS arm64
# (dev machine). Installs binaries to BIN_DIR (default: ~/.local/bin).
set -euo pipefail

LYCHEE_VERSION="0.24.2"
GITLEAKS_VERSION="8.30.1"
ACTIONLINT_VERSION="1.7.12"
ZIZMOR_VERSION="1.27.0"
CHECK_JSONSCHEMA_VERSION="0.37.4"

case "$(uname -s)-$(uname -m)" in
  Linux-x86_64)
    LYCHEE_ASSET="lychee-x86_64-unknown-linux-gnu.tar.gz"
    LYCHEE_SHA256="1f4e0ef7f6554a6ed33dd7ac144fb2e1bbed98598e7af973042fc5cd43951c9a"
    LYCHEE_MEMBER="lychee-x86_64-unknown-linux-gnu/lychee"  # lychee tarballs nest the binary
    GITLEAKS_ASSET="gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"
    GITLEAKS_SHA256="551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"
    ACTIONLINT_ASSET="actionlint_${ACTIONLINT_VERSION}_linux_amd64.tar.gz"
    ACTIONLINT_SHA256="8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8"
    ZIZMOR_ASSET="zizmor-x86_64-unknown-linux-gnu.tar.gz"
    ZIZMOR_SHA256="277f2bd8fd37cf60c42ab7afca6faa884e65440fa31e02b44bdaae60f62a358f"
    ;;
  Darwin-arm64)
    LYCHEE_ASSET="lychee-aarch64-apple-darwin.tar.gz"
    LYCHEE_SHA256="c9d3740ea2d891854d37116c9fba840f37b6e7c89d330e7db84ac333631c4977"
    LYCHEE_MEMBER="lychee-aarch64-apple-darwin/lychee"  # lychee tarballs nest the binary
    GITLEAKS_ASSET="gitleaks_${GITLEAKS_VERSION}_darwin_arm64.tar.gz"
    GITLEAKS_SHA256="b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5"
    ACTIONLINT_ASSET="actionlint_${ACTIONLINT_VERSION}_darwin_arm64.tar.gz"
    ACTIONLINT_SHA256="aba9ced2dee8d27fecca3dc7feb1a7f9a52caefa1eb46f3271ea66b6e0e6953f"
    ZIZMOR_ASSET="zizmor-aarch64-apple-darwin.tar.gz"
    ZIZMOR_SHA256="81336423d1b280c5dd0cdd8644a1e5f3238ab3ceb8d6e4334dfd05dab95a8a86"
    ;;
  *)
    echo "bootstrap-tools: unsupported platform $(uname -s)-$(uname -m)" >&2
    echo "bootstrap-tools: supported: Linux-x86_64, Darwin-arm64 (extend the pin table)" >&2
    exit 1
    ;;
esac

BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
mkdir -p "$BIN_DIR"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

sha256_verify() { # <file> <expected>
  if command -v sha256sum >/dev/null 2>&1; then
    echo "$2  $1" | sha256sum -c - >/dev/null
  else
    echo "$2  $1" | shasum -a 256 -c - >/dev/null
  fi
}

have_version() { # <tool> <version substring>
  command -v "$1" >/dev/null 2>&1 && "$1" --version 2>/dev/null | head -n 1 | grep -qF "$2"
}

install_binary() { # <tool> <version> <url> <sha256> <member-path-in-archive>
  local tool="$1" version="$2" url="$3" sha="$4" member="$5"
  if have_version "$tool" "$version"; then
    echo "bootstrap-tools: $tool $version already present - skipped"
    return 0
  fi
  echo "bootstrap-tools: installing $tool $version"
  curl -sSfL --retry 3 -o "$WORK_DIR/$tool.tar.gz" "$url"
  ( cd "$WORK_DIR" && sha256_verify "$tool.tar.gz" "$sha" )
  tar -xzf "$WORK_DIR/$tool.tar.gz" -C "$WORK_DIR" "$member"
  install -m 0755 "$WORK_DIR/$member" "$BIN_DIR/$tool"
}

install_binary lychee "$LYCHEE_VERSION" \
  "https://github.com/lycheeverse/lychee/releases/download/lychee-v${LYCHEE_VERSION}/${LYCHEE_ASSET}" \
  "$LYCHEE_SHA256" "$LYCHEE_MEMBER"

# gitleaks prints its version bare (`gitleaks version` -> "8.30.1"), so check explicitly.
if command -v gitleaks >/dev/null 2>&1 && gitleaks version 2>/dev/null | grep -qF "$GITLEAKS_VERSION"; then
  echo "bootstrap-tools: gitleaks $GITLEAKS_VERSION already present - skipped"
else
  echo "bootstrap-tools: installing gitleaks $GITLEAKS_VERSION"
  curl -sSfL --retry 3 -o "$WORK_DIR/gitleaks.tar.gz" \
    "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/${GITLEAKS_ASSET}"
  ( cd "$WORK_DIR" && sha256_verify "gitleaks.tar.gz" "$GITLEAKS_SHA256" )
  tar -xzf "$WORK_DIR/gitleaks.tar.gz" -C "$WORK_DIR" gitleaks
  install -m 0755 "$WORK_DIR/gitleaks" "$BIN_DIR/gitleaks"
fi

install_binary actionlint "$ACTIONLINT_VERSION" \
  "https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/${ACTIONLINT_ASSET}" \
  "$ACTIONLINT_SHA256" actionlint

install_binary zizmor "$ZIZMOR_VERSION" \
  "https://github.com/zizmorcore/zizmor/releases/download/v${ZIZMOR_VERSION}/${ZIZMOR_ASSET}" \
  "$ZIZMOR_SHA256" zizmor

# check-jsonschema is a Python CLI: version-pinned (not hash-pinned) install, acceptable
# for a linter that only consumes repo files (see the CI design notes in docs/ci.md).
if have_version check-jsonschema "$CHECK_JSONSCHEMA_VERSION"; then
  echo "bootstrap-tools: check-jsonschema $CHECK_JSONSCHEMA_VERSION already present - skipped"
elif command -v pipx >/dev/null 2>&1; then
  pipx install --force "check-jsonschema==${CHECK_JSONSCHEMA_VERSION}" >/dev/null
  echo "bootstrap-tools: check-jsonschema ${CHECK_JSONSCHEMA_VERSION} installed via pipx"
elif command -v uv >/dev/null 2>&1; then
  uv tool install --force "check-jsonschema==${CHECK_JSONSCHEMA_VERSION}" >/dev/null
  echo "bootstrap-tools: check-jsonschema ${CHECK_JSONSCHEMA_VERSION} installed via uv tool"
else
  python3 -m pip install --user --quiet "check-jsonschema==${CHECK_JSONSCHEMA_VERSION}"
  echo "bootstrap-tools: check-jsonschema ${CHECK_JSONSCHEMA_VERSION} installed via pip --user"
fi

# Make the install visible to later CI steps without shell-profile edits.
if [ -n "${GITHUB_PATH:-}" ]; then
  echo "$BIN_DIR" >> "$GITHUB_PATH"
fi

echo "bootstrap-tools: done (BIN_DIR=$BIN_DIR)"
