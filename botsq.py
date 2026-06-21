"""Bot SQ - Filtre les événements en supprimant les passés et garde max 2 jours."""
import os
import re

import discord
from dotenv import load_dotenv


def run() -> None:
    """Lancer le bot SQ"""

    load_dotenv()

    intents = discord.Intents.default()
    intents.message_content = True

    botsq = discord.Client(intents=intents)

    # Compilé une seule fois (au lieu de à chaque message)
    poll_line_pattern = re.compile(r"`#(\d+)` \*\*(.*?):\*\* (<t:\d+:F> - <t:\d+:R>)")

    # Source unique de vérité pour les options du sondage
    poll_options = [
        ("✅", "Can"),
        ("❗", "Can sub"),
        ("❓", "Not sure"),
        ("❌", "Can't"),
    ]

    def build_description(time_str: str, users_by_emoji: dict | None = None) -> str:
        """
        Construit la description de l'embed.
        - users_by_emoji=None  -> mode création : les 4 catégories à 0
        - users_by_emoji=dict  -> mode mise à jour :
        seules les catégories avec des votants s'affichent
        """
        parts = [time_str]
        for emoji, label in poll_options:
            if users_by_emoji is None:
                parts.append(f"{emoji} **{label} (0)**")
            else:
                users = users_by_emoji.get(emoji, [])
                if users:
                    parts.append(f"{emoji} **{label} ({len(users)})**\n" + ", ".join(users))
        return "\n\n".join(parts)

    @botsq.event
    async def on_ready() -> None:
        print("bot SQ prêt")

    @botsq.event
    async def on_message(message: discord.Message) -> None:
        if message.author == botsq.user:
            return

        if message.author.name != "ap0_64":
            return

        matches = poll_line_pattern.findall(message.content)

        for event_id, format_type, time_str in matches:
            embed = discord.Embed(
                title=f"{format_type} (ID: #{event_id})",
                description=build_description(time_str),
                color=0x2b2d31
            )

            poll_msg = await message.channel.send(embed=embed)

            for emoji, _ in poll_options:
                await poll_msg.add_reaction(emoji)

    async def update_embed(message: discord.Message) -> None:
        if not message.embeds:
            return

        embed = message.embeds[0]
        if not embed.description:
            return

        first_line = embed.description.split("\n\n")[0]

        users_by_emoji = {emoji: [] for emoji, _ in poll_options}
        for reaction in message.reactions:
            emoji = str(reaction.emoji)
            if emoji in users_by_emoji:
                async for user in reaction.users():
                    if botsq.user and user.id != botsq.user.id:
                        users_by_emoji[emoji].append(user.display_name)

        new_desc = build_description(first_line, users_by_emoji)

        if new_desc != embed.description:
            new_embed = discord.Embed(title=embed.title, description=new_desc, color=embed.color)
            await message.edit(embed=new_embed)

    async def get_poll_message(payload: discord.RawReactionActionEvent) -> discord.Message | None:
        """Récupère le message de sondage visé par le payload, ou None si non pertinent."""
        if botsq.user and payload.user_id == botsq.user.id:
            return None

        channel = botsq.get_channel(payload.channel_id) or await botsq.fetch_channel(payload.channel_id)
        if not isinstance(channel, discord.abc.Messageable):
            return None

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return None

        if not message.embeds or message.author != botsq.user:
            return None

        embed = message.embeds[0]
        if not embed.title or "(ID: #" not in embed.title:
            return None

        return message

    @botsq.event
    async def on_raw_reaction_add(payload: discord.RawReactionActionEvent) -> None:
        message = await get_poll_message(payload)
        if message is None:
            return

        # Un seul choix possible : on retire les autres réactions de ce membre
        for reaction in message.reactions:
            if str(reaction.emoji) != str(payload.emoji.name):
                async for user in reaction.users():
                    if user.id == payload.user_id:
                        await message.remove_reaction(reaction.emoji, user)

        await update_embed(message)

    @botsq.event
    async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent) -> None:
        message = await get_poll_message(payload)
        if message is None:
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
