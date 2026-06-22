# botDiscord

## Résumé

Petit projet avec trois bots Discord : `atlas`, `scora` et `botsq`. Le point d'entrée est `main.py` qui lance l'un des trois scripts.

## Prérequis

- Python 3.8+
- `pip` (ou un environnement virtuel)

## Installation

Créez et activez un environnement virtuel :

```bash
python -m venv .venv
source .venv/bin/activate
```

Installez les dépendances :

```bash
pip install -r requirements.txt
```

## Configuration

Copiez le fichier d'exemple `.env.example` vers `.env` et remplacez les valeurs par vos tokens :

```bash
cp .env.example .env
# puis ouvrez .env et collez vos tokens
```

## Variables d'environnement attendues

- `DISCORD_TOKEN_ATLAS` — token du bot Atlas
- `DISCORD_TOKEN_SCORA` — token du bot Scora
- `DISCORD_TOKEN_BOTSQ` — token du bot SQ

## Utilisation

Lancer Atlas :

```bash
python3 main.py atlas
```

Lancer Scora :

```bash
python3 main.py scora
```

Lancer SQ :

```bash
python3 main.py botsq
```

## Comportement

- `main.py` vérifie l'argument de ligne de commande (`atlas`, `scora` ou `botsq`) et exécute le script correspondant.
- `botsq.py` ne crée pas de sondage pour un événement déjà passé.
- `botsq.py` supprime les anciens messages du salon, remet `scheduled_polls.json` à zéro, conserve le message envoyé par `ap0_64`, puis crée les sondages futurs seulement 24h avant l'event.
- `scheduled_polls.json` contient uniquement la file d'attente du message courant.

## Fichiers importants

- [main.py](main.py) : point d'entrée, usage `python main.py atlas|scora|botsq`.
- [atlas.py](atlas.py) : implémentation minimale du bot Atlas, attend `DISCORD_TOKEN_ATLAS`.
- [scora.py](scora.py) : implémentation minimale du bot Scora, attend `DISCORD_TOKEN_SCORA`.
- [botsq.py](botsq.py) : bot SQ qui filtre les événements passés, nettoie le salon, réinitialise la file et attend `DISCORD_TOKEN_BOTSQ`.
- [scheduled_polls.json](scheduled_polls.json) : file d'attente réinitialisée à chaque nouveau message traité.
- [requirements.txt](requirements.txt) : dépendances Python.

## Dépannage

- Si vous obtenez l'erreur `DISCORD_TOKEN_* manquant`, vérifiez que `.env` contient la bonne variable.
- Si `Fichier introuvable` apparaît, vérifiez que les fichiers des bots existent bien à la racine.
