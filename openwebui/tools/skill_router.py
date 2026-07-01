"""
title: Skill Router
author: localia
version: 1.0.0
required_open_webui_version: 0.6.32
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field


PIPELINE_NEXT_SKILLS: List[str] = [
    "normalisation_unites",
    "detection_ambiguite",
    "estimation_complexite",
    "moteur_rendement",
    "controle_coherence",
    "sortie_json_finale",
]


TASK_TO_SKILL: Dict[str, str] = {
    "tonte_pelouse": "tonte_pelouse_extraction",
    "taille_haie": "taille_haie_extraction",
    "debroussaillage_prairie": "debroussaillage_prairie_extraction",
    "desherbage": "desherbage_extraction",
    "taille_arbustes": "taille_arbustes_extraction",
    "taille_rosiers": "taille_rosiers_extraction",
}


KEYWORDS: Dict[str, List[str]] = {
    "tonte_pelouse": ["tonte", "pelouse", "gazon"],
    "taille_haie": ["haie", "tailler la haie", "taille haie"],
    "debroussaillage_prairie": ["debroussaillage", "prairie", "friche"],
    "desherbage": ["desherbage", "desherber", "mauvaises herbes"],
    "taille_arbustes": ["arbuste", "arbustes", "taille arbuste"],
    "taille_rosiers": ["rosier", "rosiers", "taille rosier"],
}


class Tools:
    class Valves(BaseModel):
        SKILLS_DIR: str = Field(
            default="/app/backend/data/skills",
            description="Repertoire des skills JSON",
        )

    class UserValves(BaseModel):
        pass

    def __init__(self):
        self.valves = self.Valves()

    def list_skills_catalog(self, include_output_schema: bool = False) -> Dict[str, Any]:
        """
        Liste les skills d'extraction disponibles et leur validite structurelle.
        """
        files = self._list_json_skill_files()
        skills: List[Dict[str, Any]] = []

        for file_path in files:
            data = self._read_json(file_path)
            if not isinstance(data, dict):
                skills.append(
                    {
                        "file": file_path.name,
                        "status": "invalid",
                        "reason": "json_non_objet",
                    }
                )
                continue

            entry: Dict[str, Any] = {
                "file": file_path.name,
                "id": data.get("id"),
                "objectif": data.get("objectif"),
                "status": "ok" if self._is_valid_skill(data) else "invalid",
            }

            if include_output_schema:
                entry["output_keys"] = sorted(list((data.get("output_json") or {}).keys()))

            skills.append(entry)

        return {
            "skills_dir": self.valves.SKILLS_DIR,
            "skills_count": len(skills),
            "skills": skills,
            "next_pipeline_skills": PIPELINE_NEXT_SKILLS,
            "test_prompts": self.get_test_prompts(),
        }

    def get_test_prompts(self) -> Dict[str, Any]:
        """
        Retourne un mini jeu de prompts de test (1 par prestation).
        """
        return {
            "language": "fr",
            "prompts": [
                {
                    "type_tache": "tonte_pelouse",
                    "texte_demande": "Bonjour, je souhaite une tonte de pelouse sur 350 m2, terrain plat avec quelques obstacles et finition des bordures.",
                },
                {
                    "type_tache": "taille_haie",
                    "texte_demande": "Pouvez-vous tailler une haie de 42 ml, 2 m de haut, 2 faces, avec evacuation des dechets verts ?",
                },
                {
                    "type_tache": "debroussaillage_prairie",
                    "texte_demande": "Debroussaillage d'une prairie de 1200 m2, vegetation dense, pente moyenne, acces moyen.",
                },
                {
                    "type_tache": "desherbage",
                    "texte_demande": "Desherbage manuel d'allees et bordures sur environ 180 m2, presence de gravillons, intervention ponctuelle.",
                },
                {
                    "type_tache": "taille_arbustes",
                    "texte_demande": "Taille d'entretien de 18 arbustes, hauteur moyenne 1,6 m, evacuation des coupes et acces facile.",
                },
                {
                    "type_tache": "taille_rosiers",
                    "texte_demande": "Taille de 25 rosiers buissons et 6 rosiers grimpants avec evacuation, terrain accessible.",
                },
            ],
        }

    def route_skill(self, texte_demande: str, type_tache_hint: str = "") -> Dict[str, Any]:
        """
        Selectionne le skill d'extraction adapte puis retourne le chainage recommande.

        Parametres:
        - texte_demande: texte libre utilisateur
        - type_tache_hint: hint explicite (optionnel), ex: taille_haie
        """
        detected_task, reason = self._detect_task(texte_demande=texte_demande, type_tache_hint=type_tache_hint)

        if not detected_task:
            return {
                "status": "error",
                "message": "type_tache_non_detecte",
                "questions_bloquantes": [
                    "Precisez la prestation: tonte pelouse, taille haie, debroussaillage prairie, desherbage, taille arbustes, taille rosiers."
                ],
                "next_pipeline_skills": PIPELINE_NEXT_SKILLS,
            }

        skill_id = TASK_TO_SKILL[detected_task]
        skill_data = self._load_skill_by_id(skill_id)
        pipeline_status = self._check_pipeline_skills_present()

        if pipeline_status["missing_skills"]:
            return {
                "status": "error",
                "message": "pipeline_skills_manquants",
                "skill_id": skill_id,
                "questions_bloquantes": [
                    "Le pipeline aval est incomplet. Ajoutez les skills manquants avant execution."
                ],
                "missing_pipeline_skills": pipeline_status["missing_skills"],
                "present_pipeline_skills": pipeline_status["present_skills"],
                "next_pipeline_skills": PIPELINE_NEXT_SKILLS,
            }

        if skill_data is None:
            return {
                "status": "error",
                "message": "skill_introuvable",
                "skill_id": skill_id,
                "questions_bloquantes": [
                    f"Le skill {skill_id} est introuvable dans {self.valves.SKILLS_DIR}."
                ],
                "next_pipeline_skills": PIPELINE_NEXT_SKILLS,
            }

        return {
            "status": "ok",
            "type_tache_detecte": detected_task,
            "routing_reason": reason,
            "selected_skill_id": skill_data.get("id"),
            "selected_skill_file": self._find_file_by_skill_id(skill_data.get("id")),
            "selected_skill": skill_data,
            "pipeline_status": pipeline_status,
            "next_pipeline_skills": PIPELINE_NEXT_SKILLS,
        }

    def route_and_extract(self, texte_demande: str, type_tache_hint: str = "") -> Dict[str, Any]:
        """
        Route vers le bon skill d'extraction et renvoie un objet pret pour la suite du pipeline.

        Remarque:
        - Cette methode ne remplace pas l'extraction LLM.
        - Elle fournit le schema de sortie attendu et la feuille de route d'execution.
        """
        routed = self.route_skill(texte_demande=texte_demande, type_tache_hint=type_tache_hint)
        if routed.get("status") != "ok":
            return routed

        selected_skill = routed.get("selected_skill", {})
        output_schema = selected_skill.get("output_json", {})

        return {
            "status": "ok",
            "type_tache_detecte": routed.get("type_tache_detecte"),
            "selected_skill_id": routed.get("selected_skill_id"),
            "selected_skill_file": routed.get("selected_skill_file"),
            "routing_reason": routed.get("routing_reason"),
            "texte_demande": texte_demande,
            "extraction_schema": output_schema,
            "pipeline_status": routed.get("pipeline_status"),
            "next_pipeline_skills": routed.get("next_pipeline_skills", PIPELINE_NEXT_SKILLS),
            "instructions": [
                "Executer l'extraction selon extraction_schema.",
                "Passer le resultat vers normalisation_unites.",
                "Poursuivre le pipeline jusqu'a sortie_json_finale.",
            ],
        }

    def _list_json_skill_files(self) -> List[Path]:
        base = Path(self.valves.SKILLS_DIR)
        if not base.exists() or not base.is_dir():
            return []
        return sorted(base.glob("*_extraction.json"))

    def _read_json(self, file_path: Path) -> Any:
        try:
            with file_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _is_valid_skill(self, data: Dict[str, Any]) -> bool:
        required_keys = ["id", "objectif", "inputs", "regles", "output_json"]
        return all(k in data for k in required_keys)

    def _find_file_by_skill_id(self, skill_id: str | None) -> str | None:
        if not skill_id:
            return None
        for file_path in self._list_json_skill_files():
            data = self._read_json(file_path)
            if isinstance(data, dict) and data.get("id") == skill_id:
                return file_path.name
        return None

    def _load_skill_by_id(self, skill_id: str) -> Dict[str, Any] | None:
        for file_path in self._list_json_skill_files():
            data = self._read_json(file_path)
            if isinstance(data, dict) and data.get("id") == skill_id:
                return data
        return None

    def _check_pipeline_skills_present(self) -> Dict[str, Any]:
        present_ids = set()

        base = Path(self.valves.SKILLS_DIR)
        if base.exists() and base.is_dir():
            for file_path in sorted(base.glob("*.json")):
                data = self._read_json(file_path)
                if isinstance(data, dict) and isinstance(data.get("id"), str):
                    present_ids.add(data["id"])

        missing = [skill for skill in PIPELINE_NEXT_SKILLS if skill not in present_ids]
        present = [skill for skill in PIPELINE_NEXT_SKILLS if skill in present_ids]

        return {
            "status": "ok" if not missing else "incomplete",
            "present_skills": present,
            "missing_skills": missing,
        }

    def _detect_task(self, texte_demande: str, type_tache_hint: str = "") -> tuple[str | None, str]:
        hint = (type_tache_hint or "").strip().lower()
        if hint in TASK_TO_SKILL:
            return hint, "hint"

        text = (texte_demande or "").lower()
        for task, words in KEYWORDS.items():
            for word in words:
                if word in text:
                    return task, f"keyword:{word}"

        return None, "none"
