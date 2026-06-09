import asyncio
import os
import re
import sys
from datetime import timedelta

import aiohttp
import discord
from discord.ext import commands, tasks

import db

VOICE_CHANNEL_ID = 1445806750132473937
MOD_ROLE_ID = 1445145937390604523

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    sys.exit("HATA: DISCORD_TOKEN ortam değişkeni ayarlanmamış.")

TENOR_PAGE_URL = "https://tenor.com/view/anime-luminous-luminus-luminas-valentine-gif-2480934953542931736"
BAN_GIF_PATH = "ban.gif"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="k ", intents=intents)


async def download_ban_gif():
    if os.path.exists(BAN_GIF_PATH):
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(TENOR_PAGE_URL) as resp:
                html = await resp.text()

            match = re.search(r'"url"\s*:\s*"(https://media\.tenor\.com/[^"]+\.gif)"', html)
            if not match:
                match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)

            if match:
                gif_url = match.group(1)
                async with session.get(gif_url) as gif_resp:
                    if gif_resp.status == 200:
                        with open(BAN_GIF_PATH, "wb") as f:
                            f.write(await gif_resp.read())
    except Exception as e:
        print(f"GIF hata: {e}")


AVATAR_PATH = "avatar.jpg"
_avatar_set = False

async def set_avatar():
    global _avatar_set
    if _avatar_set:
        return
    try:
        with open(AVATAR_PATH, "rb") as f:
            await bot.user.edit(avatar=f.read())
        _avatar_set = True
    except:
        pass


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


@bot.event
async def on_ready():
    db.init_db()
    await download_ban_gif()
    await set_avatar()

    # ✅ DÜZELTİLMİŞ STATUS
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

    print(f"Bot hazır: {bot.user}")


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

if "kaan" in message.content.lower():
    await message.reply("mal")

if message.content.lower() == "sega":
    try:
        member = message.guild.get_member(1146881435500826704)

        if member:
            current_timeout = member.timed_out_until

            if current_timeout and current_timeout > discord.utils.utcnow():
                yeni_sure = current_timeout + timedelta(minutes=1)
            else:
                yeni_sure = discord.utils.utcnow() + timedelta(minutes=1)

            await member.edit(
                timed_out_until=yeni_sure,
                reason=f"{message.author} sega yazdı"
            )

    except Exception as e:
        print(f"SEGA timeout hatası: {e}")

await bot.process_commands(message)


@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    if before.channel is None and after.channel:
        db.record_voice_join(member.guild.id, member.id, str(member))
    elif before.channel and after.channel is None:
        db.record_voice_leave(member.guild.id, member.id)


# ---------------- COMMANDS ----------------

@bot.command(name="ban")
@is_mod()
async def ban_cmd(ctx, user_id: int, *, reason="Sebep yok"):
    user = await bot.fetch_user(user_id)
    await ctx.guild.ban(user, reason=reason)
    await ctx.send("✅ banlandı")


@bot.command(name="kick")
@is_mod()
async def kick_cmd(ctx, user_id: int, *, reason="Sebep yok"):
    member = ctx.guild.get_member(user_id)
    if member:
        await member.kick(reason=reason)
        await ctx.send("✅ kicklendi")


@bot.command(name="mute")
@is_mod()
async def mute_cmd(ctx, user_id: int):
    member = ctx.guild.get_member(user_id)
    if member:
        await member.timeout(timedelta(hours=1))
        await ctx.send("✅ mute")


@bot.command(name="del")
@is_mod()
async def del_cmd(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send("✅ silindi", delete_after=2)


# ---------------- RUN ----------------

bot.run(TOKEN)
