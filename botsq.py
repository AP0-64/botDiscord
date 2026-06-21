"""Bot SQ - Filtre les événements en supprimant les passés et garde max 2 jours."""
import os
import re

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

        pattern = re.compile(r"`#(\d+)` \*\*(.*?):\*\* (<t:\d+:F> - <t:\d+:R>)")
        matches = pattern.findall(message.content)

        for match in matches:
            event_id, format_type, time_str = match

            embed = discord.Embed(
                title=f"{format_type} (ID: #{event_id})",
                description=(
                    f"{time_str}\n\n"
                    "✅ **Can (0)**\n\n"
                    "❗ **Can sub (0)**\n\n"
                    "❓ **Not sure (0)**\n\n"
                    "❌ **Can't (0)**"
                ),
                color=0x2b2d31  # Default Discord dark embed color
            )

            poll_msg = await message.channel.send(embed=embed)

            # Ajout des réactions du sondage
            reactions = ["✅", "❗", "❓", "❌"]
            for reaction in reactions:
                await poll_msg.add_reaction(reaction)

    async def update_embed(message: discord.Message) -> None:
        if not message.embeds:
            return

        embed = message.embeds[0]
        if not embed.description:
            return
        # On garde la première ligne qui contient l'horaire
        first_line = embed.description.split("\n\n")[0]

        categories = {
            "✅": {"title": "Can", "users": []},
            "❗": {"title": "Can sub", "users": []},
            "❓": {"title": "Not sure", "users": []},
            "❌": {"title": "Can't", "users": []}
        }

        # On parcours les réactions pour récupérer les utilisateurs
        for reaction in message.reactions:
            emoji = str(reaction.emoji)
            if emoji in categories:
                async for user in reaction.users():
                    if botsq.user and user.id != botsq.user.id:
                        categories[emoji]["users"].append(user.display_name)

        # On reconstruit la description
        desc_parts = [first_line]
        for emoji in ["✅", "❗", "❓", "❌"]:
            data = categories[emoji]
            users = data["users"]
            count = len(users)
            if count > 0:
                part = f"{emoji} **{data['title']} ({count})**\n" + ", ".join(users)
                desc_parts.append(part)

        new_desc = "\n\n".join(desc_parts)

        # On met à jour le message si besoin
        if new_desc != embed.description:
            new_embed = discord.Embed(title=embed.title, description=new_desc, color=embed.color)
            await message.edit(embed=new_embed)

    @botsq.event
    async def on_raw_reaction_add(payload: discord.RawReactionActionEvent) -> None:
        if botsq.user and payload.user_id == botsq.user.id:
            return

        channel = botsq.get_channel(payload.channel_id) or await botsq.fetch_channel(payload.channel_id)
        if not isinstance(channel, discord.abc.Messageable):
            return
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        if not message.embeds or message.author != botsq.user:
            return

        embed = message.embeds[0]
        if not embed.title or "(ID: #" not in embed.title:
            return

        # Supprimer les autres réactions de ce membre (pour qu'il n'ait qu'un seul choix)
        for reaction in message.reactions:
            if str(reaction.emoji) != str(payload.emoji.name):
                async for user in reaction.users():
                    if user.id == payload.user_id:
                        await message.remove_reaction(reaction.emoji, user)

        await update_embed(message)

    @botsq.event
    async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent) -> None:
        if botsq.user and payload.user_id == botsq.user.id:
            return

        channel = botsq.get_channel(payload.channel_id) or await botsq.fetch_channel(payload.channel_id)
        if not isinstance(channel, discord.abc.Messageable):
            return
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        if not message.embeds or message.author != botsq.user:
            return

        embed = message.embeds[0]
        if not embed.title or "(ID: #" not in embed.title:
            return

        await update_embed(message)

    token = os.getenv("DISCORD_TOKEN_BOTSQ")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN_BOTSQ manquant dans le fichier .env "
        )

    botsq.run(token)


if __name__ == "__main__":
    run()
