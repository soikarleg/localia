#!/usr/bin/env bash
# backup.sh — Sauvegarde des données Ollama et OpenWebUI
# Usage : ./scripts/backup.sh
# Nécessite : docker, git

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${REPO_ROOT}/openwebui/backup"

echo "=== Backup Localia — ${TIMESTAMP} ==="

# ── 1. Sauvegarde du volume OpenWebUI ──────────────────────────────────────────
OWUI_CONTAINER="$(docker ps -q --filter name=openwebui 2>/dev/null || true)"

if [ -n "${OWUI_CONTAINER}" ]; then
    echo "[1/3] Sauvegarde du volume OpenWebUI..."
    BACKUP_FILE="${BACKUP_DIR}/openwebui_data_${TIMESTAMP}.tar.gz"
    docker exec "${OWUI_CONTAINER}" tar czf - /app/backend/data > "${BACKUP_FILE}"
    echo "      → ${BACKUP_FILE}"
else
    echo "[1/3] Container openwebui introuvable, sauvegarde ignorée."
fi

# ── 2. Sauvegarde des Modelfiles Ollama ────────────────────────────────────────
OLLAMA_CONTAINER="$(docker ps -q --filter name=ollama 2>/dev/null || true)"

if [ -n "${OLLAMA_CONTAINER}" ]; then
    echo "[2/3] Liste des modèles Ollama disponibles :"
    docker exec "${OLLAMA_CONTAINER}" ollama list || true
else
    echo "[2/3] Container ollama introuvable."
fi

# ── 3. Commit git automatique (optionnel) ─────────────────────────────────────
echo "[3/3] Commit git..."
cd "${REPO_ROOT}"
git add openwebui/backup/ openwebui/knowledge/ openwebui/tools/ ollama/ 2>/dev/null || true
if git diff --cached --quiet; then
    echo "      Aucun fichier nouveau à commiter."
else
    git commit -m "backup: sauvegarde automatique ${TIMESTAMP}"
    echo "      Commit effectué."
fi

echo "=== Backup terminé ==="
