"""Bot SQ - Filtre les événements en supprimant les passés et garde max 2 jours."""
import json
import os
import re
import time
from pathlib import Path

import discord
from discord.ext import tasks
from dotenv import load_dotenv


def run() -> None:
    """Lancer le bot SQ"""

    load_dotenv()

    intents = discord.Intents.default()
    intents.message_content = True

    botsq = discord.Client(intents=intents)

    # \3 garantit que les deux timestamps (F et R) sont bien identiques
    poll_line_pattern = re.compile(r"`#(\d+)` \*\*(.*?):\*\* <t:(\d+):F> - <t:\3:R>")

    poll_options = [
        ("✅", "Can"),
        ("❗", "Can sub"),
        ("❓", "Not sure"),
        ("❌", "Can't"),
    ]

    schedule_file = Path(__file__).parent / "scheduled_polls.json"
    seconds_before = 24 * 3600  # créer le sondage 24h avant l'event

    # État des votes en mémoire : message_id -> emoji -> {user_id: display_name}
    vote_state: dict[int, dict[str, dict[int, str]]] = {}

    # --- Persistance des sondages en attente de création ---

    def load_schedule() -> list[dict]:
        if not schedule_file.exists():
            return []
        try:
            return json.loads(schedule_file.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def save_schedule(entries: list[dict]) -> None:
        schedule_file.write_text(json.dumps(entries, indent=2))

    # --- Construction de l'embed ---

    def build_description(
        time_str: str,
        state: dict[str, dict[int, str]] | None = None,
    ) -> str:
        parts = [time_str]
        for emoji, label in poll_options:
            if state is None:
                parts.append(f"{emoji} **{label} (0)**")
            else:
                users = list(state.get(emoji, {}).values())
                if users:
                    parts.append(
                        f"{emoji} **{label} ({len(users)})**\n"
                        + ", ".join(users)
                    )
        return "\n\n".join(parts)

    async def render_embed(
        message: discord.Message,
        state: dict[str, dict[int, str]],
    ) -> None:
        embed = message.embeds[0]
        first_line = embed.description.split("\n\n")[0] if embed.description else ""
        new_desc = build_description(first_line, state)
        if new_desc != embed.description:
            new_embed = discord.Embed(
                title=embed.title,
                description=new_desc,
                color=embed.color,
            )
            await message.edit(embed=new_embed)

    async def hydrate_votes(message: discord.Message) -> dict[str, dict[int, str]]:
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

    async def create_poll(
        channel: discord.abc.Messageable,
        event_id: str,
        format_type: str,
        timestamp: str,
    ) -> None:
        """Crée le message de sondage pour un event donné."""
        time_str = f"<t:{timestamp}:F> - <t:{timestamp}:R>"
        embed = discord.Embed(
            title=f"{format_type} (ID: #{event_id})",
            description=build_description(time_str),
            color=0x2b2d31
        )
        poll_msg = await channel.send(embed=embed)
        vote_state[poll_msg.id] = {emoji: {} for emoji, _ in poll_options}

        for emoji, _ in poll_options:
            await poll_msg.add_reaction(emoji)

    @botsq.event
    async def on_ready() -> None:
        print("bot SQ prêt")
        if not check_scheduled_polls.is_running():
            check_scheduled_polls.start()

    @botsq.event
    async def on_message(message: discord.Message) -> None:
        if message.author == botsq.user:
            return
        if message.author.name != "ap0_64":
            return

        matches = poll_line_pattern.findall(message.content)
        if not matches:
            return

        schedule = load_schedule()
        now = time.time()

        for event_id, format_type, timestamp in matches:
            post_at = int(timestamp) - seconds_before

            if post_at <= now:
                # Moins de 24h avant l'event (ou déjà passé) :
                # on crée le sondage tout de suite
                await create_poll(message.channel, event_id, format_type, timestamp)
            else:
                schedule.append({
                    "event_id": event_id,
                    "format_type": format_type,
                    "timestamp": timestamp,
                    "channel_id": message.channel.id,
                    "post_at": post_at,
                })

        save_schedule(schedule)

    @tasks.loop(minutes=1)
    async def check_scheduled_polls() -> None:
        schedule = load_schedule()
        if not schedule:
            return

        now = time.time()
        due = [entry for entry in schedule if entry["post_at"] <= now]
        if not due:
            return

        remaining = [entry for entry in schedule if entry["post_at"] > now]

        for entry in due:
            channel = botsq.get_channel(entry["channel_id"])
            if channel is None:
                channel = await botsq.fetch_channel(entry["channel_id"])
            if isinstance(channel, discord.abc.Messageable):
                await create_poll(
                    channel,
                    entry["event_id"],
                    entry["format_type"],
                    entry["timestamp"],
                )

        save_schedule(remaining)

    async def get_poll_message(
        payload: discord.RawReactionActionEvent,
    ) -> discord.Message | None:
        if botsq.user and payload.user_id == botsq.user.id:
            return None

        channel = botsq.get_channel(payload.channel_id)
        if channel is None:
            channel = await botsq.fetch_channel(payload.channel_id)
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
        member = payload.member
        display_name = member.display_name if member else str(payload.user_id)
        changed = False

        for other_emoji, users in state.items():
            if other_emoji != emoji and user_id in users:
                users.pop(user_id)
                changed = True
                try:
                    await message.remove_reaction(
                        other_emoji,
                        discord.Object(id=user_id),
                    )
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
