"""Tests de l'orchestration, avec un classifieur scripté — aucun appel réseau."""

from __future__ import annotations

import pytest

from support_triage.baseline import BaselineClassifier
from support_triage.llm_classifier import ScriptedClassifier
from support_triage.schema import Priorite
from support_triage.triage import TriageService

DEMANDE = "La facture FAC00123 affiche une TVA à 19,6 % au lieu de 20 %."


def test_confiance_elevee_passe_en_automatique(fabrique) -> None:  # noqa: ANN001
    service = TriageService(ScriptedClassifier([fabrique(confiance=0.92)]), seuil_confiance=0.75)
    decision = service.trier(DEMANDE)
    assert decision.escalade_humaine is False
    assert decision.motif_escalade is None
    assert decision.source == "llm"


def test_confiance_faible_declenche_la_revue(fabrique) -> None:  # noqa: ANN001
    service = TriageService(ScriptedClassifier([fabrique(confiance=0.40)]), seuil_confiance=0.75)
    decision = service.trier(DEMANDE)
    assert decision.escalade_humaine is True
    assert "0.40" in decision.motif_escalade


def test_priorite_critique_toujours_revue_meme_confiant(fabrique) -> None:  # noqa: ANN001
    """Une P1 ne part jamais en automatique, quelle que soit la confiance."""
    service = TriageService(
        ScriptedClassifier([fabrique(confiance=0.99, priorite=Priorite.P1_CRITIQUE)]),
        seuil_confiance=0.75,
    )
    decision = service.trier(DEMANDE)
    assert decision.escalade_humaine is True
    assert "critique" in decision.motif_escalade


def test_panne_du_modele_replie_sur_les_regles() -> None:
    service = TriageService(
        ScriptedClassifier([ConnectionError("API injoignable")]), seuil_confiance=0.75
    )
    decision = service.trier(DEMANDE)
    assert decision.source == "regles"
    assert decision.escalade_humaine is True
    assert "repli" in decision.motif_escalade.lower()


def test_panne_propagee_si_repli_desactive() -> None:
    service = TriageService(
        ScriptedClassifier([ConnectionError("API injoignable")]), repli_sur_regles=False
    )
    with pytest.raises(ConnectionError):
        service.trier(DEMANDE)


def test_demande_vide_refusee() -> None:
    service = TriageService(BaselineClassifier())
    with pytest.raises(ValueError):
        service.trier("   ")


def test_seuil_invalide_refuse() -> None:
    with pytest.raises(ValueError):
        TriageService(BaselineClassifier(), seuil_confiance=1.5)


def test_le_texte_est_transmis_au_classifieur(fabrique) -> None:  # noqa: ANN001
    scripte = ScriptedClassifier([fabrique()])
    TriageService(scripte).trier(DEMANDE)
    assert scripte.appels == [DEMANDE]


def test_seuil_a_zero_automatise_tout(fabrique) -> None:  # noqa: ANN001
    service = TriageService(ScriptedClassifier([fabrique(confiance=0.01)]), seuil_confiance=0.0)
    assert service.trier(DEMANDE).escalade_humaine is False


def test_seuil_a_un_escalade_tout(fabrique) -> None:  # noqa: ANN001
    service = TriageService(ScriptedClassifier([fabrique(confiance=0.99)]), seuil_confiance=1.0)
    assert service.trier(DEMANDE).escalade_humaine is True
