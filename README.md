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

Les fichiers qui ont un effet direct dans OpenWebUI sont ceux montés par Docker dans [docker/docker-compose.override.yml](docker/docker-compose.override.yml), en particulier [openwebui/knowledge](openwebui/knowledge), [openwebui/live/tools](openwebui/live/tools), [openwebui/live/skills](openwebui/live/skills) et [openwebui/pipelines](openwebui/pipelines). Les données persistantes d'OpenWebUI viennent de [~/openwebui-data](../openwebui-data), montées par défaut dans [docker/docker-compose.yml](docker/docker-compose.yml), tandis que les modèles Ollama viennent de [~/.ollama](../.ollama), montés par défaut dans [docker/docker-compose.yml](docker/docker-compose.yml). Les sources situées dans [openwebui/tools](openwebui/tools) et [skills](skills) servent de base locale, puis sont synchronisées vers les dossiers "live" via [scripts/sync_openwebui.sh](scripts/sync_openwebui.sh) avant d'être visibles dans le container OpenWebUI.

Pour vérifier le support GPU local, charge [docker/docker-compose.gpu.yml](docker/docker-compose.gpu.yml) et utilise le service `cuda-check` basé sur `nvidia/cuda:12.0.1-base-ubuntu22.04`.

## Organisation cible prompt system + skills

Le flux recommande de separer strictement quatre niveaux: detection de l'intention, extraction metier, evaluation v6, puis chiffrage commercial. Le prompt systeme doit rester un orchestrateur global qui impose l'ordre d'execution, interdit toute invention de donnees et force une sortie JSON francaise. L'analyse des mots cles comme tonte, taille, arbustes, rosiers ou mulch doit etre confiee au routeur de skills, qui choisit ensuite le skill d'extraction specialise. Le calcul de temps doit rester dans le bloc d'evaluation base sur la connaissance v6, tandis que le calcul du prix de vente TTC doit etre traite apres estimation du temps, dans une etape distincte de pricing, afin de ne pas melanger extraction, rendement et commerce.

Organisation fonctionnelle recommandee:

| Etape                 | Role                                                                              | Entree                           | Sortie                         | Source de verite                                                                               |
| --------------------- | --------------------------------------------------------------------------------- | -------------------------------- | ------------------------------ | ---------------------------------------------------------------------------------------------- |
| 1. Prompt system      | Orchestration globale, regles, JSON final, trace d'execution                      | texte utilisateur brut           | consignes d'execution          | [openwebui/prompts/system/evalia_system_v1.txt](openwebui/prompts/system/evalia_system_v1.txt) |
| 2. Skill router       | Analyse mots cles, detection type_tache, selection du skill                       | texte_demande                    | type_tache + skill cible       | [openwebui/tools/skill_router.py](openwebui/tools/skill_router.py)                             |
| 3. Skill d'extraction | Extraire les champs specifiques a la prestation                                   | texte_demande                    | donnees_extraites              | [skills](skills)                                                                               |
| 4. Skills pipeline    | Normaliser, detecter les manquants, calculer la complexite, verifier la coherence | donnees_extraites                | donnees_normalisees + alertes  | [openwebui/live/skills](openwebui/live/skills)                                                 |
| 5. Evaluation v6      | Calculer le temps a partir du CSV de rendements                                   | donnees_normalisees + complexite | temps_total_h + details_calcul | [openwebui/knowledge/temps_reference_v6.csv](openwebui/knowledge/temps_reference_v6.csv)       |
| 6. Pricing TTC        | Transformer le temps en prix de vente TTC                                         | temps_total_h + taux_horaire_ttc | prix_vente_ttc                 | a formaliser dans un skill ou tool dedie                                                       |
| 7. Sortie finale      | Consolider temps, prix, hypotheses, questions, confiance                          | tous les objets precedents       | JSON final metier              | [skills/sortie_json_finale.json](skills/sortie_json_finale.json)                               |

Regle d'architecture: le skill d'extraction ne doit jamais calculer le prix. Le skill [openwebui/live/skills/moteur_rendement.json](openwebui/live/skills/moteur_rendement.json) calcule deja le temps et precise explicitement de ne pas calculer de prix a cette etape. Le calcul commercial recommande est donc: prix_vente_ttc = temps_total_h x taux_horaire_ttc, avec options futures pour forfait de deplacement, minimum de facturation et ajustements commerciaux.

## Todo prioritaire

| Priorite | Action                                                                                                                               | But                                                         | Fichier principal                                                                                                              |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Haute    | Etendre le routeur avec un dictionnaire de mots cles metier incluant mulch, rabattage, bordures, evacuation                          | Fiabiliser la detection automatique du bon skill            | [openwebui/tools/skill_router.py](openwebui/tools/skill_router.py)                                                             |
| Haute    | Distinguer clairement prompt systeme d'orchestration et prompt metier de sortie                                                      | Eviter de dupliquer les regles entre systeme et extraction  | [openwebui/prompts/system/evalia_system_v1.txt](openwebui/prompts/system/evalia_system_v1.txt)                                 |
| Haute    | Conserver un skill d'extraction par prestation                                                                                       | Garder des schemas simples et specialises                   | [skills](skills)                                                                                                               |
| Haute    | Verifier que le pipeline appelle toujours extraction -> normalisation -> ambiguite -> complexite -> rendement -> coherence -> sortie | Stabiliser l'ordre d'execution                              | [openwebui/knowledge/prompt_system_evaluation_devis_qwen25.txt](openwebui/knowledge/prompt_system_evaluation_devis_qwen25.txt) |
| Haute    | Figer v6 comme source de rendement active avec trace_execution.csv_temps_reference_utilise                                           | Garantir la tracabilite des temps calcules                  | [openwebui/knowledge/temps_reference_v6.csv](openwebui/knowledge/temps_reference_v6.csv)                                       |
| Haute    | Ajouter une etape dediee pricing_ttc apres moteur_rendement                                                                          | Sortir un prix de vente TTC sans polluer le calcul de temps | [openwebui/tools/tool_devis.py](openwebui/tools/tool_devis.py)                                                                 |
| Moyenne  | Definir le schema de sortie commercial final avec temps_total_h, taux_horaire_ttc, prix_vente_ttc, marge d'incertitude               | Uniformiser les sorties pour API et UI                      | [skills/sortie_json_finale.json](skills/sortie_json_finale.json)                                                               |
| Moyenne  | Ajouter des tests de routage par mots cles reels                                                                                     | Eviter les mauvaises orientations de skills                 | [scripts/test_prompt_localia.py](scripts/test_prompt_localia.py)                                                               |
| Moyenne  | Ajouter des cas de test pour absence de surface, acces ou evacuation                                                                 | Verifier les questions bloquantes                           | [scripts/test_evalia_prompt_matrix.py](scripts/test_evalia_prompt_matrix.py)                                                   |
| Basse    | Documenter un tableau de correspondance mot cle -> type_tache -> skill                                                               | Faciliter la maintenance metier                             | [docs/openwebui_linkage.md](docs/openwebui_linkage.md)                                                                         |

Paragraphe d'implementation recommande: a partir d'un texte libre utilisateur, le systeme doit d'abord detecter l'intention metier via les mots cles et expressions dominantes, puis router vers un skill d'extraction specialise qui ne fait qu'extraire et normaliser les donnees utiles. Ces donnees passent ensuite dans le pipeline d'evaluation v6 pour calculer un temps d'intervention fiable a partir des rendements internes. Une fois le temps valide, une etape commerciale distincte calcule le prix de vente TTC a partir du taux horaire TTC defini par l'entreprise. La sortie finale doit consolider type de prestation, donnees extraites, temps total, prix TTC, hypotheses, incoherences et questions bloquantes dans un JSON unique exploitable par OpenWebUI, l'API devis et les futurs ecrans metier.

## Structure

| Dossier | Contenu |
|---|---|
| `docker/` | `docker-compose.yml`, `.env.example`, override |
| `ollama/Modelfile/` | Modelfiles personnalisés |
| `openwebui/knowledge/` | Exports base de connaissance |
| `openwebui/tools/` | Exports tools/skills Python |
| `openwebui/backup/` | Snapshots horodatés des données |
| `scripts/` | `backup.sh`, `restore.sh`, `upgrade.sh`, `setup_nvidia_docker.sh`, `import_legacy_uploads.sh`, `import_knowledge_batch_api.sh`, `sync_openwebui_watch.sh`, `check_stack.sh` |
| `docs/` | Documentation |
