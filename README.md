# botDiscord

## Résumé

Petit projet avec deux bots Discord : `atlas` et `scora`. Le point d'entrée est `main.py` qui lance l'un des deux scripts.

## Prérequis

- Python 3.8+
- `pip` (ou un environnement virtuel)

## Installation

Créez et activez un environnement virtuel (optionnel mais recommandé) :

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

## Utilisation

Lancer Atlas :

```bash
python main.py atlas
```

Lancer Scora :

```bash
python main.py scora
```

## Comportement

- `main.py` vérifie l'argument de ligne de commande (`atlas` ou `scora`) et exécute le script correspondant (`atlas.py` ou `scora.py`).

## Fichiers importants

- [main.py](main.py) : point d'entrée, usage `python main.py atlas|scora`.
- [atlas.py](atlas.py) : implémentation minimale du bot Atlas, attend `DISCORD_TOKEN_ATLAS`.
- [scora.py](scora.py) : implémentation minimale du bot Scora, attend `DISCORD_TOKEN_SCORA`.
- [requirements.txt](requirements.txt) : dépendances Python.

## Dépannage

- Si vous obtenez l'erreur `DISCORD_TOKEN_* manquant`, vérifiez que `.env` contient la bonne variable.
- Si `Fichier introuvable` apparaît, vérifiez que `atlas.py` ou `scora.py` existe bien à la racine.
