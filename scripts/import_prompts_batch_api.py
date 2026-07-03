#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from urllib import error, request

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / "docker" / ".env"
DEFAULT_MANIFEST = REPO_ROOT / "openwebui" / "prompts" / "localia_prompts_v1.json"
DEFAULT_OPENWEBUI_URL = "http://localhost:3000"


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


def http_json(method: str, url: str, payload: dict | None = None, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw}
        return e.code, parsed


def signin(base_url: str, email: str, password: str) -> str:
    code, payload = http_json(
        "POST",
        f"{base_url}/api/v1/auths/signin",
        payload={"email": email, "password": password},
    )
    if code != 200 or "token" not in payload:
        raise RuntimeError(f"Authentification impossible ({code}): {payload}")
    return payload["token"]


def load_manifest(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Le manifest doit etre un tableau JSON")
    return data


def main() -> int:
    load_env(ENV_FILE)

    manifest_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_MANIFEST
    if not manifest_path.exists():
        print(f"ERROR: manifest introuvable: {manifest_path}")
        return 1

    base_url = os.getenv("OPENWEBUI_URL", DEFAULT_OPENWEBUI_URL).rstrip("/")
    email = os.getenv("OPENWEBUI_EMAIL") or os.getenv("WEBUI_ADMIN_EMAIL")
    password = os.getenv("OPENWEBUI_PASSWORD") or os.getenv("WEBUI_ADMIN_PASSWORD")

    if not email or not password:
        print("ERROR: credentials manquants (OPENWEBUI_EMAIL/PASSWORD ou WEBUI_ADMIN_EMAIL/PASSWORD)")
        return 1

    token = signin(base_url, email, password)

    code, existing = http_json("GET", f"{base_url}/api/v1/prompts/", token=token)
    if code != 200 or not isinstance(existing, list):
        print(f"ERROR: lecture prompts impossible ({code}): {existing}")
        return 1

    existing_by_command = {p.get("command"): p for p in existing if isinstance(p, dict) and p.get("command")}

    manifest = load_manifest(manifest_path)
    created = 0
    updated = 0
    failed = 0

    for item in manifest:
        try:
            name = item["name"]
            command = item["command"]
            tags = item.get("tags", [])
            meta = item.get("meta", {})
            content_file = (manifest_path.parent / item["content_file"]).resolve()
            content = content_file.read_text(encoding="utf-8").strip()

            payload = {
                "name": name,
                "command": command,
                "content": content,
                "tags": tags,
                "meta": meta,
                "data": {},
                "is_production": True,
                "commit_message": "Import Localia prompts v1",
            }

            if command in existing_by_command:
                prompt_id = existing_by_command[command]["id"]
                code, resp = http_json("POST", f"{base_url}/api/v1/prompts/id/{prompt_id}/update", payload=payload, token=token)
                if code == 200:
                    updated += 1
                    print(f"[UPDATE] {command}")
                else:
                    failed += 1
                    print(f"[FAIL] {command}: {code} {resp}")
            else:
                code, resp = http_json("POST", f"{base_url}/api/v1/prompts/create", payload=payload, token=token)
                if code == 200:
                    created += 1
                    print(f"[CREATE] {command}")
                else:
                    failed += 1
                    print(f"[FAIL] {command}: {code} {resp}")
        except Exception as e:
            failed += 1
            print(f"[FAIL] item {item}: {e}")

    print("---")
    print(f"Resultat: creates={created}, updates={updated}, fails={failed}, total={len(manifest)}")
    print(f"Workspace prompts: {base_url}/workspace/prompts")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
