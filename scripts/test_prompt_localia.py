#!/usr/bin/env python3
import json
import re
from pathlib import Path
from urllib import error, request

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / "docker" / ".env"
BASE_URL = "http://localhost:3000"
MODEL = "qwen2.5:7b-instruct-q4_K_M"


def load_env(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def http_json(method: str, url: str, payload=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw}
        return e.code, parsed


def parse_json_from_text(text: str):
    try:
        return True, json.loads(text)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return False, None
        try:
            return True, json.loads(m.group(0))
        except Exception:
            return False, None


def main() -> int:
    env = load_env(ENV_FILE)
    base_url = env.get("OPENWEBUI_URL", BASE_URL).rstrip("/")
    email = env.get("OPENWEBUI_EMAIL") or env.get("WEBUI_ADMIN_EMAIL")
    password = env.get("OPENWEBUI_PASSWORD") or env.get("WEBUI_ADMIN_PASSWORD")

    if not email or not password:
        print("ERROR: credentials manquants dans docker/.env")
        return 1

    prompt_path = REPO_ROOT / "openwebui" / "prompts" / "content" / "localia_controle_coherence_devis_v1.txt"
    system_prompt = prompt_path.read_text(encoding="utf-8")

    devis = (
        "Devis D-2026-045\n"
        "Date: 03/07/2026\n"
        "Client: Mme Martin\n"
        "Prestation: Taille de haie 40 ml + evacuation dechets\n"
        "Prix unitaire: 7 EUR/ml\n"
        "Sous-total HT: 280 EUR\n"
        "TVA: non precisee\n"
        "Total TTC: 280 EUR\n"
        "Modalites de paiement: non precisees\n"
        "Delai: intervention sous 2 semaines\n"
    )

    code, auth = http_json(
        "POST",
        f"{base_url}/api/v1/auths/signin",
        payload={"email": email, "password": password},
    )
    if code != 200 or "token" not in auth:
        print(f"ERROR auth: {code} {auth}")
        return 1

    token = auth["token"]
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": devis},
        ],
        "stream": False,
    }

    code, response = http_json(
        "POST",
        f"{base_url}/api/chat/completions",
        payload=payload,
        token=token,
    )
    if code != 200:
        print(f"ERROR chat: {code} {response}")
        return 1

    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    is_json, parsed = parse_json_from_text(content)

    print(f"CHAT_STATUS={code}")
    print(f"JSON_VALID={is_json}")
    print("RAW_PREVIEW_START")
    print(content[:900])
    print("RAW_PREVIEW_END")

    if is_json:
        print("JSON_KEYS=", sorted(parsed.keys()))
        expected = {"statut", "niveau_risque", "anomalies", "preuves", "corrections_proposees", "questions_bloquantes"}
        print("EXPECTED_KEYS_OK=", expected.issubset(set(parsed.keys())))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
