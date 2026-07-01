"""
title: Devis Evaluation Tool
author: localia
version: 1.0.0
required_open_webui_version: 0.6.32
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


DEFAULT_WEIGHTS: Dict[str, float] = {
    "conformite_documentaire": 0.20,
    "coherence_financiere": 0.25,
    "qualite_technique": 0.20,
    "gestion_risques": 0.15,
    "conditions_commerciales": 0.10,
    "lisibilite_et_justification": 0.10,
}


DEFAULT_CRITERIA: Dict[str, List[str]] = {
    "conformite_documentaire": [
        "numero_devis",
        "date_devis",
        "identification_prestataire",
        "identification_client",
        "description_detaillee_des_prestations",
        "duree_validite",
    ],
    "coherence_financiere": [
        "quantites_x_prix_unitaires_coherents",
        "sous_totaux_calcules_correctement",
        "tva_explicite_ou_exoneration_justifiee",
        "total_ht_et_ttc_coherents",
        "ecart_marche_raisonnable_si_reference_disponible",
    ],
    "qualite_technique": [
        "perimetre_clair",
        "livrables_identifies",
        "hypotheses_et_exclusions",
        "planning_ou_delai",
        "ressources_ou_methode",
    ],
    "gestion_risques": [
        "contraintes_identifiees",
        "dependances_ou_pre_requis",
        "gestion_imprevus",
        "clauses_revision_ou_avenant",
    ],
    "conditions_commerciales": [
        "modalites_paiement",
        "penalites_retard_ou_escompte",
        "conditions_annulation",
        "mentions_service_apres_vente_ou_garantie",
    ],
    "lisibilite_et_justification": [
        "structure_du_document",
        "vocabulaire_non_ambigu",
        "justification_des_postes_sensibles",
        "trace_des_calculs",
    ],
}


CRITICAL_ITEMS: List[str] = [
    "numero_devis",
    "identification_client",
    "description_detaillee_des_prestations",
    "total_ht_et_ttc_coherents",
]


@dataclass
class ScoreResult:
    score_global_100: float
    niveau_risque: str
    scores_par_axe: Dict[str, float]
    anomalies: List[str]
    questions_bloquantes: List[str]
    actions_recommandees: List[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "score_global_100": self.score_global_100,
            "niveau_risque": self.niveau_risque,
            "scores_par_axe": self.scores_par_axe,
            "anomalies": self.anomalies,
            "questions_bloquantes": self.questions_bloquantes,
            "actions_recommandees": self.actions_recommandees,
        }


class Tools:
    def evaluate_devis(
        self,
        devis_flags: Dict[str, bool],
        custom_weights: Dict[str, float] | None = None,
        custom_criteria: Dict[str, List[str]] | None = None,
    ) -> Dict[str, Any]:
        """
        Evalue un devis a partir de flags booleens.

        Parametres attendus:
        - devis_flags: dictionnaire item -> True/False
          Exemple: {"numero_devis": true, "total_ht_et_ttc_coherents": false}
        - custom_weights: surcharge optionnelle des poids par axe
        - custom_criteria: surcharge optionnelle des items par axe
        """

        weights = custom_weights or DEFAULT_WEIGHTS
        criteria = custom_criteria or DEFAULT_CRITERIA

        scores_par_axe, missing_items = _compute_axis_scores(criteria, devis_flags)
        score_global = _compute_global_score(scores_par_axe, weights)
        questions_bloquantes = [item for item in CRITICAL_ITEMS if not devis_flags.get(item, False)]

        anomalies = _build_anomalies(missing_items)
        actions = _build_actions(scores_par_axe, questions_bloquantes)
        niveau = _risk_level(score_global, questions_bloquantes)

        return ScoreResult(
            score_global_100=round(score_global, 2),
            niveau_risque=niveau,
            scores_par_axe={k: round(v, 2) for k, v in scores_par_axe.items()},
            anomalies=anomalies,
            questions_bloquantes=questions_bloquantes,
            actions_recommandees=actions,
        ).as_dict()


def _compute_axis_scores(
    criteria: Dict[str, List[str]], devis_flags: Dict[str, bool]
) -> Tuple[Dict[str, float], Dict[str, List[str]]]:
    scores: Dict[str, float] = {}
    missing: Dict[str, List[str]] = {}

    for axis, items in criteria.items():
        if not items:
            scores[axis] = 0.0
            missing[axis] = []
            continue

        present = [item for item in items if devis_flags.get(item, False)]
        absent = [item for item in items if not devis_flags.get(item, False)]

        ratio = len(present) / len(items)
        scores[axis] = ratio * 100.0
        missing[axis] = absent

    return scores, missing


def _compute_global_score(scores_par_axe: Dict[str, float], weights: Dict[str, float]) -> float:
    # Le score global est une somme ponderee sur 100.
    total_weight = sum(weights.values()) or 1.0
    weighted = 0.0
    for axis, axis_score in scores_par_axe.items():
        weighted += axis_score * (weights.get(axis, 0.0) / total_weight)
    return weighted


def _build_anomalies(missing_items: Dict[str, List[str]]) -> List[str]:
    anomalies: List[str] = []
    for axis, missing in missing_items.items():
        if missing:
            anomalies.append(f"{axis}: elements manquants -> {', '.join(missing)}")
    return anomalies


def _build_actions(scores_par_axe: Dict[str, float], questions_bloquantes: List[str]) -> List[str]:
    actions: List[str] = []

    if questions_bloquantes:
        actions.append(
            "Completer en priorite les champs critiques: " + ", ".join(questions_bloquantes)
        )

    for axis, score in scores_par_axe.items():
        if score < 60:
            actions.append(f"Renforcer l'axe {axis} (score {score:.1f}/100)")

    if not actions:
        actions.append("Devis coherent: lancer une verification humaine finale avant envoi.")

    return actions


def _risk_level(score_global: float, questions_bloquantes: List[str]) -> str:
    if questions_bloquantes:
        return "eleve"
    if score_global >= 80:
        return "faible"
    if score_global >= 60:
        return "moyen"
    return "eleve"
