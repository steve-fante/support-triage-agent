"""Tests sur le jeu de données lui-même.

Un jeu d'évaluation incohérent invalide toutes les mesures qui en découlent.
Ces tests sont donc au moins aussi importants que ceux du code.
"""

from __future__ import annotations

from support_triage.baseline import ROUTAGE
from support_triage.dataset import load_tickets, split_tickets
from support_triage.schema import Categorie, Equipe


def test_le_jeu_est_charge(tickets) -> None:  # noqa: ANN001
    assert len(tickets) == 45


def test_repartition_des_ensembles(exemples, evaluation) -> None:  # noqa: ANN001
    assert len(exemples) == 6
    assert len(evaluation) == 39


def test_aucune_fuite_entre_les_ensembles(exemples, evaluation) -> None:  # noqa: ANN001
    """Un ticket ne peut pas servir d'exemple et de cas d'évaluation."""
    assert not {t.id for t in exemples} & {t.id for t in evaluation}


def test_identifiants_uniques(tickets) -> None:  # noqa: ANN001
    identifiants = [t.id for t in tickets]
    assert len(identifiants) == len(set(identifiants))


def test_textes_uniques(tickets) -> None:  # noqa: ANN001
    textes = [t.texte for t in tickets]
    assert len(textes) == len(set(textes))


def test_routage_coherent_avec_les_regles(tickets) -> None:  # noqa: ANN001
    """Le routage annoté doit suivre la table, sauf exception documentée.

    L'exception prévue par les règles : une anomalie dont la correction exige du
    développement part directement à l'équipe de développement.
    """
    for ticket in tickets:
        attendu = ROUTAGE[ticket.categorie]
        exception_dev = (
            ticket.categorie is Categorie.ANOMALIE and ticket.equipe is Equipe.DEVELOPPEMENT
        )
        assert ticket.equipe is attendu or exception_dev, (
            f"{ticket.id} : {ticket.categorie.value} routé vers {ticket.equipe.value}"
        )


def test_toutes_les_categories_sont_representees(evaluation) -> None:  # noqa: ANN001
    """Une classe absente du jeu d'évaluation ne peut pas être mesurée."""
    presentes = {t.categorie for t in evaluation}
    assert presentes == set(Categorie)


def test_les_priorites_critiques_sont_rares(evaluation) -> None:  # noqa: ANN001
    """Le déséquilibre est voulu : il reflète une file réelle et justifie le F1 macro."""
    critiques = [t for t in evaluation if t.priorite.value.startswith("P1")]
    assert 1 <= len(critiques) <= 5


def test_fichier_absent(tmp_path) -> None:  # noqa: ANN001
    import pytest

    with pytest.raises(FileNotFoundError):
        load_tickets(tmp_path / "absent.jsonl")


def test_ligne_invalide_est_signalee(tmp_path) -> None:  # noqa: ANN001
    import pytest

    fichier = tmp_path / "mauvais.jsonl"
    fichier.write_text('{"id": "X1"}\n', encoding="utf-8")
    with pytest.raises(ValueError) as info:
        load_tickets(fichier)
    assert "ligne 1" in str(info.value)


def test_split_tickets_ignore_les_autres_valeurs() -> None:
    assert split_tickets([]) == ([], [])
