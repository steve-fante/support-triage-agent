"""Des métriques fausses donnent une fausse confiance : elles ont leurs tests."""

from __future__ import annotations

from support_triage.metrics import (
    calibration,
    confusions,
    evaluer_champ,
    exactitude,
    f1_macro,
    scores_par_classe,
)


def test_exactitude_parfaite() -> None:
    assert exactitude(["a", "b", "c"], ["a", "b", "c"]) == 1.0


def test_exactitude_nulle() -> None:
    assert exactitude(["a", "b"], ["b", "a"]) == 0.0


def test_exactitude_partielle() -> None:
    assert exactitude(["a", "b", "c", "d"], ["a", "b", "x", "y"]) == 0.5


def test_exactitude_liste_vide() -> None:
    assert exactitude([], []) == 0.0


def test_scores_par_classe() -> None:
    attendus = ["a", "a", "b", "b"]
    predits = ["a", "b", "b", "b"]
    scores = {s.classe: s for s in scores_par_classe(attendus, predits)}
    # classe a : 1 vrai positif, 1 faux négatif, 0 faux positif
    assert scores["a"].rappel == 0.5
    assert scores["a"].precision == 1.0
    # classe b : 2 vrais positifs, 1 faux positif
    assert scores["b"].rappel == 1.0
    assert round(scores["b"].precision, 3) == 0.667


def test_f1_macro_ne_pondere_pas_par_effectif() -> None:
    """Une classe rare pèse autant qu'une classe fréquente : c'est l'intérêt."""
    attendus = ["frequent"] * 9 + ["rare"]
    predits = ["frequent"] * 10  # la classe rare n'est jamais prédite
    assert exactitude(attendus, predits) == 0.9
    assert f1_macro(attendus, predits) < 0.6


def test_confusions_triees_par_frequence() -> None:
    attendus = ["a", "a", "a", "b"]
    predits = ["b", "b", "c", "b"]
    resultat = confusions(attendus, predits)
    assert resultat[0] == ("a", "b", 2)
    assert ("a", "c", 1) in resultat


def test_aucune_confusion_si_tout_est_juste() -> None:
    assert confusions(["a", "b"], ["a", "b"]) == []


def test_evaluer_champ_assemble_le_tout() -> None:
    r = evaluer_champ("priorite", ["P1", "P2", "P2"], ["P1", "P2", "P3"])
    assert r.champ == "priorite"
    assert round(r.exactitude, 3) == 0.667
    assert r.confusions == [("P2", "P3", 1)]


def test_calibration_detecte_l_exces_de_confiance() -> None:
    """Confiance annoncée à 0,9 mais une réponse juste sur deux : écart positif."""
    tranches = calibration([0.9, 0.9], [True, False], paliers=4)
    assert len(tranches) == 1
    assert tranches[0]["ecart"] > 0.3


def test_calibration_modele_bien_regle() -> None:
    tranches = calibration([0.5, 0.5, 0.5, 0.5], [True, True, False, False], paliers=4)
    assert abs(tranches[0]["ecart"]) < 0.05


def test_calibration_liste_vide() -> None:
    assert calibration([], []) == []


def test_calibration_inclut_la_confiance_maximale() -> None:
    tranches = calibration([1.0], [True], paliers=4)
    assert tranches and tranches[0]["effectif"] == 1
