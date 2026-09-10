# Architecture et décisions

Ce document explique **pourquoi** chaque pièce est là, et ce qui a été écarté.
Le code dit comment ; il ne dit pas à quelles conditions il faudrait changer d'avis.

## Vue d'ensemble

```
   demande brute
        │
        ▼
 ┌──────────────────────────────────────────────┐
 │ TriageService.trier()                        │
 │                                              │
 │  1. classifier.classer(texte)                │
 │        ├─ LangChainClassifier  (production)  │
 │        ├─ BaselineClassifier   (ligne de base│
 │        │                        et repli)    │
 │        └─ ScriptedClassifier   (tests)       │
 │                                              │
 │  2. validation Pydantic  ─── échec ──▶ erreur│
 │                                              │
 │  3. règles d'escalade                        │
 │        · confiance < seuil                   │
 │        · priorité P1                         │
 │        · panne du modèle                     │
 └──────────────────┬───────────────────────────┘
                    ▼
                Decision
```

## Décisions

### Pourquoi une sortie typée plutôt que du texte à analyser

Un agent de triage n'a d'intérêt que branché à un système d'information :
créer le ticket, l'assigner, déclencher une alerte. Un texte libre demanderait
une couche d'analyse fragile qui se casserait à chaque reformulation du modèle.

`with_structured_output` contraint la génération, et Pydantic valide ensuite.
Les deux se cumulent : le premier réduit la probabilité d'une sortie invalide,
le second garantit qu'une sortie invalide n'atteint jamais le reste du
programme. Une catégorie inventée lève une erreur, elle ne provoque pas un
routage silencieusement faux.

### Pourquoi des énumérations en français

Les libellés des énumérations sont repris tels quels dans le prompt. Le modèle
n'a donc jamais à traduire entre le vocabulaire du prompt et celui du schéma,
et les valeurs produites sont directement lisibles par le responsable support
qui relira les décisions. Le coût est nul, le bénéfice est une source d'erreur
en moins.

### Pourquoi une ligne de base par règles

C'est la décision structurante du projet. Sans point de comparaison, un score
d'exactitude ne dit rien : peut-être que la tâche est facile.

La ligne de base répond aussi à deux besoins pratiques : elle rend les tests
hors ligne significatifs — ils portent sur un vrai classifieur, pas sur un
bouchon — et elle sert de repli quand l'API est indisponible.

Elle est écrite honnêtement, sans être bridée pour flatter le modèle : c'est la
transcription littérale de `data/regles_priorisation.md`. Sa confiance plafonne
volontairement à 0,70, en dessous du seuil d'escalade, parce qu'un compteur de
mots-clés ne doit jamais décider seul.

### Pourquoi le seuil de confiance, et pourquoi il est configurable

Un système de triage entièrement automatique est dangereux ; entièrement manuel,
il est inutile. Le seuil est le curseur, et il ne peut pas être choisi une fois
pour toutes : il dépend du coût d'une erreur chez le client. Un support interne
tolère un mauvais routage ; un support contractuel avec engagement de délai, non.

Il se règle avec les données de calibration : on cherche la valeur au-dessus de
laquelle le taux de réussite observé devient acceptable.

### Pourquoi les priorités critiques échappent au seuil

Une P1 passe systématiquement en revue humaine, même annoncée avec 0,99 de
confiance. Le raisonnement est asymétrique : le coût d'un faux négatif — une
urgence traitée comme une demande banale — est sans commune mesure avec celui
d'une validation humaine de trente secondes. Les rares cas critiques ne
justifient pas le risque.

### Pourquoi le repli sur les règles en cas de panne

Un support ne s'arrête pas parce qu'une API tierce est injoignable. La panne est
capturée, la qualification produite par les règles, et la décision marquée pour
revue humaine avec le motif. Le service se dégrade, il ne tombe pas.

**Quand changer d'avis :** si l'exploitation préfère une file bloquée à des
qualifications de moindre qualité, `repli_sur_regles=False` propage l'erreur.
Le choix est explicite dans le constructeur, pas enfoui dans le code.

### Pourquoi des métriques écrites à la main

Précision, rappel, F1 et calibration tiennent en quelques lignes. Sur un
problème à cinq classes et quarante exemples, importer scikit-learn ajouterait
une dépendance lourde pour des formules qu'il vaut mieux savoir écrire — et
donc comprendre.

**Quand changer d'avis :** dès qu'on a besoin de validation croisée,
d'intervalles de confiance ou de tests statistiques, la bibliothèque devient
justifiée.

### Pourquoi le F1 macro plutôt que la seule exactitude

Les classes sont volontairement déséquilibrées : les P1 sont rares, comme dans
une file réelle. Un classifieur qui ne détecterait jamais une P1 pourrait
afficher une exactitude flatteuse. Le F1 macro donne le même poids à chaque
classe et fait apparaître ce défaut immédiatement.

### Pourquoi mesurer la calibration

L'exactitude dit si le classifieur a raison. La calibration dit s'il **sait**
quand il a raison. C'est cette seconde propriété qui rend le seuil utilisable :
un modèle sûr de lui à tort laisse passer des erreurs sous le seuil, là où un
modèle hésitant les envoie en revue humaine.

Un écart positif entre confiance annoncée et taux de réussite signale un excès
de confiance — le cas dangereux. Un écart négatif signale un modèle trop
prudent, qui coûte inutilement du temps humain.

### Pourquoi l'évaluation n'a pas de repli

En exploitation, `TriageService` bascule sur les règles si l'appel au modèle
échoue : une panne d'API ne doit pas interrompre un support. En évaluation, ce
repli est **désactivé** (`repli_sur_regles=False`).

La raison a été apprise de la manière la plus instructive. Lors d'une première
exécution, le harnais a produit pour le modèle des chiffres identiques, au
millième près, à ceux de la ligne de base. Une telle coïncidence est impossible ;
le repli avait absorbé silencieusement une erreur d'API et rendu les résultats
des règles sous l'étiquette du modèle.

Un mécanisme de robustesse laissé actif dans un banc de mesure ne rend pas la
mesure robuste : il la rend fausse sans le dire. Un harnais d'évaluation doit
tomber bruyamment.

### Pourquoi le schéma normalise au lieu de rejeter

`informations_manquantes` est déclaré `list[str]`. En pratique, un modèle qui
n'a rien à réclamer renvoie parfois une chaîne vide, la mention « aucune », ou
plusieurs éléments dans un seul texte. Refuser ces formes ferait échouer une
qualification par ailleurs correcte, pour un détail de sérialisation.

Le validateur est donc en `mode="before"` : il normalise avant le contrôle de
type. La frontière est nette — on tolère les variantes de **forme**, jamais les
variantes de **fond**. Une catégorie inventée reste rejetée, une confiance hors
de [0, 1] aussi, parce que ces valeurs-là engagent une décision.

## L'étanchéité du jeu de données

Six tickets alimentent le prompt, trente-neuf servent à mesurer, et les deux
ensembles ne se recoupent pas. Un test le vérifie explicitement.

C'est l'erreur méthodologique la plus fréquente dans les projets de
classification par LLM : montrer au modèle les exemples sur lesquels on le note.
Le score obtenu est alors sans rapport avec la capacité à traiter une demande
nouvelle, qui est la seule chose qui compte en production.

## Ce qui manquerait pour un usage réel

| Manque | Conséquence | Piste |
|---|---|---|
| Jeu de données réel | Les scores ne préjugent de rien sur des tickets clients | Trente tickets du client, qualifiés par leur expert |
| Détection de doublons | Un incident signalé cinq fois crée cinq tickets | Similarité sur les tickets ouverts des dernières heures |
| Mémoire entre tickets | Un incident récurrent n'est pas reconnu | Historique consultable par le classifieur |
| Coût par ticket | Latence mesurée (3,6 s/ticket), coût en jetons non mesuré | Comptage des jetons dans `Decision` |
| Boucle de retour | Les corrections humaines ne servent à rien | Enregistrer les qualifications corrigées et les réinjecter comme exemples |

La dernière ligne est la plus importante à moyen terme. Chaque fois qu'un
technicien corrige une qualification, il produit une donnée annotée de meilleure
qualité que tout jeu synthétique. Capter ces corrections transforme un système
figé en système qui s'améliore.
