"""Boucles de fond : sondages, cycle de vie des lobbies et ping Lounge."""
import time

import discord
from discord.ext import tasks

from .client import botsq
from .config import (
    LOUNGE_PING_CHANNEL_ID,
    LOUNGE_PING_TIMES,
    LOUNGE_ROLE_NAME,
    REMINDER_BEFORE,
    THREADS_LIFETIME,
)
from .lobby import delete_lobby, open_lobby
from .polls import create_poll, fetch_poll_message
from .storage import (
    load_active_polls,
    load_schedule,
    polls_lock,
    save_active_polls,
    save_schedule,
)


@tasks.loop(minutes=1)
async def check_scheduled_polls() -> None:
    """H-24h : publie les sondages dont l'heure est venue."""
    schedule = load_schedule()
    if not schedule:
        return

    now = time.time()
    due = [
        entry for entry in schedule
        if entry["post_at"] <= now < int(entry["timestamp"])
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


@tasks.loop(minutes=1)
async def check_active_polls() -> None:
    """H-1h : ouvre le lobby. H+4h : le supprime."""
    async with polls_lock:
        await process_active_polls()


async def process_active_polls() -> None:
    """Ouvre les lobbies à H-1h et supprime les fils après l'event."""
    active_polls = load_active_polls()
    if not active_polls:
        return

    now = time.time()
    remaining: list[dict] = []

    for entry in active_polls:
        ts = entry["timestamp"]
        if now >= ts + THREADS_LIFETIME:
            await delete_lobby(entry)
            continue  # Event terminé : plus rien à faire
        if ts <= now:
            remaining.append(entry)  # On garde l'entrée pour supprimer les fils plus tard
            continue

        if not entry["reminded"] and now >= ts - REMINDER_BEFORE:
            message = await fetch_poll_message(entry)
            if message is None:
                continue  # Sondage supprimé : on arrête de le suivre
            await open_lobby(entry, message)
            entry["reminded"] = True

        remaining.append(entry)

    save_active_polls(remaining)


@tasks.loop(time=LOUNGE_PING_TIMES)
async def ping_lounge() -> None:
    """Tous les jours à 9h et 16h : ping du rôle Lounge dans le salon."""
    channel = botsq.get_channel(LOUNGE_PING_CHANNEL_ID)
    if channel is None:
        try:
            channel = await botsq.fetch_channel(LOUNGE_PING_CHANNEL_ID)
        except discord.HTTPException as e:
            print(f"Salon du ping Lounge introuvable : {e}")
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
        print(f"Impossible d'envoyer le ping Lounge : {e}")
