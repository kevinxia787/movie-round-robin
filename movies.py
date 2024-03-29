import os

import discord
import random
import giphy_client
import tmdbsimple as tmdb
import re
import json
import boto3
import DiscordUtils

from discord.ext import commands
from dotenv import load_dotenv
from giphy_client.rest import ApiException
from botocore.exceptions import ClientError
from mongodb_util import update_current_movie
from mongodb_util import get_movie_menu
from mongodb_util import add_user_selection
from mongodb_util import update_user_selection
from mongodb_util import add_movie_to_watched_list
from mongodb_util import get_movie_watched_list
from mongodb_util import get_current_selected_movie
from mongodb_util import get_threesome_watched_list
from mongodb_util import add_movie_threesome_menu
from mongodb_util import add_movie_to_threesome_watched_list
from mongodb_util import delete_threesome_menu_movies
from mongodb_util import get_threesome_menu
from mongodb_util import update_current_movie_threesome
from mongodb_util import get_current_selected_movie_threesome
load_dotenv()

GIPHY_KEY = os.getenv('GIPHY_API_KEY')
TMDB_KEY = os.getenv('TMDB_API_KEY')

tmdb.API_KEY = TMDB_KEY

giphy_api_instance = giphy_client.DefaultApi()
session_movie = None

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
    print(json.dumps(embedded_movie.to_dict()))
    return embedded_movie

class Movies(commands.Cog):
    def __init__(self, bot, threesome):
        self.bot = bot
        self.threesome = False

    @commands.command()
    async def admin_select(self, ctx, movie_name, year, user):

        if self.threesome:
            await ctx.send(f'Threesome in progress. Ssssshhhh!')
            return

        author = str(ctx.author)
        roles = ctx.author.roles
        author = author.split('#')[0]
       
        menu_list = get_movie_menu()
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
            
            for movie_data_entry in menu_list:
                if movie_data_entry['user'] == user:
                    new_selection = movie_embed.to_dict()
                    new_selection['user'] = user
                    update_user_selection(user, new_selection, self.threesome)
                    await ctx.send(f'{author} changed {user}\'s mind! They selected....{movie_embed.title} for {user}.')
                    await ctx.send(embed=movie_embed)
                    return

            # user didn't make a selection yet
            movie_dict = movie_embed.to_dict()
            # append user to dict
            movie_dict['user'] = user
            add_user_selection(user, movie_dict)
            await ctx.send(f'{author} has selected....{movie_embed.title} for {user}! Dictatorship!')
            await ctx.send(embed=movie_embed)
            return
        
    @commands.command()
    async def select(self, ctx, movie_name, year : str = None):

        if self.threesome:
            await ctx.send(f'Threesome in progress. Ssssshhhh!')
            return

        author = str(ctx.author)
        roles = ctx.author.roles
        author = author.split('#')[0]

        menu_list = get_movie_menu()
        # create movie embed object
        movie_embed = create_movie_embed(movie_name, year)

        if (movie_embed == None):
            await ctx.send('Hmm...not sure if that movie exists in the TMDB Database. Check your spelling of the title and make sure you\'re using quotes!')
            return 

        for movie_data_entry in menu_list:
            if movie_data_entry['user'] == author:
                new_selection = movie_embed.to_dict()
                new_selection['user'] = author
                update_user_selection(author, new_selection, self.threesome)
                await ctx.send(f'{author} changed their mind! They selected....{movie_embed.title}')
                await ctx.send(embed=movie_embed)
                return

        # user has not made a selection, add new entry
        movie_dict = movie_embed.to_dict()
        # append user to dict
        movie_dict['user'] = author
        add_user_selection(author, movie_dict)
        await ctx.send(f'{author} has selected....{movie_embed.title}')
        await ctx.send(embed=movie_embed)
        return
            
    @commands.command()
    async def get_menu(self, ctx):

        if self.threesome:
            await ctx.send(f'Threesome in progress. Ssssshhhh!')
            return

        menu_list = get_movie_menu()
        if len(menu_list) == 0:
            try:
                api_response = giphy_api_instance.gifs_search_get(GIPHY_KEY, limit=1, rating='g', q='boring')
                embedded_gif = discord.Embed(description='Uh oh! Looks like your movie list is empty! How boring...')
                embedded_gif.set_image(url=api_response.data[0].images.downsized_medium.url)
                await ctx.send(embed=embedded_gif)
                return
            except ApiException as e:
                print("Exception when calling DefaultAPI --> gifs_search_get: %s\n" % e)

        await ctx.send("Here's the menu!")
        for entry in menu_list:
            movie_embed_obj = discord.Embed(title=entry["title"], description=entry["description"])
            movie_embed_obj.set_image(url=entry["image"]["url"])
            await ctx.send(embed=movie_embed_obj)
    
    @commands.command()
    async def random_choice(self, ctx):
        if self.threesome:
            await ctx.send(f'Threesome in progress. Ssssshhhh!')
            return

        # mongodb call
        menu_list = get_movie_menu()

        if len(menu_list) == 0:
            try:
                api_response = giphy_api_instance.gifs_search_get(GIPHY_KEY, limit=1, rating='g', q='picard facepalm')
                embedded_gif = discord.Embed(description='How tf am I supposed to randomly pick a movie if your list is empty?')
                embedded_gif.set_image(url=str(api_response.data[0].images.downsized_medium.url))
                await ctx.send(embed=embedded_gif)
                return
            except ApiException as e:
                print("Exception when calling DefaultAPI --> gifs_search_get: %s\n" % e)
        random_choice = random.choice(menu_list)
        random_choice_embed = discord.Embed(title=random_choice["title"], description=random_choice["description"])
        random_choice_embed.set_image(url=random_choice["image"]["url"])

        # mongodb call
        update_current_movie(random_choice)

        await ctx.send(f'Grab your popcorn folks...we\'re watching:')
        await ctx.send(embed=random_choice_embed)
        return

    @commands.command()
    async def finish(self, ctx):

        if self.threesome:
            await ctx.send(f'Threesome in progress. Ssssshhhh!')
            return

        # get data here, if movieMenu is empty, tell channel to pick new movies
        selected_movie = get_current_selected_movie()

        if (selected_movie == None):
            await ctx.send("Looks like you haven't randomly selected something to watch yet. Do that first, will ya?")
            return

        # call method to move watched movie to watchedMovies list, remove it from menu
        # update_movie_list_to_watched_dynamodb(1, selected_movie, )
        
        add_movie_to_watched_list(selected_movie)

        
        watched_movie_embed = discord.Embed(title=selected_movie["title"], description=selected_movie["description"])
        watched_movie_embed.set_image(url=selected_movie["image"]["url"])
        await ctx.send("What did y'all think of the movie? Rate it by reacting to the following message, out of 10!")
        await ctx.send(embed=watched_movie_embed)

        movie_menu = get_movie_menu()

        if (len(movie_menu) == 0):
            await ctx.send("It's time for some new movies! Pick 'em and get these showings on the road!")

    @commands.command()
    async def watched_list(self, ctx):
        movie_watched_list = get_movie_watched_list()
        embeds = []
        paginator = DiscordUtils.Pagination.CustomEmbedPaginator(ctx)
        paginator.add_reaction('⏮️', "first")
        paginator.add_reaction('⏪', "back")
        #paginator.add_reaction('🔐', "lock")
        paginator.add_reaction('⏩', "next")
        paginator.add_reaction('⏭️', "last")
        for entry in movie_watched_list:
            movie_embed_obj = discord.Embed(title=entry["title"], description=entry["description"])
            movie_embed_obj.set_image(url=entry["image"]["url"])
            embeds.append(movie_embed_obj)
        await paginator.run(embeds)    
        return

    @commands.command()
    async def start_threesome(self, ctx):
        if self.threesome:
            await ctx.send("Threesome in progress. Ssssshhhh!")
            return
        
        self.threesome = True
        await ctx.send("Threesome started! Ooh austyn u so sec see")
        return
    
    @commands.command()
    async def select_threesome(self, ctx, movie_name, year : str = None):
        if not self.threesome:
            await ctx.send(f'Threesome not started!')
            return
        
        author = str(ctx.author)
        roles = ctx.author.roles
        author = author.split('#')[0]

        menu_list = get_threesome_menu()
        movie_embed = create_movie_embed(movie_name, year)

        if (movie_embed == None):
            await ctx.send('Hmm...not sure if that movie exists in the TMDB Database. Check your spelling of the title and make sure you\'re using quotes!')
            return 

        for movie_data_entry in menu_list:
            if movie_data_entry['user'] == author:
                new_selection = movie_embed.to_dict()
                new_selection['user'] = author
                update_user_selection(author, new_selection)
                await ctx.send(f'{author} changed their mind! They selected....{movie_embed.title}')
                await ctx.send(embed=movie_embed)
                return
        
        # user has not made a selection, add new entry
        movie_dict = movie_embed.to_dict()
        # append user to dict
        movie_dict['user'] = author
        add_movie_threesome_menu(author, movie_dict)
        await ctx.send(f'{author} has selected....{movie_embed.title} for the threesome.')
        await ctx.send(embed=movie_embed)
        return

    @commands.command()
    async def random_choice_threesome(self, ctx):
        if not self.threesome:
            await ctx.send(f'Threesome not started yet!')
            return
        
        menu_list = get_threesome_menu()
        if len(menu_list) == 0:
            await ctx.send("The threesome movie menu is empty, pick some movies!!")
            return
        random_choice = random.choice(menu_list)
        random_choice_embed = discord.Embed(title=random_choice["title"], description=random_choice["description"])
        random_choice_embed.set_image(url=random_choice["image"]["url"])

         # mongodb call
        update_current_movie_threesome(random_choice)

        await ctx.send(f'Grab your popcorn folks...we\'re watching:')
        await ctx.send(embed=random_choice_embed)
        return

    @commands.command()
    async def finish_threesome(self, ctx):
        if not self.threesome:
            await ctx.send("Threesome not started yet!")
            return

        curr_threesome_movie = get_current_selected_movie_threesome()

        add_movie_to_threesome_watched_list(curr_threesome_movie)

        self.threesome = False

        await ctx.send("Threesome completed. ")

        watched_movie_embed = discord.Embed(title=curr_threesome_movie["title"], description=curr_threesome_movie["description"])
        watched_movie_embed.set_image(url=curr_threesome_movie["image"]["url"])
        await ctx.send("What did y'all think of the movie? Rate it by reacting to the following message, out of 10!")
        await ctx.send(embed=watched_movie_embed)

    @commands.command()
    async def watched_list_threesome(self, ctx):
        
        movie_watched_list = get_threesome_watched_list()
        if len(movie_watched_list) == 0:
            await ctx.send("No movies in threesome watched list!")
            return
        embeds = []
        paginator = DiscordUtils.Pagination.CustomEmbedPaginator(ctx)
        paginator.add_reaction('⏮️', "first")
        paginator.add_reaction('⏪', "back")
        #paginator.add_reaction('🔐', "lock")
        paginator.add_reaction('⏩', "next")
        paginator.add_reaction('⏭️', "last")
        print(movie_watched_list)
        for entry in movie_watched_list:
            movie_embed_obj = discord.Embed(title=entry["title"], description=entry["description"])
            movie_embed_obj.set_image(url=entry["image"]["url"])
            embeds.append(movie_embed_obj)
        await paginator.run(embeds)    
        return
def setup(bot):
    bot.add_cog(Movies(bot, False))