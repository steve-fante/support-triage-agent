"""Le prompt est du code : il mérite des tests, en particulier contre la fuite."""

from __future__ import annotations

from support_triage.prompt import construire_prompt


def test_les_regles_metier_sont_incluses(regles_path, exemples) -> None:  # noqa: ANN001
    prompt = construire_prompt(regles_path, exemples)
    assert "P1_critique" in prompt
    assert "Routage" in prompt


def test_les_exemples_sont_inclus(regles_path, exemples) -> None:  # noqa: ANN001
    prompt = construire_prompt(regles_path, exemples)
    for ticket in exemples:
        assert ticket.texte[:40] in prompt


def test_aucune_fuite_du_jeu_d_evaluation(regles_path, exemples, evaluation) -> None:  # noqa: ANN001
    """Le test le plus important du fichier.

    Si un ticket d'évaluation figurait dans le prompt, le modèle en connaîtrait
    la réponse et le score mesuré serait sans valeur.
    """
    prompt = construire_prompt(regles_path, exemples)
    for ticket in evaluation:
        extrait = ticket.texte[:60]
        assert extrait not in prompt, f"{ticket.id} présent dans le prompt"


def test_prompt_sans_exemple(regles_path) -> None:  # noqa: ANN001
    prompt = construire_prompt(regles_path, [])
    assert "EXEMPLES" not in prompt
    assert "RÈGLES MÉTIER" in prompt


def test_consignes_de_prudence_presentes(regles_path, exemples) -> None:  # noqa: ANN001
    prompt = construire_prompt(regles_path, exemples)
    assert "inconnu" in prompt
    assert "confiance" in prompt.lower()
