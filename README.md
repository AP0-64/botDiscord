# Bot SQ

Bot Discord qui organise les events : il poste un sondage de dispo, ouvre un lobby pour former les équipes, puis crée un fil privé par équipe.

## Installation

Python 3.10+ requis.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.exemple .env   # puis colle le token du bot dans DISCORD_TOKEN_BOTSQ
```

Lancer le bot :

```bash
python3 main.py
```

## Déroulé

1. **Planning** : `ap0_64` poste un message avec des lignes du type
   `` `#12` **3v3:** <t:TIMESTAMP:F> - <t:TIMESTAMP:R> ``
   Chaque nouveau planning remplace le précédent. Les events passés sont ignorés.

2. **H-24h : sondage** dans le salon, avec les réactions ✅ Can / ❓ Not sure / ❌ Can't.
   Un seul vote par joueur, et la liste des votants se met à jour en direct.

3. **H-1h : lobby**. Un fil privé `… - #12 - Lobby` est créé avec tous les ✅, qui y sont pingés.
   Les joueurs y forment leurs équipes :
   - `!team @joueur2 @joueur3` : enregistre une équipe (toi + les joueurs mentionnés).
     La taille dépend du format : 2v2 → 2, 3v3 → 3, 4v4 → 4, 6v6 → 6.
   - `!unteam` : annule ton équipe.

   Un joueur qui vote ✅ plus tard est ajouté au lobby. Un joueur qui retire son ✅ en est retiré, et son équipe est dissoute.

4. **H-5min : fils d'équipe**. Un fil privé `… - #12 - Room N` est créé par équipe enregistrée.
   Les inscriptions sont closes, et les ✅ sans équipe sont annoncés **absents** dans le lobby.

5. **H+4h : nettoyage**. Tous les fils de l'event (lobby et rooms) sont supprimés.

Le suivi est enregistré dans `scheduled_polls.json` et `active_polls.json`, donc un redémarrage du bot ne fait rien perdre.

## Permissions Discord

**Portail développeur → Bot** : activer **Message Content Intent**.

**Sur le salon des sondages** :

| Permission | Pourquoi |
| --- | --- |
| Voir le salon | Voir les messages et réactions |
| Envoyer des messages | Poster les sondages |
| Intégrer des liens | Afficher l'embed du sondage |
| Lire l'historique des messages | Retrouver les sondages après un redémarrage |
| Ajouter des réactions | Mettre ✅ ❓ ❌ |
| Gérer les messages | Retirer l'ancien vote quand un joueur change d'avis |
| Créer des fils privés | Créer le lobby et les rooms |
| Envoyer des messages dans les fils | Écrire dans les fils |
| Gérer les fils | Supprimer les fils à H+4h |

## Réglages

Les délais se trouvent en haut de [botsq.py](botsq.py) :

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `seconds_before` | 24h | Publication du sondage |
| `reminder_before` | 1h | Ouverture du lobby |
| `threads_before` | 5 min | Création des fils d'équipe |
| `threads_lifetime` | 4h | Suppression des fils après le début de l'event |

## Vérifier le code

```bash
pip install pyright
pyright botsq.py
```
