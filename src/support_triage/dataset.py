"""Chargement du jeu de tickets annotés.

Le jeu est séparé en deux parties étanches :

- `few_shot` : les six exemples insérés dans le prompt ;
- `eval` : les trente-neuf tickets sur lesquels on mesure.

Cette séparation n'est pas cosmétique. Évaluer un modèle sur des exemples
figurant dans son propre prompt produit un score flatteur et faux. Un test
vérifie qu'aucun identifiant n'appartient aux deux ensembles.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .schema import Categorie, Equipe, Module, Priorite


@dataclass(frozen=True)
class Ticket:
    """Un ticket et sa qualification de référence, posée à la main."""

    id: str
    split: str
    texte: str
    categorie: Categorie
    module: Module
    priorite: Priorite
    equipe: Equipe
    est_bloquant: bool

    @classmethod
    def from_dict(cls, raw: dict) -> Ticket:
        return cls(
            id=raw["id"],
            split=raw["split"],
            texte=raw["texte"],
            categorie=Categorie(raw["categorie"]),
            module=Module(raw["module"]),
            priorite=Priorite(raw["priorite"]),
            equipe=Equipe(raw["equipe"]),
            est_bloquant=bool(raw["est_bloquant"]),
        )

    def reference(self) -> dict[str, object]:
        """Les valeurs de référence, sous la forme comparée par les métriques."""
        return {
            "categorie": self.categorie,
            "module": self.module,
            "priorite": self.priorite,
            "equipe": self.equipe,
            "est_bloquant": self.est_bloquant,
        }


def load_tickets(path: Path | str) -> list[Ticket]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Jeu de tickets introuvable : {path}")
    tickets: list[Ticket] = []
    for numero, ligne in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        ligne = ligne.strip()
        if not ligne:
            continue
        try:
            tickets.append(Ticket.from_dict(json.loads(ligne)))
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            raise ValueError(f"Ticket invalide ligne {numero} de {path} : {exc}") from exc
    if not tickets:
        raise ValueError(f"Aucun ticket dans {path}")
    return tickets


def split_tickets(tickets: list[Ticket]) -> tuple[list[Ticket], list[Ticket]]:
    """Renvoie (exemples du prompt, tickets d'évaluation)."""
    exemples = [t for t in tickets if t.split == "few_shot"]
    evaluation = [t for t in tickets if t.split == "eval"]
    return exemples, evaluation
