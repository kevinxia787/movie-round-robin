import pymongo
from pymongo import MongoClient


client = MongoClient()

cinephile_db = client.cinephile

watched_movies = cinephile_db.watched_movies
movie_menu_collection = cinephile_db.movie_menu
current_movie = cinephile_db.current_movie
threesome_movies = cinephile_db.threesome_movies
threesome_menu = cinephile_db.threesome_menu
threesome_current_movie = cinephile_db.threesome_current_movie

def update_current_movie(selected_movie):
    # current movie should always be empty
    if (current_movie.find_one() != None):
        print("Overwrite protection on selected movie. Finish the movie night session!")
        return
    current_movie.insert_one(selected_movie)
    print("Inserted \'" + selected_movie["title"] + "\' into current movie collection.")

    movie_menu_collection.delete_one({"title": selected_movie["title"]})
    return

# get the current list of movies people want to see
def get_movie_menu():
    movie_menu = []
    movie_cursor = movie_menu_collection.find()
    for movie_doc in movie_cursor:
        movie_menu.append(movie_doc)
    return movie_menu

# add user's selection
def add_user_selection(user, movie):
    movie_menu_collection.insert_one(movie)
    print("Inserted \'" + movie["title"] + "\' into movie menu collection.")
    return
        
# update user's selection
def update_user_selection(user, movie, threesome):
    if threesome:
        threesome_menu.update_one(
            {"user": user},
            {"$set": {"image": movie["image"], "description": movie["description"], "title": movie["title"]}}
        )
    else:
        movie_menu_collection.update_one(
            {"user": user},
            {"$set": {"image": movie["image"], "description": movie["description"], "title": movie["title"]}}
        )
    print("Updated " + user + "\'s selection to " + movie["title"])
    return


# add currently selected movie to the watched movie master list
def add_movie_to_watched_list(movie):
    watched_movies.insert_one(movie)

    # delete the current movie watched 
    current_movie.delete_many({})

    print("Inserted: " + movie["title"] + " into the master list of watched movies.")
    return

def get_current_selected_movie():
    current_movie_document = current_movie.find_one()

    # remove the id (VERY rare case that another movie has same id in the movie master list, just to be safe)
    current_movie_document.pop('_id', None)

    return current_movie_document

def get_movie_watched_list():
    
    movie_watched_list = []
    cursor = watched_movies.find()
    for movie_doc in cursor:
        movie_watched_list.append(movie_doc)

    return movie_watched_list

def get_threesome_watched_list():
    threesome_watched_list = []
    cursor = threesome_movies.find()
    for movie_doc in cursor:
        threesome_watched_list = []
        threesome_watched_list.append(movie_doc)
    
    return threesome_watched_list

def get_threesome_menu():
    threesome = []
    movie_cursor = threesome_menu.find({})
    print(movie_cursor)
    for movie_doc in movie_cursor:
        print(movie_doc)
        threesome.append(movie_doc)
    return threesome

def add_movie_threesome_menu(user, movie):
    threesome_menu.insert_one(movie)
    print("Inserted \'" + movie["title"] + "\' into threesome movie menu collection.")
    return

def add_movie_to_threesome_watched_list(movie):
    threesome_movies.insert_one(movie)

    threesome_current_movie.delete_many({})
    print("Inserted: " + movie["title"] + " into the master list of threesome watched movies.")
    return

def delete_threesome_menu_movies():
    threesome_menu.delete_many({})
    print("Deleted all moves in threesome movie menu. ")
    return

def get_current_selected_movie_threesome():
    threesome_curr = threesome_current_movie.find_one()

    threesome_curr.pop('_id', None)

    return threesome_curr

def update_current_movie_threesome(selected_movie):
    if (threesome_current_movie.find_one() != None):
        print("Overwrite protection on selected movie. Finish the movie night session!")
        return
    
    threesome_current_movie.insert_one(selected_movie)

    delete_threesome_menu_movies()
    return