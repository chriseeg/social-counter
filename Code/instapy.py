from __future__ import print_function

from InstagramAPI import InstagramAPI
from threading import Thread
import time, json, os, re, requests, numpy, ciso8601
from datetime import datetime

#trying to solve max connection problem
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

#for communication with splitflapdisplay
import serial
import serial.tools.list_ports
from splitflap import splitflap

import mongoDB_functions as mf

def run():

    i = 0
    #with splitflap("/dev/ttyACM0") as s:
    while True:
        print("#"*40+"\nRound %s"%(i))
        starttime = time.time()

        if i%1000 == 0:
            #crawling user feed all over again. API Login required
            #print("Getting user feed")
            user_feed = insta_get_feed(insta_user_id)
            print("Getting rid of extra data")
            user_feed = keep_only_interesting_data_from_feed(user_feed)
            mf.write_insta_posts_to_mongodb(db_collection, user_feed)
            print(mf.get_total_post_counts(db_collection))
            #print("\n###"*5+"This is the user feed"+"\n###"*5)
            #print(user_feed)
            i+=1

        if i%50 == 0:
            post_list = mf.last_insta_posts_by_days(db_collection, 28)
            scrape_stats(db_collection, post_list)
            
            print("Posts of the last 28 days updated")
            print(mf.get_total_post_counts(db_collection))
            
        if i%10 == 0:
            post_list = mf.last_insta_posts_by_days(db_collection, 14)
            scrape_stats(db_collection, post_list)
            print("Posts of the last 14 days updated")
            print(mf.get_total_post_counts(db_collection))
        else:
            post_list = mf.last_insta_posts_by_posts(db_collection, 2)
            scrape_stats(db_collection, post_list)
            print(mf.get_total_post_counts(db_collection))
            

        print("Counting Likes and Comments")
        #likes_comments = count_likes_and_comments_from_user_feed(user_feed)
        likes = str(mf.get_total_post_counts(db_collection)[0])
        
        #aufbereitung der zahl muss noch optimiert werden
        if len(likes)<8:
            likes = " "*(8-len(likes))+likes
        
        #comments = likes_comments[1]
        endtime = time.time()
        print("This took %0.2f seconds" %(endtime-starttime))
        
        i += 1
        print('Going to {}'.format(likes))
        #when spolitflap connected send to splitflap
        #status = s.set_text(str(likes))
        time.sleep(1)
        #update_likes_comments_from_user_feed(new_user_feed)


# Import config and set global variables
def load_config(filepath):
    dirname = os.path.dirname(__file__) + "/" + filepath
    
    #wenn auf pi dann folgende zeile aktivieren und darüberliegende auskommentieren
    #dirname = filepath
    with open(dirname) as json_config_file:
        config = json.load(json_config_file)
    insta_username = config["insta_username"]
    insta_password = config["insta_password"]
    print("Configuration set")
    return insta_username, insta_password
    
# Initialize api
def insta_initialize(api_username, password):
    insta_api = InstagramAPI(api_username,password)
    insta_api.login()
    print("Api initialized for {}".format(api_username))
    return insta_api

# Retrieve user id for username 
def insta_get_user_id(username):
    _ = insta_api.searchUsername(username)
    result = insta_api.LastJson
    user_id = result['user']['pk'] # Get user ID
    return user_id

# Retrieve posts for user
def insta_get_feed(user_id):
    print("Getting insta_feed for " + str(user_id) )
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
        #time.sleep(0.5)
    print("Number of posts: {}".format(len(user_feed)))
    return user_feed

def insta_get_number_of_followers(user):
    print("Getting followers")
    url = 'https://www.instagram.com/' + user
    r = requests.get(url).text
    follower_count = re.search('"edge_followed_by":{"count":([0-9]+)}',r).group(1)
    return follower_count

def keep_only_interesting_data_from_feed(user_feed):
    simple_posts = []

    for post in user_feed:
        try:
            view_count = post["view_count"]
        except:
            view_count = 0

        taken_at = datetime.fromtimestamp(post["taken_at"]).strftime('%Y-%m-%d %H:%M:%S')

        clean_post = {
            "_id": post["id"],
            "platform": "instagram",
            "url": "https://www.instagram.com/p/" + post["code"],
            "username": post["user"]["username"],
            "taken_at": ciso8601.parse_datetime(str(taken_at)),
            "comment_count": post["comment_count"],
            "like_count": post["like_count"],
            "media_type": post["media_type"],
            "view_count": view_count
        }       
        
        simple_posts.append(clean_post)
    
    return simple_posts

def scrape_stats(collection, post_list):
    #print("\n#"*5+"#These are the single post batches a thread is runnig on\n"+"\n#"*5)
    #print(post)

    #setting up sessions for avoiding ssl problems
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)   
    
    insertion_count = 0
    update_count = 0

    for post in post_list:
               
        r = session.get(post["url"]).text
        #video posts need to be crawled differently
        
        try:
            #better use this because to many views result in abreviation
            view_count = int(re.search('"video_view_count":([0-9]+),',r).group(1))
        except:
            view_count = 0
        #Photos and carousels can be treated the same way
        post["like_count"] = int(re.search('"edge_media_preview_like":{"count":([0-9]+),',r).group(1))
        post["comment_count"] = int(re.search('"edge_media_to_parent_comment":{"count":([0-9]+),',r).group(1))
        post["view_count"] = view_count
    
        i,j = mf.write_insta_posts_to_mongodb(collection, post)
        insertion_count += i
        update_count += j

    print("Instagram Posts written to MongoDB " + collection.name + ": {} inserted, {} updated".format(insertion_count, update_count))

    return

if __name__ == '__main__':
    # Initialization
    target_username = "fimbim"
    number_of_threads = 1

    insta_username, insta_password = load_config("config.json")
    insta_api = insta_initialize(insta_username, insta_password)
    insta_user_id = insta_get_user_id(target_username)
    
    DB = mf.initialize_db()

    db_collection = DB.collection
    
    run()