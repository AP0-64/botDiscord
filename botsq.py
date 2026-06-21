"""Bot SQ - Filtre les événements en supprimant les passés et garde max 2 jours."""
import os

import discord
from dotenv import load_dotenv


def run() -> None:
    """Lancer le bot SQ"""

    load_dotenv()

    # Configurer les intents nécessaires
    intents = discord.Intents.default()
    intents.message_content = True

    botsq = discord.Client(intents=intents)

    @botsq.event
    async def on_ready() -> None:
        print("bot SQ prêt")

    @botsq.event
    async def on_message(message: discord.Message) -> None:
        if message.author == botsq.user:
            return

        if message.author.name != "ap0_64":
            return

    token = os.getenv("DISCORD_TOKEN_BOTSQ")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN_BOTSQ manquant dans le fichier .env "
        )

    botsq.run(token)


if __name__ == "__main__":
    run()
