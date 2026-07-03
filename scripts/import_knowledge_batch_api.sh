#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/docker/.env"

OPENWEBUI_URL="${OPENWEBUI_URL:-http://localhost:3000}"
SOURCE_DIR="${1:-${REPO_ROOT}/openwebui/knowledge/legacy_uploads}"
KB_NAME="${2:-Legacy imports $(date +%Y-%m-%d_%H-%M)}"
KB_DESC="${KB_DESC:-Import automatique depuis ${SOURCE_DIR}}"

if [ ! -d "${SOURCE_DIR}" ]; then
  echo "ERROR: dossier source introuvable: ${SOURCE_DIR}"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 est requis."
  exit 1
fi

if [ -f "${ENV_FILE}" ]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

EMAIL="${OPENWEBUI_EMAIL:-${WEBUI_ADMIN_EMAIL:-}}"
PASSWORD="${OPENWEBUI_PASSWORD:-${WEBUI_ADMIN_PASSWORD:-}}"

if [ -z "${EMAIL}" ] || [ -z "${PASSWORD}" ]; then
  echo "ERROR: credentials manquants."
  echo "Definir OPENWEBUI_EMAIL/OPENWEBUI_PASSWORD ou WEBUI_ADMIN_EMAIL/WEBUI_ADMIN_PASSWORD dans docker/.env"
  exit 1
fi

COOKIE_JAR="$(mktemp)"
cleanup() {
  rm -f "${COOKIE_JAR}" /tmp/localia_signin.json /tmp/localia_kb_create.json /tmp/localia_upload.json /tmp/localia_add.json
}
trap cleanup EXIT

echo "[1/4] Auth OpenWebUI (${OPENWEBUI_URL})"
signin_payload="$(OPENWEBUI_EMAIL="${EMAIL}" OPENWEBUI_PASSWORD="${PASSWORD}" python3 - <<'PY'
import json, os
print(json.dumps({"email": os.environ["OPENWEBUI_EMAIL"], "password": os.environ["OPENWEBUI_PASSWORD"]}))
PY
)"

curl -fsS -c "${COOKIE_JAR}" -H 'Content-Type: application/json' \
  -X POST "${OPENWEBUI_URL}/api/v1/auths/signin" \
  -d "${signin_payload}" \
  > /tmp/localia_signin.json

TOKEN="$(python3 - <<'PY'
import json
with open('/tmp/localia_signin.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(data.get('token', ''))
PY
)"
if [ -z "${TOKEN}" ]; then
  echo "ERROR: authentification echouee"
  cat /tmp/localia_signin.json
  exit 1
fi

echo "[2/4] Creation base de connaissance: ${KB_NAME}"
kb_payload="$(KB_NAME="${KB_NAME}" KB_DESC="${KB_DESC}" python3 - <<'PY'
import json, os
print(json.dumps({
    "name": os.environ["KB_NAME"],
    "description": os.environ["KB_DESC"],
    "access_control": {}
}))
PY
)"

curl -fsS -b "${COOKIE_JAR}" -H "Authorization: Bearer ${TOKEN}" -H 'Content-Type: application/json' \
  -X POST "${OPENWEBUI_URL}/api/v1/knowledge/create" \
  -d "${kb_payload}" \
  > /tmp/localia_kb_create.json

KB_ID="$(python3 - <<'PY'
import json
with open('/tmp/localia_kb_create.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(data.get('id', ''))
PY
)"
if [ -z "${KB_ID}" ]; then
  echo "ERROR: creation knowledge echouee"
  cat /tmp/localia_kb_create.json
  exit 1
fi

echo "[3/4] Import fichiers depuis ${SOURCE_DIR}"
count_total=0
count_ok=0

while IFS= read -r -d '' file; do
  count_total=$((count_total+1))
  base="$(basename "${file}")"

  echo "  - upload: ${base}"
  if ! curl -fsS -b "${COOKIE_JAR}" -H "Authorization: Bearer ${TOKEN}" \
      -X POST "${OPENWEBUI_URL}/api/v1/files/" \
      -F "file=@${file}" > /tmp/localia_upload.json; then
    echo "    WARN: upload echec pour ${base}"
    continue
  fi

  file_id="$(python3 - <<'PY'
import json
with open('/tmp/localia_upload.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(data.get('id', ''))
PY
)"
  if [ -z "${file_id}" ]; then
    echo "    WARN: file_id manquant pour ${base}"
    continue
  fi

  add_payload="$(FILE_ID="${file_id}" python3 - <<'PY'
import json, os
print(json.dumps({"file_id": os.environ["FILE_ID"]}))
PY
)"

  if curl -fsS -b "${COOKIE_JAR}" -H "Authorization: Bearer ${TOKEN}" -H 'Content-Type: application/json' \
      -X POST "${OPENWEBUI_URL}/api/v1/knowledge/${KB_ID}/file/add" \
      -d "${add_payload}" > /tmp/localia_add.json; then
    count_ok=$((count_ok+1))
  else
    echo "    WARN: association knowledge echec pour ${base}"
  fi
done < <(find "${SOURCE_DIR}" -maxdepth 1 -type f \( -iname '*.csv' -o -iname '*.txt' -o -iname '*.md' -o -iname '*.json' \) -print0)

echo "[4/4] Resultat"
echo "KB_ID: ${KB_ID}"
echo "Fichiers traites: ${count_ok}/${count_total}"
echo "URL: ${OPENWEBUI_URL}/workspace/knowledge/${KB_ID}"
