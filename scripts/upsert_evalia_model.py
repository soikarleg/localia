#!/usr/bin/env python3
import json
import os
from pathlib import Path
from urllib import error, request

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / "docker" / ".env"
SYSTEM_PROMPT_FILE = REPO_ROOT / "openwebui" / "prompts" / "system" / "evalia_system_v1.txt"

MODEL_ID = "evalia"
BASE_MODEL_ID = "qwen2.5:7b-instruct-q4_K_M"
MODEL_NAME = "Evalia"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def http_json(method: str, url: str, payload=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(url, data=data, headers=headers, method=method)
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


def main() -> int:
    load_env(ENV_FILE)

    base_url = os.getenv("OPENWEBUI_URL", "http://localhost:3000").rstrip("/")
    email = os.getenv("OPENWEBUI_EMAIL") or os.getenv("WEBUI_ADMIN_EMAIL")
    password = os.getenv("OPENWEBUI_PASSWORD") or os.getenv("WEBUI_ADMIN_PASSWORD")

    if not email or not password:
        print("ERROR: credentials manquants")
        return 1

    system_prompt = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()

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
        "id": MODEL_ID,
        "base_model_id": BASE_MODEL_ID,
        "name": MODEL_NAME,
        "params": {
            "temperature": 0.2,
            "top_p": 0.9,
            "system": system_prompt
        },
        "meta": {
            "description": "Modele metier Localia: devis B2C, base v6, skills orchestration.",
            "tags": [
                {"name": "localia"},
                {"name": "evalia"},
                {"name": "v1"}
            ]
        },
        "access_grants": [],
        "is_active": True
    }

    code, current = http_json("GET", f"{base_url}/api/v1/models/list?page=1", token=token)
    if code != 200:
        print(f"ERROR list models: {code} {current}")
        return 1

    exists = False
    for item in current.get("items", []):
        if item.get("id") == MODEL_ID:
            exists = True
            break

    if exists:
        code, resp = http_json("POST", f"{base_url}/api/v1/models/model/update", payload=payload, token=token)
        action = "UPDATE"
    else:
        code, resp = http_json("POST", f"{base_url}/api/v1/models/create", payload=payload, token=token)
        action = "CREATE"

    if code != 200:
        print(f"ERROR {action}: {code} {resp}")
        return 1

    print(f"{action} OK: {MODEL_ID} ({BASE_MODEL_ID})")
    print(f"Workspace modeles: {base_url}/workspace/models")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
