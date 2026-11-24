"""Lancement du bot Toadette : python -m bot"""
import os

from dotenv import load_dotenv

# Import nécessaire : enregistre les handlers sur le client
from . import events  # noqa: F401  # pylint: disable=unused-import
from .client import client


def run() -> None:
    """Lancer le bot Toadette"""
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN_BOTTOADETTE")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN_BOTTOADETTE manquant dans le fichier .env "
        )

    client.run(token)


if __name__ == "__main__":
    run()
