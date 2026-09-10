"""Le contrat de sortie de l'agent.

Tout le projet tourne autour de ce fichier. Un agent de triage n'est utile que
si sa sortie est exploitable par un système d'information : un texte libre ne
l'est pas, un objet typé et validé l'est.

Les libellés des énumérations sont en français et repris tels quels dans le
prompt : le modèle n'a donc jamais à traduire, et une valeur inventée est
rejetée par Pydantic avant d'atteindre le reste du programme.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Categorie(str, Enum):
    """Nature de la demande."""

    ANOMALIE = "anomalie"
    QUESTION_UTILISATION = "question_utilisation"
    PROBLEME_DONNEES = "probleme_donnees"
    DEMANDE_EVOLUTION = "demande_evolution"
    ACCES_DROITS = "acces_droits"
    PERFORMANCE = "performance"
    FORMATION = "formation"
    HORS_PERIMETRE = "hors_perimetre"


class Module(str, Enum):
    """Module Odoo concerné."""

    VENTES = "ventes"
    ACHATS = "achats"
    STOCK = "stock"
    COMPTABILITE = "comptabilite"
    PRODUCTION = "production"
    RH = "rh"
    CRM = "crm"
    PROJETS = "projets"
    SITE_WEB = "site_web"
    TRANSVERSE = "transverse"
    INCONNU = "inconnu"


class Priorite(str, Enum):
    """Niveau de priorité, du plus urgent au moins urgent."""

    P1_CRITIQUE = "P1_critique"
    P2_MAJEUR = "P2_majeur"
    P3_MINEUR = "P3_mineur"
    P4_COSMETIQUE = "P4_cosmetique"


class Equipe(str, Enum):
    """Équipe vers laquelle router la demande."""

    SUPPORT_N1 = "support_n1"
    SUPPORT_N2_FONCTIONNEL = "support_n2_fonctionnel"
    DEVELOPPEMENT = "developpement"
    INFRASTRUCTURE = "infrastructure"
    ADMINISTRATION_FONCTIONNELLE = "administration_fonctionnelle"
    COMMERCIAL = "commercial"


class Qualification(BaseModel):
    """Résultat du triage d'une demande.

    `confiance` n'est pas décoratif : c'est lui qui déclenche l'escalade vers un
    humain lorsque le modèle n'est pas sûr. Voir `triage.py`.
    """

    categorie: Categorie = Field(description="Nature de la demande")
    module: Module = Field(description="Module Odoo concerné, 'inconnu' si indéterminable")
    priorite: Priorite = Field(description="Priorité selon les règles de l'entreprise")
    equipe: Equipe = Field(description="Équipe qui doit prendre en charge la demande")
    resume: str = Field(description="Reformulation du besoin en une phrase, 20 mots maximum")
    est_bloquant: bool = Field(description="Vrai si l'utilisateur ne peut plus travailler")
    informations_manquantes: list[str] = Field(
        default_factory=list,
        description=(
            "Informations indispensables absentes de la demande et à réclamer au demandeur. "
            "Liste vide si la demande est complète."
        ),
    )
    confiance: float = Field(
        ge=0.0, le=1.0, description="Confiance dans cette qualification, entre 0 et 1"
    )
    justification: str = Field(description="En une phrase, ce qui motive la priorité retenue")

    @field_validator("resume", "justification")
    @classmethod
    def _non_vide(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Le champ ne peut pas être vide.")
        return value.strip()

    @field_validator("informations_manquantes", mode="before")
    @classmethod
    def _normaliser_liste(cls, value: object) -> list[str]:
        """Accepte les variantes que les modèles produisent en pratique.

        Un modèle qui n'a rien à réclamer renvoie souvent une chaîne vide, un
        « aucune », ou une énumération dans un seul texte, plutôt qu'un tableau
        vide. Refuser ces formes ferait échouer toute la qualification pour un
        détail de sérialisation, alors que l'intention est parfaitement claire.

        Un schéma robuste ne se contente pas de valider : il normalise.
        """
        if value is None:
            return []
        if isinstance(value, str):
            texte = value.strip()
            if not texte or texte.lower() in {"aucune", "aucun", "néant", "neant", "n/a", "-"}:
                return []
            morceaux = re.split(r"[;\n]+", texte)
            return [m.strip(" -•\t") for m in morceaux if m.strip(" -•\t")]
        if isinstance(value, list | tuple):
            return [str(v).strip() for v in value if str(v).strip()]
        return [str(value).strip()]


# Champs sur lesquels porte l'évaluation. Les champs textuels libres
# (resume, justification) ne sont pas comparables automatiquement.
CHAMPS_EVALUES: tuple[str, ...] = ("categorie", "module", "priorite", "equipe", "est_bloquant")


class Decision(BaseModel):
    """Ce que le système renvoie réellement : la qualification et son traitement."""

    qualification: Qualification
    escalade_humaine: bool = Field(
        description="Vrai si la confiance est insuffisante pour un traitement automatique"
    )
    motif_escalade: str | None = None
    source: str = Field(description="Classifieur utilisé : 'llm' ou 'regles'")
