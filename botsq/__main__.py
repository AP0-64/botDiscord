"""Lancement du bot SQ : python -m botsq"""
import os

from dotenv import load_dotenv

from . import events  # noqa: F401  (enregistre les handlers sur le client)
from .client import botsq


def run() -> None:
    """Lancer le bot SQ"""
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN_BOTSQ")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN_BOTSQ manquant dans le fichier .env "
        )

    botsq.run(token)


if __name__ == "__main__":
    run()
