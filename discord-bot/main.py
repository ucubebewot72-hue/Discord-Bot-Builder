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

TOKEN = os.getenv("DISCORD_TOKEN")
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


# ---------------- MOD CHECK ----------------

def is_mod(member: discord.Member):
    return any(r.id == MOD_ROLE_ID for r in member.roles)


# ---------------- DELETE COMMAND ----------------

@bot.command(name="del")
async def delete_cmd(ctx, amount: int):
    if not is_mod(ctx.author):
        return

    if amount <= 0:
        return await ctx.send("❌ Geçersiz sayı")

    if amount > 100:
        amount = 100

    deleted = await ctx.channel.purge(limit=amount + 1)

    msg = await ctx.send(f"🧹 {len(deleted)-1} mesaj silindi")
    await asyncio.sleep(2)
    await msg.delete()


# ---------------- EMOTE ADD ----------------

@tree.command(name="emote_add", description="Emote ekle")
async def emote_add(interaction: discord.Interaction, name: str, url: str):
    emotes[name.lower()] = url
    save_emotes(emotes)
    await interaction.response.send_message(f"✅ Emote eklendi: {name}")


# ---------------- EMOTE SEND ----------------

@tree.command(name="emote", description="Emote gönder")
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


# ---------------- RUN ----------------

bot.run(TOKEN)
