"""Réglages du bot SQ."""
import datetime
import re
from zoneinfo import ZoneInfo

# Seuls ces comptes peuvent poster un planning (nom d'utilisateur, pas le pseudo).
# "MK8DX 150cc Lounge #sq-schedule" est le webhook du salon d'annonces suivi.
PLANNING_AUTHORS = {
    "ap0_64",
    "MK8DX 150cc Lounge #sq-schedule",
}

# \3 garantit que les deux timestamps (F et R) sont bien identiques
POLL_LINE_PATTERN = re.compile(r"`#(\d+)` \*\*(.*?):\*\* <t:(\d+):F> - <t:\3:R>")

POLL_OPTIONS = [
    ("✅", "Can"),
    ("❓", "Not sure"),
    ("❌", "Can't"),
]
CAN_EMOJI = "✅"

# Nombre max de messages relus pour retrouver le planning et les sondages du salon
HISTORY_LIMIT = 200

SECONDS_BEFORE = 24 * 3600  # Publication du sondage
REMINDER_BEFORE = 3600  # Ouverture du lobby
THREADS_LIFETIME = 4 * 3600  # Lobby supprimé 4h après le début de l'event

# Salon où les squads s'inscrivent (autre serveur)
REGISTRATION_URL = "https://discord.com/channels/445404006177570829/772517883107475516"

# Salons où le bot travaille (un par serveur) : sondages, lobbies et ping Lounge
BOT_CHANNEL_IDS = {
    1553721228194226266,  # https://discord.com/channels/1342045498554712118/1553721228194226266
    1553710725241765889,  # https://discord.com/channels/1374645694618665060/1553710725241765889
}

# Ping quotidien du rôle Lounge
LOUNGE_ROLE_NAME = "Lounge"
LOUNGE_PING_TIMES = [
    datetime.time(hour=9, tzinfo=ZoneInfo("Europe/Paris")),
    datetime.time(hour=16, tzinfo=ZoneInfo("Europe/Paris")),
]
