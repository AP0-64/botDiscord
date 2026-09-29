"""Lecture / écriture des fichiers JSON de suivi."""
import asyncio
import json

from .config import ACTIVE_POLLS_FILE, SCHEDULE_FILE

# Protège active_polls.json entre la boucle et les réactions
polls_lock = asyncio.Lock()


def save_schedule(entries: list[dict]) -> None:
    """Enregistre les sondages à publier plus tard."""
    SCHEDULE_FILE.write_text(json.dumps(entries, indent=2))


def load_schedule() -> list[dict]:
    """Charge les sondages à publier (liste vide si fichier absent ou invalide)."""
    if not SCHEDULE_FILE.exists():
        return []
    try:
        return json.loads(SCHEDULE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def save_active_polls(entries: list[dict]) -> None:
    """Enregistre les sondages publiés en cours de suivi."""
    ACTIVE_POLLS_FILE.write_text(json.dumps(entries, indent=2))


def load_active_polls() -> list[dict]:
    """Charge les sondages suivis (liste vide si fichier absent ou invalide)."""
    if not ACTIVE_POLLS_FILE.exists():
        return []
    try:
        entries = json.loads(ACTIVE_POLLS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    for entry in entries:
        entry.setdefault("lobby_thread_id", None)
    return entries
