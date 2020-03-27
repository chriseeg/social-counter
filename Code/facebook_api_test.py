#!pip3 install facebook_business


from facebook_business.adobjects.page import Page
from facebook_business.adobjects.pagepost import PagePost
from facebook_business.api import FacebookAdsApi
import requests
import pymongo
import re


def initialize_db():
    print("MongoDB initialized")
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client.socialcounter_db
    return db


def write_insta_posts_to_mongodb(posts, collection, raw_values=False):
    # takes a list of instagram posts in original formatting and writes it into the mongoDB collection

    if type(posts) is not list:
        posts = [posts]

    if raw_values:
        collection.insert_many(posts)
        return posts

    clean_json_list = []
    new_ids = []
    for post in posts:
        try:
            view_count = post["view_count"]
        except:
            view_count = 0

        clean_json = {
            "_id": post["id"],
            "platform": "instagram",
            "url": "https://www.instagram.com/p/" + post["code"],
            "username": post["user"]["username"],
            "taken_at": post["taken_at"],
            "comment_count": post["comment_count"],
            "like_count": post["like_count"],
            "media_type": post["media_type"],
            "view_count": view_count
        }

        clean_json_list.append(clean_json)
        new_ids.append(post["id"])

    # delete all items that are in new_ids
    collection.delete_many({"_id": {"$in": new_ids}})
    collection.insert_many(clean_json_list)  # upload multiple items
    print("Instagram Posts written to MongoDB")
    return(clean_json_list)


def scrape_fb_likes_comments(url):
    post_id = url.split("posts")[-1].split("/")[1]
    regex_like_string = r'share_fbid:"' + \
        post_id + r'",reactors:{count:([0-9]+)'
    regex_comment_string = r'comment_count:{total_count:([0-9]+)},.+' + \
        post_id + r'"'
    r = requests.get(url).text
    like_count = int(re.search(regex_like_string, r).group(1))
    comment_count = int(re.search(regex_comment_string, r).group(1))
    # open("demo_r_file.txt","w").write(requests.get(urls[1]).text)
    return (like_count, comment_count)


my_app_id = '127335021929773'
my_app_secret = '7a67323c9c38771878a60c03934f8c38'
my_access_token = 'EAABzz36ZC5S0BAAMZAf4OG2ZC81QZAZBVMt4qUaZB5z7WWLeBnlgFCf5FjCVSqduW5q2bqwjlF5kT7NwID9v98Xnu7j5H1Qgqk3yxCzLzdYYomancm0N1N8sXAVV76r7yrJ0vRNQBT2nxG7ZCvpVOOJ0Q2pb3VYLZCNwJQXAmwi686utZCkicpOhHBXlrhH7SQKHDeCZBJO3T7oQZDZD'
FacebookAdsApi.init(my_app_id, my_app_secret, my_access_token)

fb_page_id = "751183738294559"  # wne
fb_page = Page(fb_page_id)

#fields = ["id","permalink_url","created_time","from","comments.summary(true)","likes.summary(true)"]
fields = ["id", "permalink_url", "created_time", "from"]
fb_feed = fb_page.get_feed(fields=fields, params={})  # "limit":100})
fb_post_list = list(fb_feed)


# params = {
#     "metric": ['post_reactions_by_type_total', "post_impressions", "post_clicks"],
#     "period": 'lifetime',
#     "show_description_from_api_doc": True
# }

def format_time(time):
    #TODO
    return time

def enrich_format_fb_post(post):
    user_id = post["id"].split("_")[0]
    if post["from"]["id"] == user_id:
        new_post["_id"] = post["id"]
        new_post["platform"] = "facebook"
        new_post["url"] = post["permalink_url"]
        new_post["username"] = post["from"]["name"]
        new_post["taken_at"] = format_time(post["created_time"]) #TODO: Create function to format from "2020-03-13T19:19:23+0000" to insta time format
        new_post["like_count"],new_post["comment_count"] = scrape_fb_likes_comments(post["permalink_url"])
        new_post[""]
        return new_post
    return False
    
def write_fb_posts_to_mongodb(posts,  collection, raw_values=False):
    # takes a list of enriched fb posts (or one post) and writes it into the mongoDB collection

    if type(posts) is not list:
        posts = [posts]

    if raw_values:
        collection.insert_many(posts)
        return posts

    new_ids = [p["_id"] for p in posts]

    # delete all items that are in new_ids
    #TODO replace by update one, if _id exists (on error)!!!
    collection.delete_many({"_id": {"$in": new_ids}})
    collection.insert_many(clean_json_list)  # upload multiple items

    print("Instagram Posts written to MongoDB")
    return(clean_json_list)

print(len(fb_post_list))
#print (fb_post_list)
for p in fb_post_list[0:5]:
    
    #likes = PagePost(post["id"]).get_insights(params = params)
    print(p["permalink_url"])
    p["likes"],p["comments"] = scrape_fb_likes_comments(p["permalink_url"])
    print(p)

#db = initialize_db()
#write_insta_posts_to_mongodb(fb_post_list,db.facebook_test,True)
