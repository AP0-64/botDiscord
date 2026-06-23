"""Bot SQ - Filtre les événements en supprimant les passés et garde max 2 jours."""
import asyncio
import json
import os
import re
import time
from pathlib import Path

import discord
from dotenv import load_dotenv
from discord.ext import tasks


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
        ("❓", "Not sure"),
        ("❌", "Can't"),
    ]

    schedule_file = Path(__file__).parent / "scheduled_polls.json"
    seconds_before = 24 * 3600

    # État des votes en mémoire : message_id -> emoji -> {user_id: display_name}
    vote_state: dict[int, dict[str, dict[int, str]]] = {}

    def save_schedule(entries: list[dict]) -> None:
        schedule_file.write_text(json.dumps(entries, indent=2))

    def load_schedule() -> list[dict]:
        if not schedule_file.exists():
            return []
        try:
            return json.loads(schedule_file.read_text())
        except (json.JSONDecodeError, OSError):
            return []

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

    async def clear_previous_messages(message: discord.Message) -> None:
        channel = message.channel
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            await channel.purge(before=message, limit=None)
        except (discord.Forbidden, discord.HTTPException):
            pass

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

        now = time.time()

        await clear_previous_messages(message)
        save_schedule([])

        schedule: list[dict] = []

        for event_id, format_type, timestamp in matches:
            event_timestamp = int(timestamp)
            if event_timestamp <= now:
                continue

            post_at = event_timestamp - seconds_before

            if post_at <= now:
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
        due = [
            entry for entry in schedule
            if entry["post_at"] <= now and int(entry["timestamp"]) > now
        ]
        if not due:
            return

        remaining = [
            entry for entry in schedule
            if entry["post_at"] > now and int(entry["timestamp"]) > now
        ]

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
    async def maybe_create_team_channel(
        message: discord.Message,
        state: dict[str, dict[int, str]]
    ) -> None:

        """Crée un salon éphémère par équipe complète dès que le quota 'Can' est atteint."""
        embed = message.embeds[0]
        title = embed.title or ""

        # Extrait le format (2v2, 3v3, 4v4, 6v6) depuis le titre de l'embed
        match = re.search(r"(\d+)v\d+", title, re.IGNORECASE)
        if not match:
            return
        team_size = int(match.group(1))

        guild = message.guild
        if guild is None:
            return

        can_emoji = "✅"
        can_users: dict[int, str] = state.get(can_emoji, {})
        can_ids = list(can_users.keys())
        total_can = len(can_ids)

        if total_can < team_size:
            return  # Pas encore assez de joueurs

        # Récupère les salons éphémères déjà créés pour ce sondage
        already_assigned: set[int] = set()
        for existing_channel in guild.channels:
            if isinstance(existing_channel, discord.TextChannel):
                topic = existing_channel.topic or ""
                if f"poll:{message.id}" in topic:
                    # Récupère les membres du salon depuis le topic
                    members_part = re.search(r"members:([\d,]+)", topic)
                    if members_part:
                        ids = [int(x) for x in members_part.group(1).split(",") if x]
                        already_assigned.update(ids)

        # Joueurs "can" pas encore dans un salon
        unassigned = [uid for uid in can_ids if uid not in already_assigned]

        # Crée autant d'équipes complètes que possible avec les non-assignés
        teams_to_create = len(unassigned) // team_size
        if teams_to_create == 0:
            return

        category = None  # Met une catégorie si tu veux, ou laisse None

        for i in range(teams_to_create):
            team_ids = unassigned[i * team_size : (i + 1) * team_size]
            members = [guild.get_member(uid) for uid in team_ids]
            members = [m for m in members if m is not None]

            # Extrait l'event_id depuis le titre "#N"
            event_match = re.search(r"#(\d+)", title)
            event_id = event_match.group(1) if event_match else "?"

            # Nom du salon : eq-{format}-{event_id}-{index}
            team_index = (len(already_assigned) // team_size) + i + 1
            channel_name = f"eq-{match.group(0).lower()}-{event_id}-{team_index}"

            # Permissions : visible uniquement par les membres de l'équipe + admins
            overwrites: dict[
                discord.Role | discord.Member | discord.Object,
                discord.PermissionOverwrite
            ] = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
            }
            for member in members:
                overwrites[member] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                )

            topic = (
                f"poll:{message.id} "
                f"members:{','.join(str(uid) for uid in team_ids)}"
            )

            try:
                new_channel = await guild.create_text_channel(
                    name=channel_name,
                    overwrites=overwrites,
                    topic=topic,
                    category=category,
                    reason=f"Équipe {team_index} pour l'event #{event_id}",
                )
                mentions = " ".join(m.mention for m in members)
                await new_channel.send(
                    f"🎮 **Équipe {team_index}** — {match.group(0).upper()} event #{event_id}\n"
                    f"Joueurs : {mentions}\n"
                    f"Ce salon sera supprimé après l'event."
                )

                await asyncio.sleep(12 * 3600)
                await new_channel.delete(reason="Salon éphémère — 12h écoulées")

            except (discord.Forbidden, discord.HTTPException) as e:
                print(f"Impossible de créer le salon équipe : {e}")

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
            if emoji == "✅":
                await maybe_create_team_channel(message, state)

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
