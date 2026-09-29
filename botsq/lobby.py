"""Lobby : fil privé ouvert à H-1 pour les joueurs 'Can'."""
import re
from datetime import datetime

import discord

from .client import botsq
from .config import REGISTRATION_URL
from .polls import get_can_ids
from .storage import load_active_polls, polls_lock


def thread_name(entry: dict, suffix: str) -> str:
    dt = datetime.fromtimestamp(entry["timestamp"])
    date_str = f"{dt.month}/{dt.day}, {dt:%H:%M:%S}"
    return f"{date_str} - {entry['format_type']} - #{entry['event_id']} - {suffix}"[:100]


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
        f"{REGISTRATION_URL}\n"
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
