import os

import discord
import random
import giphy_client
import tmdbsimple as tmdb
import re

from discord.ext import commands
from dotenv import load_dotenv
from giphy_client.rest import ApiException

load_dotenv()

GIPHY_KEY = os.getenv('GIPHY_API_KEY')
TMDB_KEY = os.getenv('TMDB_API_KEY')

tmdb.API_KEY = TMDB_KEY

giphy_api_instance = giphy_client.DefaultApi()

selections = []
selections_db = []

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

class Movies(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def arise(self, ctx):
        await ctx.send("I have arisen.")
        
    @commands.command()
    async def select(self, ctx, movie_name, year : str = None, user : str = None):
        author = str(ctx.author)
        roles = ctx.author.roles
        author = author.split('#')[0]
        if (user != None):
            is_head_sloth = False
            for role in roles:
                if role.name == 'Head Sloth':
                    is_head_sloth = True
                    break
            if (not is_head_sloth):
                try:
                    api_response = giphy_api_instance.gifs_search_get(GIPHY_KEY, limit=1, rating='g', q='dikembe mutombo finger wag')
                    embedded_gif = discord.Embed(description='Oops! Someone\'s being a bit naughty! This feature isn\'t for you!')
                    embedded_gif.set_image(url=api_response.data[0].images.downsized_medium.url)
                    await ctx.send(embed=embedded_gif)
                except ApiException as e:
                    print("Exception when calling DefaultAPI --> gifs_search_get: %s\n" % e)
                return
            else:
                movie_embed = create_movie_embed(movie_name, year)
                if (movie_embed == None or len(movie_embed) == 0):
                    await ctx.send('Hmm...not sure if that movie exists in the TMDB Database. Check your spelling of the title and make sure you\'re using quotes!')
                    return

                for entry in selections:
                    # user made a selection before, head sloth is overwriting
                    if entry[0] == user:
                        entry[1] = movie_embed
                        await ctx.send(f'{author} changed their mind! They selected....{movie_embed.title}')
                        await ctx.send(embed=movie_embed)
                        return

                # user didn't make a selection yet
                selections.append([user, movie_embed, False])
                selections_db.append([user, movie_embed.to_dict(), False])
                print(selections_db)
                await ctx.send(f'{author} has selected....{movie_embed.title} for {user}! Dictatorship!')
                await ctx.send(embed=movie_embed)
                return
        
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
        selections_db.append([author, movie_embed.to_dict(), False])
        await ctx.send(f'{author} has selected....{movie_embed.title}')
        await ctx.send(embed=movie_embed)

        print(selections_db)
        return
            
    @commands.command()
    async def get_menu(self, ctx):
        if len(selections) == 0:
            try:
                api_response = giphy_api_instance.gifs_search_get(GIPHY_KEY, limit=1, rating='g', q='boring')
                embedded_gif = discord.Embed(description='Uh oh! Looks like your movie list is empty! How boring...')
                embedded_gif.set_image(url=api_response.data[0].images.downsized_medium.url)
                await ctx.send(embed=embedded_gif)
                return
            except ApiException as e:
                print("Exception when calling DefaultAPI --> gifs_search_get: %s\n" % e)

        await ctx.send("Here's the menu!")
        for selection in selections:
            if (not selection[2]):
                await ctx.send(embed=selection[1])
    
    @commands.command()
    async def random_choice(self, ctx):
        if len(selections) == 0:
            try:
                api_response = giphy_api_instance.gifs_search_get(GIPHY_KEY, limit=1, rating='g', q='picard facepalm')
                embedded_gif = discord.Embed(description='How tf am I supposed to randomly pick if your list is empty?')
                embedded_gif.set_image(url=str(api_response.data[0].images.downsized_medium.url))
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
        global session_movie
        session_movie = random_choice[1]
        print(session_movie)
        return

    @commands.command()
    async def clear(self, ctx):
        roles = ctx.author.roles
        is_head_sloth = False
        for role in roles:
            if role.name == 'Head Sloth':
                is_head_sloth = True
                break

        if is_head_sloth and len(selections) != 0 and len(selections_db) != 0:
            selections.clear()
            selections_db.clear()
            await ctx.send("I cleared our session data! Can't wait for the next session!")
        elif not is_head_sloth:
            try:
                api_response = giphy_api_instance.gifs_search_get(GIPHY_KEY, limit=1, rating='g', q='dikembe mutombo finger wag')
                embedded_gif = discord.Embed(description='Oops! Someone\'s being a bit naughty! This feature isn\'t for you!')
                embedded_gif.set_image(url=api_response.data[0].images.downsized_medium.url)
                await ctx.send(embed=embedded_gif)
            except ApiException as e:
                print("Exception when calling DefaultAPI --> gifs_search_get: %s\n" % e)
        else:
            await ctx.send("Current session is already empty...")


def setup(bot):
    bot.add_cog(Movies(bot))