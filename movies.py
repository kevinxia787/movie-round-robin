import os

import discord
import random
import giphy_client
import tmdbsimple as tmdb
import re
import json
import boto3

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

load_dotenv()

GIPHY_KEY = os.getenv('GIPHY_API_KEY')
TMDB_KEY = os.getenv('TMDB_API_KEY')

tmdb.API_KEY = TMDB_KEY

giphy_api_instance = giphy_client.DefaultApi()
session_movie = None

def update_watch_movie(id, selected_movie, dynamodb=None):
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('discord-cinephile-db')
    response = table.update_item(
        Key={'id': id},
        UpdateExpression="set selectedMovie = :sm",
        ExpressionAttributeValues={
            ':sm': selected_movie
        },
        ReturnValues="UPDATED_NEW"
    )
    return response

def get_movie_list_dynamodb(id, dynamodb=None):
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('discord-cinephile-db')
    try:
        response = table.get_item(Key={'id': id})
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        return response['Item']

def add_movie_to_list_dynamodb(id, selected_movie, dynamodb=None):
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb')
    
    table = dynamodb.Table('discord-cinephile-db')
    response = table.update_item(
        Key={'id': id},
        UpdateExpression="set movieMenu = list_append(movieMenu, :wm)",
        ExpressionAttributeValues={
            ':wm': [selected_movie]
        },
        ReturnValues="UPDATED_NEW"
    )
    return response

def update_movie_list_to_watched_dynamodb(id, watched_movie, dynamodb=None):
    
    data = get_movie_list_dynamodb(id, )
    # watched_movie = data['selectedMovie']
    watched_movie_index = data['movieMenu'].index(watched_movie)

    if not dynamodb:
        dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('discord-cinephile-db')
    response = table.update_item(
        Key={'id': id},
        UpdateExpression="set watchedMovies = list_append(watchedMovies, :wm)",
        ExpressionAttributeValues={
            ':wm': [watched_movie]
        },
        ReturnValues="UPDATED_NEW"
    )
    response = table.update_item(
        Key={'id': id},
        UpdateExpression="remove movieMenu[" + str(watched_movie_index) + "]",
        ReturnValues="UPDATED_NEW"
    )

    
    return response

def replace_movie_list_dynamodb(id, prev_movie, new_movie, dynamodb=None):
    data = get_movie_list_dynamodb(id, )
    watched_movie_index = data['movieMenu'].index(prev_movie)

    if not dynamodb:
        dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('discord-cinephile-db')
    response = table.update_item(
        Key={'id': id},
        UpdateExpression="set movieMenu[" + str(watched_movie_index) + "] = :nm",
        ExpressionAttributeValues={
            ':nm': new_movie
        },
        ReturnValues="UPDATED_NEW"
    )
    return response

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
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def arise(self, ctx):
        await ctx.send("I have arisen.")

    @commands.command()
    async def admin_select(self, ctx, movie_name, year, user):
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
                    update_user_selection(user, new_selection)
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
                update_user_selection(author, new_selection)
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



def setup(bot):
    bot.add_cog(Movies(bot))