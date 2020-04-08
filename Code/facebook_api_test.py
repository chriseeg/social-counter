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

def fb_initialize():
    fb_app_id, fb_app_secret, fb_access_token = load_config("config.json")
    FacebookAdsApi.init(fb_app_id, fb_app_secret, fb_access_token)
    print("Facebook Api initialized")
    return fb_access_token

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

def get_fb_page_token(fb_target_page_id):
    url = "https://graph.facebook.com/v6.0/" + fb_target_page_id
    params = {"fields" : "page_token", "access_token" : fb_access_token}
    r = requests.get(url = url, params = params).json()
    print(r)
    page_token = r["page_token"]
    
    return page_token

################################################################

def fb_get_api_feed(fb_target_page_id, limit):
    if limit == None:
        limit = 100000
    print("Getting facebook feed")
    fb_page = Page(fb_target_page_id)

    #fields = ["id","permalink_url","created_time","from","comments.summary(true)","likes.summary(true)"]
    fields = ["id", "permalink_url", "created_time", "from"]
    page_token = get_fb_page_token(fb_target_page_id)
    fb_feed = fb_page.get_feed(fields=fields, params={"limit":limit})
    fb_post_list = list(fb_feed)
    print("Retrieved {} posts".format(len(fb_post_list)))
    return fb_post_list, page_token

def fb_get_page_metrics():
    #TODO:

    # unused!
    # params = {
    #     "metric": ['post_reactions_by_type_total', "post_impressions", "post_clicks"],
    #     "period": 'lifetime',
    #     "show_description_from_api_doc": True
    # }
    return True

################################################################

def convert_fb_posts(posts, page_token):
    input_type = list
    if type(posts) is not list:
        posts = [posts]
        input_type = dict
    
    converted_posts = []
    for post in posts:
        target_user_id = post["id"].split("_")[0]
        new_post = {}

        try:
            post_creator_id = post["from"]["id"]
        except:
            continue  # drop post if creator can't be identified

        media_type = re.search(
            r"([0-9]{15,16}){0,1}\/([a-z]+)\/([0-9]{15,16})\/", post["permalink_url"]).group(2)

        if media_type == "events":
            continue

        if post_creator_id == target_user_id:  # check if it is not a post from another user
            new_post["_id"] = post["id"]
            new_post["platform"] = "facebook"
            new_post["url"] = post["permalink_url"]
            new_post["username"] = page_token
            new_post["taken_at"] = ciso8601.parse_datetime(
                post["created_time"])
            new_post["like_count"] = 0
            new_post["comment_count"] = 0
            new_post["notes"] = 0
            new_post["media_type"] = media_type
            converted_posts.append(new_post)

    if input_type is list:
        return converted_posts
    else:
        return converted_posts[0]

def scrape_write_fb_posts(posts, collection):
    # Scrapes one or multiple facebook posts and writes it to mongoDB
    print("Scraping and writing facebook posts")

    input_type = list
    if type(posts) is not list:
        posts = [posts]
        input_type = dict

    scraped_posts = []

    for post in posts:
        post["like_count"], post["comment_count"], post["notes"] = scrape_fb_likes_comments(post["url"])
        scraped_posts.append(post)

        mf.write_fb_posts_to_mongodb(collection,post)

    if input_type is list:
        return scraped_posts
    else:
        return scraped_posts[0]

def scrape_fb_likes_comments(url):
    regex_post_id = re.search(
        r"([0-9]{15,16}){0,1}\/([a-z]+)\/([0-9]{15,16})\/", url)
    post_id = regex_post_id.group(3)

    re_comment_string = r'subscription_target_id:"' + post_id + \
        r'",owning_profile:{__typename:"Page",id:"[0-9]+"},num_localized_comment_orderings:[0-9]+,comment_count:{total_count:([0-9]+)}'

    r = requests.get(url).text
    error_note = ""

    try:
        reference_id = re.findall(r'top_level_post_id.([0-9]+)', r)[0]
        re_like_string = r'share_fbid:"' + reference_id + r'",reactors:{count:([0-9]+)'
        #print(reference_id)
        if reference_id == post_id:
            like_count = int(re.search(re_like_string, r).group(1))
            comment_count = int(re.search(re_comment_string, r).group(1))
            #print("solution 1")
        else:
            try:
                re_like_string2 = r'share_fbid:"' + reference_id + r'",reactors:{count:([0-9]+)'
                re_comment_string2 = r'subscription_target_id:"' + reference_id + \
                    r'",owning_profile:{__typename:"Page",id:"[0-9]+"},num_localized_comment_orderings:[0-9]+,comment_count:{total_count:([0-9]+)}'

                like_count = int(re.search(re_like_string2, r).group(1))
                comment_count = int(re.search(re_comment_string2, r).group(1))
                #print("solution2 {}".format(url))
            except:
                print("yo {}".format(url))
                
                raise Exception("not so good")
    except:
        try:
            re_like_string3 = r'likecount:([0-9]+)'
            re_comment_string3 = r'commentcount:([0-9]+)'

            like_count = int(re.search(re_like_string3, r).group(1))
            comment_count = int(re.search(re_comment_string3, r).group(1))
            #print("solution 3 {}".format(url)")
        except:
            like_count = 0
            comment_count = 0
            print("Could not scrape facebook likes/comments from {}".format(url))
            open("problem_posts/problem_post {}.html".format(post_id), "w").write(r)
            error_note = "like + comment scraping error"

    return (like_count, comment_count, error_note)

################################################################

def scrape_recent_fb_posts(collection, no_of_days):
    # read recent posts from mongoDB and get collect/update counts
    recent_posts = mf.last_fb_posts_by_days(collection, no_of_days)
    scrape_write_fb_posts(recent_posts,collection)
    return True

def scrape_recent_x_fb_posts(collection, no_of_posts):
    # read recent posts from mongoDB and get collect/update counts
    recent_posts = mf.last_fb_posts_by_posts(collection, no_of_posts)
    scrape_write_fb_posts(recent_posts,collection)
    return True

def scrape_all_fb_posts(collection):
    # read all posts from mongoDB and get collect/update counts
    return scrape_recent_fb_posts(collection,10000)

def scrape_fb_feed(collection,fb_target_page_id,limit=None):
    # get feed and scrape posts and load to mongodb
    fb_post_list, page_token = fb_get_api_feed(fb_target_page_id,limit)
    converted_posts = convert_fb_posts(fb_post_list[:limit],page_token)
    scrape_write_fb_posts(converted_posts,collection)
    return True

################################################################

# params = {
#     "metric": ['post_reactions_by_type_total', "post_impressions", "post_clicks"],
#     "period": 'lifetime',
#     "show_description_from_api_doc": True
# }



fb_access_token = fb_initialize()

DB = mf.initialize_db()
post_col = mf.initialize_posts_collection(DB,True)

fb_target_page_id = "751183738294559"   # wne

scrape_fb_feed(post_col,fb_target_page_id,10)

print(mf.get_total_post_counts(post_col, True, True, "2009-12-31"))
