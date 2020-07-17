import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

bot = commands.Bot(command_prefix="!")



@bot.command(name='arise')
async def test(ctx):
    await ctx.send("I have arisen.")

@bot.command(name='users')
async def get_movie_rr_order(ctx):
    text_channels = ctx.guild.text_channels
    for channel in text_channels:
        if channel.name == "movie-round-robin":
            members = '\n - '.join([member.display_name for member in channel.members if member.bot == False])
            await ctx.send(f'List of degenerates:\n - {members}')


@bot.event
async def on_ready():
    guild = discord.utils.find(lambda g: g.name == GUILD, bot.guilds)
    print(
        f'{bot.user} is connected to: \n'
        f'{guild.name}(id: {guild.id})'
    )            
bot.run(TOKEN)