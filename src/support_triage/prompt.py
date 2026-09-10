"""Construction du prompt système.

Le prompt est assemblé à partir de trois sources, et non écrit en dur :

- les règles métier, lues depuis `data/regles_priorisation.md` ;
- les exemples annotés du jeu `few_shot` ;
- des consignes de comportement constantes.

Conséquence pratique : adapter l'agent à un nouveau client revient à modifier
un fichier Markdown et quelques exemples. Le code ne bouge pas.
"""

from __future__ import annotations

import json
from pathlib import Path

from .dataset import Ticket

CONSIGNES = """Tu qualifies les demandes de support d'un ERP Odoo, en français.

Tu reçois le texte brut d'une demande — courriel, ticket, message — souvent mal
rédigé, parfois incomplet. Tu produis une qualification structurée.

Règles de comportement :

1. Applique strictement les règles de priorisation fournies ci-dessous. Elles
   priment sur ton intuition.
2. En cas d'hésitation entre deux priorités, retiens la plus basse, sauf si la
   demande mentionne un blocage explicite ou une échéance datée.
3. Si le module concerné n'est pas identifiable, réponds « inconnu » plutôt que
   de deviner. Une erreur de routage coûte plus cher qu'un aiguillage manuel.
4. Liste dans `informations_manquantes` uniquement ce dont le support a réellement
   besoin pour traiter la demande. Une demande complète donne une liste vide.
5. `confiance` doit refléter ton incertitude réelle. Une demande de trois mots
   sans contexte ne mérite pas 0,9. Cette valeur déclenche une revue humaine :
   la surestimer fait passer des erreurs en production.
6. `resume` fait une phrase, vingt mots au maximum, et décrit le besoin du
   demandeur — pas ce qu'il a écrit.
"""


def _exemple_en_texte(ticket: Ticket) -> str:
    attendu = {
        "categorie": ticket.categorie.value,
        "module": ticket.module.value,
        "priorite": ticket.priorite.value,
        "equipe": ticket.equipe.value,
        "est_bloquant": ticket.est_bloquant,
    }
    return (
        f"Demande :\n{ticket.texte}\n\n"
        f"Qualification attendue :\n{json.dumps(attendu, ensure_ascii=False, indent=2)}"
    )


def construire_prompt(regles_path: Path | str, exemples: list[Ticket]) -> str:
    regles = Path(regles_path).read_text(encoding="utf-8")
    blocs = [
        CONSIGNES,
        "\n\n===== RÈGLES MÉTIER =====\n\n" + regles,
    ]
    if exemples:
        blocs.append("\n\n===== EXEMPLES QUALIFIÉS PAR UN EXPERT =====\n")
        blocs.extend("\n---\n\n" + _exemple_en_texte(t) + "\n" for t in exemples)
    return "".join(blocs)
