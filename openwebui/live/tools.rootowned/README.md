# Exports des tools / skills OpenWebUI
# Déposez ici les fichiers Python des tools exportés depuis l'interface OpenWebUI.
# Format attendu : fichier .py tel qu'exporté via Settings → Tools → Export

Tool ajoute:
- devis_evaluation_tool.py
	- Methode principale: evaluate_devis(devis_flags, custom_weights=None, custom_criteria=None)
	- Entree attendue: dictionnaire de flags booleens item -> true/false
	- Sortie: score global, risque, scores par axe, anomalies, questions bloquantes, actions recommandees

- skill_router.py
	- Methode principale: route_skill(texte_demande, type_tache_hint='')
	- Diagnostic: list_skills_catalog(include_output_schema=False)
	- Aide tests: get_test_prompts()
	- Orchestration: route_and_extract(texte_demande, type_tache_hint='')
	- Role: selectionner le bon skill d'extraction puis indiquer le chainage vers
	  normalisation_unites, detection_ambiguite, estimation_complexite,
	  moteur_rendement, controle_coherence, sortie_json_finale
	- Controle bloquant: verifie la presence des skills aval et retourne une erreur
	  `pipeline_skills_manquants` si le pipeline est incomplet
