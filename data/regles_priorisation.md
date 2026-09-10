# Règles de qualification et de priorisation

Ce document est la référence métier du triage. Il est annexé au prompt du modèle
et sert également de spécification à la ligne de base par règles.

Dans une vraie mise en œuvre, c'est ce fichier — et lui seul — qui est adapté au
client. Le code ne change pas.

## Priorité

| Niveau | Critère | Exemples |
|---|---|---|
| **P1_critique** | L'activité est arrêtée : impossible de facturer, d'expédier, de produire ou de se connecter. Plusieurs utilisateurs touchés, aucun contournement. | Serveur inaccessible, aucune facture ne peut être validée, perte de données |
| **P2_majeur** | Un utilisateur ou un service est bloqué sans contournement, ou une fonction importante est dégradée à l'approche d'une échéance. | Clôture comptable dans deux jours et les écritures ne se génèrent pas |
| **P3_mineur** | Gêne réelle mais contournement possible, ou demande d'information sur l'usage de l'outil. | Question sur un paramétrage, export à refaire à la main |
| **P4_cosmetique** | Confort, affichage, libellé, ou demande d'évolution sans caractère d'urgence. | Renommer une colonne, ajouter un champ facultatif |

**Règle d'arbitrage.** En cas d'hésitation entre deux niveaux, retenir le plus
bas, sauf si la demande mentionne explicitement un blocage ou une échéance
datée. Sur-prioriser désorganise la file d'attente plus sûrement que
sous-prioriser.

## Catégories

| Catégorie | Définition |
|---|---|
| `anomalie` | Le logiciel ne fait pas ce qu'il devrait : erreur, calcul faux, comportement inattendu. |
| `question_utilisation` | L'outil fonctionne, l'utilisateur ne sait pas s'en servir. |
| `probleme_donnees` | Le logiciel fonctionne, les données sont fausses, en double ou manquantes. |
| `demande_evolution` | Une fonction qui n'existe pas est demandée. |
| `acces_droits` | Connexion, mot de passe, permissions, création de compte. |
| `performance` | Lenteur, temps de réponse, indisponibilité, saturation. |
| `formation` | Demande d'accompagnement ou de session de formation. |
| `hors_perimetre` | Sans rapport avec l'ERP : matériel, réseau, sujets commerciaux, démarchage. |

## Routage

| Catégorie | Équipe |
|---|---|
| `question_utilisation`, `formation` | `support_n1` |
| `anomalie`, `probleme_donnees` | `support_n2_fonctionnel` |
| `demande_evolution` | `developpement` |
| `performance` | `infrastructure` |
| `acces_droits` | `administration_fonctionnelle` |
| `hors_perimetre` | `commercial` |

**Exception.** Une anomalie dont la correction exige manifestement du
développement — module sur mesure, script d'import, rapport personnalisé — est
routée directement vers `developpement`.

## Caractère bloquant

`est_bloquant` vaut vrai lorsque l'utilisateur ne peut pas poursuivre son
travail, y compris par un moyen détourné. Une lenteur pénible n'est pas
bloquante ; une erreur qui empêche d'enregistrer l'est.

## Informations manquantes

Un ticket est exploitable si l'on peut, à sa seule lecture, reproduire le
problème. Réclamer systématiquement, quand elles sont absentes :

- la référence de la pièce concernée (commande, facture, article) ;
- le message d'erreur exact ou une capture ;
- l'utilisateur et le moment de survenue ;
- ce qui était attendu, si le comportement obtenu est décrit sans point de comparaison.

Ne rien réclamer lorsque la demande est déjà complète : une liste vide est une
réponse valable, et c'est souvent la bonne.
