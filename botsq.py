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

    poll_line_pattern = re.compile(r"`#(\d+)` \*\*(.*?):\*\* (<t:\d+:F> - <t:\d+:R>)")

    poll_options = [
        ("✅", "Can"),
        ("❗", "Can sub"),
        ("❓", "Not sure"),
        ("❌", "Can't"),
    ]

    # État en mémoire : message_id -> emoji -> {user_id: display_name}
    vote_state: dict[int, dict[str, dict[int, str]]] = {}

    def build_description(time_str: str, state: dict[str, dict[int, str]] | None = None) -> str:
        parts = [time_str]
        for emoji, label in poll_options:
            if state is None:
                parts.append(f"{emoji} **{label} (0)**")
            else:
                users = list(state.get(emoji, {}).values())
                if users:
                    parts.append(f"{emoji} **{label} ({len(users)})**\n" + ", ".join(users))
        return "\n\n".join(parts)

    async def render_embed(message: discord.Message, state: dict[str, dict[int, str]]) -> None:
        embed = message.embeds[0]
        first_line = embed.description.split("\n\n")[0] if embed.description else ""
        new_desc = build_description(first_line, state)
        if new_desc != embed.description:
            new_embed = discord.Embed(title=embed.title, description=new_desc, color=embed.color)
            await message.edit(embed=new_embed)

    async def hydrate_votes(message: discord.Message) -> dict[str, dict[int, str]]:
        """Charge l'état des votes depuis Discord, une seule fois par message (coût ponctuel)."""
        if message.id in vote_state:
            return vote_state[message.id]

        state: dict[str, dict[int, str]] = {emoji: {} for emoji, _ in poll_options}
        for reaction in message.reactions:
            emoji = str(reaction.emoji)
            if emoji in state:
                async for user in reaction.users():
                    if botsq.user and user.id != botsq.user.id:
                        state[emoji][user.id] = user.display_name

        vote_state[message.id] = state
        return state

    @botsq.event
    async def on_ready() -> None:
        print("bot SQ prêt")

    @botsq.event
    async def on_message(message: discord.Message) -> None:
        if message.author == botsq.user:
            return
        if message.author.name != "ap0_64":
            return

        for event_id, format_type, time_str in poll_line_pattern.findall(message.content):
            embed = discord.Embed(
                title=f"{format_type} (ID: #{event_id})",
                description=build_description(time_str),
                color=0x2b2d31
            )
            poll_msg = await message.channel.send(embed=embed)
            vote_state[poll_msg.id] = {emoji: {} for emoji, _ in poll_options}

            for emoji, _ in poll_options:
                await poll_msg.add_reaction(emoji)

    async def get_poll_message(payload: discord.RawReactionActionEvent) -> discord.Message | None:
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

        state = await hydrate_votes(message)
        emoji = str(payload.emoji)
        if emoji not in state:
            return

        user_id = payload.user_id
        display_name = payload.member.display_name if payload.member else str(payload.user_id)
        changed = False

        # Un seul choix possible : on retire les autres votes du membre (sans refetch, juste sur l'état connu)
        for other_emoji, users in state.items():
            if other_emoji != emoji and user_id in users:
                users.pop(user_id)
                changed = True
                try:
                    await message.remove_reaction(other_emoji, discord.Object(id=user_id))
                except discord.HTTPException:
                    pass

        if user_id not in state[emoji]:
            state[emoji][user_id] = display_name
            changed = True

        if changed:
            await render_embed(message, state)

    @botsq.event
    async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent) -> None:
        message = await get_poll_message(payload)
        if message is None:
            return

        state = await hydrate_votes(message)
        emoji = str(payload.emoji)
        if emoji in state and state[emoji].pop(payload.user_id, None) is not None:
            await render_embed(message, state)

    token = os.getenv("DISCORD_TOKEN_BOTSQ")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN_BOTSQ manquant dans le fichier .env "
        )

    botsq.run(token)


if __name__ == "__main__":
    run()
