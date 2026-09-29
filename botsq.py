"""Bot SQ - Filtre les événements en supprimant les passés et garde max 2 jours."""
import asyncio
import json
import os
import re
import time
from datetime import datetime
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

    # Sondages publiés, suivis pour l'ouverture du lobby (H-1) et sa suppression (H+4h)
    active_polls_file = Path(__file__).parent / "active_polls.json"
    reminder_before = 3600
    threads_lifetime = 4 * 3600  # Lobby supprimé 4h après le début de l'event
    # Protège active_polls.json entre la boucle et les réactions
    polls_lock = asyncio.Lock()

    # Salon où les équipes s'inscrivent (autre serveur)
    registration_url = "https://discord.com/channels/445404006177570829/772517883107475516"

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

    def save_active_polls(entries: list[dict]) -> None:
        active_polls_file.write_text(json.dumps(entries, indent=2))

    def load_active_polls() -> list[dict]:
        if not active_polls_file.exists():
            return []
        try:
            entries = json.loads(active_polls_file.read_text())
        except (json.JSONDecodeError, OSError):
            return []
        for entry in entries:
            entry.setdefault("lobby_thread_id", None)
        return entries

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

        active_polls = load_active_polls()
        active_polls.append({
            "message_id": poll_msg.id,
            "channel_id": poll_msg.channel.id,
            "event_id": event_id,
            "format_type": format_type,
            "timestamp": int(timestamp),
            "reminded": False,
            "lobby_thread_id": None,
        })
        save_active_polls(active_polls)

    async def clear_previous_messages(message: discord.Message) -> None:
        channel = message.channel
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            pass # await channel.purge(before=message, limit=None)
        except (discord.Forbidden, discord.HTTPException):
            pass

    @botsq.event
    async def on_ready() -> None:
        print("bot SQ prêt")
        if not check_scheduled_polls.is_running():
            check_scheduled_polls.start()
        if not check_active_polls.is_running():
            check_active_polls.start()

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
                try:
                    channel = await botsq.fetch_channel(entry["channel_id"])
                except discord.NotFound:
                    print(f"Salon introuvable (channel_id={entry['channel_id']}), entrée ignorée.")
                    continue
                except discord.HTTPException as e:
                    print(f"Erreur HTTP en récupérant le salon : {e}")
                    continue
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
            try:
                channel = await botsq.fetch_channel(payload.channel_id)
            except discord.NotFound:
                print(f"Salon introuvable (channel_id={payload.channel_id}), entrée ignorée.")
                return None
            except discord.HTTPException as e:
                print(f"Erreur HTTP en récupérant le salon : {e}")
                return None
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

    async def fetch_poll_message(entry: dict) -> discord.Message | None:
        channel = botsq.get_channel(entry["channel_id"])
        if channel is None:
            try:
                channel = await botsq.fetch_channel(entry["channel_id"])
            except discord.HTTPException as e:
                print(f"Salon du sondage #{entry['event_id']} introuvable : {e}")
                return None
        if not isinstance(channel, discord.TextChannel):
            return None
        try:
            return await channel.fetch_message(entry["message_id"])
        except discord.HTTPException as e:
            print(f"Sondage #{entry['event_id']} introuvable : {e}")
            return None

    def thread_name(entry: dict, suffix: str) -> str:
        dt = datetime.fromtimestamp(entry["timestamp"])
        date_str = f"{dt.month}/{dt.day}, {dt:%H:%M:%S}"
        return f"{date_str} - {entry['format_type']} - #{entry['event_id']} - {suffix}"[:100]

    async def get_can_ids(message: discord.Message) -> list[int]:
        state = await hydrate_votes(message)
        return list(state.get("✅", {}).keys())

    async def get_thread(thread_id: int | None) -> discord.Thread | None:
        if thread_id is None:
            return None
        try:
            thread = botsq.get_channel(thread_id) or await botsq.fetch_channel(thread_id)
        except discord.HTTPException:
            return None
        return thread if isinstance(thread, discord.Thread) else None

    async def open_lobby(entry: dict, message: discord.Message) -> None:
        """H-1 : crée un fil privé avec tous les 'Can' pour qu'ils discutent des équipes."""
        channel = message.channel
        if not isinstance(channel, discord.TextChannel):
            return
        can_ids = await get_can_ids(message)
        if not can_ids:
            return

        try:
            lobby = await channel.create_thread(
                name=thread_name(entry, "Lobby"),
                type=discord.ChannelType.private_thread,
                invitable=False,
                auto_archive_duration=1440,
                reason=f"Lobby de l'event #{entry['event_id']}",
            )
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"Impossible de créer le lobby : {e}")
            return

        entry["lobby_thread_id"] = lobby.id
        entry.setdefault("thread_ids", []).append(lobby.id)
        for uid in can_ids:
            try:
                await lobby.add_user(discord.Object(id=uid))
            except discord.HTTPException:
                pass

        ts = entry["timestamp"]
        mentions = " ".join(f"<@{uid}>" for uid in can_ids)
        text = (
            f"{mentions}\n"
            f"Vous avez voté **Can** pour **{entry['format_type']} (ID: #{entry['event_id']})** : "
            f"l'event commence <t:{ts}:R> (<t:{ts}:t>)."
        )
        size_match = re.search(r"(\d+)v\d+", entry["format_type"], re.IGNORECASE)
        teams_of = f"de **{size_match.group(1)}** " if size_match else ""
        text += (
            f"\n\nDiscutez ici pour former vos équipes {teams_of}puis inscrivez-les ici : "
            f"{registration_url}\n"
            f"Un fil sera créé là-bas pour chaque équipe inscrite."
        )
        await lobby.send(text)

    async def sync_lobby(message: discord.Message, user_id: int, is_can: bool) -> None:
        """Répercute un changement de vote 'Can' sur le lobby déjà ouvert."""
        async with polls_lock:
            active_polls = load_active_polls()
            entry = next((e for e in active_polls if e["message_id"] == message.id), None)
            if entry is None:
                return
            lobby = await get_thread(entry.get("lobby_thread_id"))
            if lobby is None:
                return
            try:
                if is_can:
                    await lobby.add_user(discord.Object(id=user_id))
                    await lobby.send(f"<@{user_id}> a rejoint le lobby.")
                else:
                    await lobby.remove_user(discord.Object(id=user_id))
            except discord.HTTPException:
                pass

    async def delete_lobby(entry: dict) -> None:
        for thread_id in entry.get("thread_ids", []):
            try:
                thread = botsq.get_channel(thread_id) or await botsq.fetch_channel(thread_id)
                if isinstance(thread, discord.Thread):
                    await thread.delete()
            except discord.NotFound:
                pass  # Déjà supprimé à la main
            except discord.HTTPException as e:
                print(f"Impossible de supprimer le fil {thread_id} : {e}")

    @tasks.loop(minutes=1)
    async def check_active_polls() -> None:
        async with polls_lock:
            await process_active_polls()

    async def process_active_polls() -> None:
        active_polls = load_active_polls()
        if not active_polls:
            return

        now = time.time()
        remaining: list[dict] = []

        for entry in active_polls:
            ts = entry["timestamp"]
            if now >= ts + threads_lifetime:
                await delete_lobby(entry)
                continue  # Event terminé : plus rien à faire
            if ts <= now:
                remaining.append(entry)  # On garde l'entrée pour supprimer les fils plus tard
                continue

            if not entry["reminded"] and now >= ts - reminder_before:
                message = await fetch_poll_message(entry)
                if message is None:
                    continue  # Sondage supprimé : on arrête de le suivre
                await open_lobby(entry, message)
                entry["reminded"] = True

            remaining.append(entry)

        save_active_polls(remaining)

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
        was_can = user_id in state.get("✅", {})

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
            if emoji == "✅" or was_can:
                await sync_lobby(message, user_id, emoji == "✅")

    @botsq.event
    async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent) -> None:
        message = await get_poll_message(payload)
        if message is None:
            return

        state = await hydrate_votes(message)
        emoji = str(payload.emoji)
        if emoji in state and state[emoji].pop(payload.user_id, None) is not None:
            await render_embed(message, state)
            if emoji == "✅":
                await sync_lobby(message, payload.user_id, False)

    token = os.getenv("DISCORD_TOKEN_BOTSQ")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN_BOTSQ manquant dans le fichier .env "
        )

    botsq.run(token)


if __name__ == "__main__":
    run()
