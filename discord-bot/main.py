import asyncio
import os
import re
import sys
import json
from datetime import timedelta

import aiohttp
import discord
from discord.ext import commands, tasks
from discord import app_commands

import db

VOICE_CHANNEL_ID = 1445806750132473937
MOD_ROLE_ID = 1445145937390604523

TOKEN = os.getenv("MTUxMTQyMjg0OTUyNzcwOTcxNg.GZxWvh.wOm9M2c39saSNuqlUK8ejBGvDKScLBj29arv1s")
if not TOKEN:
    sys.exit("HATA: DISCORD_TOKEN ortam değişkeni ayarlanmamış.")

TENOR_PAGE_URL = "https://tenor.com/view/anime-luminous-luminus-luminas-valentine-gif-2480934953542931736"
BAN_GIF_PATH = "ban.gif"

EMOTE_DB_FILE = "emotes.json"


# ---------------- EMOTES ----------------

def load_emotes():
    if not os.path.exists(EMOTE_DB_FILE):
        return {}
    try:
        with open(EMOTE_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_emotes(data):
    with open(EMOTE_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


emotes = load_emotes()


# ---------------- BOT ----------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="k ", intents=intents)
tree = bot.tree


# ---------------- BAN GIF ----------------

async def download_ban_gif():
    if os.path.exists(BAN_GIF_PATH):
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(TENOR_PAGE_URL) as resp:
                html = await resp.text()

            match = re.search(r'"url"\s*:\s*"(https://media\.tenor\.com/[^"]+\.gif)"', html)

            if match:
                gif_url = match.group(1)
                async with session.get(gif_url) as gif_resp:
                    if gif_resp.status == 200:
                        with open(BAN_GIF_PATH, "wb") as f:
                            f.write(await gif_resp.read())
    except Exception as e:
        print(f"GIF hata: {e}")


# ---------------- MOD CHECK ----------------

async def send_dm(user, **kwargs):
    try:
        await user.send(**kwargs)
    except:
        pass


def is_mod():
    async def predicate(ctx):
        if any(r.id == MOD_ROLE_ID for r in ctx.author.roles):
            return True
        await send_dm(ctx.author, content="❌ Yetkin yok.")
        return False
    return commands.check(predicate)


# ---------------- EMOTE SYSTEM (FIXED) ----------------

@tree.command(name="emote_add", description="Emote ekle")
@app_commands.describe(name="isim", url="gif link")
async def emote_add(interaction: discord.Interaction, name: str, url: str):
    emotes[name.lower()] = url
    save_emotes(emotes)

    await interaction.response.send_message(f"✅ Emote eklendi: {name}")


@tree.command(name="emote", description="Emote gönder")
@app_commands.describe(name="emote ismi")
async def emote_send(interaction: discord.Interaction, name: str):
    url = emotes.get(name.lower())

    if not url:
        await interaction.response.send_message("❌ Emote yok", ephemeral=True)
        return

    embed = discord.Embed()
    embed.set_image(url=url)

    await interaction.response.send_message(embed=embed)


# ---------------- VOICE ----------------

async def join_voice():
    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if not isinstance(channel, discord.VoiceChannel):
        return

    vc = channel.guild.voice_client

    try:
        if vc and vc.is_connected():
            if vc.channel.id != channel.id:
                await vc.move_to(channel)
        else:
            await channel.connect(self_mute=True, self_deaf=True)
    except Exception as e:
        print(f"Voice error: {e}")


@tasks.loop(seconds=30)
async def voice_keepalive():
    await join_voice()


# ---------------- READY ----------------

@bot.event
async def on_ready():
    db.init_db()
    await download_ban_gif()

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="discord.gg/steamart"
        ),
    )

    try:
        await bot.user.edit(bio="discord.gg/steamart")
    except:
        pass

    await join_voice()

    if not voice_keepalive.is_running():
        voice_keepalive.start()

    await tree.sync()

    print(f"Bot hazır: {bot.user}")


# ---------------- EVENTS ----------------

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.guild:
        db.increment_messages(
            message.guild.id,
            message.author.id,
            str(message.author)
        )

    await bot.process_commands(message)


# ---------------- RUN ----------------

bot.run(TOKEN)
