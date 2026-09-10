"""Harnais d'évaluation : le modèle contre la ligne de base.

    python evals/run_eval.py --regles          # ligne de base seule, gratuit
    python evals/run_eval.py                   # modèle seul
    python evals/run_eval.py --comparer        # les deux, côte à côte
    python evals/run_eval.py --comparer --json metrics.json

L'évaluation porte exclusivement sur le sous-ensemble `eval`. Les six exemples
du prompt en sont exclus : les inclure gonflerait les scores sans rien dire de
la capacité du modèle à traiter une demande nouvelle.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_triage.baseline import BaselineClassifier  # noqa: E402
from support_triage.config import Settings  # noqa: E402
from support_triage.dataset import Ticket, load_tickets, split_tickets  # noqa: E402
from support_triage.llm_classifier import Classifier  # noqa: E402
from support_triage.metrics import calibration, evaluer_champ  # noqa: E402
from support_triage.prompt import construire_prompt  # noqa: E402
from support_triage.schema import CHAMPS_EVALUES  # noqa: E402
from support_triage.triage import TriageService  # noqa: E402


def evaluer(service: TriageService, tickets: list[Ticket]) -> dict:
    predictions, confiances, corrects, escalades = [], [], [], 0
    debut = time.time()

    for ticket in tickets:
        decision = service.trier(ticket.texte)
        q = decision.qualification
        predictions.append({
            "categorie": q.categorie,
            "module": q.module,
            "priorite": q.priorite,
            "equipe": q.equipe,
            "est_bloquant": q.est_bloquant,
        })
        confiances.append(q.confiance)
        corrects.append(all(
            str(getattr(q, champ)) == str(ticket.reference()[champ]) for champ in CHAMPS_EVALUES
        ))
        escalades += int(decision.escalade_humaine)

    duree = round(time.time() - debut, 2)
    resultats = {}
    for champ in CHAMPS_EVALUES:
        attendus = [t.reference()[champ] for t in tickets]
        predits = [p[champ] for p in predictions]
        resultats[champ] = asdict(evaluer_champ(champ, attendus, predits))

    return {
        "effectif": len(tickets),
        "exact_sur_tous_les_champs": round(sum(corrects) / len(tickets), 3),
        "taux_escalade": round(escalades / len(tickets), 3),
        "duree_totale_s": duree,
        "champs": resultats,
        "calibration": calibration(confiances, corrects),
    }


def afficher(titre: str, r: dict) -> None:
    print(f"\n=== {titre} ===")
    print(f"Tickets évalués            : {r['effectif']}")
    print(f"Exact sur les 5 champs     : {r['exact_sur_tous_les_champs']:.1%}")
    print(f"Envoyés en revue humaine   : {r['taux_escalade']:.1%}")
    print(f"Durée totale               : {r['duree_totale_s']} s\n")
    print(f"{'champ':<16}{'exactitude':>12}{'F1 macro':>12}")
    for champ, valeurs in r["champs"].items():
        print(f"{champ:<16}{valeurs['exactitude']:>12.3f}{valeurs['f1_macro']:>12.3f}")

    erreurs = [
        (champ, c) for champ, v in r["champs"].items() for c in v["confusions"]
    ]
    if erreurs:
        print("\nPrincipales confusions (attendu → prédit) :")
        for champ, (attendu, predit, n) in sorted(erreurs, key=lambda e: -e[1][2])[:6]:
            print(f"  {champ:<14} {attendu} → {predit}  ({n})")

    if r["calibration"]:
        print("\nCalibration de la confiance :")
        print(f"  {'tranche':<18}{'n':>4}{'confiance':>12}{'réussite':>11}{'écart':>9}")
        for tr in r["calibration"]:
            print(
                f"  {tr['tranche']:<18}{tr['effectif']:>4}{tr['confiance_moyenne']:>12.3f}"
                f"{tr['taux_reussite']:>11.3f}{tr['ecart']:>9.3f}"
            )


def construire_service(settings: Settings, exemples: list[Ticket], regles: bool) -> TriageService:
    classifier: Classifier
    if regles:
        classifier = BaselineClassifier()
    else:
        from support_triage.llm_classifier import LangChainClassifier  # noqa: PLC0415

        classifier = LangChainClassifier(
            system_prompt=construire_prompt(settings.regles_path, exemples),
            model=settings.llm_model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )
    # En évaluation, aucun repli : une panne du modèle doit faire échouer le
    # harnais plutôt que produire silencieusement les chiffres de la ligne de base.
    return TriageService(
        classifier,
        seuil_confiance=settings.seuil_confiance,
        repli_sur_regles=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Évaluation du triage")
    parser.add_argument("--regles", action="store_true", help="Ligne de base uniquement")
    parser.add_argument("--comparer", action="store_true", help="Ligne de base et modèle")
    parser.add_argument("--json", dest="json_out", help="Fichier de sortie des métriques")
    args = parser.parse_args()

    settings = Settings()
    exemples, evaluation = split_tickets(load_tickets(settings.dataset_path))
    print(f"{len(exemples)} exemples dans le prompt, {len(evaluation)} tickets d'évaluation.")

    sortie: dict[str, dict] = {}

    if args.regles or args.comparer:
        r = evaluer(construire_service(settings, exemples, regles=True), evaluation)
        afficher("Ligne de base (règles)", r)
        sortie["regles"] = r

    if not args.regles:
        r = evaluer(construire_service(settings, exemples, regles=False), evaluation)
        afficher(f"Modèle ({settings.llm_model})", r)
        sortie["llm"] = r

    if "regles" in sortie and "llm" in sortie:
        base = sortie["regles"]["exact_sur_tous_les_champs"]
        llm = sortie["llm"]["exact_sur_tous_les_champs"]
        print("\n=== Apport du modèle ===")
        print(f"Exact sur les 5 champs : {base:.1%} → {llm:.1%}  ({llm - base:+.1%})")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(sortie, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        print(f"\nMétriques écrites dans {args.json_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
