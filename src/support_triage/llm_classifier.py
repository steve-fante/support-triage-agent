"""Classifieur fondé sur un modèle de langage, via LangChain.

Le point important est `with_structured_output` : le modèle ne renvoie pas du
texte à analyser ensuite, mais un objet conforme au schéma Pydantic. La
validation est faite par Pydantic avant que le programme ne voie la réponse —
une catégorie inventée lève une erreur au lieu de se propager silencieusement.

C'est la différence entre un prototype et un composant qu'on branche à un
système d'information.
"""

from __future__ import annotations

from typing import Protocol

from .schema import Qualification


class Classifier(Protocol):
    """Interface commune aux classifieurs, pour qu'ils soient interchangeables."""

    nom: str

    def classer(self, texte: str) -> Qualification: ...


class LangChainClassifier:
    """Appelle le modèle et exige une sortie conforme au schéma."""

    nom = "llm"

    def __init__(
        self,
        system_prompt: str,
        model: str = "claude-sonnet-5",
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> None:
        try:
            from langchain_anthropic import ChatAnthropic  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - dépend de l'installation
            raise RuntimeError(
                "langchain-anthropic est requis : pip install 'support-triage-agent[llm]'"
            ) from exc

        self.system_prompt = system_prompt
        self._modele = ChatAnthropic(
            model=model, max_tokens=max_tokens
        ).with_structured_output(Qualification)

    def classer(self, texte: str) -> Qualification:
        messages = [
            ("system", self.system_prompt),
            ("human", f"Demande à qualifier :\n\n{texte}"),
        ]
        return self._modele.invoke(messages)


class ScriptedClassifier:
    """Rejoue des qualifications préparées. Utilisé par les tests.

    Permet de couvrir toute la chaîne — seuil de confiance, escalade, repli,
    métriques — sans clé d'API ni appel réseau, donc dans une CI gratuite et
    déterministe.
    """

    nom = "llm"

    def __init__(self, reponses: list[Qualification | Exception]) -> None:
        self._reponses = list(reponses)
        self.appels: list[str] = []

    def classer(self, texte: str) -> Qualification:
        self.appels.append(texte)
        if not self._reponses:
            raise RuntimeError("Scénario épuisé : aucune réponse préparée restante.")
        reponse = self._reponses.pop(0)
        if isinstance(reponse, Exception):
            raise reponse
        return reponse
