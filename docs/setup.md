# Guide d'installation et de gestion — Localia (Ollama + OpenWebUI)

## Prérequis

- Docker Engine ≥ 24
- Docker Compose plugin (`docker compose` — pas l'ancienne commande `docker-compose`)
- (Optionnel) NVIDIA Container Toolkit pour GPU

---

## Installation initiale

```bash
# 1. Cloner ce dépôt
git clone https://github.com/soikarleg/localia.git
cd localia

# 2. Configurer l'environnement
cp docker/.env.example docker/.env
# Éditer docker/.env selon votre machine (ports, clé secrète, etc.)

# 3. Démarrer les services
cd docker
docker compose up -d

# 4. Vérifier le démarrage
docker compose logs -f
```

L'interface OpenWebUI est accessible sur `http://localhost:3000` (port configurable dans `.env`).

---

## Structure du dépôt

```
localia/
├── docker/
│   ├── docker-compose.yml          # Composition principale
│   ├── docker-compose.override.yml # Surcharges locales (GPU, ports, etc.)
│   ├── .env.example                # Template de configuration (versionné)
│   └── .env                        # Configuration locale (NON versionné)
├── ollama/
│   └── Modelfile/                  # Modelfiles personnalisés
├── openwebui/
│   ├── knowledge/                  # Exports de la base de connaissance
│   ├── tools/                      # Exports des tools/skills Python
│   ├── pipelines/                  # Pipelines personnalisés
│   └── backup/                     # Snapshots horodatés des données
├── scripts/
│   ├── backup.sh                   # Sauvegarde automatisée
│   ├── restore.sh                  # Restauration depuis backup
│   └── upgrade.sh                  # Mise à jour contrôlée
└── docs/
    └── setup.md                    # Ce fichier
```

---

## Activation GPU NVIDIA

Le mode GPU est séparé dans `docker/docker-compose.gpu.yml` afin de ne pas bloquer un démarrage CPU sur une machine sans GPU NVIDIA.

Les données persistantes d'OpenWebUI sont montées par défaut depuis `~/openwebui-data`. Les modèles Ollama viennent de `~/.ollama`, qui contient les blobs et manifests réels.

Vérifier l'installation du NVIDIA Container Toolkit :

```bash
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

Pour un contrôle local via Compose, charger le fichier GPU puis lancer le service `cuda-check` :

```bash
cd /home/otto/localia/docker
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm cuda-check
```

Le tag Compose par défaut est `nvidia/cuda:12.0.1-base-ubuntu22.04`, qui est disponible publiquement. Le GPU s'active via `docker-compose.gpu.yml`.

Si `apt install nvidia-container-toolkit` renvoie `Impossible de trouver le paquet`, il faut d'abord ajouter le dépôt NVIDIA sur la machine hôte. Sur Linux Mint 22.1 / Ubuntu 24.04, la procédure minimale en fish est :

```fish
set -l distribution (begin; . /etc/os-release; switch $UBUNTU_CODENAME; case noble; echo ubuntu24.04; case jammy; echo ubuntu22.04; case '*'; echo ubuntu24.04; end; end)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list |
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' |
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Si `sudo apt update` échoue encore avec un dépôt Docker en `xia`, le problème vient du dépôt tiers Docker enregistré pour la mauvaise base Ubuntu. Il faut corriger ou désactiver l'entrée `download.docker.com/linux/ubuntu xia` dans `/etc/apt/sources.list.d/` avant de relancer `apt update`.

Puis relancer :

```bash
cd /home/otto/localia/docker
docker compose up -d
```

---

## Gestion des modèles Ollama

```bash
# Entrer dans le container ollama
docker exec -it ollama bash

# Télécharger un modèle
ollama pull llama3.2

# Lister les modèles disponibles
ollama list

# Créer un modèle depuis un Modelfile local
ollama create mon-modele -f /chemin/vers/Modelfile
```

---

## Sauvegarde

```bash
./scripts/backup.sh
```

Crée une archive horodatée dans `openwebui/backup/` et effectue un commit git.

---

## Restauration

```bash
./scripts/restore.sh openwebui/backup/openwebui_data_20260701_120000.tar.gz
```

⚠️ Arrête le container OpenWebUI, restaure les données, puis le redémarre.

---

## Mise à jour d'OpenWebUI

```bash
# Mettre à jour vers la version 0.10.7
./scripts/upgrade.sh --openwebui 0.10.7
```

Le script effectue automatiquement une sauvegarde avant la mise à jour.

**Règle importante :** Ne jamais utiliser le tag `latest` en production. Toujours spécifier une version précise dans `docker/.env`.

---

## Procédure de migration (ex : 0.09 → 0.10)

1. **Sauvegarder** les données de l'ancienne installation :
   ```bash
   docker cp <ancien_container>:/app/backend/data ./openwebui/backup/migration_avant_0.10/
   ```
2. **Exporter** manuellement depuis l'UI :
   - Base de connaissance : Settings → Knowledge → Export → sauvegarder dans `openwebui/knowledge/`
   - Tools : Settings → Tools → Export → sauvegarder dans `openwebui/tools/`
3. **Arrêter** l'ancienne installation.
4. **Démarrer** la nouvelle version avec un volume vierge (`docker volume rm openwebui_data`).
5. **Tester** que l'interface démarre correctement.
6. **Restaurer** les données avec `./scripts/restore.sh` ou réimporter manuellement.

> ⚠️ Les schémas de base de données peuvent différer entre versions majeures.  
> En cas d'échec de la restauration automatique, réimporter manuellement depuis les exports JSON/Python.

---

## Commandes utiles

```bash
# Voir les logs en temps réel
cd docker && docker compose logs -f

# Arrêter les services
docker compose down

# Arrêter et supprimer les volumes (DESTRUCTIF)
docker compose down -v

# Inspecter les volumes
docker volume ls
docker volume inspect openwebui_data

# Accéder au shell du container OpenWebUI
docker exec -it openwebui bash
```
