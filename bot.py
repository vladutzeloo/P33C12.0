import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from nim_services import NIMServices
from audio_handler import AudioHandler
from db import init_db

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
nim = NIMServices()
audio_handler = AudioHandler()


@bot.event
async def on_ready():
    init_db()
    print(f"[P33C1 2.0] Logged in as {bot.user} — rat mode activated.")


@bot.command(name="voice")
async def join_voice(ctx: commands.Context):
    """Join the user's voice channel and start listening."""
    if not ctx.author.voice:
        await ctx.send("Oi, get in a voice channel first, genius.")
        return

    channel = ctx.author.voice.channel
    vc = await channel.connect()
    await ctx.send(f"Rat is in the walls... joined {channel.name}.")

    try:
        await audio_handler.listen_and_respond(vc, nim)
    except Exception as e:
        await ctx.send(f"Pipe burst: {e}")
        await vc.disconnect()


@bot.command(name="leave")
async def leave_voice(ctx: commands.Context):
    """Disconnect from voice channel."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Scurrying back into the walls. Later.")
    else:
        await ctx.send("I'm not even in a channel, mate.")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
