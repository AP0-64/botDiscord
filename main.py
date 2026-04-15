"""importation des modules nécessaires pour le bot Discord"""
import os
import discord
from dotenv import load_dotenv


load_dotenv()

print("Lancement du bot")

# Initialisation du bot
bot = discord.Client(intents=discord.Intents.all())
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("DISCORD_TOKEN manquant dans le fichier .env")

bot.run(token)
