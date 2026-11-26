"""Réglages du bot Toadette."""
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

# --- Wars ---------------------------------------------------------------------
PARIS = ZoneInfo("Europe/Paris")

# Salons des sondages de war -> rôles mentionnés dans les rappels
WAR_CHANNELS = {
    # https://discord.com/channels/1374645694618665060/1378729909224210538
    1378729909224210538: (1374702249531543553, 1374688737111310367),
    # https://discord.com/channels/1342045498554712118/1342050908195782707
    1342050908195782707: (1342050846736646206, 1342050845750988852),
}

# Salons vidés tous les soirs (sauf messages épinglés)
WAR_PURGE_CHANNEL_IDS = {
    1378729909224210538,  # https://discord.com/channels/1374645694618665060/1378729909224210538
    1395709948318711829,  # https://discord.com/channels/1374645694618665060/1395709948318711829
    1439239489334677504,  # https://discord.com/channels/1374645694618665060/1439239489334677504
    1342050908195782707,  # https://discord.com/channels/1342045498554712118/1342050908195782707
    1342050909877829713,  # https://discord.com/channels/1342045498554712118/1342050909877829713
    1342050927485521962,  # https://discord.com/channels/1342045498554712118/1342050927485521962
}

WAR_HOURS = [20, 21, 22, 23]  # Heures des wars (heure de Paris)
WAR_TITLE = "War"
WAR_COLOR = 0xE74C3C
WAR_OPTIONS = [
    ("✅", "Can"),
    ("❕", "Can sub"),
    ("❔", "Not sure"),
    ("❌", "Can't"),
]
WAR_CAN_EMOJIS = ("✅", "❕")  # Comptent comme dispo (pour les Dropped)
WAR_PLAYER_EMOJI = "✅"  # Seuls les Can comptent dans les joueurs du rappel de 17h
WAR_CANT_EMOJI = "❌"
WAR_DROPPED = ("✖️", "Dropped")  # Pas une réaction : attribué par le bot
WAR_DROP_WINDOW = 2 * 3600  # Can/Can sub -> Can't à moins de 2h = Dropped
WAR_TEAM_SIZE = 6
WAR_MAX_MISSING = 3  # Au-delà, l'heure n'apparaît pas dans le rappel de 17h

WAR_PURGE_TIME = datetime.time(hour=23, minute=30, tzinfo=PARIS)
WAR_POLLS_TIME = datetime.time(hour=0, tzinfo=PARIS)
# Rappels : heure -> texte après les mentions
WAR_REMINDERS = {
    datetime.time(hour=0, minute=5, tzinfo=PARIS): "",
    datetime.time(hour=9, tzinfo=PARIS): "oubliez pas de voter",
    datetime.time(hour=13, tzinfo=PARIS): "oubliez pas de mettre vos dispos",
}
# Salons où les rappels sont aussi écrits en anglais
WAR_ENGLISH_CHANNEL_IDS = {
    1378729909224210538,  # https://discord.com/channels/1374645694618665060/1378729909224210538
}
WAR_REMINDERS_EN = {
    "oubliez pas de voter": "don't forget to vote",
    "oubliez pas de mettre vos dispos": "don't forget to set your availability",
}
WAR_MISSING_TIME = datetime.time(hour=17, tzinfo=PARIS)
