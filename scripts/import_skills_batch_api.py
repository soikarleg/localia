#!/usr/bin/env python3
import json
import os
import re
import sys
from glob import glob
from pathlib import Path
from urllib import error, request

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / "docker" / ".env"
DEFAULT_SOURCE_DIR = REPO_ROOT / "skills"
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


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9._-]", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "skill-sans-id"


def build_content(data: dict, source_name: str) -> str:
    if isinstance(data.get("content"), str) and data.get("content", "").strip():
        return data["content"].strip()

    lines: list[str] = []
    objectif = data.get("objectif") or data.get("description") or ""
    if objectif:
        lines.append("## Objectif")
        lines.append(str(objectif).strip())
        lines.append("")

    inputs = data.get("inputs")
    if isinstance(inputs, list) and inputs:
        lines.append("## Inputs")
        for item in inputs:
            lines.append(f"- {item}")
        lines.append("")

    regles = data.get("regles")
    if isinstance(regles, list) and regles:
        lines.append("## Regles")
        for item in regles:
            lines.append(f"- {item}")
        lines.append("")

    output_json = data.get("output_json")
    if output_json is not None:
        lines.append("## Output JSON")
        lines.append("```json")
        lines.append(json.dumps(output_json, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

    if not lines:
        lines.append(f"Skill importe depuis {source_name}")

    return "\n".join(lines).strip()


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

    status, current_skills = http_json("GET", f"{OPENWEBUI_URL}/api/v1/skills/", token=token)
    if status != 200 or not isinstance(current_skills, list):
        print(f"ERROR lecture skills existants ({status}): {current_skills}")
        return 1

    existing_ids = {item.get("id") for item in current_skills if isinstance(item, dict)}

    paths = sorted(glob(str(source_dir / "*.json")))
    if not paths:
        print(f"Aucun fichier JSON trouve dans {source_dir}")
        return 0

    created = 0
    updated = 0
    failed = 0

    for path in paths:
        file_name = Path(path).name
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as e:
            failed += 1
            print(f"[FAIL] {file_name}: JSON invalide ({e})")
            continue

        raw_id = str(data.get("id") or Path(path).stem)
        skill_id = slugify(raw_id)

        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            name = raw_id.replace("_", " ").replace("-", " ").strip().title()

        description = data.get("description") or data.get("objectif") or f"Import auto depuis {file_name}"
        content = build_content(data, file_name)

        payload = {
            "id": skill_id,
            "name": name,
            "description": str(description),
            "content": content,
            "meta": {"tags": ["localia", "import-auto"]},
            "is_active": True,
        }

        if skill_id in existing_ids:
            status, resp = http_json("POST", f"{OPENWEBUI_URL}/api/v1/skills/id/{skill_id}/update", token=token, payload=payload)
            if status == 200:
                updated += 1
                print(f"[UPDATE] {file_name} -> {skill_id}")
            else:
                failed += 1
                print(f"[FAIL] {file_name} -> {skill_id}: {status} {resp}")
            continue

        status, resp = http_json("POST", f"{OPENWEBUI_URL}/api/v1/skills/create", token=token, payload=payload)
        if status == 200:
            created += 1
            existing_ids.add(skill_id)
            print(f"[CREATE] {file_name} -> {skill_id}")
        else:
            failed += 1
            print(f"[FAIL] {file_name} -> {skill_id}: {status} {resp}")

    print("---")
    print(f"Resultat: creates={created}, updates={updated}, fails={failed}, total={len(paths)}")
    print(f"Skills UI: {OPENWEBUI_URL}/workspace/skills")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
