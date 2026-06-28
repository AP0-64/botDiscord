"""Point d'entrée pour lancer un bot spécifique."""
from pathlib import Path
import subprocess
import sys


def get_python_executable() -> str:
    """
    Retourne le chemin du Python de l'environnement virtuel s'il existe
    sinon le Python système.
    """
    venv_python = Path(__file__).parent / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def main() -> None:
    """Lancer le bot spécifié en argument de la ligne de commande"""

    if len(sys.argv) != 2 or sys.argv[1] not in {"atlas", "scora", "botsq"}:
        print("Usage: python main.py atlas|scora|botsq")
        return

    bot_name = sys.argv[1]
    script_path = Path(__file__).with_name(f"{bot_name}.py")

    if not script_path.exists():
        print(f"Fichier introuvable: {script_path}")
        return

    python_exe = get_python_executable()
    try:
        subprocess.run([python_exe, str(script_path)], check=True)
    except KeyboardInterrupt:
        print("\nInterruption demandée. Arrêt du bot.")


if __name__ == "__main__":
    main()
