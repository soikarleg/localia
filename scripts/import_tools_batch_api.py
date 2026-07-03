#!/usr/bin/env python3
import json
import os
import sys
from glob import glob
from pathlib import Path
from urllib import error, request

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / "docker" / ".env"
DEFAULT_SOURCE_DIR = REPO_ROOT / "openwebui" / "tools"
OPENWEBUI_URL = os.getenv("OPENWEBUI_URL", "http://localhost:3000").rstrip("/")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def http_json(method: str, url: str, token: str | None = None, payload: dict | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except Exception:
            data = {"raw": raw}
        return e.code, data


def tool_id_from_content(content: str, fallback: str) -> str:
    title = None
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("title:"):
            title = stripped.split(":", 1)[1].strip()
            break
    if title:
        return title.lower().replace(" ", "_").replace("-", "_")
    return fallback


def main() -> int:
    load_env_file(ENV_FILE)

    email = os.getenv("OPENWEBUI_EMAIL") or os.getenv("WEBUI_ADMIN_EMAIL")
    password = os.getenv("OPENWEBUI_PASSWORD") or os.getenv("WEBUI_ADMIN_PASSWORD")

    source_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_SOURCE_DIR
    if not source_dir.exists() or not source_dir.is_dir():
        print(f"ERROR: dossier introuvable: {source_dir}")
        return 1

    if not email or not password:
        print("ERROR: credentials OpenWebUI manquants (OPENWEBUI_EMAIL/PASSWORD ou WEBUI_ADMIN_EMAIL/PASSWORD)")
        return 1

    status, auth = http_json(
        "POST",
        f"{OPENWEBUI_URL}/api/v1/auths/signin",
        payload={"email": email, "password": password},
    )
    if status != 200 or "token" not in auth:
        print(f"ERROR auth ({status}): {auth}")
        return 1
    token = auth["token"]

    status, current_tools = http_json("GET", f"{OPENWEBUI_URL}/api/v1/tools/", token=token)
    if status != 200 or not isinstance(current_tools, list):
        print(f"ERROR lecture tools existants ({status}): {current_tools}")
        return 1

    existing_ids = {item.get("id") for item in current_tools if isinstance(item, dict)}

    paths = sorted(glob(str(source_dir / "*.py")))
    if not paths:
        print(f"Aucun fichier Python trouve dans {source_dir}")
        return 0

    created = 0
    updated = 0
    failed = 0

    for path in paths:
        file_name = Path(path).name
        content = Path(path).read_text(encoding="utf-8")
        fallback_id = Path(path).stem
        tool_id = tool_id_from_content(content, fallback_id)
        name = tool_id.replace("_", " ").strip().title()

        payload = {
            "id": tool_id,
            "name": name,
            "content": content,
            "meta": {"description": f"Import auto depuis {file_name}"},
        }

        if tool_id in existing_ids:
            status, resp = http_json("POST", f"{OPENWEBUI_URL}/api/v1/tools/id/{tool_id}/update", token=token, payload=payload)
            if status == 200:
                updated += 1
                print(f"[UPDATE] {file_name} -> {tool_id}")
            else:
                failed += 1
                print(f"[FAIL] {file_name} -> {tool_id}: {status} {resp}")
            continue

        status, resp = http_json("POST", f"{OPENWEBUI_URL}/api/v1/tools/create", token=token, payload=payload)
        if status == 200:
            created += 1
            existing_ids.add(tool_id)
            print(f"[CREATE] {file_name} -> {tool_id}")
        else:
            failed += 1
            print(f"[FAIL] {file_name} -> {tool_id}: {status} {resp}")

    print("---")
    print(f"Resultat: creates={created}, updates={updated}, fails={failed}, total={len(paths)}")
    print(f"Tools UI: {OPENWEBUI_URL}/workspace/tools")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
