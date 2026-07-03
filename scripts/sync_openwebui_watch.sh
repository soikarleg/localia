#!/usr/bin/env bash
set -euo pipefail

# Watch local sources and auto-sync to OpenWebUI live mounts.
# Sources watched:
# - openwebui/tools
# - skills
#
# Usage:
#   ./scripts/sync_openwebui_watch.sh
#   ./scripts/sync_openwebui_watch.sh --interval 2
#   ./scripts/sync_openwebui_watch.sh --no-initial-sync

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SYNC_SCRIPT="${REPO_ROOT}/scripts/sync_openwebui.sh"
SRC_TOOLS="${REPO_ROOT}/openwebui/tools"
SRC_SKILLS="${REPO_ROOT}/skills"

POLL_INTERVAL=2
INITIAL_SYNC=1

while [ $# -gt 0 ]; do
  case "$1" in
    --interval)
      POLL_INTERVAL="${2:-2}"
      shift 2
      ;;
    --no-initial-sync)
      INITIAL_SYNC=0
      shift
      ;;
    -h|--help)
      sed -n '1,22p' "$0"
      exit 0
      ;;
    *)
      echo "Argument inconnu: $1"
      exit 1
      ;;
  esac
done

if [ ! -x "${SYNC_SCRIPT}" ]; then
  echo "ERROR: script introuvable ou non executable: ${SYNC_SCRIPT}"
  exit 1
fi

for d in "${SRC_TOOLS}" "${SRC_SKILLS}"; do
  if [ ! -d "${d}" ]; then
    echo "ERROR: dossier source introuvable: ${d}"
    exit 1
  fi
done

snapshot_state() {
  {
    find "${SRC_TOOLS}" "${SRC_SKILLS}" -type f \
      ! -path '*/__pycache__/*' \
      ! -name '*.pyc' \
      -printf '%p|%T@|%s\n' 2>/dev/null | LC_ALL=C sort
  } | sha256sum | awk '{print $1}'
}

run_sync() {
  echo "[sync] $(date '+%F %T') changement detecte -> sync_openwebui.sh"
  "${SYNC_SCRIPT}" || echo "WARN: sync_openwebui.sh a retourne une erreur"
}

cleanup() {
  echo
  echo "Arret du watch auto-sync."
}
trap cleanup INT TERM

echo "Auto-sync watch actif."
echo "- Sources: ${SRC_TOOLS} ; ${SRC_SKILLS}"
echo "- Mode: $(command -v inotifywait >/dev/null 2>&1 && echo inotify || echo polling ${POLL_INTERVAL}s)"

if [ "${INITIAL_SYNC}" -eq 1 ]; then
  echo "[init] sync initiale"
  "${SYNC_SCRIPT}"
fi

if command -v inotifywait >/dev/null 2>&1; then
  inotifywait -m -r \
    -e close_write,create,delete,move \
    --format '%w%f' \
    "${SRC_TOOLS}" "${SRC_SKILLS}" | while IFS= read -r changed; do
      case "${changed}" in
        *"/__pycache__/"*|*.pyc)
          continue
          ;;
      esac
      run_sync
    done
else
  last_state="$(snapshot_state)"
  while true; do
    sleep "${POLL_INTERVAL}"
    new_state="$(snapshot_state)"
    if [ "${new_state}" != "${last_state}" ]; then
      last_state="${new_state}"
      run_sync
    fi
  done
fi
