"""Wars : sondages quotidiens de 20h à 23h, rappels et nettoyage du soir.

Comme pour les SQ, rien n'est stocké sur disque : les sondages sont retrouvés
dans les salons et les votes relus depuis les réactions.
"""
import datetime
import re
import time

import discord
from discord.ext import tasks

from .client import client
from .config import (
    PARIS,
    WAR_CAN_EMOJIS,
    WAR_CANT_EMOJI,
    WAR_CHANNELS,
    WAR_COLOR,
    WAR_DROP_WINDOW,
    WAR_DROPPED,
    WAR_HOURS,
    WAR_MAX_MISSING,
    WAR_MISSING_TIME,
    WAR_OPTIONS,
    WAR_POLLS_TIME,
    WAR_PURGE_CHANNEL_IDS,
    WAR_PURGE_TIME,
    WAR_REMINDERS,
    WAR_TEAM_SIZE,
    WAR_TITLE,
)
from .polls import resolve_channel
from .state import channel_lock

WAR_TIME_PATTERN = re.compile(r"<t:(\d+):F>")
DROPPED_EMOJI, DROPPED_LABEL = WAR_DROPPED
VOTE_EMOJIS = [emoji for emoji, _ in WAR_OPTIONS]

# message_id -> catégorie (emoji, dont ✖️ Dropped) -> {user_id: display_name}
Votes = dict[str, dict[int, str]]
war_votes: dict[int, Votes] = {}


# --- Sondages -----------------------------------------------------------------

def war_timestamp(message: discord.Message) -> int | None:
    """Heure d'une war si le message est un de nos sondages, sinon None."""
    if message.author != client.user or not message.embeds:
        return None
    embed = message.embeds[0]
    match = WAR_TIME_PATTERN.search(embed.description or "")
    if embed.title != WAR_TITLE or not match:
        return None
    return int(match.group(1))


def build_description(timestamp: int, votes: Votes | None = None) -> str:
    """Horaire (converti à l'heure de chaque membre) puis votants par catégorie."""
    parts = [f"<t:{timestamp}:F> - <t:{timestamp}:R>"]
    for emoji, label in [*WAR_OPTIONS, WAR_DROPPED]:
        users = list((votes or {}).get(emoji, {}).values())
        if votes is None and emoji != DROPPED_EMOJI:
            parts.append(f"{emoji} **{label} (0)**")
        elif users:
            parts.append(f"{emoji} **{label} ({len(users)})**\n" + ", ".join(users))
    return "\n\n".join(parts)


def empty_votes() -> Votes:
    """Aucun vote, Dropped compris."""
    return {emoji: {} for emoji in [*VOTE_EMOJIS, DROPPED_EMOJI]}


async def create_war_poll(channel: discord.TextChannel, timestamp: int) -> None:
    """Poste le sondage d'une war et ses réactions."""
    embed = discord.Embed(
        title=WAR_TITLE,
        description=build_description(timestamp),
        color=WAR_COLOR,
    )
    message = await channel.send(embed=embed)
    war_votes[message.id] = empty_votes()
    for emoji in VOTE_EMOJIS:
        await message.add_reaction(emoji)


async def find_war_polls(channel: discord.TextChannel) -> dict[int, discord.Message]:
    """Sondages de war présents dans le salon, par heure de la war."""
    polls: dict[int, discord.Message] = {}
    async for message in channel.history(limit=100):
        timestamp = war_timestamp(message)
        if timestamp is not None:
            polls.setdefault(timestamp, message)
    return polls


def today_wars() -> list[int]:
    """Timestamps des wars du jour (heure de Paris)."""
    today = datetime.datetime.now(PARIS).date()
    return [
        int(datetime.datetime.combine(today, datetime.time(hour), PARIS).timestamp())
        for hour in WAR_HOURS
    ]


async def post_war_polls() -> None:
    """Poste les sondages du jour qui manquent (wars pas encore commencées)."""
    now = time.time()
    for channel_id in WAR_CHANNELS:
        channel = await resolve_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            continue
        async with channel_lock(channel_id):
            try:
                existing = await find_war_polls(channel)
                for timestamp in today_wars():
                    if timestamp > now and timestamp not in existing:
                        await create_war_poll(channel, timestamp)
            except discord.HTTPException as e:
                print(f"Impossible de poster les sondages de war ({channel_id}) : {e}")


# --- Votes --------------------------------------------------------------------

def dropped_names(message: discord.Message) -> set[str]:
    """Noms affichés dans la catégorie Dropped de l'embed."""
    description = message.embeds[0].description or ""
    for part in description.split("\n\n"):
        if part.startswith(DROPPED_EMOJI) and "\n" in part:
            return set(part.split("\n", 1)[1].split(", "))
    return set()


async def hydrate_war_votes(message: discord.Message) -> Votes:
    """Votes du sondage, relus depuis les réactions s'ils ne sont pas en mémoire.

    Dropped n'est pas une réaction : ce sont des ❌ déjà affichés en Dropped.
    """
    if message.id in war_votes:
        return war_votes[message.id]

    votes = empty_votes()
    for reaction in message.reactions:
        emoji = str(reaction.emoji)
        if emoji in VOTE_EMOJIS:
            async for user in reaction.users():
                if client.user and user.id != client.user.id:
                    votes[emoji][user.id] = user.display_name

    dropped = dropped_names(message)
    for user_id, name in list(votes[WAR_CANT_EMOJI].items()):
        if name in dropped:
            votes[DROPPED_EMOJI][user_id] = votes[WAR_CANT_EMOJI].pop(user_id)

    war_votes[message.id] = votes
    return votes


async def render_war_poll(message: discord.Message, timestamp: int, votes: Votes) -> None:
    """Met à jour l'embed si les votes affichés ont changé."""
    embed = message.embeds[0]
    description = build_description(timestamp, votes)
    if description != embed.description:
        await message.edit(embed=discord.Embed(
            title=embed.title,
            description=description,
            color=embed.color,
        ))


async def fetch_war_poll(
    payload: discord.RawReactionActionEvent,
) -> tuple[discord.Message, int] | None:
    """Sondage de war visé par une réaction (et heure de la war), sinon None."""
    if client.user and payload.user_id == client.user.id:
        return None
    channel = await resolve_channel(payload.channel_id)
    if not isinstance(channel, discord.TextChannel):
        return None
    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.HTTPException:
        return None
    timestamp = war_timestamp(message)
    if timestamp is None:
        return None
    return message, timestamp


async def on_war_reaction_add(payload: discord.RawReactionActionEvent) -> None:
    """Un seul vote par joueur. Can/Can sub -> Can't à moins de 2h : Dropped."""
    found = await fetch_war_poll(payload)
    if found is None:
        return
    message, timestamp = found
    emoji = str(payload.emoji)
    if emoji not in VOTE_EMOJIS:
        return

    async with channel_lock(payload.channel_id):
        # Relu après un redémarrage : la réaction est déjà dedans, il faut tout répercuter
        changed = message.id not in war_votes
        votes = await hydrate_war_votes(message)
        user_id = payload.user_id
        name = payload.member.display_name if payload.member else str(user_id)
        was_in = any(user_id in votes[e] for e in WAR_CAN_EMOJIS)
        was_dropped = user_id in votes[DROPPED_EMOJI]

        for other in VOTE_EMOJIS:
            # Un Dropped garde sa réaction ❌ : elle part aussi s'il revote
            has_other = user_id in votes[other] or (other == WAR_CANT_EMOJI and was_dropped)
            if other != emoji and has_other:
                votes[other].pop(user_id, None)
                changed = True
                try:
                    await message.remove_reaction(other, discord.Object(id=user_id))
                except discord.HTTPException:
                    pass

        late = time.time() >= timestamp - WAR_DROP_WINDOW
        if emoji == WAR_CANT_EMOJI and (was_dropped or (was_in and late)):
            votes[WAR_CANT_EMOJI].pop(user_id, None)
            votes[DROPPED_EMOJI][user_id] = name
            changed = True
        else:
            if votes[DROPPED_EMOJI].pop(user_id, None) is not None:
                changed = True
            if user_id not in votes[emoji]:
                votes[emoji][user_id] = name
                changed = True

        if changed:
            await render_war_poll(message, timestamp, votes)


async def on_war_reaction_remove(payload: discord.RawReactionActionEvent) -> None:
    """Retire le vote du joueur (un ❌ retiré sort aussi de Dropped)."""
    found = await fetch_war_poll(payload)
    if found is None:
        return
    message, timestamp = found
    emoji = str(payload.emoji)
    if emoji not in VOTE_EMOJIS:
        return

    async with channel_lock(payload.channel_id):
        changed = message.id not in war_votes
        votes = await hydrate_war_votes(message)
        if votes[emoji].pop(payload.user_id, None) is not None:
            changed = True
        if emoji == WAR_CANT_EMOJI and votes[DROPPED_EMOJI].pop(payload.user_id, None):
            changed = True
        if changed:
            await render_war_poll(message, timestamp, votes)


# --- Messages programmés ------------------------------------------------------

def role_mentions(channel_id: int) -> str:
    """Mentions des rôles du salon."""
    return " ".join(f"<@&{role_id}>" for role_id in WAR_CHANNELS[channel_id])


async def send_to_war_channel(channel_id: int, content: str) -> None:
    """Envoie un message en autorisant les mentions de rôles."""
    channel = await resolve_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return
    try:
        await channel.send(content, allowed_mentions=discord.AllowedMentions(roles=True))
    except discord.HTTPException as e:
        print(f"Impossible d'envoyer le rappel de war ({channel_id}) : {e}")


async def missing_lines(channel_id: int) -> list[str]:
    """Lignes « 21:00 : +x » des wars du jour à qui il manque 1 à 3 joueurs."""
    channel = await resolve_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return []
    lines = []
    async with channel_lock(channel_id):
        polls = await find_war_polls(channel)
        for timestamp in today_wars():
            message = polls.get(timestamp)
            if message is None:
                continue
            votes = await hydrate_war_votes(message)
            available = sum(len(votes[e]) for e in WAR_CAN_EMOJIS)
            missing = WAR_TEAM_SIZE - available
            if 0 < missing <= WAR_MAX_MISSING:
                lines.append(f"<t:{timestamp}:t> : +{missing}")
    return lines


@tasks.loop(time=WAR_POLLS_TIME)
async def war_polls_loop() -> None:
    """Minuit : sondages des wars de 20h, 21h, 22h et 23h."""
    await post_war_polls()


@tasks.loop(time=list(WAR_REMINDERS))
async def war_reminders_loop() -> None:
    """00h05, 9h, 13h : mention des rôles (+ texte du rappel)."""
    now = datetime.datetime.now(PARIS)
    # Rappel le plus proche de l'heure actuelle
    reminder = min(
        WAR_REMINDERS,
        key=lambda t: abs((t.hour * 60 + t.minute) - (now.hour * 60 + now.minute)),
    )
    text = WAR_REMINDERS[reminder]
    for channel_id in WAR_CHANNELS:
        await send_to_war_channel(channel_id, f"{role_mentions(channel_id)} {text}".strip())


@tasks.loop(time=WAR_MISSING_TIME)
async def war_missing_loop() -> None:
    """17h : combien il manque de joueurs par war (rien si personne n'est à 1-3 près)."""
    for channel_id in WAR_CHANNELS:
        try:
            lines = await missing_lines(channel_id)
        except discord.HTTPException as e:
            print(f"Impossible de compter les dispos de war ({channel_id}) : {e}")
            continue
        if lines:
            await send_to_war_channel(
                channel_id, role_mentions(channel_id) + "\n" + "\n".join(lines)
            )


@tasks.loop(time=WAR_PURGE_TIME)
async def war_purge_loop() -> None:
    """23h30 : vide les salons, sauf les messages épinglés."""
    for channel_id in WAR_PURGE_CHANNEL_IDS:
        channel = await resolve_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            continue
        async with channel_lock(channel_id):
            try:
                deleted = await channel.purge(limit=None, check=lambda m: not m.pinned)
            except discord.HTTPException as e:
                print(f"Impossible de vider le salon {channel_id} : {e}")
                continue
        for message in deleted:
            war_votes.pop(message.id, None)


def start_war_loops() -> None:
    """Démarre les boucles des wars (une seule fois)."""
    for loop in (war_polls_loop, war_reminders_loop, war_missing_loop, war_purge_loop):
        if not loop.is_running():
            loop.start()
