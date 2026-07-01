"""
Outil OpenWebUI: calcul_devis
- Appelle une API HTTP distante (ton endpoint PHP)
- Retourne le JSON de chiffrage
"""

from pydantic import BaseModel, Field
import requests


class Tools:
    class Valves(BaseModel):
        DEVIS_API_URL: str = Field(
            default="https://ai.ejeri.fr/api/devis",
            description="URL de l'API devis"
        )
        DEVIS_API_KEY: str = Field(
            default="CHANGE_ME_STRONG_KEY",
            description="Clé API envoyée dans X-API-Key"
        )
        TIMEOUT_SECONDS: int = Field(
            default=90,
            description="Timeout HTTP"
        )

    class UserValves(BaseModel):
        pass

    def __init__(self):
        self.valves = self.Valves()

    def calcul_devis(
        self,
        type_taille: str,
        longueur_ml: float,
        hauteur_m: float,
        nb_faces: int,
        acces: str,
        evacuation: str,
        adventices: str = ""
    ) -> dict:
        """
        Calcule un devis via API distante.

        Paramètres attendus:
        - type_taille: taille_haie_entretien|taille_haie_formation|rabattage
        - longueur_ml: ex 60
        - hauteur_m: ex 2.5
        - nb_faces: 1..4
        - acces: tres_facile|facile|moyen|difficile
        - evacuation: oui|non
        - adventices: texte libre optionnel
        """
        payload = {
            "type_taille": type_taille,
            "longueur_ml": longueur_ml,
            "hauteur_m": hauteur_m,
            "nb_faces": nb_faces,
            "acces": acces,
            "evacuation": evacuation,
            "adventices": adventices,
        }

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.valves.DEVIS_API_KEY
        }

        try:
            r = requests.post(
                self.valves.DEVIS_API_URL,
                json=payload,
                headers=headers,
                timeout=self.valves.TIMEOUT_SECONDS
            )
            # Si erreur HTTP, on essaie de remonter le body
            if r.status_code >= 400:
                try:
                    return {
                        "status": "error",
                        "http_status": r.status_code,
                        "details": r.json()
                    }
                except Exception:
                    return {
                        "status": "error",
                        "http_status": r.status_code,
                        "details": r.text
                    }

            return r.json()

        except requests.Timeout:
            return {"status": "error", "message": "timeout_api_devis"}
        except Exception as e:
            return {"status": "error", "message": f"tool_exception: {str(e)}"}