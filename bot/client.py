"""Instance unique du client Discord, partagée par tous les modules."""
import discord

intents = discord.Intents.default()
intents.message_content = True

botsq = discord.Client(intents=intents)
