"""Réglages du bot SQ."""
import datetime
import re
from pathlib import Path
from zoneinfo import ZoneInfo

# Dossier racine du projet (où sont stockés les fichiers JSON)
ROOT_DIR = Path(__file__).resolve().parent.parent

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

SCHEDULE_FILE = ROOT_DIR / "scheduled_polls.json"
SECONDS_BEFORE = 24 * 3600  # Publication du sondage

# Sondages publiés, suivis pour l'ouverture du lobby (H-1) et sa suppression (H+4h)
ACTIVE_POLLS_FILE = ROOT_DIR / "active_polls.json"
REMINDER_BEFORE = 3600  # Ouverture du lobby
THREADS_LIFETIME = 4 * 3600  # Lobby supprimé 4h après le début de l'event

# Salon où les équipes s'inscrivent (autre serveur)
REGISTRATION_URL = "https://discord.com/channels/445404006177570829/772517883107475516"

# Ping quotidien du rôle Lounge
LOUNGE_PING_CHANNEL_ID = 1342050873177542719
LOUNGE_ROLE_NAME = "Lounge"
LOUNGE_PING_TIMES = [
    datetime.time(hour=9, tzinfo=ZoneInfo("Europe/Paris")),
    datetime.time(hour=16, tzinfo=ZoneInfo("Europe/Paris")),
]
