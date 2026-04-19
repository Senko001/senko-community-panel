import discord
from discord.ext import commands

from bot.config import TOKEN, PREFIX

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)


@bot.event
async def on_ready():
    print(f"✅ Bot online: {bot.user}")


@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")


if __name__ == "__main__":
    bot.run(TOKEN)
