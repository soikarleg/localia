#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_DIR="${REPO_ROOT}/openwebui/knowledge/legacy_uploads"
SOURCE_VOLUME="${1:-openwebui_data}"

mkdir -p "${TARGET_DIR}"

echo "Import depuis volume Docker: ${SOURCE_VOLUME}"

docker run --rm \
  -v "${SOURCE_VOLUME}:/from" \
  -v "${TARGET_DIR}:/to" \
  alpine sh -lc '
    set -e
    copied=0
    if [ -d /from/uploads ]; then
      for f in /from/uploads/*; do
        if [ -f "$f" ]; then
          cp "$f" "/to/$(basename "$f")"
          copied=$((copied+1))
        fi
      done
    fi
    echo "copied:${copied}"
  '

if ! chown -R "$(id -u)":"$(id -g)" "${TARGET_DIR}" 2>/dev/null; then
  echo "WARN: chown non autorise sur ${TARGET_DIR} (copie effectuee)."
fi

echo "Fichiers disponibles dans ${TARGET_DIR}:"
ls -la "${TARGET_DIR}"
