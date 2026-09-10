"""Tests de fumée de l'interface en ligne de commande.

Écrits parce que sur le projet précédent, soixante et un tests étaient verts
alors que la commande annoncée dans le README ne fonctionnait pas : le paquet
n'avait pas de `__main__.py`. Les tests couvraient la logique interne, jamais
l'interface publique.
"""

from __future__ import annotations

import subprocess
import sys


def _lancer(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "support_triage", *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_le_module_est_executable() -> None:
    r = _lancer("--help")
    assert r.returncode == 0, r.stderr
    assert "trier" in r.stdout
    assert "demo" in r.stdout


def test_la_demonstration_fonctionne_hors_ligne() -> None:
    r = _lancer("demo", "-n", "3")
    assert r.returncode == 0, r.stderr
    assert "référence" in r.stdout


def test_trier_avec_la_ligne_de_base() -> None:
    r = _lancer("trier", "--regles", "Impossible de valider une facture, message d'erreur rouge.")
    assert r.returncode == 0, r.stderr
    assert "Confiance" in r.stdout
