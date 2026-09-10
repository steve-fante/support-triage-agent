from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from support_triage.dataset import Ticket, load_tickets, split_tickets  # noqa: E402
from support_triage.schema import Categorie, Equipe, Module, Priorite, Qualification  # noqa: E402


@pytest.fixture(scope="session")
def tickets() -> list[Ticket]:
    return load_tickets(ROOT / "data" / "tickets.jsonl")


@pytest.fixture(scope="session")
def exemples(tickets) -> list[Ticket]:  # noqa: ANN001
    return split_tickets(tickets)[0]


@pytest.fixture(scope="session")
def evaluation(tickets) -> list[Ticket]:  # noqa: ANN001
    return split_tickets(tickets)[1]


@pytest.fixture(scope="session")
def regles_path() -> Path:
    return ROOT / "data" / "regles_priorisation.md"


def qualification(**surcharges) -> Qualification:  # noqa: ANN003
    """Fabrique une qualification valide, personnalisable champ par champ."""
    valeurs = {
        "categorie": Categorie.ANOMALIE,
        "module": Module.VENTES,
        "priorite": Priorite.P3_MINEUR,
        "equipe": Equipe.SUPPORT_N2_FONCTIONNEL,
        "resume": "Le devis ne se génère pas",
        "est_bloquant": False,
        "informations_manquantes": [],
        "confiance": 0.9,
        "justification": "Contournement possible, aucun blocage signalé.",
    }
    valeurs.update(surcharges)
    return Qualification(**valeurs)


@pytest.fixture()
def fabrique():  # noqa: ANN201
    return qualification
