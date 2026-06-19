"""Bot Scora"""
import os

import discord
from dotenv import load_dotenv


def run() -> None:
    """Lancer le bot Scora"""

    load_dotenv()

    scora = discord.Client(intents=discord.Intents.all())

    @scora.event
    async def on_ready() -> None:
        print("bot Scora prêt")

    token = os.getenv("DISCORD_TOKEN_SCORA")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN_SCORA manquant dans le fichier .env "
        )

    scora.run(token)


if __name__ == "__main__":
    run()
