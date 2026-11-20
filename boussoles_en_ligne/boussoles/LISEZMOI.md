# Boussoles SCANOPTIMUS9 (Streamlit)

## Lancer sur ton ordinateur
1. Installer Python 3.10 ou plus récent.
2. Dans ce dossier : `pip install -r requirements.txt`
3. `streamlit run app.py` : la page s'ouvre dans le navigateur.

Les données (Yahoo Finance, FRED, CFTC) sont téléchargées à l'ouverture, puis gardées 6 heures.
Le bouton « Mettre à jour les données » force un nouveau téléchargement.
Une copie locale est écrite dans `cache/` : si une source ne répond pas, l'application utilise la dernière copie (pastille 🟡 dans « Sources »).

## La mettre en ligne (gratuit)
1. Mettre ce dossier dans un dépôt GitHub.
2. Sur share.streamlit.io, choisir « New app », puis le dépôt et le fichier `app.py`.
3. L'application se met à jour seule à chaque visite (toutes les 6 heures au plus).

## Organisation
- `boussoles/regles.py` : seuils et lois validés. On n'y touche qu'après un nouveau test.
- `boussoles/donnees.py` : les téléchargements et la copie de secours.
- `boussoles/calcul.py` : cycles, S7, stratégie A, S5 et sa gestion, P4, E80, carte des prix, alertes de fond, or.
- `boussoles/ui.py` : cartes, jauges et compteurs.
- `app.py` : les quatre onglets (Vue d'ensemble, Marchés, Or, Interroger l'historique).

## Barre latérale
- Séance analysée : rejoue n'importe quelle séance passée (seules les données connues ce jour-là sont utilisées).
- Comparer avec une autre séance : affiche les écarts (⇄) sur la vue d'ensemble et en tête de chaque marché.
- Mémoire des statistiques : 4 dernières années (par défaut) ou tout l'historique. Elle règle les âges, les profondeurs, les situations comparables et la carte des prix. Les lois du VIX restent ajustées sur 1990-2026.

## Carte des prix
Le cône n'est plus symétrique : il reprend ce qu'ont fait les jours les plus proches de la situation actuelle (même phase, même profondeur, même âge relatif ; 6 marchés), ramenés à la volatilité du jour.

## Titres de chaque thématique (v5, 17/11/2026)
- Sous l'analyse de SOX, Logiciel et NDX, l'application affiche :
  - la position en titres : cœur, liste des 5, cash ou à l'abri ;
  - les 5 titres choisis et le cœur ;
  - pour chaque titre : son bêta en correction, sa performance depuis le S5 et sa moyenne 50.
- Fichier à rafraîchir chaque trimestre : `boussoles/compositions_actuelles.csv` (poids de SOXX et IGV). Pour le NDX, les membres sont dans `ndx_membres.csv` et le classement se fait par volume en dollars.

## Or en titres et péremption (v5.1, 17/11/2026)
- Onglet « Or · stratégie » : les 5 plus gros poids de GDX, à parts égales, détenus quand la stratégie or est investie (or_sans_etf).
- Barre latérale « Péremption » : réglages et fichiers, avec 🟢, 🟡 (30 jours) ou 🔴 (expiré), et une alerte en haut de page si une date est dépassée.
- La composition GDX vient de la dernière déclaration SEC (telecharger_y4_or.py).
