"""Le schéma est le contrat du projet : c'est lui qui est testé en premier."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from support_triage.schema import CHAMPS_EVALUES, Categorie, Qualification


def test_qualification_valide(fabrique) -> None:  # noqa: ANN001
    q = fabrique()
    assert q.categorie is Categorie.ANOMALIE
    assert q.informations_manquantes == []


def test_categorie_inventee_est_rejetee(fabrique) -> None:  # noqa: ANN001
    """Une valeur hors énumération doit échouer ici, pas se propager plus loin."""
    with pytest.raises(ValidationError):
        Qualification(**{**fabrique().model_dump(), "categorie": "urgence_absolue"})


def test_confiance_hors_bornes_est_rejetee(fabrique) -> None:  # noqa: ANN001
    with pytest.raises(ValidationError):
        Qualification(**{**fabrique().model_dump(), "confiance": 1.4})
    with pytest.raises(ValidationError):
        Qualification(**{**fabrique().model_dump(), "confiance": -0.1})


def test_resume_vide_est_rejete(fabrique) -> None:  # noqa: ANN001
    with pytest.raises(ValidationError):
        Qualification(**{**fabrique().model_dump(), "resume": "   "})


def test_les_espaces_sont_nettoyes(fabrique) -> None:  # noqa: ANN001
    q = Qualification(**{**fabrique().model_dump(), "resume": "  un résumé  "})
    assert q.resume == "un résumé"


def test_informations_manquantes_nettoyees(fabrique) -> None:  # noqa: ANN001
    q = Qualification(
        **{**fabrique().model_dump(), "informations_manquantes": ["  Référence  ", "", "   "]}
    )
    assert q.informations_manquantes == ["Référence"]


def test_champs_evalues_existent_sur_le_modele(fabrique) -> None:  # noqa: ANN001
    q = fabrique()
    for champ in CHAMPS_EVALUES:
        assert hasattr(q, champ), champ


def test_serialisation_json(fabrique) -> None:  # noqa: ANN001
    """La sortie doit être transmissible telle quelle à un système tiers."""
    charge = fabrique().model_dump(mode="json")
    assert charge["categorie"] == "anomalie"
    assert isinstance(charge["confiance"], float)

def test_chaine_vide_devient_liste_vide(fabrique) -> None:  # noqa: ANN001
    """Cas rencontré en production : le modèle renvoie "" plutôt que []."""
    q = Qualification(**{**fabrique().model_dump(), "informations_manquantes": ""})
    assert q.informations_manquantes == []


def test_mention_aucune_devient_liste_vide(fabrique) -> None:  # noqa: ANN001
    for mot in ("aucune", "Aucun", "néant", "N/A", "-"):
        q = Qualification(**{**fabrique().model_dump(), "informations_manquantes": mot})
        assert q.informations_manquantes == [], mot


def test_chaine_multiple_est_decoupee(fabrique) -> None:  # noqa: ANN001
    q = Qualification(
        **{
            **fabrique().model_dump(),
            "informations_manquantes": "Référence de la pièce; Message d'erreur",
        }
    )
    assert q.informations_manquantes == ["Référence de la pièce", "Message d'erreur"]


def test_valeur_nulle_devient_liste_vide(fabrique) -> None:  # noqa: ANN001
    q = Qualification(**{**fabrique().model_dump(), "informations_manquantes": None})
    assert q.informations_manquantes == []
