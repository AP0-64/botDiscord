"""Sondages : construction de l'embed, suivi des votes et création."""
import discord

from .client import botsq
from .config import CAN_EMOJI, POLL_OPTIONS
from .storage import load_active_polls, save_active_polls

# État des votes en mémoire : message_id -> emoji -> {user_id: display_name}
vote_state: dict[int, dict[str, dict[int, str]]] = {}


def build_description(
    time_str: str,
    state: dict[str, dict[int, str]] | None = None,
) -> str:
    """Construit la description de l'embed : horaire puis votants par option."""
    parts = [time_str]
    for emoji, label in POLL_OPTIONS:
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
    """Met à jour l'embed du sondage si les votes ont changé."""
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
    """Retourne l'état des votes, reconstruit depuis les réactions si absent du cache."""
    if message.id in vote_state:
        return vote_state[message.id]

    state: dict[str, dict[int, str]] = {emoji: {} for emoji, _ in POLL_OPTIONS}
    for reaction in message.reactions:
        emoji = str(reaction.emoji)
        if emoji in state:
            async for user in reaction.users():
                if botsq.user and user.id != botsq.user.id:
                    state[emoji][user.id] = user.display_name

    vote_state[message.id] = state
    return state


async def get_can_ids(message: discord.Message) -> list[int]:
    """Retourne les ids des joueurs ayant voté 'Can'."""
    state = await hydrate_votes(message)
    return list(state.get(CAN_EMOJI, {}).keys())


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
    vote_state[poll_msg.id] = {emoji: {} for emoji, _ in POLL_OPTIONS}

    for emoji, _ in POLL_OPTIONS:
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


async def get_poll_message(
    payload: discord.RawReactionActionEvent,
) -> discord.Message | None:
    """Retourne le sondage visé par une réaction, ou None si ce n'en est pas un."""
    if botsq.user and payload.user_id == botsq.user.id:
        return None

    channel = await resolve_channel(payload.channel_id)
    if not isinstance(channel, discord.abc.Messageable):
        return None

    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.NotFound:
        return None

    title = message.embeds[0].title if message.embeds else None
    if message.author != botsq.user or not title or "(ID: #" not in title:
        return None

    return message


async def resolve_channel(channel_id: int):
    """Retourne le salon depuis le cache, sinon via l'API (None en cas d'échec)."""
    channel = botsq.get_channel(channel_id)
    if channel is not None:
        return channel
    try:
        return await botsq.fetch_channel(channel_id)
    except discord.NotFound:
        print(f"Salon introuvable (channel_id={channel_id}), entrée ignorée.")
    except discord.HTTPException as e:
        print(f"Erreur HTTP en récupérant le salon : {e}")
    return None


async def fetch_poll_message(entry: dict) -> discord.Message | None:
    """Retrouve le message d'un sondage suivi dans active_polls.json."""
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
