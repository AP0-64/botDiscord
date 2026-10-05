"""Événements Discord : démarrage, planning posté, votes."""
import time

import discord

from .client import botsq
from .config import CAN_EMOJI, PLANNING_AUTHORS, POLL_LINE_PATTERN, SECONDS_BEFORE
from .lobby import sync_lobby
from .polls import create_poll, get_poll_message, hydrate_votes, render_embed
from .scheduler import check_active_polls, check_scheduled_polls, ping_lounge
from .storage import save_schedule


async def clear_previous_messages(message: discord.Message) -> None:
    """Supprime tout ce qui précède le planning dans le salon (désactivé).

    Pour l'activer, décommenter le bloc ci-dessous.
    Nécessite les permissions "Gérer les messages" et "Voir les anciens messages".
    """
    channel = message.channel
    if not isinstance(channel, discord.TextChannel):
        return

    # try:
    #     await channel.purge(before=message, limit=None)
    # except (discord.Forbidden, discord.HTTPException) as e:
    #     print(f"Impossible de vider le salon : {e}")


@botsq.event
async def on_ready() -> None:
    """Démarre les boucles de fond une fois le bot connecté."""
    print("bot SQ prêt")
    if not check_scheduled_polls.is_running():
        check_scheduled_polls.start()
    if not check_active_polls.is_running():
        check_active_polls.start()
    if not ping_lounge.is_running():
        ping_lounge.start()


@botsq.event
async def on_message(message: discord.Message) -> None:
    """Un nouveau planning remplace le précédent."""
    if message.author == botsq.user:
        return
    if message.author.name not in PLANNING_AUTHORS:
        return

    matches = POLL_LINE_PATTERN.findall(message.content)
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

        post_at = event_timestamp - SECONDS_BEFORE

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


@botsq.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent) -> None:
    """Un seul vote par joueur : le nouveau remplace l'ancien."""
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
    was_can = user_id in state.get(CAN_EMOJI, {})

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
        if emoji == CAN_EMOJI or was_can:
            await sync_lobby(message, user_id, emoji == CAN_EMOJI)


@botsq.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent) -> None:
    """Retire le vote du joueur et met à jour le sondage et le lobby."""
    message = await get_poll_message(payload)
    if message is None:
        return

    state = await hydrate_votes(message)
    emoji = str(payload.emoji)
    if emoji in state and state[emoji].pop(payload.user_id, None) is not None:
        await render_embed(message, state)
        if emoji == CAN_EMOJI:
            await sync_lobby(message, payload.user_id, False)
