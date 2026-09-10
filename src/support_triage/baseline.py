"""Ligne de base : un classifieur par règles, sans modèle de langage.

Pourquoi ce module existe, alors que le projet porte sur un agent IA :

1. **Pour mesurer l'apport réel du modèle.** Annoncer « 85 % d'exactitude » ne
   veut rien dire si de simples mots-clés en obtiennent 80. La comparaison est
   la seule façon de justifier le coût et la latence d'un appel au modèle.
2. **Pour tester hors ligne.** La ligne de base est déterministe et gratuite :
   toute la chaîne — chargement, triage, seuil, métriques — est couverte par des
   tests sans clé d'API.
3. **Pour dégrader proprement.** Si l'API est indisponible, le système peut
   basculer sur les règles plutôt que de ne rien renvoyer.

Elle est écrite honnêtement, sans être bridée pour flatter le modèle : c'est
l'implémentation directe du fichier `data/regles_priorisation.md`.
"""

from __future__ import annotations

import re
import unicodedata

from .schema import Categorie, Decision, Equipe, Module, Priorite, Qualification

# --------------------------------------------------------------------- routage

ROUTAGE: dict[Categorie, Equipe] = {
    Categorie.QUESTION_UTILISATION: Equipe.SUPPORT_N1,
    Categorie.FORMATION: Equipe.SUPPORT_N1,
    Categorie.ANOMALIE: Equipe.SUPPORT_N2_FONCTIONNEL,
    Categorie.PROBLEME_DONNEES: Equipe.SUPPORT_N2_FONCTIONNEL,
    Categorie.DEMANDE_EVOLUTION: Equipe.DEVELOPPEMENT,
    Categorie.PERFORMANCE: Equipe.INFRASTRUCTURE,
    Categorie.ACCES_DROITS: Equipe.ADMINISTRATION_FONCTIONNELLE,
    Categorie.HORS_PERIMETRE: Equipe.COMMERCIAL,
}

# ------------------------------------------------------------------- lexiques

MODULES: dict[Module, tuple[str, ...]] = {
    Module.STOCK: ("stock", "livraison", "expedition", "entrepot", "reception", "magasin",
                   "transfert", "emplacement", "inventaire", "article", "lot"),
    Module.COMPTABILITE: ("facture", "comptab", "tva", "ecriture", "journal", "fec",
                          "cloture", "reglement", "avoir"),
    Module.VENTES: ("devis", "commande client", "bon de commande", "prix de vente",
                    "tarif", "catalogue", "commercial"),
    Module.ACHATS: ("fournisseur", "achat", "commande fournisseur", "approvisionnement"),
    Module.PRODUCTION: ("production", "fabrication", "nomenclature", "ordre de fabrication",
                        "of0", "produit fini", "cout de revient"),
    Module.RH: ("conge", "paie", "salarie", "employe", "absence", "solde", "planning"),
    Module.CRM: ("contact", "prospect", "client", "relance", "opportunite", "piste"),
    Module.PROJETS: ("projet", "tache", "feuille de temps", "marge par projet"),
    Module.SITE_WEB: ("site web", "site internet", "ecommerce", "formulaire de contact",
                      "boutique en ligne"),
}

CATEGORIES: dict[Categorie, tuple[str, ...]] = {
    Categorie.ACCES_DROITS: ("mot de passe", "connecter", "connexion", "droit", "acces",
                             "compte", "desactiver", "permission", "identifiant"),
    Categorie.PERFORMANCE: ("lent", "lenteur", "minute", "seconde", "rame", "temps de reponse",
                            "delai depasse", "sauvegarde", "espace disque", "indisponib"),
    Categorie.FORMATION: ("formation", "former", "session", "accompagnement", "demi-journee"),
    Categorie.DEMANDE_EVOLUTION: ("serait-il possible", "serait-il envisageable",
                                  "peut-on ajouter", "ajouter un champ", "developper",
                                  "ce serait bien", "aimerions", "envisageable"),
    Categorie.PROBLEME_DONNEES: ("double", "doublon", "fusionner", "disparu", "manquant",
                                 "import", "reprise de donnees", "orthographi", "faux",
                                 "en triple"),
    Categorie.HORS_PERIMETRE: ("imprimante", "reseau", "demarchage", "visibilite",
                               "contrat de maintenance", "devis pour", "utilisateurs supplementaires"),
    Categorie.ANOMALIE: ("erreur", "message rouge", "ne fonctionne", "ne marche", "bloque",
                         "impossible", "refuse", "bug", "anormal", "au lieu de", "faussé"),
    Categorie.QUESTION_UTILISATION: ("comment", "ou est-ce", "ou puis-je", "quelle difference",
                                     "peut-on parametrer", "je voudrais savoir", "expliquer"),
}

URGENCE_CRITIQUE = ("toute l'entreprise", "plus personne", "a l'arret", "arret",
                    "aucune facture", "on ne peut plus", "rien ne part", "urgent")
URGENCE_MAJEURE = ("bloqu", "ne peux plus travailler", "echeance", "cloture",
                   "avant le", "vendredi", "comite de direction", "fin de mois")
FAIBLE_ENJEU = ("pas urgent", "pas pressé", "pas presse", "quand vous aurez le temps",
                "ce n'est pas grave", "confort", "harmoniser", "libelle")

REF_PIECE = re.compile(r"\b(?:[A-Z]{2,4}[-/]?\d{3,}|\d{5,})\b")


def _normaliser(texte: str) -> str:
    sans_accent = "".join(
        c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn"
    )
    return sans_accent.lower()


def _premier_match(texte: str, lexiques: dict) -> tuple[object | None, int]:
    """Renvoie la clé dont le lexique obtient le plus de correspondances."""
    meilleur, score = None, 0
    for cle, mots in lexiques.items():
        n = sum(1 for mot in mots if mot in texte)
        if n > score:
            meilleur, score = cle, n
    return meilleur, score


def _informations_manquantes(texte_brut: str, texte: str, categorie: Categorie) -> list[str]:
    manquantes: list[str] = []
    if categorie in (Categorie.ANOMALIE, Categorie.PROBLEME_DONNEES):
        if not REF_PIECE.search(texte_brut):
            manquantes.append("Référence de la pièce concernée")
        if "erreur" not in texte and "message" not in texte:
            manquantes.append("Message d'erreur exact ou capture d'écran")
    if len(texte_brut.split()) < 12:
        manquantes.append("Description détaillée de ce qui était attendu")
    return manquantes


def classer_par_regles(texte_brut: str) -> Qualification:
    """Qualifie une demande sans appel à un modèle de langage."""
    texte = _normaliser(texte_brut)

    categorie, score_cat = _premier_match(texte, CATEGORIES)
    if categorie is None:
        categorie, score_cat = Categorie.QUESTION_UTILISATION, 0

    module, score_mod = _premier_match(texte, MODULES)
    if module is None:
        module, score_mod = Module.INCONNU, 0
    if categorie == Categorie.HORS_PERIMETRE:
        module, score_mod = Module.INCONNU, 1

    critique = any(m in texte for m in URGENCE_CRITIQUE)
    majeure = any(m in texte for m in URGENCE_MAJEURE)
    faible = any(m in texte for m in FAIBLE_ENJEU)

    if critique:
        priorite = Priorite.P1_CRITIQUE
    elif majeure:
        priorite = Priorite.P2_MAJEUR
    elif faible or categorie in (Categorie.DEMANDE_EVOLUTION, Categorie.FORMATION):
        priorite = Priorite.P4_COSMETIQUE
    else:
        priorite = Priorite.P3_MINEUR

    bloquant = critique or "ne peux plus travailler" in texte or "ne peut plus" in texte

    # La confiance reflète le nombre de signaux trouvés, sans jamais atteindre
    # les valeurs hautes : des mots-clés ne comprennent pas une phrase.
    confiance = min(0.30 + 0.12 * score_cat + 0.08 * score_mod, 0.70)

    return Qualification(
        categorie=categorie,
        module=module,
        priorite=priorite,
        equipe=ROUTAGE[categorie],
        resume=texte_brut.strip().split(".")[0][:120] or "Demande sans description",
        est_bloquant=bloquant,
        informations_manquantes=_informations_manquantes(texte_brut, texte, categorie),
        confiance=round(confiance, 2),
        justification=f"Classement par mots-clés : {score_cat} indice(s) de catégorie trouvé(s).",
    )


class BaselineClassifier:
    """Interface commune avec le classifieur LLM, pour être interchangeables."""

    nom = "regles"

    def classer(self, texte: str) -> Qualification:
        return classer_par_regles(texte)


def decision_par_regles(texte: str, seuil: float = 0.75) -> Decision:
    qualification = classer_par_regles(texte)
    escalade = qualification.confiance < seuil
    return Decision(
        qualification=qualification,
        escalade_humaine=escalade,
        motif_escalade="Confiance insuffisante du classifieur par règles" if escalade else None,
        source="regles",
    )
