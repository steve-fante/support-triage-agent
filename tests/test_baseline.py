from __future__ import annotations

from support_triage.baseline import ROUTAGE, classer_par_regles, decision_par_regles
from support_triage.schema import Categorie, Equipe, Module, Priorite, Qualification


def test_sortie_toujours_valide(evaluation) -> None:  # noqa: ANN001
    """Quelle que soit l'entrée, la ligne de base produit un objet conforme."""
    for ticket in evaluation:
        assert isinstance(classer_par_regles(ticket.texte), Qualification)


def test_urgence_critique_detectee() -> None:
    q = classer_par_regles(
        "Plus personne ne peut se connecter, toute l'entreprise est à l'arrêt depuis ce matin."
    )
    assert q.priorite is Priorite.P1_CRITIQUE
    assert q.est_bloquant is True


def test_faible_enjeu_detecte() -> None:
    q = classer_par_regles(
        "Le libellé de la colonne pourrait être harmonisé, ce n'est pas pressé."
    )
    assert q.priorite is Priorite.P4_COSMETIQUE


def test_module_identifie() -> None:
    q = classer_par_regles("La facture client affiche une TVA erronée dans la comptabilité.")
    assert q.module is Module.COMPTABILITE


def test_module_inconnu_quand_aucun_indice() -> None:
    q = classer_par_regles("Bonjour, pouvez-vous me rappeler demain matin ?")
    assert q.module is Module.INCONNU


def test_acces_droits_route_vers_administration() -> None:
    q = classer_par_regles("J'ai oublié mon mot de passe et je ne peux plus me connecter.")
    assert q.categorie is Categorie.ACCES_DROITS
    assert q.equipe is Equipe.ADMINISTRATION_FONCTIONNELLE


def test_routage_toujours_conforme_a_la_table(evaluation) -> None:  # noqa: ANN001
    for ticket in evaluation:
        q = classer_par_regles(ticket.texte)
        assert q.equipe is ROUTAGE[q.categorie]


def test_confiance_bornee_et_modeste(evaluation) -> None:  # noqa: ANN001
    """Des mots-clés ne comprennent pas une phrase : la confiance reste basse."""
    for ticket in evaluation:
        assert 0.0 <= classer_par_regles(ticket.texte).confiance <= 0.70


def test_demande_courte_reclame_des_precisions() -> None:
    q = classer_par_regles("Ça ne marche pas.")
    assert q.informations_manquantes


def test_demande_detaillee_ne_reclame_pas_de_reference() -> None:
    q = classer_par_regles(
        "Sur la commande SO00042, le message d'erreur « Aucun emplacement » "
        "apparaît quand je valide la livraison depuis l'entrepôt principal."
    )
    assert "Référence de la pièce concernée" not in q.informations_manquantes


def test_decision_escalade_sous_le_seuil() -> None:
    d = decision_par_regles("Ça ne marche pas.", seuil=0.75)
    assert d.escalade_humaine is True
    assert d.source == "regles"


def test_accents_et_casse_sans_effet() -> None:
    a = classer_par_regles("La FACTURE est erronée")
    b = classer_par_regles("la facture est erronee")
    assert a.module is b.module
