"""importation des modules nécessaires pour le bot Discord"""
import os
import discord
from dotenv import load_dotenv


load_dotenv()

print("Lancement du bot")

# Initialisation du bot
bot = discord.Client(intents=discord.Intents.all())

# Événement déclenché lorsque le bot est prêt
@bot.event
async def on_ready():
    """Affiche un message dans la console lorsque le bot est prêt"""
    print("bot prêt")

# Récupération du token depuis les variables d'environnement et lancement du bot
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("DISCORD_TOKEN manquant dans le fichier .env")
bot.run(token)
