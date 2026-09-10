"""Interface en ligne de commande."""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .baseline import BaselineClassifier
from .config import Settings
from .dataset import load_tickets, split_tickets
from .llm_classifier import Classifier
from .prompt import construire_prompt
from .schema import Decision
from .triage import TriageService

console = Console()


def _service(settings: Settings, forcer_regles: bool) -> TriageService:
    classifier: Classifier
    if forcer_regles:
        classifier = BaselineClassifier()
    else:
        from .llm_classifier import LangChainClassifier  # noqa: PLC0415

        tickets = load_tickets(settings.dataset_path)
        exemples, _ = split_tickets(tickets)
        classifier = LangChainClassifier(
            system_prompt=construire_prompt(settings.regles_path, exemples),
            model=settings.llm_model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )
    return TriageService(classifier, seuil_confiance=settings.seuil_confiance)


def _afficher(decision: Decision) -> None:
    q = decision.qualification
    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column(style="bold", width=24)
    table.add_column()
    table.add_row("Catégorie", q.categorie.value)
    table.add_row("Module", q.module.value)
    table.add_row("Priorité", q.priorite.value)
    table.add_row("Équipe", q.equipe.value)
    table.add_row("Bloquant", "oui" if q.est_bloquant else "non")
    table.add_row("Confiance", f"{q.confiance:.2f}")
    table.add_row("Source", decision.source)

    console.print(Panel(q.resume, title="Résumé", border_style="cyan"))
    console.print(table)

    if q.informations_manquantes:
        console.print("\n[bold]À réclamer au demandeur[/bold]")
        for item in q.informations_manquantes:
            console.print(f"  · {item}")

    console.print(f"\n[dim]{q.justification}[/dim]")

    if decision.escalade_humaine:
        console.print(
            Panel(decision.motif_escalade or "", title="Revue humaine requise", border_style="yellow")
        )
    else:
        console.print("[green]Traitement automatique : la demande peut être routée.[/green]")


def cmd_trier(args: argparse.Namespace) -> int:
    settings = Settings()
    decision = _service(settings, args.regles).trier(args.demande)
    _afficher(decision)
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """Démonstration hors ligne : la ligne de base sur quelques tickets réels."""
    settings = Settings()
    tickets = load_tickets(settings.dataset_path)
    _, evaluation = split_tickets(tickets)
    service = TriageService(BaselineClassifier(), seuil_confiance=settings.seuil_confiance)

    console.print(
        "[bold cyan]Démonstration hors ligne[/bold cyan] — classifieur par règles, "
        "aucun appel réseau.\n"
    )
    for ticket in evaluation[: args.nombre]:
        console.print(f"[dim]{ticket.id}[/dim] {ticket.texte[:110]}…")
        decision = service.trier(ticket.texte)
        q = decision.qualification
        marque = "[yellow]revue humaine[/yellow]" if decision.escalade_humaine else "[green]auto[/green]"
        console.print(
            f"   -> {q.categorie.value} · {q.module.value} · {q.priorite.value} "
            f"· {q.equipe.value} · confiance {q.confiance:.2f} · {marque}"
        )
        attendu = (
            f"{ticket.categorie.value} · {ticket.module.value} · "
            f"{ticket.priorite.value} · {ticket.equipe.value}"
        )
        console.print(f"   [dim]référence : {attendu}[/dim]\n")

    console.print(
        "[dim]Ces écarts sont attendus : des mots-clés ne comprennent pas une phrase.\n"
        "Lancer « python evals/run_eval.py » pour comparer chiffres en main.[/dim]"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="support-triage",
        description="Qualifie une demande de support Odoo et décide de son routage.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_trier = sub.add_parser("trier", help="Qualifier une demande")
    p_trier.add_argument("demande", help="Le texte de la demande, entre guillemets")
    p_trier.add_argument(
        "--regles", action="store_true", help="Utiliser la ligne de base au lieu du modèle"
    )
    p_trier.set_defaults(func=cmd_trier)

    p_demo = sub.add_parser("demo", help="Démonstration hors ligne, sans clé d'API")
    p_demo.add_argument("-n", "--nombre", type=int, default=6, help="Nombre de tickets")
    p_demo.set_defaults(func=cmd_demo)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
