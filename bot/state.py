"""État du bot relu directement sur Discord : planning, sondages publiés et lobbies.

Rien n'est stocké sur disque : après un redémarrage, le bot retrouve tout en
relisant ses salons.
"""
import asyncio
import re
from dataclasses import dataclass

import discord

from .client import botsq
from .config import HISTORY_LIMIT, PLANNING_AUTHORS, POLL_LINE_PATTERN, REMINDER_BEFORE

POLL_TITLE_PATTERN = re.compile(r"^(.*) \(ID: #(\d+)\)$")
POLL_TIME_PATTERN = re.compile(r"<t:(\d+):F>")
LOBBY_NAME_PATTERN = re.compile(r" - #(\d+) - Lobby$")
LOBBY_TIME_PATTERN = re.compile(r"<t:(\d+):R>")

# Un verrou par salon : le planning, la boucle et les votes ne se marchent pas dessus
_locks: dict[int, asyncio.Lock] = {}
# Heure de l'event de chaque lobby, lue une seule fois dans son message d'accueil
_lobby_timestamps: dict[int, int] = {}


@dataclass
class Event:
    """Un event du planning."""
    event_id: str
    format_type: str
    timestamp: int


def channel_lock(channel_id: int) -> asyncio.Lock:
    """Verrou propre au salon."""
    return _locks.setdefault(channel_id, asyncio.Lock())


def planning_events(message: discord.Message) -> list[Event]:
    """Events d'un message de planning (liste vide si ce n'en est pas un)."""
    if message.author.name not in PLANNING_AUTHORS:
        return []
    return [
        Event(event_id, format_type, int(timestamp))
        for event_id, format_type, timestamp in POLL_LINE_PATTERN.findall(message.content)
    ]


def poll_event(message: discord.Message) -> Event | None:
    """Event d'un sondage publié par le bot (None si ce n'est pas un sondage)."""
    if message.author != botsq.user or not message.embeds:
        return None
    embed = message.embeds[0]
    title = POLL_TITLE_PATTERN.match(embed.title or "")
    when = POLL_TIME_PATTERN.search(embed.description or "")
    if not title or not when:
        return None
    return Event(title.group(2), title.group(1), int(when.group(1)))


async def read_channel(
    channel: discord.TextChannel,
) -> tuple[discord.Message | None, dict[str, tuple[discord.Message, Event]]]:
    """Retourne le dernier planning du salon et les sondages publiés depuis (par event_id).

    Ce qui précède le planning est obsolète : le salon est vidé à chaque planning.
    """
    polls: dict[str, tuple[discord.Message, Event]] = {}
    async for message in channel.history(limit=HISTORY_LIMIT):
        if planning_events(message):
            return message, polls
        event = poll_event(message)
        if event:
            polls.setdefault(event.event_id, (message, event))
    return None, polls


async def find_lobbies(
    channel: discord.TextChannel,
    include_archived: bool = False,
) -> dict[str, discord.Thread]:
    """Retourne les lobbies du salon, par event_id."""
    threads = list(channel.threads)
    if include_archived:
        try:
            async for thread in channel.archived_threads(private=True, limit=50):
                threads.append(thread)
        except discord.HTTPException as e:
            print(f"Impossible de lister les fils archivés : {e}")

    lobbies: dict[str, discord.Thread] = {}
    for thread in threads:
        match = LOBBY_NAME_PATTERN.search(thread.name)
        if match:
            lobbies.setdefault(match.group(1), thread)
    return lobbies


async def lobby_timestamp(thread: discord.Thread) -> int | None:
    """Heure de l'event d'un lobby, lue dans le message d'accueil du bot."""
    if thread.id in _lobby_timestamps:
        return _lobby_timestamps[thread.id]

    timestamp = None
    try:
        async for message in thread.history(limit=100, oldest_first=True):
            match = LOBBY_TIME_PATTERN.search(message.content)
            if message.author == botsq.user and match:
                timestamp = int(match.group(1))
                break
    except discord.HTTPException:
        pass
    # Message d'accueil introuvable : le lobby est normalement ouvert à H-1
    if timestamp is None and thread.created_at:
        timestamp = int(thread.created_at.timestamp()) + REMINDER_BEFORE
    if timestamp is not None:
        _lobby_timestamps[thread.id] = timestamp
    return timestamp
