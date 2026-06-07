import os
import sys
from datetime import timedelta

import discord
from discord.ext import commands

import db

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    sys.exit("ERROR: DISCORD_TOKEN environment variable is not set.")

BAN_GIF = "https://tenor.com/view/anime-luminous-luminus-luminas-valentine-gif-2480934953542931736"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="k ", intents=intents)


@bot.event
async def on_ready():
    db.init_db()
    print(f"Bot ready — logged in as {bot.user} (ID: {bot.user.id})")
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
async def ban_cmd(ctx, user_id: int, *, reason: str = "No reason provided"):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.ban(user, reason=reason)

        embed = discord.Embed(title="User Banned", color=discord.Color.red())
        embed.add_field(name="User", value=f"{user} (ID: `{user_id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)

        try:
            await ctx.author.send(embed=embed)
            await ctx.author.send(BAN_GIF)
        except discord.Forbidden:
            pass

    except discord.NotFound:
        await ctx.send(f"❌ No user found with ID `{user_id}`.")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to ban this user.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")


@ban_cmd.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("Usage: k ban user id")


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_cmd(ctx, user_id: int, *, reason: str = "No reason provided"):
    try:
        member = ctx.guild.get_member(user_id) or await ctx.guild.fetch_member(user_id)
        await member.kick(reason=reason)
        await ctx.send(f"✅ Kicked **{member}** (ID: `{user_id}`)\nReason: {reason}")
    except discord.NotFound:
        await ctx.send(f"❌ No member found with ID `{user_id}` in this server.")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to kick this user.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")


@kick_cmd.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("Usage: k kick user id")


@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute_cmd(ctx, user_id: int, *, reason: str = "No reason provided"):
    try:
        member = ctx.guild.get_member(user_id) or await ctx.guild.fetch_member(user_id)
        await member.timeout(timedelta(hours=1), reason=reason)
        await ctx.send(
            f"✅ Timed out **{member}** (ID: `{user_id}`) for **1 hour**\nReason: {reason}"
        )
    except discord.NotFound:
        await ctx.send(f"❌ No member found with ID `{user_id}` in this server.")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to timeout this user.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")


@mute_cmd.error
async def mute_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("Usage: k mute user id")


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
        await ctx.send(
            f"⚠️ Warned **{member}** (ID: `{user_id}`)\nReason: {reason}\nTotal warnings: **{len(warnings)}**"
        )
    except discord.NotFound:
        await ctx.send(f"❌ No member found with ID `{user_id}` in this server.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")


@warn_cmd.error
async def warn_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send("Usage: k warn user id reason")


@bot.command(name="top")
async def top_cmd(ctx):
    top_messages = db.get_top_messages(ctx.guild.id, limit=5)
    top_voice = db.get_top_voice(ctx.guild.id, limit=5)

    embed = discord.Embed(title="🏆 Server Leaderboard", color=discord.Color.gold())

    if top_messages:
        msg_lines = [
            f"`{i + 1}.` **{name}** — {count:,} messages"
            for i, (name, count) in enumerate(top_messages)
        ]
        embed.add_field(
            name="💬 Top Message Senders", value="\n".join(msg_lines), inline=False
        )
    else:
        embed.add_field(
            name="💬 Top Message Senders", value="No data yet.", inline=False
        )

    if top_voice:
        voice_lines = []
        for i, (name, seconds) in enumerate(top_voice):
            seconds = int(seconds)
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            voice_lines.append(f"`{i + 1}.` **{name}** — {hours}h {minutes}m")
        embed.add_field(
            name="🎙️ Top Voice Activity", value="\n".join(voice_lines), inline=False
        )
    else:
        embed.add_field(
            name="🎙️ Top Voice Activity", value="No data yet.", inline=False
        )

    await ctx.send(embed=embed)


bot.run(TOKEN)
