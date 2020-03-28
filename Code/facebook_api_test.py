#!pip3 install facebook_business

from facebook_business.adobjects.page import Page
from facebook_business.adobjects.pagepost import PagePost
from facebook_business.api import FacebookAdsApi
import mongoDB_functions as mf
import requests
import pymongo
import ciso8601
import json
import re
import os


def enrich_format_fb_posts(posts):
    # Converts one or multiple facebook posts for mongoDB
    print("Enriching facebook posts")

    input_type = list
    if type(posts) is not list:
        posts = [posts]
        input_type = dict

    enriched_posts = []

    for post in posts:
        #print(post)
        target_user_id = post["id"].split("_")[0]
        new_post = {}
        try:
            post_creator_id = post["from"]["id"]
        except:
            continue

        if post_creator_id == target_user_id:  # check if it is not a post from another user
            new_post["_id"] = post["id"]
            new_post["platform"] = "facebook"
            new_post["url"] = post["permalink_url"]
            new_post["username"] = post["from"]["name"]
            # TODO: Create function to format from "2020-03-13T19:19:23+0000" to insta time format
            new_post["taken_at"] = ciso8601.parse_datetime(post["created_time"])
            new_post["like_count"], new_post["comment_count"] = scrape_fb_likes_comments(
                post["permalink_url"])
            enriched_posts.append(new_post)

    if input_type is list:
        return enriched_posts
    else:
        return enriched_posts[0]


def scrape_fb_likes_comments(url):
    post_id = url.split("posts")[-1].split("/")[1]
    regex_like_string = r'share_fbid:"' + \
        post_id + r'",reactors:{count:([0-9]+)'
    regex_comment_string = r'comment_count:{total_count:([0-9]+)},.+' + \
        post_id + r'"'
    r = requests.get(url).text
    try:
        like_count = int(re.search(regex_like_string, r).group(1))
    except:
        print("Could not scrape facebook likes from {}".format(url))
        like_count = 0
    try:
        comment_count = int(re.search(regex_comment_string, r).group(1))
    except:
        print("Could not scrape facebook comments from {}".format(url))
        comment_count = 0

    # open("demo_r_file.txt","w").write(requests.get(urls[1]).text)
    return (like_count, comment_count)


def load_config(filepath):
    dirname = os.path.dirname(__file__) + "/" + filepath
    #dirname = filepath
    with open(dirname) as json_config_file:
        config = json.load(json_config_file)
    fb_app_id = config["fb_app_id"]
    fb_app_secret = config["fb_app_secret"]
    fb_access_token = config["fb_access_token"]
    print("Configuration set")
    return fb_app_id, fb_app_secret, fb_access_token


def get_page_metrics():
    # unused!
    # params = {
    #     "metric": ['post_reactions_by_type_total', "post_impressions", "post_clicks"],
    #     "period": 'lifetime',
    #     "show_description_from_api_doc": True
    # }
    return True


def fb_get_feed(fb_target_page_id):
    print("Getting facebook feed")
    fb_page = Page(fb_target_page_id)

    #fields = ["id","permalink_url","created_time","from","comments.summary(true)","likes.summary(true)"]
    fields = ["id", "permalink_url", "created_time", "from"]
    fb_feed = fb_page.get_feed(fields=fields, params={})  # "limit":100})
    fb_post_list = list(fb_feed)
    return fb_post_list

def scrape_recent_fb_posts(collection, no_of_days):
    # read recent posts from mongoDB and get collect/update counts


# params = {
#     "metric": ['post_reactions_by_type_total', "post_impressions", "post_clicks"],
#     "period": 'lifetime',
#     "show_description_from_api_doc": True
# }

fb_app_id, fb_app_secret, fb_access_token = load_config("config.json")
FacebookAdsApi.init(fb_app_id, fb_app_secret, fb_access_token)
DB = mf.initialize_db()

fb_target_page_id = "751183738294559"   # wne

fb_post_list = fb_get_feed(fb_target_page_id)
print(len(fb_post_list))
enriched_posts = enrich_format_fb_posts(fb_post_list)
mf.write_fb_posts_to_mongodb(enriched_posts, DB.posts)
print(mf.get_total_post_counts(DB.posts,True,True,"2019-12-31"))