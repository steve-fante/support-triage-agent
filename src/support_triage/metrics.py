"""Métriques de classification, écrites à la main.

Aucune dépendance à scikit-learn : les formules tiennent en quelques lignes, et
les écrire soi-même oblige à savoir ce qu'on mesure. Sur un projet à cinq
classes et quarante exemples, importer une bibliothèque de calcul scientifique
serait disproportionné.

Trois familles de mesures :

- **exactitude par champ** : la proportion de prédictions correctes ;
- **F1 macro** : la moyenne des F1 par classe, sans pondération par effectif.
  C'est la métrique honnête quand les classes sont déséquilibrées — ici les P1
  sont rares, et une exactitude élevée peut masquer un modèle qui ne les
  détecte jamais ;
- **calibration** : lorsque le modèle annonce 0,9 de confiance, a-t-il raison
  neuf fois sur dix ? Un modèle sûr de lui à tort est plus dangereux qu'un
  modèle hésitant.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class ScoreClasse:
    classe: str
    support: int
    precision: float
    rappel: float
    f1: float


@dataclass
class ResultatChamp:
    champ: str
    exactitude: float
    f1_macro: float
    par_classe: list[ScoreClasse] = field(default_factory=list)
    confusions: list[tuple[str, str, int]] = field(default_factory=list)


def _valeur(v: object) -> str:
    return v.value if hasattr(v, "value") else str(v)


def exactitude(attendus: list, predits: list) -> float:
    if not attendus:
        return 0.0
    justes = sum(1 for a, p in zip(attendus, predits, strict=True) if _valeur(a) == _valeur(p))
    return justes / len(attendus)


def scores_par_classe(attendus: list, predits: list) -> list[ScoreClasse]:
    """Précision, rappel et F1 pour chaque classe présente dans la référence."""
    vp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    fn: dict[str, int] = defaultdict(int)
    support: dict[str, int] = defaultdict(int)

    for attendu, predit in zip(attendus, predits, strict=True):
        a, p = _valeur(attendu), _valeur(predit)
        support[a] += 1
        if a == p:
            vp[a] += 1
        else:
            fn[a] += 1
            fp[p] += 1

    resultats: list[ScoreClasse] = []
    for classe in sorted(support):
        precision = vp[classe] / (vp[classe] + fp[classe]) if (vp[classe] + fp[classe]) else 0.0
        rappel = vp[classe] / (vp[classe] + fn[classe]) if (vp[classe] + fn[classe]) else 0.0
        f1 = 2 * precision * rappel / (precision + rappel) if (precision + rappel) else 0.0
        resultats.append(
            ScoreClasse(classe, support[classe], round(precision, 3), round(rappel, 3), round(f1, 3))
        )
    return resultats


def f1_macro(attendus: list, predits: list) -> float:
    scores = scores_par_classe(attendus, predits)
    return round(sum(s.f1 for s in scores) / len(scores), 3) if scores else 0.0


def confusions(attendus: list, predits: list) -> list[tuple[str, str, int]]:
    """Les erreurs, de la plus fréquente à la plus rare : (attendu, prédit, nombre)."""
    compte: dict[tuple[str, str], int] = defaultdict(int)
    for attendu, predit in zip(attendus, predits, strict=True):
        a, p = _valeur(attendu), _valeur(predit)
        if a != p:
            compte[(a, p)] += 1
    return [(a, p, n) for (a, p), n in sorted(compte.items(), key=lambda kv: -kv[1])]


def evaluer_champ(champ: str, attendus: list, predits: list) -> ResultatChamp:
    return ResultatChamp(
        champ=champ,
        exactitude=round(exactitude(attendus, predits), 3),
        f1_macro=f1_macro(attendus, predits),
        par_classe=scores_par_classe(attendus, predits),
        confusions=confusions(attendus, predits),
    )


def calibration(confiances: list[float], corrects: list[bool], paliers: int = 4) -> list[dict]:
    """Compare la confiance annoncée au taux de réussite observé.

    Un modèle bien calibré affiche un écart proche de zéro dans chaque tranche.
    Un écart positif signale un excès de confiance — le cas dangereux, puisque
    c'est lui qui laisse passer des erreurs sous le seuil d'escalade.
    """
    if not confiances:
        return []
    largeur = 1.0 / paliers
    tranches: list[dict] = []
    for i in range(paliers):
        bas, haut = i * largeur, (i + 1) * largeur
        indices = [
            j for j, c in enumerate(confiances)
            if (bas <= c < haut) or (i == paliers - 1 and c == 1.0)
        ]
        if not indices:
            continue
        confiance_moyenne = sum(confiances[j] for j in indices) / len(indices)
        taux_reussite = sum(1 for j in indices if corrects[j]) / len(indices)
        tranches.append({
            "tranche": f"[{bas:.2f} – {haut:.2f}[",
            "effectif": len(indices),
            "confiance_moyenne": round(confiance_moyenne, 3),
            "taux_reussite": round(taux_reussite, 3),
            "ecart": round(confiance_moyenne - taux_reussite, 3),
        })
    return tranches
