# Programme d'amelioration - TODO

Objectif: rendre le modele plus performant et plus rapide pour l'evaluation du temps d'intervention des prestations d'entretien.

## Phase 1 - Fondations donnees

- [ ] Creer `openwebui/knowledge/temps_reference_v1.csv` avec les colonnes minimales:
  - [ ] essence
  - [ ] type_taille
  - [ ] unite
  - [ ] rendement_reference
  - [ ] temps_fixe_preparation_h
  - [ ] temps_fixe_finition_h
  - [ ] version
  - [ ] date_effet
- [ ] Ajouter 20 lignes metier realistes pour les prestations principales.
- [ ] Definir la convention de versionning CSV:
  - [ ] format `temps_reference_vN.csv`
  - [ ] regle de selection: plus grand N puis date de modification.
- [ ] Ajouter un fichier de changelog des rendements dans `openwebui/knowledge/README.md`.

## Phase 2 - Prompt et orchestration

- [ ] Verifier que le prompt systeme actif est `openwebui/knowledge/prompt_system_evaluation_devis_qwen25.txt`.
- [ ] Ajouter le champ `langue_sortie` dans le schema JSON final (`fr` attendu).
- [ ] Ajouter une regle de rejet si des champs texte sortent en langue non francaise.
- [ ] Verifier la coherence entre:
  - [ ] les noms de champs attendus dans le prompt
  - [ ] les noms de champs sortis par les skills
  - [ ] les noms de champs utilises par les tools.

## Phase 3 - Skills et tools

- [ ] Garder JSON comme source de verite pour import OpenWebUI:
  - [ ] `skills/*.json` utilises en production
  - [ ] `skills/*.yaml` conserves pour edition seulement.
- [ ] Documenter l'ordre d'execution des skills dans un seul fichier de reference.
- [ ] Supprimer ou completer `openwebui/tools/tool_devis.py` (actuellement vide).
- [ ] Faire evoluer `openwebui/tools/devis_evaluation_tool.py`:
  - [ ] prise en charge explicite du CSV de rendements
  - [ ] controle strict des seuils de risque
  - [ ] alignement exact avec le schema de sortie du prompt.

## Phase 4 - Reglages modele et performance

- [ ] Renseigner `params` de l'assistant Evaluation:
  - [ ] temperature: 0.2
  - [ ] top_p: 0.9
  - [ ] repeat_penalty: 1.1
  - [ ] max_tokens: 700 a 1200
- [ ] Limiter le contexte de travail a 6k-10k tokens pour ce workflow.
- [ ] Desactiver les capacites non necessaires pour ce profil (si non utilisees):
  - [ ] vision
  - [ ] code_execution
  - [ ] code_interpreter
  - [ ] memories.

## Phase 5 - Qualite, tests et exploitation

- [ ] Constituer un jeu de 10 devis anonymises de reference.
- [ ] Definir 5 KPI de qualite:
  - [ ] validite JSON
  - [ ] latence
  - [ ] stabilite des scores
  - [ ] precision du temps estime
  - [ ] taux de questions bloquantes pertinentes.
- [ ] Creer un protocole de benchmark reproductible (avant/apres).
- [ ] Ajouter un test de non-regression a chaque modification prompt/skills/tools.
- [ ] Mettre en place une revue humaine finale pour les devis a risque moyen/eleve.

## Phase 6 - Gouvernance et maintenance

- [ ] Definir un rythme de mise a jour des rendements (mensuel ou trimestriel).
- [ ] Nommer un responsable metier pour valider les changements de coefficients.
- [ ] Tracer les changements critiques dans un journal d'audit.
- [ ] Planifier une revue complete du systeme tous les 90 jours.

## Definition de termine

- [ ] 100% des sorties sont en JSON valide et en francais.
- [ ] Le CSV `temps_reference_v*.csv` est present et versionne.
- [ ] Le pipeline skills est stable et trace dans `trace_execution`.
- [ ] Le temps de reponse est compatible avec l'usage operationnel.
- [ ] Les scores et le niveau de risque sont juges fiables par la validation metier.
