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
