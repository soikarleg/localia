# Liaison entre le dépôt Localia et le container OpenWebUI/Ollama

Ce dépôt n'est pas lié au container dans sa globalité. OpenWebUI et Ollama ne voient que les chemins explicitement montés dans [docker/docker-compose.override.yml](../docker/docker-compose.override.yml). En pratique, les dossiers [openwebui/knowledge](../openwebui/knowledge), [openwebui/live/tools](../openwebui/live/tools), [openwebui/live/skills](../openwebui/live/skills) et [openwebui/pipelines](../openwebui/pipelines) sont les plus importants, car ils sont exposés directement au container OpenWebUI.

Les dossiers [openwebui/tools](../openwebui/tools) et [skills](../skills) sont des sources locales de travail. Pour les rendre visibles dans OpenWebUI, il faut lancer [scripts/sync_openwebui.sh](../scripts/sync_openwebui.sh). Ce script copie les fichiers vers les répertoires "live" montés dans le container, puis recharge OpenWebUI.

Conséquence pratique :

1. Une modification dans un dossier monté directement peut être visible après redémarrage ou rechargement du service.
2. Une modification dans un dossier source doit passer par la synchronisation.
3. Si un skill ou un tool n'apparaît pas, il faut vérifier à la fois le montage Docker et la synchronisation vers les dossiers "live".

Pour le GPU, la logique est séparée : il faut une configuration Docker active côté Ollama. Tant que le bloc GPU reste commenté dans [docker/docker-compose.yml](../docker/docker-compose.yml), le container ne recevra pas d'instruction explicite pour utiliser la carte.

Vérification rapide recommandée :

```bash
cd /home/otto/localia
./scripts/sync_openwebui.sh
cd docker && docker compose ps
```

Si tu veux valider la présence des fichiers dans le container, tu peux ensuite vérifier les montages et le contenu de [openwebui/live/tools](../openwebui/live/tools) et [openwebui/live/skills](../openwebui/live/skills).