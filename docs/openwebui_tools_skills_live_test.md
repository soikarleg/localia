# Test rapide (2 minutes) - Tools & Skills live

Objectif: verifier que les changements locaux se repercutent bien dans OpenWebUI (localhost:3000).

## 1) Synchroniser + recharger

```bash
cd /home/otto/localia
./scripts/sync_openwebui.sh
```

Attendu:
- montage `openwebui/live/tools -> /app/backend/data/tools`
- montage `openwebui/live/skills -> /app/backend/data/skills`
- liste des fichiers tools/skills visible dans le conteneur

## 2) Test skills

- Modifier un skill local dans `skills/` (ex: ajouter une regle).
- Relancer `./scripts/sync_openwebui.sh`.
- Dans OpenWebUI, reimporter le skill si l'interface ne recharge pas automatiquement.

## 3) Test tools

- Modifier un tool local dans `openwebui/tools/`.
- Relancer `./scripts/sync_openwebui.sh`.
- Ouvrir OpenWebUI et verifier que le tool apparait/est recharge.

## 4) Verification service

```bash
cd /home/otto/localia/docker
docker compose ps
```

Attendu:
- `openwebui` en etat `Up`
- acces web sur `http://localhost:3000`

## Notes

- Les bind mounts rendent les fichiers visibles immediatement dans le conteneur.
- Certains objets OpenWebUI peuvent demander un reimport via l'UI selon leur type.
