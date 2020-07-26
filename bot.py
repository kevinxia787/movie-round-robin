import os

import discord
import random
import giphy_client
import tmdbsimple as tmdb
import re

from discord.ext import commands
from dotenv import load_dotenv
from tabulate import tabulate
from giphy_client.rest import ApiException
from pprint import pprint

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GIPHY_KEY = os.getenv('GIPHY_API_KEY')
TMDB_KEY = os.getenv('TMDB_API_KEY')

bot = commands.Bot(command_prefix='!')
# bot.remove_command('help')

# selections = [["beemu", "Kimi No Na Wa", True], ["docquan", "Being John Malkovich", False], ["Parz", "A Silent Voice", False], ["bombuh", "Art of Self Defense", False]]
selections = []

giphy_api_instance = giphy_client.DefaultApi()

embedded_gif = discord.Embed()
embedded_movie = discord.Embed()


tmdb.API_KEY = TMDB_KEY


def create_movie_embed(arg, year):
    # call tmdb api
    search = tmdb.Search()
    results = search.movie(query=arg)['results']

    # convert user input to lowercase
    arg = arg.lower()
    arg = re.sub(r'[^\w\s]','',arg)

    movie_selection = []

    # iterate through results
    if (len(results) == 1):
        movie_selection = results
    else:
        if (year != None):
            movie_selection = [result for result in results if ((re.sub(r'[^\w\s]','',result['title'].lower()) == arg) and (result['release_date'].split('-')[0] == year))]
        else:
            movie_selection = [result for result in results if ((re.sub(r'[^\w\s]','',result['title'].lower()) == arg) and (result['poster_path'] != None))]
    
    if (len(movie_selection) == 0):
        return None

    embedded_movie = discord.Embed(title=movie_selection[0]['title'], description=movie_selection[0]['overview'])
    tmdb_poster_url = "http://image.tmdb.org/t/p/w500" + movie_selection[0]['poster_path']
    embedded_movie.set_image(url=tmdb_poster_url)
    return embedded_movie

@bot.command(name='arise')
async def test(ctx):
    await ctx.send('I have arisen.')

@bot.command(name='select')
async def set_user_selection(ctx, movie_name, year : str = None):
    author = str(ctx.author)
    author = author.split("#")[0]
    # create movie embed object
    movie_embed = create_movie_embed(movie_name, year)

    if (movie_embed == None):
        await ctx.send('Hmm...not sure if that movie exists in the TMDB Database. Check your spelling of the title and make sure you\'re using quotes!')
        return

    for entry in selections:
        # user has made a selection before, overwriting
        if entry[0] == author:
            entry[1] = movie_embed
            await ctx.send(f'{author} changed their mind! They selected....{movie_embed.title}')
            await ctx.send(embed=movie_embed)
            return

    # user has not made a selection, add new entry
    selections.append([author, movie_embed, False])
    await ctx.send(f'{author} has selected....{movie_embed.title}')
    await ctx.send(embed=movie_embed)

@bot.command(name='get_menu')
async def get_cinephile_menu(ctx):
    if len(selections) == 0:
        try:
            api_response = giphy_api_instance.gifs_search_get(GIPHY_KEY, limit=1, rating='g', q='boring')
            embedded_gif.set_image(url=api_response.data[0].images.downsized_medium.url)
            await ctx.send('Uh oh! Looks like your movie list is empty! How boring...')
            await ctx.send(embed=embedded_gif)
            return
        except ApiException as e:
            print("Exception when calling DefaultAPI --> gifs_search_get: %s\n" % e)

    await ctx.send("Here's the menu!")
    for selection in selections:
        if (not selection[2]):
            await ctx.send(embed=selection[1])
    

@bot.command(name='random_choice')
async def get_random_choice(ctx):
    if len(selections) == 0:
        try:
            api_response = giphy_api_instance.gifs_search_get(GIPHY_KEY, limit=1, rating='g', q='picard facepalm')
            embedded_gif.set_image(url=str(api_response.data[0].images.downsized_medium.url))
            await ctx.send('How tf am I supposed to randomly pick if your list is empty?')
            await ctx.send(embed=embedded_gif)
            return
        except ApiException as e:
            print("Exception when calling DefaultAPI --> gifs_search_get: %s\n" % e)
    # watched = all_watched(selections)
    # if watched:
    #     await ctx.send('Time for new selections folks! Use !clear to clear selections.')
    random_choice = random.choice(selections)
    while (random_choice[2]):
        random_choice = random.choice(selections)

    await ctx.send(f'Grab your popcorn folks...we\'re watching:')
    await ctx.send(embed=random_choice[1])


@bot.event
async def on_ready():
    guild = discord.utils.find(lambda g: g.name == GUILD, bot.guilds)
    print(
        f'{bot.user} is connected to: \n'
        f'{guild.name}(id: {guild.id})'
    )            


bot.run(TOKEN)