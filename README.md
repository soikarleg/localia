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
