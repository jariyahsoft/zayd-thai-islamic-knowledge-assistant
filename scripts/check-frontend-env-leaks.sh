#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEAK_MARKER="${1:-server-secret-test-marker}"

if rg --hidden --glob '.next/**' --fixed-strings --quiet "${LEAK_MARKER}" "${ROOT_DIR}/apps"; then
  echo "Found leaked server secret marker in frontend build output"
  exit 1
fi

echo "No frontend server-secret marker found in build output"
