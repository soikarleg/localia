#!/usr/bin/env bash
set -euo pipefail

# Sync local tools/skills to live mounts used by OpenWebUI, then restart service.

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_DIR="${REPO_ROOT}/docker"

SRC_TOOLS="${REPO_ROOT}/openwebui/tools"
SRC_SKILLS="${REPO_ROOT}/skills"
LIVE_TOOLS="${REPO_ROOT}/openwebui/live/tools"
LIVE_SKILLS="${REPO_ROOT}/openwebui/live/skills"

mkdir -p "${LIVE_TOOLS}" "${LIVE_SKILLS}"

copy_dir() {
  local src="$1"
  local dst="$2"

  if command -v rsync >/dev/null 2>&1; then
    if [ "${DRY_RUN}" -eq 1 ]; then
      rsync -avn --delete --exclude '__pycache__/' --exclude '*.pyc' "${src}/" "${dst}/"
    else
      rsync -a --delete --exclude '__pycache__/' --exclude '*.pyc' "${src}/" "${dst}/"
    fi
  else
    if [ "${DRY_RUN}" -eq 1 ]; then
      echo "[dry-run] rsync indisponible: simulation detaillee non disponible pour ${src} -> ${dst}"
      return
    fi
    rm -rf "${dst:?}"/*
    cp -a "${src}/." "${dst}/"
    rm -rf "${dst}/__pycache__"
    find "${dst}" -name '*.pyc' -delete
  fi
}

echo "[1/4] Sync tools -> live/tools"
copy_dir "${SRC_TOOLS}" "${LIVE_TOOLS}"

echo "[2/4] Sync skills -> live/skills"
copy_dir "${SRC_SKILLS}" "${LIVE_SKILLS}"

if [ "${DRY_RUN}" -eq 1 ]; then
  echo "[3/4] Dry-run: skip reload openwebui"
else
  echo "[3/4] Reload openwebui (compose up -d)"
  cd "${DOCKER_DIR}"
  docker compose up -d >/dev/null
fi

echo "[4/4] Check mounts and sample files"
if [ "${DRY_RUN}" -eq 1 ]; then
  echo "[dry-run] Skip docker checks"
  echo "Planned live mounts:"
  echo "- ${LIVE_TOOLS} -> /app/backend/data/tools"
  echo "- ${LIVE_SKILLS} -> /app/backend/data/skills"
  echo "Done (dry-run)."
  exit 0
fi

docker inspect openwebui --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}' | grep '/openwebui/live/tools -> /app/backend/data/tools\|/openwebui/live/skills -> /app/backend/data/skills' || true

# echo "Tools in container:"
# docker exec openwebui sh -lc 'ls -1 /app/backend/data/tools | head -n 20'

echo "Skills dans le container:"
docker exec openwebui sh -lc 'ls -1 /app/backend/data/skills | head -n 30'

echo "Done."

