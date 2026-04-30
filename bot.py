import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from nim_services import NIMServices
from audio_handler import AudioHandler
from db import init_db, get_usage_summary

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ALLOWED_GUILD_IDS = {
    int(g.strip())
    for g in os.getenv("ALLOWED_GUILD_IDS", "").split(",")
    if g.strip().isdigit()
}

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
nim = NIMServices()
audio_handler = AudioHandler()


def guild_allowed(ctx: commands.Context) -> bool:
    if not ALLOWED_GUILD_IDS:
        return True
    return ctx.guild is not None and ctx.guild.id in ALLOWED_GUILD_IDS


@bot.event
async def on_ready():
    init_db()
    print(f"[P33C1 2.0] Logged in as {bot.user} — RATTUS online.")
    if ALLOWED_GUILD_IDS:
        print(f"[P33C1 2.0] Restricted to guilds: {ALLOWED_GUILD_IDS}")


@bot.command(name="voice")
async def join_voice(ctx: commands.Context):
    """Join your voice channel and start listening."""
    if not guild_allowed(ctx):
        return
    if not ctx.author.voice:
        await ctx.send("bagă-te într-un voice mai întâi.")
        return

    channel = ctx.author.voice.channel
    vc = await channel.connect()
    await ctx.send(f"intru în {channel.name}.")

    try:
        await audio_handler.listen_and_respond(vc, nim)
    except Exception as e:
        await ctx.send(f"crăpat: {e}")
        await vc.disconnect()


@bot.command(name="leave")
async def leave_voice(ctx: commands.Context):
    if not guild_allowed(ctx):
        return
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("plec. lasă-mă.")
    else:
        await ctx.send("nu sunt în voice, frate.")


@bot.command(name="stats")
async def stats(ctx: commands.Context):
    """Show NIM token usage."""
    if not guild_allowed(ctx):
        return
    rows = get_usage_summary()
    if not rows:
        await ctx.send("zero token-uri folosite.")
        return
    lines = ["**NIM usage:**"]
    for r in rows:
        lines.append(
            f"`{r['model']}` — calls: {r['calls']}, "
            f"in: {r['input']}, out: {r['output']}, total: {r['total']}"
        )
    await ctx.send("\n".join(lines))


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
