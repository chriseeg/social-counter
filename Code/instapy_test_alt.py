from mongodb_functions import *
from InstagramAPI import InstagramAPI
from threading import Thread
import time
import json
import os
import re
import requests
import numpy


# Import config and set global variables
def load_config(filepath):
    dirname = os.path.dirname(__file__) + "/" + filepath
    #dirname = filepath
    with open(dirname) as json_config_file:
        config = json.load(json_config_file)
    insta_username = config["insta_username"]
    insta_password = config["insta_password"]
    print("Configuration set")
    return insta_username, insta_password

# Initialize api


def insta_initialize(api_username, password):
    insta_api = InstagramAPI(api_username, password)
    insta_api.login()
    print("Api initialized for {}".format(api_username))
    return insta_api

# Retrieve user id for username


def insta_get_user_id(username):
    _ = insta_api.searchUsername(username)
    result = insta_api.LastJson
    user_id = result['user']['pk']  # Get user ID
    return user_id

# Retrieve posts for user


def insta_get_feed(user_id):
    print("Getting insta_feed for " + str(user_id))
    max_id = ""
    user_feed = []
    more_available = True
    # read batch of posts and continue while more posts are available
    while more_available:
        _ = insta_api.getUserFeed(user_id, max_id)
        user_feed += insta_api.LastJson["items"]
        if not insta_api.LastJson["more_available"]:
            more_available = False
            break
        max_id = insta_api.LastJson["next_max_id"]
        # time.sleep(0.5)
    print("Number of posts: {}".format(len(user_feed)))
    return user_feed


def insta_count_likes_and_comments(user_id):
    print("Getting likes and comments")

    like_count = 0
    comment_count = 0
    user_feed = insta_get_feed(user_id)
    threads = []
    urls = [insta_get_media_url(post["id"].split("_")[0])
            for post in user_feed]
    url_batches = numpy.array_split(numpy.array(
        urls), number_of_threads)  # split into batches
    result = [{} for x in url_batches]
    for i, urls in enumerate(url_batches):
        process = Thread(target=scrape_likes_comments, args=[urls, result, i])
        process.start()
        threads.append(process)
    for process in threads:
        process.join()

    like_count = sum([x[0] for x in result])
    comment_count = sum([x[1] for x in result])
    return like_count, comment_count


def scrape_likes_comments(urls, result, index):
    like_count = 0
    comment_count = 0
    for url in urls:
        r = requests.get(url).text
        like_count += int(
            re.search('"userInteractionCount":"([0-9]+)"', r).group(1))
        comment_count += int(
            re.search('"commentCount":"([0-9]+)"', r).group(1))
    result[index] = [like_count, comment_count]
    return True


def insta_get_number_of_followers(user):
    print("Getting followers")
    url = 'https://www.instagram.com/' + user
    r = requests.get(url).text
    follower_count = re.search(
        '"edge_followed_by":{"count":([0-9]+)}', r).group(1)
    return follower_count


def insta_get_media_url(media_id):
    media_id = int(media_id)
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    shortened_id = ''
    while media_id > 0:
        remainder = media_id % 64
        # dual conversion sign gets the right ID for new posts
        media_id = (media_id - remainder) // 64
        # remainder should be casted as an integer to avoid a type error.
        shortened_id = alphabet[int(remainder)] + shortened_id

    return 'https://instagram.com/p/' + shortened_id + '/'


# Initialization
target_username = "weihnachtenneuerleben"
number_of_threads = 300

insta_username, insta_password = load_config("config_insta_count.json")
insta_api = insta_initialize(insta_username, insta_password)
insta_user_id = insta_get_user_id(target_username)

feed = insta_get_feed(insta_user_id)

# print(feed)
# print(insta_count_likes_and_comments(insta_user_id))
# print(insta_get_number_of_followers(target_username))


################

db = initialize_db()
write_insta_posts_to_mongodb(feed, db.posts)
