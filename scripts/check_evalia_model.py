#!/usr/bin/env python3
import json
import os
from pathlib import Path
from urllib import error, request
from urllib.parse import quote


def load_env(path: Path) -> dict:
    data = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def main() -> int:
    env = load_env(Path("docker/.env"))
    base = (env.get("OPENWEBUI_URL") or "http://localhost:3000").rstrip("/")
    email = env.get("OPENWEBUI_EMAIL") or env.get("WEBUI_ADMIN_EMAIL")
    password = env.get("OPENWEBUI_PASSWORD") or env.get("WEBUI_ADMIN_PASSWORD")

    req = request.Request(
        f"{base}/api/v1/auths/signin",
        data=json.dumps({"email": email, "password": password}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    token = json.loads(request.urlopen(req).read().decode("utf-8"))["token"]

    obj = None
    for url in (
        f"{base}/api/v1/models/id/evalia",
        f"{base}/api/v1/models/model?model_id={quote('evalia')}",
        f"{base}/api/v1/models/model?url_idx=0&model_id={quote('evalia')}",
    ):
        req2 = request.Request(
            url,
            headers={"Authorization": f"Bearer {token}"},
            method="GET",
        )
        try:
            raw = request.urlopen(req2).read().decode("utf-8", errors="replace")
        except error.HTTPError:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if isinstance(data, dict) and data.get("id") == "evalia":
            obj = data
            break

    if obj is None:
        print("MODEL_ID evalia introuvable via API GET")
        return 1

    params = obj.get("params", {})
    print("MODEL_ID", obj.get("id"))
    print("BASE", obj.get("base_model_id"))
    print("HAS_SYSTEM", "system" in params)
    print("SYSTEM_CHARS", len(params.get("system", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
