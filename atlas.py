"""Bot Atlas."""
import os

import discord
from dotenv import load_dotenv


def run() -> None:
    """Lancer le bot Atlas"""

    load_dotenv()

    atlas = discord.Client(intents=discord.Intents.all())

    @atlas.event
    async def on_ready() -> None:
        print("bot Atlas prêt")

    token = os.getenv("DISCORD_TOKEN_ATLAS")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN_ATLAS manquant dans le fichier .env "
        )

    atlas.run(token)


if __name__ == "__main__":
    run()
