"""Événements Discord : démarrage, planning posté, votes."""
import discord

from .client import botsq
from .config import (
    BOT_CHANNEL_IDS,
    CAN_EMOJI,
)
from .lobby import sync_lobby
from .polls import (
    get_poll_message,
    hydrate_votes,
    render_embed,
    resolve_channel,
    vote_state,
)
from .scheduler import check_channels, ping_lounge, process_channel
from .state import channel_lock, planning_events, read_channel


async def clear_previous_messages(message: discord.Message) -> None:
    """Supprime tout ce qui précède le message dans le salon, sauf les messages épinglés."""
    channel = message.channel
    if not isinstance(channel, discord.TextChannel):
        return

    try:
        await channel.purge(before=message, limit=None, check=lambda m: not m.pinned)
    except (discord.Forbidden, discord.HTTPException) as e:
        print(f"Impossible de vider le salon : {e}")


async def catch_up_plannings() -> None:
    """Au démarrage : vide le salon si un planning a été posté pendant que le bot était éteint."""
    for channel_id in BOT_CHANNEL_IDS:
        channel = await resolve_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            continue
        async with channel_lock(channel_id):
            try:
                planning, _ = await read_channel(channel)
            except discord.HTTPException as e:
                print(f"Impossible de relire le salon {channel_id} : {e}")
                continue
            if planning is not None:
                await clear_previous_messages(planning)


@botsq.event
async def on_ready() -> None:
    """Démarre les boucles de fond une fois le bot connecté."""
    print("bot SQ prêt")
    await catch_up_plannings()
    if not check_channels.is_running():
        check_channels.start()
    if not ping_lounge.is_running():
        ping_lounge.start()


@botsq.event
async def on_message(message: discord.Message) -> None:
    """Un nouveau planning vide le salon et remplace le précédent."""
    if message.author == botsq.user:
        return
    if message.channel.id not in BOT_CHANNEL_IDS:
        return
    if not isinstance(message.channel, discord.TextChannel):
        return

    # Seul un message de planning déclenche quelque chose (un simple "ok" est ignoré)
    if not planning_events(message):
        return

    async with channel_lock(message.channel.id):
        await clear_previous_messages(message)
        # Le planning est relu dans le salon : les events dans moins de 24h ont leur sondage
        try:
            await process_channel(message.channel)
        except discord.HTTPException as e:
            print(f"Erreur HTTP sur le salon {message.channel.id} : {e}")


@botsq.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent) -> None:
    """Un seul vote par joueur : le nouveau remplace l'ancien."""
    message = await get_poll_message(payload)
    if message is None:
        return

    # Sondage pas encore en cache (redémarrage) : les votes sont relus depuis les
    # réactions, qui contiennent déjà celle-ci. Il faut quand même tout répercuter.
    fresh = message.id not in vote_state
    state = await hydrate_votes(message)
    emoji = str(payload.emoji)
    if emoji not in state:
        return

    user_id = payload.user_id
    member = payload.member
    display_name = member.display_name if member else str(payload.user_id)
    changed = fresh
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

    # Même cas qu'à l'ajout : relu après un redémarrage, le vote est déjà absent
    fresh = message.id not in vote_state
    state = await hydrate_votes(message)
    emoji = str(payload.emoji)
    if emoji not in state:
        return
    removed = state[emoji].pop(payload.user_id, None) is not None
    if removed or fresh:
        await render_embed(message, state)
        if emoji == CAN_EMOJI:
            await sync_lobby(message, payload.user_id, False)
