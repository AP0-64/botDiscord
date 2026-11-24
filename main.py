"""Point d'entrée pour lancer le bot Toadette."""
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
    """Lancer le bot Toadette"""

    project_dir = Path(__file__).parent

    if not (project_dir / "bot").is_dir():
        print(f"Package introuvable: {project_dir / 'bot'}")
        return

    python_exe = get_python_executable()
    try:
        subprocess.run([python_exe, "-m", "bot"], cwd=project_dir, check=True)
    except KeyboardInterrupt:
        print("\nInterruption demandée. Arrêt du bot.")


if __name__ == "__main__":
    main()
