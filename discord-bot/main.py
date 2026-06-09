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
        print("GIF zaten mevcut, tekrar indirilmedi.")
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
                        print(f"GIF indirildi: {gif_url}")
                        return
        print("GIF indirilemedi, URL bulunamadı.")
    except Exception as e:
        print(f"GIF indirme hatası: {e}")


async def send_dm(user, **kwargs):
    try:
        await user.send(**kwargs)
    except discord.Forbidden:
        print(f"DM gönderilemedi → {user} (DM kapalı veya engellendi)")
    except Exception as e:
        print(f"DM hatası → {user}: {e}")


async def join_kaine():
    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if not channel or not isinstance(channel, discord.VoiceChannel):
        print(f"Ses kanalı bulunamadı (ID: {VOICE_CHANNEL_ID})")
        return
    vc = channel.guild.voice_client
    if vc and vc.is_connected():
        if vc.channel.id != VOICE_CHANNEL_ID:
            await vc.move_to(channel)
    else:
        try:
            await channel.connect()
            print(f"'{channel.name}' ses kanalına bağlanıldı")
        except Exception as e:
            print(f"Ses kanalına bağlanılamadı: {e}")


@tasks.loop(seconds=30)
async def voice_keepalive():
    await join_kaine()


@voice_keepalive.before_loop
async def before_keepalive():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    db.init_db()
    await download_ban_gif()
    await join_kaine()
    if not voice_keepalive.is_running():
        voice_keepalive.start()
    print(f"Bot hazır — {bot.user} olarak giriş yapıldı (ID: {bot.user.id})")
    print("------")


@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        return
    db.increment_messages(message.guild.id, message.author.id, str(message.author))
    if "kaan" in message.content.lower():
        await message.reply("mal")
    await bot.process_commands(message)


@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None and after.channel is not None:
        db.record_voice_join(member.guild.id, member.id, str(member))
    elif before.channel is not None and after.channel is None:
        db.record_voice_leave(member.guild.id, member.id)


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_cmd(ctx, user_id: int, *, reason: str = "Sebep belirtilmedi"):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.ban(user, reason=reason)
        await ctx.message.add_reaction("✅")

        embed = discord.Embed(title="Kullanıcı Banlandı", color=discord.Color.red())
        embed.add_field(name="Kullanıcı", value=f"{user} (ID: `{user_id}`)", inline=False)
        embed.add_field(name="Sebep", value=reason, inline=False)

        if os.path.exists(BAN_GIF_PATH):
            embed.set_image(url="attachment://ban.gif")
            await send_dm(
                ctx.author,
                embed=embed,
                file=discord.File(BAN_GIF_PATH, filename="ban.gif"),
            )
        else:
            await send_dm(ctx.author, embed=embed)

    except discord.NotFound:
        await send_dm(ctx.author, content=f"❌ `{user_id}` ID'li bir kullanıcı bulunamadı.")
    except discord.Forbidden:
        await send_dm(ctx.author, content="❌ Bu kullanıcıyı banlama yetkim yok.")
    except Exception as e:
        await send_dm(ctx.author, content=f"❌ Hata: {e}")


@ban_cmd.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await send_dm(ctx.author, content="❌ Bu komutu kullanma yetkiniz yok.")
    elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("k ban user id")


@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban_cmd(ctx, user_id: int):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.message.add_reaction("✅")

        embed = discord.Embed(title="Ban Kaldırıldı", color=discord.Color.green())
        embed.add_field(name="Kullanıcı", value=f"{user} (ID: `{user_id}`)", inline=False)
        await send_dm(ctx.author, embed=embed)

    except discord.NotFound:
        await send_dm(ctx.author, content=f"❌ `{user_id}` ID'li kullanıcı banlanmış listesinde bulunamadı.")
    except discord.Forbidden:
        await send_dm(ctx.author, content="❌ Bu kullanıcının banını kaldırma yetkim yok.")
    except Exception as e:
        await send_dm(ctx.author, content=f"❌ Hata: {e}")


@unban_cmd.error
async def unban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await send_dm(ctx.author, content="❌ Bu komutu kullanma yetkiniz yok.")
    elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("k unban user id")


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_cmd(ctx, user_id: int, *, reason: str = "Sebep belirtilmedi"):
    try:
        member = ctx.guild.get_member(user_id) or await ctx.guild.fetch_member(user_id)
        await member.kick(reason=reason)
        await ctx.message.add_reaction("✅")

        embed = discord.Embed(title="Kullanıcı Atıldı", color=discord.Color.orange())
        embed.add_field(name="Kullanıcı", value=f"{member} (ID: `{user_id}`)", inline=False)
        embed.add_field(name="Sebep", value=reason, inline=False)
        await send_dm(ctx.author, embed=embed)

    except discord.NotFound:
        await send_dm(ctx.author, content=f"❌ `{user_id}` ID'li bir üye bu sunucuda bulunamadı.")
    except discord.Forbidden:
        await send_dm(ctx.author, content="❌ Bu kullanıcıyı atma yetkim yok.")
    except Exception as e:
        await send_dm(ctx.author, content=f"❌ Hata: {e}")


@kick_cmd.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await send_dm(ctx.author, content="❌ Bu komutu kullanma yetkiniz yok.")
    elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("k kick user id")


@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute_cmd(ctx, user_id: int, *, reason: str = "Sebep belirtilmedi"):
    try:
        member = ctx.guild.get_member(user_id) or await ctx.guild.fetch_member(user_id)
        await member.timeout(timedelta(hours=1), reason=reason)
        await ctx.message.add_reaction("✅")

        embed = discord.Embed(title="Kullanıcı Susturuldu", color=discord.Color.blue())
        embed.add_field(name="Kullanıcı", value=f"{member} (ID: `{user_id}`)", inline=False)
        embed.add_field(name="Süre", value="1 saat", inline=False)
        embed.add_field(name="Sebep", value=reason, inline=False)
        await send_dm(ctx.author, embed=embed)

    except discord.NotFound:
        await send_dm(ctx.author, content=f"❌ `{user_id}` ID'li bir üye bu sunucuda bulunamadı.")
    except discord.Forbidden:
        await send_dm(ctx.author, content="❌ Bu kullanıcıyı susturma yetkim yok.")
    except Exception as e:
        await send_dm(ctx.author, content=f"❌ Hata: {e}")


@mute_cmd.error
async def mute_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await send_dm(ctx.author, content="❌ Bu komutu kullanma yetkiniz yok.")
    elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("k mute user id")


@bot.command(name="warn")
@commands.has_permissions(moderate_members=True)
async def warn_cmd(ctx, user_id: int, *, reason: str):
    try:
        member = ctx.guild.get_member(user_id) or await ctx.guild.fetch_member(user_id)
        db.add_warning(ctx.guild.id, user_id, str(member), ctx.author.id, str(ctx.author), reason)
        warnings = db.get_warnings(ctx.guild.id, user_id)
        await ctx.message.add_reaction("✅")

        embed = discord.Embed(title="Kullanıcı Uyarıldı", color=discord.Color.yellow())
        embed.add_field(name="Kullanıcı", value=f"{member} (ID: `{user_id}`)", inline=False)
        embed.add_field(name="Sebep", value=reason, inline=False)
        embed.add_field(name="Toplam Uyarı", value=str(len(warnings)), inline=False)
        await send_dm(ctx.author, embed=embed)

    except discord.NotFound:
        await send_dm(ctx.author, content=f"❌ `{user_id}` ID'li bir üye bu sunucuda bulunamadı.")
    except Exception as e:
        await send_dm(ctx.author, content=f"❌ Hata: {e}")


@warn_cmd.error
async def warn_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await send_dm(ctx.author, content="❌ Bu komutu kullanma yetkiniz yok.")
    elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("k warn user id reason")


@bot.command(name="del")
@commands.has_permissions(manage_messages=True)
async def del_cmd(ctx, amount: int):
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        await send_dm(ctx.author, content=f"✅ {len(deleted) - 1} mesaj silindi.")
    except discord.Forbidden:
        await send_dm(ctx.author, content="❌ Mesaj silme yetkim yok.")
    except Exception as e:
        await send_dm(ctx.author, content=f"❌ Hata: {e}")


@del_cmd.error
async def del_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await send_dm(ctx.author, content="❌ Bu komutu kullanma yetkiniz yok.")
    elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("k del number")


@bot.command(name="top")
async def top_cmd(ctx):
    top_messages = db.get_top_messages(ctx.guild.id, limit=5)
    top_voice = db.get_top_voice(ctx.guild.id, limit=5)

    embed = discord.Embed(title="🏆 Sunucu Sıralaması", color=discord.Color.gold())

    if top_messages:
        msg_lines = [
            f"`{i + 1}.` **{name}** — {count:,} mesaj"
            for i, (name, count) in enumerate(top_messages)
        ]
        embed.add_field(name="💬 En Çok Mesaj Atan Kullanıcılar", value="\n".join(msg_lines), inline=False)
    else:
        embed.add_field(name="💬 En Çok Mesaj Atan Kullanıcılar", value="Henüz veri yok.", inline=False)

    if top_voice:
        voice_lines = []
        for i, (name, seconds) in enumerate(top_voice):
            seconds = int(seconds)
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            voice_lines.append(f"`{i + 1}.` **{name}** — {hours}sa {minutes}dk")
        embed.add_field(name="🎙️ En Çok Ses Kanalında Bulunan Kullanıcılar", value="\n".join(voice_lines), inline=False)
    else:
        embed.add_field(name="🎙️ En Çok Ses Kanalında Bulunan Kullanıcılar", value="Henüz veri yok.", inline=False)

    await ctx.send(embed=embed)


bot.run(TOKEN)
