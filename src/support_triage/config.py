"""Configuration lue depuis l'environnement, avec chargement d'un fichier .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "tickets.jsonl"
DEFAULT_REGLES = PROJECT_ROOT / "data" / "regles_priorisation.md"


def load_dotenv(path: Path | None = None) -> None:
    """Charge un fichier .env sans dépendance externe.

    Une variable déjà présente dans l'environnement l'emporte sur le fichier :
    un export explicite doit toujours primer.
    """
    env_file = path or PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip("'\"")


load_dotenv()


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Paramètres d'exécution.

    `seuil_confiance` est le curseur métier du projet : plus il est haut, moins
    de tickets partent en traitement automatique, mais plus les décisions
    automatiques sont sûres. Voir la section « calibration » du README.
    """

    llm_model: str = os.getenv("LLM_MODEL", "claude-sonnet-5")
    dataset_path: Path = Path(os.getenv("DATASET_PATH", str(DEFAULT_DATASET)))
    regles_path: Path = Path(os.getenv("REGLES_PATH", str(DEFAULT_REGLES)))
    seuil_confiance: float = _float_env("SEUIL_CONFIANCE", 0.75)
    temperature: float = _float_env("TEMPERATURE", 0.0)
    max_tokens: int = int(os.getenv("MAX_TOKENS", "1024"))
