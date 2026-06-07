import os
import sys
from datetime import timedelta

import discord
from discord.ext import commands

import db

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    sys.exit("HATA: DISCORD_TOKEN ortam değişkeni ayarlanmamış.")

BAN_GIF = "https://tenor.com/view/anime-luminous-luminus-luminas-valentine-gif-2480934953542931736"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="k ", intents=intents)


@bot.event
async def on_ready():
    db.init_db()
    print(f"Bot hazır — {bot.user} olarak giriş yapıldı (ID: {bot.user.id})")
    print("------")


@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        return
    db.increment_messages(message.guild.id, message.author.id, str(message.author))
    await bot.process_commands(message)


@bot.event
async def on_voice_state_update(member, before, after):
    joined = before.channel is None and after.channel is not None
    left = before.channel is not None and after.channel is None

    if joined:
        db.record_voice_join(member.guild.id, member.id, str(member))
    elif left:
        db.record_voice_leave(member.guild.id, member.id)


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_cmd(ctx, user_id: int, *, reason: str = "Sebep belirtilmedi"):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.ban(user, reason=reason)

        embed = discord.Embed(title="Kullanıcı Banlandı", color=discord.Color.red())
        embed.add_field(name="Kullanıcı", value=f"{user} (ID: `{user_id}`)", inline=False)
        embed.add_field(name="Sebep", value=reason, inline=False)

        try:
            await ctx.author.send(embed=embed)
            await ctx.author.send(BAN_GIF)
        except discord.Forbidden:
            pass

    except discord.NotFound:
        try:
            await ctx.author.send(f"❌ `{user_id}` ID'li bir kullanıcı bulunamadı.")
        except discord.Forbidden:
            pass
    except discord.Forbidden:
        try:
            await ctx.author.send("❌ Bu kullanıcıyı banlama yetkim yok.")
        except discord.Forbidden:
            pass
    except Exception as e:
        try:
            await ctx.author.send(f"❌ Hata: {e}")
        except discord.Forbidden:
            pass


@ban_cmd.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        try:
            await ctx.author.send("❌ Bu komutu kullanma yetkiniz yok.")
        except discord.Forbidden:
            pass
    elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("k ban user id")


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_cmd(ctx, user_id: int, *, reason: str = "Sebep belirtilmedi"):
    try:
        member = ctx.guild.get_member(user_id) or await ctx.guild.fetch_member(user_id)
        await member.kick(reason=reason)

        embed = discord.Embed(title="Kullanıcı Atıldı", color=discord.Color.orange())
        embed.add_field(name="Kullanıcı", value=f"{member} (ID: `{user_id}`)", inline=False)
        embed.add_field(name="Sebep", value=reason, inline=False)

        try:
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            pass

    except discord.NotFound:
        try:
            await ctx.author.send(f"❌ `{user_id}` ID'li bir üye bu sunucuda bulunamadı.")
        except discord.Forbidden:
            pass
    except discord.Forbidden:
        try:
            await ctx.author.send("❌ Bu kullanıcıyı atma yetkim yok.")
        except discord.Forbidden:
            pass
    except Exception as e:
        try:
            await ctx.author.send(f"❌ Hata: {e}")
        except discord.Forbidden:
            pass


@kick_cmd.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        try:
            await ctx.author.send("❌ Bu komutu kullanma yetkiniz yok.")
        except discord.Forbidden:
            pass
    elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("k kick user id")


@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute_cmd(ctx, user_id: int, *, reason: str = "Sebep belirtilmedi"):
    try:
        member = ctx.guild.get_member(user_id) or await ctx.guild.fetch_member(user_id)
        await member.timeout(timedelta(hours=1), reason=reason)

        embed = discord.Embed(title="Kullanıcı Susturuldu", color=discord.Color.blue())
        embed.add_field(name="Kullanıcı", value=f"{member} (ID: `{user_id}`)", inline=False)
        embed.add_field(name="Süre", value="1 saat", inline=False)
        embed.add_field(name="Sebep", value=reason, inline=False)

        try:
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            pass

    except discord.NotFound:
        try:
            await ctx.author.send(f"❌ `{user_id}` ID'li bir üye bu sunucuda bulunamadı.")
        except discord.Forbidden:
            pass
    except discord.Forbidden:
        try:
            await ctx.author.send("❌ Bu kullanıcıyı susturma yetkim yok.")
        except discord.Forbidden:
            pass
    except Exception as e:
        try:
            await ctx.author.send(f"❌ Hata: {e}")
        except discord.Forbidden:
            pass


@mute_cmd.error
async def mute_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        try:
            await ctx.author.send("❌ Bu komutu kullanma yetkiniz yok.")
        except discord.Forbidden:
            pass
    elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("k mute user id")


@bot.command(name="warn")
@commands.has_permissions(moderate_members=True)
async def warn_cmd(ctx, user_id: int, *, reason: str):
    try:
        member = ctx.guild.get_member(user_id) or await ctx.guild.fetch_member(user_id)
        db.add_warning(
            ctx.guild.id,
            user_id,
            str(member),
            ctx.author.id,
            str(ctx.author),
            reason,
        )
        warnings = db.get_warnings(ctx.guild.id, user_id)

        embed = discord.Embed(title="Kullanıcı Uyarıldı", color=discord.Color.yellow())
        embed.add_field(name="Kullanıcı", value=f"{member} (ID: `{user_id}`)", inline=False)
        embed.add_field(name="Sebep", value=reason, inline=False)
        embed.add_field(name="Toplam Uyarı", value=str(len(warnings)), inline=False)

        try:
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            pass

    except discord.NotFound:
        try:
            await ctx.author.send(f"❌ `{user_id}` ID'li bir üye bu sunucuda bulunamadı.")
        except discord.Forbidden:
            pass
    except Exception as e:
        try:
            await ctx.author.send(f"❌ Hata: {e}")
        except discord.Forbidden:
            pass


@warn_cmd.error
async def warn_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        try:
            await ctx.author.send("❌ Bu komutu kullanma yetkiniz yok.")
        except discord.Forbidden:
            pass
    elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("k warn user id reason")


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
        embed.add_field(
            name="💬 En Çok Mesaj Atan Kullanıcılar",
            value="\n".join(msg_lines),
            inline=False,
        )
    else:
        embed.add_field(
            name="💬 En Çok Mesaj Atan Kullanıcılar",
            value="Henüz veri yok.",
            inline=False,
        )

    if top_voice:
        voice_lines = []
        for i, (name, seconds) in enumerate(top_voice):
            seconds = int(seconds)
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            voice_lines.append(f"`{i + 1}.` **{name}** — {hours}sa {minutes}dk")
        embed.add_field(
            name="🎙️ En Çok Ses Kanalında Bulunan Kullanıcılar",
            value="\n".join(voice_lines),
            inline=False,
        )
    else:
        embed.add_field(
            name="🎙️ En Çok Ses Kanalında Bulunan Kullanıcılar",
            value="Henüz veri yok.",
            inline=False,
        )

    await ctx.send(embed=embed)


bot.run(TOKEN)
