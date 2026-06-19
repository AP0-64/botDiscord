"""Point d'entrée pour lancer un bot spécifique."""
from pathlib import Path
import subprocess
import sys


def main() -> None:
    """Lancer le bot spécifié en argument de la ligne de commande"""

    if len(sys.argv) != 2 or sys.argv[1] not in {"atlas", "scora"}:
        print("Usage: python main.py atlas|scora")
        return

    bot_name = sys.argv[1]
    script_path = Path(__file__).with_name(f"{bot_name}.py")

    if not script_path.exists():
        print(f"Fichier introuvable: {script_path}")
        return

    if bot_name == "atlas":
        subprocess.run([sys.executable, str(script_path)], check=True)
        return

    if bot_name == "scora":
        subprocess.run([sys.executable, str(script_path)], check=True)
        return

    subprocess.run([sys.executable, str(script_path)], check=True)


if __name__ == "__main__":
    main()
