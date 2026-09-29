"""Point d'entrée pour lancer le bot SQ."""
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
    """Lancer le bot SQ"""

    script_path = Path(__file__).with_name("botsq.py")

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
