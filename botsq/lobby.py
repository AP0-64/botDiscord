"""Lobby : fil privé ouvert à H-1 pour les joueurs 'Can'."""
import re
from datetime import datetime

import discord

from .config import REGISTRATION_URL, THREADS_LIFETIME
from .polls import get_can_ids
from .state import Event, channel_lock, find_lobbies, poll_event


def thread_name(event: Event, suffix: str) -> str:
    """Nom du fil : date - format - #id - suffixe (100 caractères max)."""
    dt = datetime.fromtimestamp(event.timestamp)
    date_str = f"{dt.month}/{dt.day}, {dt:%H:%M:%S}"
    return f"{date_str} - {event.format_type} - #{event.event_id} - {suffix}"[:100]


async def open_lobby(event: Event, message: discord.Message) -> bool:
    """H-1 : crée un fil privé avec tous les 'Can'. Retourne True si le lobby est créé."""
    channel = message.channel
    if not isinstance(channel, discord.TextChannel):
        return False
    can_ids = await get_can_ids(message)
    if not can_ids:
        return False

    try:
        lobby = await channel.create_thread(
            name=thread_name(event, "Lobby"),
            type=discord.ChannelType.private_thread,
            invitable=False,
            auto_archive_duration=1440,
            reason=f"Lobby de l'event #{event.event_id}",
        )
    except (discord.Forbidden, discord.HTTPException) as e:
        print(f"Impossible de créer le lobby : {e}")
        return False

    for uid in can_ids:
        try:
            await lobby.add_user(discord.Object(id=uid))
        except discord.HTTPException:
            pass

    ts = event.timestamp
    mentions = " ".join(f"<@{uid}>" for uid in can_ids)
    text = (
        f"{mentions}\n"
        f"Vous avez voté **Can** pour **{event.format_type} (ID: #{event.event_id})** : "
        f"l'event commence <t:{ts}:R> (<t:{ts}:t>)."
    )
    size_match = re.search(r"(\d+)v\d+", event.format_type, re.IGNORECASE)
    teams_of = f"de **{size_match.group(1)}** " if size_match else ""
    text += (
        f"\n\nDiscutez ici pour former vos équipes {teams_of}puis inscrivez-les ici : "
        f"{REGISTRATION_URL}\n"
        f"Un fil sera créé là-bas pour chaque équipe inscrite.\n"
        f"Ce fil sera automatiquement supprimé à <t:{ts + THREADS_LIFETIME}:t> "
        f"({THREADS_LIFETIME // 3600}h après le début de l'event)."
    )
    await lobby.send(text)
    return True


async def sync_lobby(message: discord.Message, user_id: int, is_can: bool) -> None:
    """Répercute un changement de vote 'Can' sur le lobby déjà ouvert."""
    event = poll_event(message)
    channel = message.channel
    if event is None or not isinstance(channel, discord.TextChannel):
        return
    async with channel_lock(channel.id):
        lobby = (await find_lobbies(channel)).get(event.event_id)
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


async def delete_lobby(lobby: discord.Thread) -> None:
    """Supprime le lobby d'un event terminé."""
    try:
        await lobby.delete()
    except discord.NotFound:
        pass  # Déjà supprimé à la main
    except discord.HTTPException as e:
        print(f"Impossible de supprimer le fil {lobby.id} : {e}")
