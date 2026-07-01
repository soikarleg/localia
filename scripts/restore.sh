#!/usr/bin/env bash
# restore.sh — Restauration des données OpenWebUI depuis une sauvegarde
# Usage : ./scripts/restore.sh <fichier_backup.tar.gz>
# Nécessite : docker

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BACKUP_FILE="${1:-}"

if [ -z "${BACKUP_FILE}" ]; then
    echo "Usage : $0 <fichier_backup.tar.gz>"
    echo ""
    echo "Sauvegardes disponibles :"
    ls -lh "${REPO_ROOT}/openwebui/backup/"*.tar.gz 2>/dev/null || echo "  (aucune)"
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Erreur : fichier introuvable : ${BACKUP_FILE}"
    exit 1
fi

OWUI_CONTAINER="$(docker ps -q --filter name=openwebui 2>/dev/null || true)"

if [ -z "${OWUI_CONTAINER}" ]; then
    echo "Erreur : container openwebui non trouvé. Démarrez-le d'abord avec :"
    echo "  cd docker && docker compose up -d"
    exit 1
fi

echo "=== Restauration depuis : ${BACKUP_FILE} ==="
echo "ATTENTION : cette opération va écraser les données actuelles d'OpenWebUI."
read -r -p "Confirmer ? (oui/non) : " CONFIRM
if [ "${CONFIRM}" != "oui" ]; then
    echo "Annulé."
    exit 0
fi

echo "[1/3] Arrêt du container OpenWebUI..."
docker stop "${OWUI_CONTAINER}"

echo "[2/3] Restauration des données..."
docker run --rm \
    --volumes-from "${OWUI_CONTAINER}" \
    -v "$(realpath "${BACKUP_FILE}"):/backup.tar.gz:ro" \
    busybox \
    sh -c "cd / && tar xzf /backup.tar.gz"

echo "[3/3] Redémarrage du container OpenWebUI..."
docker start "${OWUI_CONTAINER}"

echo "=== Restauration terminée. Vérifiez l'interface OpenWebUI. ==="
