"""Orchestration du triage.

Trois responsabilités, et rien d'autre :

1. appeler le classifieur ;
2. décider si la qualification part en traitement automatique ou en revue
   humaine, selon le seuil de confiance ;
3. se rabattre sur les règles si le modèle est indisponible.

Le point 2 est le cœur métier. Un système de triage qui automatise tout est
dangereux ; un système qui n'automatise rien est inutile. Le seuil est le
curseur entre les deux, et il se règle avec les données de calibration.
"""

from __future__ import annotations

from .baseline import classer_par_regles
from .llm_classifier import Classifier
from .schema import Decision, Qualification


class TriageService:
    def __init__(
        self,
        classifier: Classifier,
        seuil_confiance: float = 0.75,
        repli_sur_regles: bool = True,
    ) -> None:
        if not 0.0 <= seuil_confiance <= 1.0:
            raise ValueError("Le seuil de confiance doit être compris entre 0 et 1.")
        self.classifier = classifier
        self.seuil = seuil_confiance
        self.repli = repli_sur_regles

    def trier(self, texte: str) -> Decision:
        if not texte or not texte.strip():
            raise ValueError("La demande est vide.")

        try:
            qualification = self.classifier.classer(texte)
            source = self.classifier.nom
            incident = None
        except Exception as exc:  # noqa: BLE001 - toute panne du modèle est traitée pareil
            if not self.repli:
                raise
            qualification = classer_par_regles(texte)
            source = "regles"
            incident = f"Modèle indisponible ({type(exc).__name__}), repli sur les règles"

        return self._decider(qualification, source, incident)

    def _decider(
        self, qualification: Qualification, source: str, incident: str | None
    ) -> Decision:
        motifs: list[str] = []
        if incident:
            motifs.append(incident)
        if qualification.confiance < self.seuil:
            motifs.append(
                f"Confiance {qualification.confiance:.2f} inférieure au seuil {self.seuil:.2f}"
            )
        if qualification.priorite.value.startswith("P1"):
            motifs.append("Priorité critique : validation humaine systématique")

        return Decision(
            qualification=qualification,
            escalade_humaine=bool(motifs),
            motif_escalade=" ; ".join(motifs) if motifs else None,
            source=source,
        )
