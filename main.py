"""importation des modules nécessaires pour le bot Discord"""
import os
import discord
from dotenv import load_dotenv


load_dotenv()

print("Lancement du bot Atlas")

# Initialisation du bot Atlas avec tous les intents activés
atlas = discord.Client(intents=discord.Intents.all())

# Événement déclenché lorsque le bot est prêt
@atlas.event
async def on_ready():
    """Affiche un message dans la console lorsque le bot Atlas est prêt"""
    print("bot Atlas prêt")

# Récupération du token depuis les variables d'environnement et lancement du bot Atlas
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("DISCORD_TOKEN manquant dans le fichier .env")
atlas.run(token)
