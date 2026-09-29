# Bot SQ

Bot Discord qui organise les events : il poste un sondage de dispo, puis ouvre un lobby privé où les joueurs dispo s'organisent en équipes.

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
   Les joueurs y discutent pour former leurs équipes, puis les inscrivent sur le
   [salon d'inscription](https://discord.com/channels/445404006177570829/772517883107475516)
   (autre serveur), où un fil est créé pour chaque équipe.

   Un joueur qui vote ✅ plus tard est ajouté au lobby, et celui qui retire son ✅ en est retiré.

4. **H+4h : nettoyage**. Le lobby est supprimé.

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
| Créer des fils privés | Créer le lobby |
| Envoyer des messages dans les fils | Écrire dans le lobby |
| Gérer les fils | Supprimer le lobby à H+4h |

## Réglages

Les réglages se trouvent en haut de [botsq.py](botsq.py) :

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `seconds_before` | 24h | Publication du sondage |
| `reminder_before` | 1h | Ouverture du lobby |
| `threads_lifetime` | 4h | Suppression du lobby après le début de l'event |
| `registration_url` | — | Lien du salon d'inscription des équipes |

## Vérifier le code

```bash
pip install pyright
pyright botsq.py
```
