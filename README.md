# support-triage-agent

**Qualification automatique des demandes de support d'un ERP Odoo : catégorie, module, priorité, routage — et la décision d'escalader vers un humain quand le modèle n'est pas sûr.**

[![CI](https://github.com/steve-fante/support-triage-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/steve-fante/support-triage-agent/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Licence](https://img.shields.io/badge/licence-MIT-green)

> **Résultat mesuré** — sur 39 tickets tenus à l'écart du prompt, la
> qualification est exacte sur les cinq champs dans **69,2 %** des cas, contre
> **28,2 %** pour une ligne de base par mots-clés. Le tiers des demandes dont la
> confiance dépasse le seuil part en routage automatique ; le reste va en revue
> humaine. [Détail des mesures](#résultats-du-modèle).

---

## Le problème

Un support ERP reçoit des demandes rédigées par des utilisateurs pressés. « Ça ne
marche pas. » « Il y a un souci avec la facture. » Avant de traiter quoi que ce
soit, quelqu'un doit lire, comprendre, classer, prioriser, router, et souvent
rappeler le demandeur pour obtenir les informations qu'il a omises.

Ce travail de tri est répétitif, occupe un technicien expérimenté, et se fait mal
quand la file s'allonge — au moment précis où il faudrait le faire bien.

Automatiser ce tri pose trois problèmes que ce dépôt traite explicitement :

| Problème | Réponse apportée |
|---|---|
| La sortie doit être exploitable par un système, pas lisible par un humain | Schéma Pydantic typé, validé avant que le programme ne voie la réponse |
| Un modèle qui se trompe avec assurance est pire qu'un modèle qui hésite | Seuil de confiance, escalade humaine, mesure de la calibration |
| « 85 % d'exactitude » ne veut rien dire dans l'absolu | Une ligne de base par règles, pour mesurer ce que le modèle apporte réellement |

## Démonstration en 30 secondes, sans clé d'API

```bash
git clone https://github.com/steve-fante/support-triage-agent.git
cd support-triage-agent
pip install -e ".[dev]"
python -m support_triage demo
```

```
T008 Quand je valide une facture client, le montant de TVA calculé est de 19,6 %…
   → anomalie · comptabilite · P2_majeur · support_n2_fonctionnel
     confiance 0.66 · revue humaine
   référence : anomalie · comptabilite · P2_majeur · support_n2_fonctionnel
```

La démonstration utilise la ligne de base par règles : gratuite, déterministe,
et volontairement imparfaite. Elle montre le mécanisme complet — qualification,
seuil, escalade — et les écarts avec la référence annotée.

## Ce que produit l'agent

```python
class Qualification(BaseModel):
    categorie: Categorie                  # anomalie, question_utilisation, …
    module: Module                        # ventes, stock, comptabilite, …
    priorite: Priorite                    # P1_critique … P4_cosmetique
    equipe: Equipe                        # support_n1, developpement, …
    resume: str                           # une phrase, 20 mots maximum
    est_bloquant: bool
    informations_manquantes: list[str]    # ce qu'il faut réclamer au demandeur
    confiance: float                      # 0 à 1 — déclenche l'escalade
    justification: str
```

Le typage n'est pas décoratif. `with_structured_output` de LangChain contraint le
modèle à produire un objet conforme, et **Pydantic valide avant que le programme
ne voie la réponse** : une catégorie inventée lève une erreur au lieu de se
propager silencieusement jusqu'à un mauvais routage.

`informations_manquantes` est le champ qui rend l'agent utile plutôt que
décoratif. Un ticket sans référence de pièce ni message d'erreur ne sera pas
traité : autant le demander tout de suite.

## Le seuil de confiance, cœur métier du projet

Un système de triage qui automatise tout est dangereux. Un système qui
n'automatise rien est inutile. Le curseur entre les deux est le seuil de
confiance, et trois règles décident du sort d'une qualification :

1. confiance inférieure au seuil → **revue humaine** ;
2. priorité `P1_critique` → **revue humaine systématique**, quelle que soit la confiance ;
3. modèle indisponible → **repli sur les règles**, et revue humaine.

Le troisième point mérite d'exister : un support ne s'arrête pas parce qu'une API
est injoignable. Le système se dégrade au lieu de tomber.

## La ligne de base, et pourquoi elle compte

`baseline.py` classe les demandes par mots-clés, sans modèle de langage. Ce n'est
pas un homme de paille : c'est l'implémentation directe des règles métier
documentées dans `data/regles_priorisation.md`.

Trois raisons de l'avoir écrite :

- **mesurer l'apport réel du modèle.** Annoncer un score sans point de comparaison
  ne dit rien. Si des mots-clés obtenaient les mêmes résultats, l'appel au modèle
  serait un coût sans contrepartie ;
- **tester hors ligne.** Toute la chaîne est couverte sans clé d'API ;
- **dégrader proprement**, comme décrit plus haut.

### Résultats de la ligne de base

Mesurés sur les 39 tickets d'évaluation, sans appel réseau :

```
Exact sur les 5 champs     : 28.2%
Envoyés en revue humaine   : 100.0%

champ             exactitude    F1 macro
categorie              0.564       0.605
module                 0.692       0.574
priorite               0.590       0.577
equipe                 0.564       0.580
est_bloquant           0.897       0.770

Principales confusions (attendu → prédit)
  priorite       P2_majeur → P3_mineur           (8)
  equipe         support_n2_fonctionnel → n1     (8)
  categorie      anomalie → question_utilisation (7)
```

Ces chiffres racontent quelque chose de précis. Les mots-clés identifient
correctement le **module** deux fois sur trois — le vocabulaire y est explicite,
« facture » désigne la comptabilité. Ils échouent sur la **priorité** parce
qu'elle exige de comprendre l'enjeu d'une phrase, pas d'y repérer un mot. Et le
100 % d'escalade est le comportement attendu : la confiance des règles plafonne
délibérément à 0,70, en dessous du seuil. Ce classifieur ne doit jamais décider
seul.

### Résultats du modèle

```bash
cp .env.example .env          # renseigner ANTHROPIC_API_KEY
pip install -e ".[llm]"
python evals/run_eval.py --comparer --json metrics.json
```

```
=== Modèle (claude-sonnet-5) ===
Tickets évalués            : 39
Exact sur les 5 champs     : 69.2%
Envoyés en revue humaine   : 66.7%
Durée totale               : 140.23 s

champ             exactitude    F1 macro
categorie              0.923       0.928
module                 0.846       0.850
priorite               0.872       0.892
equipe                 0.949       0.957
est_bloquant           0.974       0.954

Principales confusions (attendu → prédit)
  module         crm → ventes                          (2)
  priorite       P3_mineur → P4_cosmetique             (2)
  categorie      probleme_donnees → demande_evolution  (1)

=== Apport du modèle ===
Exact sur les 5 champs : 28.2% → 69.2%  (+41.0%)
```

**Lecture.** Le gain est net, mais l'écart entre les deux façons de compter
mérite d'être explicité. Champ par champ, le modèle est entre 0,85 et 0,97 ;
sur les cinq champs simultanément, il tombe à 69 %. Ce n'est pas une
contradiction : douze tickets sur trente-neuf ont une seule erreur, souvent sur
le module ou un cran de priorité. La métrique « exact sur les cinq champs » est
volontairement sévère parce qu'elle correspond au seul cas où la qualification
est exploitable sans relecture.

Les confusions restantes sont défendables. `crm → ventes` porte sur des tickets
où le demandeur parle d'un devis attaché à une opportunité : les deux modules
sont concernés. `P3_mineur → P4_cosmetique` est un désaccord d'un cran sur des
demandes d'affichage. Aucune erreur ne fait passer un incident bloquant pour une
question de confort — `est_bloquant` est à 0,974, et c'est le champ dont dépend
le délai de prise en charge.

**Coût et latence.** 3,6 s par ticket, 39 appels pour 140 s. Un triage de
support n'est pas une opération temps réel : la contrainte est le délai de
première réponse, mesuré en minutes. La latence n'est donc pas un obstacle ici.

**Le taux d'escalade reste élevé — et c'est le vrai sujet.** Deux tiers des
tickets partent en revue humaine, contre 100 % pour les règles. Le seuil à 0,75
est conservateur : quinze tickets seulement dépassent cette barre. Le système
automatise donc un tiers des demandes. Abaisser le seuil augmenterait ce taux
mécaniquement, mais la section suivante montre pourquoi ce serait prématuré.

## Calibration : le modèle est-il sûr à bon escient ?

Quand un classifieur annonce 0,9 de confiance, a-t-il raison neuf fois sur dix ?
La question n'est pas théorique : c'est cette valeur qui décide si une
qualification part en traitement automatique.

```
tranche              n   confiance   réussite    écart
[0.25 – 0.50[        9       0.424      0.000    0.424
[0.50 – 0.75[       30       0.587      0.367    0.220
```

Un écart positif signale un **excès de confiance** — le cas dangereux, puisque
c'est lui qui fait passer des erreurs au-dessus du seuil. La ligne de base est
nettement trop sûre d'elle, ce qui est logique : elle compte des mots-clés et
prend leur nombre pour de la certitude.

Le modèle est bien mieux réglé :

```
tranche              n   confiance   réussite    écart
[0.00 – 0.25[        2       0.150      1.000   -0.850
[0.25 – 0.50[        1       0.350      1.000   -0.650
[0.50 – 0.75[       21       0.626      0.619   +0.007
[0.75 – 1.00[       15       0.803      0.733   +0.070
```

Sur les deux tranches qui portent la quasi-totalité des tickets, l'écart est de
+0,007 et +0,070 : quand le modèle annonce 0,63, il a raison 62 % du temps.
Cette confiance est donc **utilisable comme critère de décision**, ce qui est la
condition pour que le seuil ait un sens.

Deux réserves, à énoncer plutôt qu'à masquer. D'abord les tranches basses
affichent un écart spectaculaire (-0,85), mais sur **trois tickets au total** :
le modèle s'est sous-estimé trois fois, ce qui ne permet aucune conclusion.
Ensuite, la tranche haute reste à 0,733 de réussite pour 0,803 de confiance
annoncée : au-dessus du seuil, un peu plus d'un quart des qualifications
comportent encore au moins une erreur. C'est précisément pourquoi le seuil de
0,75 n'est pas abaissé — le gain d'automatisation se paierait en erreurs
routées sans relecture. Le réglage de ce curseur est une décision d'exploitant,
pas un choix technique : il dépend du coût relatif d'un ticket mal routé et
d'un ticket relu pour rien.

Trente-neuf tickets restent un effectif modeste. Ces chiffres indiquent un ordre
de grandeur, pas une performance garantie en production.

## Architecture

```
              demande brute (courriel, ticket)
                          │
                          ▼
           ┌──────────────────────────────┐
           │ TriageService                │
           │   ├─ classifieur ────────────┼──▶ LangChain + sortie structurée
           │   │      (repli si panne) ───┼──▶ règles par mots-clés
           │   ├─ seuil de confiance      │
           │   └─ règles d'escalade       │
           └──────────────┬───────────────┘
                          ▼
                      Decision
                      · qualification typée
                      · escalade_humaine
                      · motif_escalade
                      · source
```

```
src/support_triage/
├── schema.py          le contrat de sortie : énumérations et modèle Pydantic
├── dataset.py         chargement du jeu annoté, séparation prompt / évaluation
├── baseline.py        classifieur par règles : ligne de base et repli
├── prompt.py          assemblage du prompt à partir des règles et des exemples
├── llm_classifier.py  LangChain avec sortie structurée, et classifieur scripté
├── triage.py          orchestration, seuil, escalade
├── metrics.py         exactitude, F1 macro, confusions, calibration
└── cli.py
data/
├── tickets.jsonl              45 tickets annotés à la main
└── regles_priorisation.md     les règles métier, annexées au prompt
```

Détail des arbitrages dans [`docs/architecture.md`](docs/architecture.md).

## Le jeu de données

Quarante-cinq tickets en français, **écrits pour ce projet** — ils ne proviennent
d'aucun client réel, ce qui évite toute question de confidentialité mais limite
la portée des résultats. Ils reproduisent des situations rencontrées en
déploiement Odoo : demandes vagues, urgences réelles et supposées, démarchage
commercial arrivé sur la boîte du support.

Le jeu est séparé en deux parties étanches : **6 exemples** insérés dans le
prompt, **39 tickets** d'évaluation. Un test vérifie qu'aucun ticket
d'évaluation ne figure dans le prompt — évaluer un modèle sur des exemples qu'on
lui a montrés produit un score flatteur et faux.

Le déséquilibre des classes est volontaire : les priorités critiques sont rares,
comme dans une file réelle. C'est ce qui justifie le **F1 macro**, où une classe
rare pèse autant qu'une classe fréquente.

## Adapter l'agent à un client

Deux fichiers, pas de code :

1. `data/regles_priorisation.md` — les règles de priorisation et de routage du
   client, recueillies en atelier avec le responsable support ;
2. `data/tickets.jsonl` — une trentaine de leurs vrais tickets, qualifiés par
   leur expert. C'est ce jeu qui rend les mesures crédibles à leurs yeux.

Une demi-journée d'atelier, et l'agent parle leur langue. C'est du travail de
consultant fonctionnel, et c'est là que se situe la valeur.

## Tests

```bash
pytest -q          # 62 tests, aucun appel réseau
ruff check .
```

Le classifieur scripté rejoue des qualifications préparées : le graphe complet —
seuil, escalade, repli sur panne, métriques — est couvert sans clé d'API. La CI
reste verte, gratuite et déterministe.

Les tests portent aussi sur le jeu de données lui-même : identifiants uniques,
étanchéité des ensembles, cohérence du routage annoté avec la table de règles,
présence de toutes les catégories dans l'évaluation. Un jeu incohérent invalide
toutes les mesures qui en découlent.

## Limites assumées

| Limite | Conséquence |
|---|---|
| Jeu de données synthétique | Les scores ne préjugent pas des performances sur des tickets réels |
| Pas de détection de doublons | Deux signalements du même incident sont traités séparément |
| Pas de mémoire entre tickets | Un incident récurrent n'est pas reconnu comme tel |
| Coût par ticket non instrumenté | Le comptage de jetons reste à ajouter |
| Français uniquement | Les lexiques de la ligne de base sont monolingues |

## Auteur

**Steve Christian FANTE** — Consultant ERP Odoo, Master MIAGE Management des SI.
Onze ans en systèmes d'information, dont quatre ans comme point d'entrée unique
des utilisateurs sur les incidents applicatifs.

[LinkedIn](https://linkedin.com/in/steve-c-fante) · [odoo-ai-agent](https://github.com/steve-fante/odoo-ai-agent)

## Licence

MIT — voir [LICENSE](LICENSE).
