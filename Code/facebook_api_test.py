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


def fb_get_feed(fb_target_page_id):
    print("Getting facebook feed")
    fb_page = Page(fb_target_page_id)

    #fields = ["id","permalink_url","created_time","from","comments.summary(true)","likes.summary(true)"]
    fields = ["id", "permalink_url", "created_time", "from"]
    fb_feed = fb_page.get_feed(fields=fields, params={})  # "limit":100})
    fb_post_list = list(fb_feed)
    return fb_post_list


def fb_get_page_metrics():
    # unused!
    # params = {
    #     "metric": ['post_reactions_by_type_total', "post_impressions", "post_clicks"],
    #     "period": 'lifetime',
    #     "show_description_from_api_doc": True
    # }
    return True


def enrich_format_fb_posts(posts):
    # Converts one or multiple facebook posts for mongoDB
    #TODO: Instantly write post to mongoDB
    print("Enriching facebook posts")

    input_type = list
    if type(posts) is not list:
        posts = [posts]
        input_type = dict

    enriched_posts = []

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
            new_post["username"] = post["from"]["name"]
            new_post["taken_at"] = ciso8601.parse_datetime(
                post["created_time"])
            new_post["like_count"], new_post["comment_count"], new_post["notes"] = scrape_fb_likes_comments(
                post["permalink_url"])
            new_post["media_type"] = media_type
            enriched_posts.append(new_post)

    if input_type is list:
        return enriched_posts
    else:
        return enriched_posts[0]


def scrape_fb_likes_comments(url):
    regex_post_id = re.search(
        r"([0-9]{15,16}){0,1}\/([a-z]+)\/([0-9]{15,16})\/", url)
    post_id = regex_post_id.group(3)

    re_like_string = r'share_fbid:"([0-9]+)",reactors:{count:([0-9]+)'
    re_comment_string = r'subscription_target_id:"' + post_id + \
        r'",owning_profile:{__typename:"Page",id:"[0-9]+"},num_localized_comment_orderings:[0-9]+,comment_count:{total_count:([0-9]+)}'

    r = requests.get(url).text
    error_note = ""

    try:
        re_like_result = re.search(re_like_string, r)
        reference_id = re.findall(r'top_level_post_id.([0-9]+)', r)[0]
        #print(reference_id)
        if reference_id == post_id:
            like_count = int(re_like_result.group(2))
            comment_count = int(re.search(re_comment_string, r).group(1))
            #print("solution 1")
        else:
            try:
                re_like_string2 = r'share_fbid:"' + \
                    reference_id + r'",reactors:{count:([0-9]+)'
                re_comment_string2 = r'subscription_target_id:"' + reference_id + \
                    r'",owning_profile:{__typename:"Page",id:"[0-9]+"},num_localized_comment_orderings:[0-9]+,comment_count:{total_count:([0-9]+)}'

                like_count = int(re.search(re_like_string2, r).group(1))
                comment_count = int(re.search(re_comment_string2, r).group(1))
                print("solution2")
            except:
                print("yo")
                
                raise Exception("not so good")
    except:
        try:
            re_like_string3 = r'likecount:([0-9]+)'
            re_comment_string3 = r'commentcount:([0-9]+)'

            like_count = int(re.search(re_like_string3, r).group(1))
            comment_count = int(re.search(re_comment_string3, r).group(1))
            print("solution 3")
        except:
            like_count = 0
            comment_count = 0
            print("Could not scrape facebook likes/comments from {}".format(url))
            open("problem_posts/problem_post {}.html".format(post_id), "w").write(r)
            error_note = "like + comment scraping error"

    return (like_count, comment_count, error_note)


def scrape_recent_fb_posts(collection, no_of_days):
    # read recent posts from mongoDB and get collect/update counts
    return True

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
mf.write_fb_posts_to_mongodb(enriched_posts, DB.fb_test)
print(mf.get_total_post_counts(DB.fb_test, True, True, "2009-12-31"))
