"""Boucles de fond : sondages, cycle de vie des lobbies et ping Lounge."""
import time

import discord
from discord.ext import tasks

from .client import botsq
from .config import (
    BOT_CHANNEL_IDS,
    LOUNGE_PING_TIMES,
    LOUNGE_ROLE_NAME,
    REMINDER_BEFORE,
    SECONDS_BEFORE,
    THREADS_LIFETIME,
)
from .lobby import delete_lobby, open_lobby
from .polls import create_poll, resolve_channel
from .state import (
    channel_lock,
    find_lobbies,
    lobby_timestamp,
    planning_events,
    read_channel,
)


@tasks.loop(minutes=1)
async def check_channels() -> None:
    """H-24h : sondage. H-1h : lobby. H+4h : suppression du lobby."""
    for channel_id in BOT_CHANNEL_IDS:
        channel = await resolve_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            continue
        async with channel_lock(channel_id):
            try:
                await process_channel(channel)
            except discord.HTTPException as e:
                print(f"Erreur HTTP sur le salon {channel_id} : {e}")


async def process_channel(channel: discord.TextChannel) -> None:
    """Relit le salon et fait ce qui est dû. À appeler avec channel_lock(channel.id)."""
    now = time.time()
    planning, polls = await read_channel(channel)

    # H-24h : sondage de chaque event du planning qui n'en a pas encore
    if planning is not None:
        for event in planning_events(planning):
            if event.event_id in polls:
                continue
            if event.timestamp - SECONDS_BEFORE <= now < event.timestamp:
                message = await create_poll(channel, event)
                polls[event.event_id] = (message, event)

    # H-1h : lobby (réessayé chaque minute tant que personne n'a voté 'Can')
    lobbies = await find_lobbies(channel, include_archived=True)
    for event_id, (message, event) in polls.items():
        if event_id in lobbies:
            continue
        if event.timestamp - REMINDER_BEFORE <= now < event.timestamp:
            await open_lobby(event, message)

    # H+4h : suppression du lobby
    for lobby in lobbies.values():
        timestamp = await lobby_timestamp(lobby)
        if timestamp is not None and now >= timestamp + THREADS_LIFETIME:
            await delete_lobby(lobby)


@tasks.loop(time=LOUNGE_PING_TIMES)
async def ping_lounge() -> None:
    """Tous les jours à 9h et 16h : ping du rôle Lounge dans chaque salon du bot."""
    for channel_id in BOT_CHANNEL_IDS:
        await send_lounge_ping(channel_id)


async def send_lounge_ping(channel_id: int) -> None:
    """Mentionne le rôle Lounge (ou écrit "@Lounge" si le rôle n'existe pas)."""
    channel = botsq.get_channel(channel_id)
    if channel is None:
        try:
            channel = await botsq.fetch_channel(channel_id)
        except discord.HTTPException as e:
            print(f"Salon du ping Lounge introuvable (channel_id={channel_id}) : {e}")
            return
    if not isinstance(channel, discord.TextChannel):
        return

    # Vraie mention si le rôle existe, sinon simple texte
    role = discord.utils.get(channel.guild.roles, name=LOUNGE_ROLE_NAME)
    content = role.mention if role else f"@{LOUNGE_ROLE_NAME}"
    try:
        await channel.send(
            content,
            allowed_mentions=discord.AllowedMentions(roles=True),
        )
    except discord.HTTPException as e:
        print(f"Impossible d'envoyer le ping Lounge (channel_id={channel_id}) : {e}")
