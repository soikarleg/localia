# localia

Infrastructure locale pour IA avec **Ollama** + **OpenWebUI**, gérée via Docker Compose.

## Démarrage rapide

```bash
cp docker/.env.example docker/.env
# Éditer docker/.env selon votre machine
cd docker && docker compose up -d
```

Interface disponible sur `http://localhost:3000`

## Documentation

Voir [docs/setup.md](docs/setup.md) pour le guide complet : installation, GPU, sauvegarde, restauration, mise à jour.

Les fichiers qui ont un effet direct dans OpenWebUI sont ceux montés par Docker dans [docker/docker-compose.override.yml](docker/docker-compose.override.yml), en particulier [openwebui/knowledge](openwebui/knowledge), [openwebui/live/tools](openwebui/live/tools), [openwebui/live/skills](openwebui/live/skills) et [openwebui/pipelines](openwebui/pipelines). Les sources situées dans [openwebui/tools](openwebui/tools) et [skills](skills) servent de base locale, puis sont synchronisées vers les dossiers "live" via [scripts/sync_openwebui.sh](scripts/sync_openwebui.sh) avant d'être visibles dans le container OpenWebUI.

## Structure

| Dossier | Contenu |
|---|---|
| `docker/` | `docker-compose.yml`, `.env.example`, override |
| `ollama/Modelfile/` | Modelfiles personnalisés |
| `openwebui/knowledge/` | Exports base de connaissance |
| `openwebui/tools/` | Exports tools/skills Python |
| `openwebui/backup/` | Snapshots horodatés des données |
| `scripts/` | `backup.sh`, `restore.sh`, `upgrade.sh` |
| `docs/` | Documentation |
