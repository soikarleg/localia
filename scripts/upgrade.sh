#!/usr/bin/env bash
# upgrade.sh — Mise à jour contrôlée d'OpenWebUI (et Ollama)
# Usage : ./scripts/upgrade.sh [--openwebui <tag>] [--ollama <tag>]
# Exemple : ./scripts/upgrade.sh --openwebui 0.10.7
# Nécessite : docker, sed ou perl

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_DIR="${REPO_ROOT}/docker"
ENV_FILE="${COMPOSE_DIR}/.env"

NEW_OWUI_TAG=""
NEW_OLLAMA_TAG=""

# ── Parsing des arguments ──────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --openwebui) NEW_OWUI_TAG="$2"; shift 2 ;;
        --ollama)    NEW_OLLAMA_TAG="$2"; shift 2 ;;
        *) echo "Option inconnue : $1"; exit 1 ;;
    esac
done

if [ -z "${NEW_OWUI_TAG}" ] && [ -z "${NEW_OLLAMA_TAG}" ]; then
    echo "Usage : $0 [--openwebui <tag>] [--ollama <tag>]"
    exit 1
fi

# ── Vérification du fichier .env ──────────────────────────────────────────────
if [ ! -f "${ENV_FILE}" ]; then
    echo "Erreur : ${ENV_FILE} introuvable. Copiez .env.example en .env."
    exit 1
fi

echo "=== Mise à jour contrôlée ==="

# ── Étape 1 : Sauvegarde préalable ────────────────────────────────────────────
echo "[1/4] Sauvegarde préalable..."
"${SCRIPT_DIR}/backup.sh"

# ── Étape 2 : Mise à jour du fichier .env ─────────────────────────────────────
echo "[2/4] Mise à jour des tags dans .env..."

if [ -n "${NEW_OWUI_TAG}" ]; then
    # Portable sed -i : fonctionne sur Linux et macOS
    sed -i.bak "s/^OPENWEBUI_IMAGE_TAG=.*/OPENWEBUI_IMAGE_TAG=${NEW_OWUI_TAG}/" "${ENV_FILE}" && rm -f "${ENV_FILE}.bak"
    echo "      OPENWEBUI_IMAGE_TAG → ${NEW_OWUI_TAG}"
fi

if [ -n "${NEW_OLLAMA_TAG}" ]; then
    sed -i.bak "s/^OLLAMA_IMAGE_TAG=.*/OLLAMA_IMAGE_TAG=${NEW_OLLAMA_TAG}/" "${ENV_FILE}" && rm -f "${ENV_FILE}.bak"
    echo "      OLLAMA_IMAGE_TAG → ${NEW_OLLAMA_TAG}"
fi

# ── Étape 3 : Pull des nouvelles images ───────────────────────────────────────
echo "[3/4] Téléchargement des nouvelles images..."
cd "${COMPOSE_DIR}"
docker compose pull

# ── Étape 4 : Redémarrage ─────────────────────────────────────────────────────
echo "[4/4] Redémarrage des services..."
docker compose up -d

echo ""
echo "=== Mise à jour terminée ==="
echo "Vérifiez l'interface OpenWebUI et les logs avec :"
echo "  cd docker && docker compose logs -f openwebui"
