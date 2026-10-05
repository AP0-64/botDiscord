# Bot SQ

Bot Discord qui organise les events : il poste un sondage de dispo, puis ouvre un lobby privé où les joueurs dispo s'organisent en équipes.

Il tourne dans 2 salons, sur 2 serveurs différents (`BOT_CHANNEL_IDS`). Chaque salon a son propre planning, ses sondages et ses lobbies.

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

1. **Planning** : `ap0_64` ou le salon d'annonces suivi `MK8DX 150cc Lounge #sq-schedule` poste, dans un des salons du bot, un message avec des lignes du type
   `` `#12` **3v3:** <t:TIMESTAMP:F> - <t:TIMESTAMP:R> ``

   - Tous les messages postés **avant** le planning sont supprimés (anciens sondages et pings compris). Le planning lui-même reste.
   - Le nouveau planning remplace le précédent **de ce salon** (l'autre serveur garde le sien).
   - Les events passés sont ignorés. Un event dans moins de 24h a son sondage posté tout de suite.
   - Un autre message (« ok », etc.) ne déclenche rien.

2. **H-24h : sondage** dans le salon, avec les réactions ✅ Can / ❓ Not sure / ❌ Can't.
   Un seul vote par joueur, et la liste des votants se met à jour en direct.

3. **H-1h : lobby**. Un fil privé `… - #12 - Lobby` est créé avec tous les ✅, qui y sont pingés.
   Les joueurs y discutent pour former leurs équipes, puis les inscrivent sur le
   [salon d'inscription](https://discord.com/channels/445404006177570829/772517883107475516)
   (autre serveur), où un fil est créé pour chaque équipe.

   Un joueur qui vote ✅ plus tard est ajouté au lobby, et celui qui retire son ✅ en est retiré.

4. **H+4h : nettoyage**. Le lobby est supprimé.

5. **Ping Lounge** : tous les jours à 9h et 16h (heure de Paris), le bot écrit `@Lounge` dans chacun de ses salons.
   Si le serveur a un rôle `Lounge`, il est vraiment mentionné (notification). Sinon c'est du simple texte.

Le suivi est enregistré dans `scheduled_polls.json` et `active_polls.json`, donc un redémarrage du bot ne fait rien perdre.

## Permissions Discord

**Portail développeur → Bot** : activer **Message Content Intent**.

**Portail développeur → OAuth2 / Bot → Permissions du bot** : cocher les cases ci-dessous (entier : `360777477184`).

| Permission | Pourquoi |
| --- | --- |
| Voir les salons | Voir les messages et réactions |
| Envoyer des messages | Poster les sondages |
| Intégrer des liens | Afficher l'embed du sondage |
| Voir les anciens messages | Retrouver les sondages après un redémarrage |
| Ajouter des réactions | Mettre ✅ ❓ ❌ |
| Gérer les messages | Retirer l'ancien vote quand un joueur change d'avis, vider le salon à chaque planning |
| Créer des fils privés | Créer le lobby |
| Envoyer des messages dans les fils | Écrire dans le lobby |
| Gérer les fils | Supprimer le lobby à H+4h |
| Mentionner @everyone, @here et tous les rôles | Pinger le rôle `@Lounge` s'il n'est pas mentionnable par tous |

## Réglages

Les réglages se trouvent dans [botsq/config.py](botsq/config.py) :

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `SECONDS_BEFORE` | 24h | Publication du sondage |
| `REMINDER_BEFORE` | 1h | Ouverture du lobby |
| `THREADS_LIFETIME` | 4h | Suppression du lobby après le début de l'event |
| `REGISTRATION_URL` | — | Lien du salon d'inscription des équipes |
| `BOT_CHANNEL_IDS` | 2 salons (un par serveur) | Seuls salons où le bot lit les plannings et écrit |
| `LOUNGE_PING_TIMES` | 9h et 16h (Paris) | Heures du ping `@Lounge` |
| `LOUNGE_ROLE_NAME` | `@Lounge` | Nom du rôle pingé |
| `PLANNING_AUTHORS` | `ap0_64`, `MK8DX 150cc Lounge #sq-schedule` | Comptes autorisés à poster un planning |

## Organisation du code

| Fichier | Rôle |
| --- | --- |
| [main.py](main.py) | Point d'entrée (lance `python -m botsq` avec le Python du venv) |
| [botsq/\_\_main\_\_.py](botsq/__main__.py) | Charge le token et démarre le client |
| [botsq/config.py](botsq/config.py) | Réglages |
| [botsq/client.py](botsq/client.py) | Client Discord partagé |
| [botsq/storage.py](botsq/storage.py) | Lecture/écriture des JSON de suivi |
| [botsq/polls.py](botsq/polls.py) | Sondages : embed, votes, création |
| [botsq/lobby.py](botsq/lobby.py) | Lobby : création, synchro des votes, suppression |
| [botsq/scheduler.py](botsq/scheduler.py) | Boucles de fond (H-24h, H-1h, H+4h, ping Lounge) |
| [botsq/events.py](botsq/events.py) | Handlers Discord (planning, purge du salon, réactions) |
