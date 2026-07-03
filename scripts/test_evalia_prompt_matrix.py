#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path
from urllib import error, request

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / "docker" / ".env"
SYSTEM_PROMPT_FILE = REPO_ROOT / "openwebui" / "prompts" / "system" / "evalia_system_v1.txt"
PROMPTS_DIR = REPO_ROOT / "openwebui" / "prompts" / "content"
MODEL = "qwen2.5:7b-instruct-q4_K_M"

DEVISES = {
    "controle": "Devis D-2026-045\\nDate: 03/07/2026\\nClient: Mme Martin\\nPrestation: Taille de haie 40 ml + evacuation dechets\\nPrix unitaire: 7 EUR/ml\\nSous-total HT: 280 EUR\\nTVA: non precisee\\nTotal TTC: 280 EUR\\nModalites de paiement: non precisees\\nDelai: intervention sous 2 semaines\\n",
    "extraction": "Bonjour, j'ai une haie de 35 ml a tailler sur 2 faces a 2.2m de haut, acces moyen et evacuation demandee.",
}


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
        with request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw}
        return e.code, parsed


def parse_json(text: str):
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
    load_env(ENV_FILE)
    base_url = os.getenv("OPENWEBUI_URL", "http://localhost:3000").rstrip("/")
    email = os.getenv("OPENWEBUI_EMAIL") or os.getenv("WEBUI_ADMIN_EMAIL")
    password = os.getenv("OPENWEBUI_PASSWORD") or os.getenv("WEBUI_ADMIN_PASSWORD")

    if not email or not password:
        print("ERROR: credentials manquants")
        return 1

    system_prompt = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()

    code, auth = http_json("POST", f"{base_url}/api/v1/auths/signin", payload={"email": email, "password": password})
    if code != 200 or "token" not in auth:
        print(f"ERROR auth: {code} {auth}")
        return 1
    token = auth["token"]

    prompt_files = sorted(PROMPTS_DIR.glob("localia_*_v1.txt"))
    if not prompt_files:
        print("ERROR: aucun prompt v1 trouve")
        return 1

    failures = 0
    for pf in prompt_files:
        sub_prompt = pf.read_text(encoding="utf-8").strip()
        case = "controle" if "coherence" in pf.name else "extraction"
        user_text = DEVISES[case]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": "Prompt metier specialise:\n" + sub_prompt},
            {"role": "user", "content": user_text},
        ]

        payload = {"model": MODEL, "messages": messages, "stream": False}
        code, response = http_json("POST", f"{base_url}/api/chat/completions", payload=payload, token=token)
        if code != 200:
            failures += 1
            print(f"[FAIL] {pf.name}: status={code}")
            continue

        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        ok, parsed = parse_json(content)
        if not ok or not isinstance(parsed, dict):
            failures += 1
            print(f"[FAIL] {pf.name}: sortie non JSON")
            print(content[:280].replace("\n", " "))
            continue

        print(f"[OK] {pf.name}: keys={sorted(parsed.keys())[:6]}")

    print("---")
    print(f"MATRIX_RESULT failures={failures} total={len(prompt_files)}")
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
