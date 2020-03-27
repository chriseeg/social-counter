from InstagramAPI import InstagramAPI
from threading import Thread
import time
import json
import os
import re
import requests
import numpy
import ciso8601

# trying to solve max connection problem
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# for communication with splitflapdisplay
import serial
import serial.tools.list_ports
from splitflap import splitflap


def run():

    # Initialization
    target_username = "icf.karlsruhe"
    number_of_threads = 1

    insta_username, insta_password = load_config("config_insta_count.json")
    insta_api = insta_initialize(insta_username, insta_password)
    insta_user_id = insta_get_user_id(target_username)

    i = 0
    with splitflap("/dev/ttyACM0") as s:
        while True:
            print("#"*40+"\nRound %s" % (i))
            starttime = time.time()

            if i % 1000 == 0:
                # crawling user feed all over again. API Login required
                #print("Getting user feed")
                user_feed = insta_get_feed(insta_user_id)
                print("Getting rid of extra data")
                user_feed = keep_only_interesting_data_from_feed(user_feed)
                # print("\n###"*5+"This is the user feed"+"\n###"*5)
                # print(user_feed)
                i += 1

            if i % 50 == 0:
                user_feed = update_posts_in_last_x_days_in_user_feed(
                    user_feed, 28)

            if i % 10 == 0:
                user_feed = update_posts_in_last_x_days_in_user_feed(
                    user_feed, 14)

            else:
                # divide user feed in small batches for threading
                #url_batches = numpy.array_split(numpy.array(urls),number_of_threads)
                # using user feed to crawl post urls. No API login required
                user_feed = update_posts_in_last_x_days_in_user_feed(
                    user_feed, 7)
                # print("\n######"*5+"This is the new user feed"+"\n#####"*5)
                # print(user_feed)

            #startdate = "2020-03-13"
            #startdate = ciso8601.parse_datetime(startdate)
            # to get time in seconds:
            # startdate=int(time.mktime(ciso8601.parse_datetime(startdate).timetuple()))

            print("Counting Likes and Comments")
            #likes_comments = count_likes_and_comments_from_user_feed(user_feed)
            likes_comments = count_likes_and_comments_from_user_feed(user_feed)
            likes = str(likes_comments[0])

            # aufbereitung der zahl muss noch optimiert werden
            if len(likes) < 8:
                likes = " "*(8-len(likes))+likes

            comments = likes_comments[1]
            endtime = time.time()
            print("This took %0.2f seconds" % (endtime-starttime))

            i += 1
            print('Going to {}'.format(likes))
            status = s.set_text(str(likes))
            time.sleep(1)
            # update_likes_comments_from_user_feed(new_user_feed)


# Import config and set global variables
def load_config(filepath):
    #dirname = os.path.dirname(__file__) + "/" + filepath
    dirname = filepath
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


def insta_get_number_of_followers(user):
    print("Getting followers")
    url = 'https://www.instagram.com/' + user
    r = requests.get(url).text
    follower_count = re.search(
        '"edge_followed_by":{"count":([0-9]+)}', r).group(1)
    return follower_count


def keep_only_interesting_data_from_feed(user_feed):
    new_feed = []
    for post in user_feed:
        big_post = post
        wanted_keys = ["taken_at", "code", "comment_count",
                       "like_count", "media_type", "view_count"]
        simple_post = {k: big_post[k]
                       for k in set(wanted_keys) & set(big_post.keys())}
        new_feed.append(simple_post)
    return new_feed


def count_likes_and_comments_from_user_feed(user_feed, startdate=0):
    # sum up like_count and comment_count on posts newer than startdate if the key exists if not use 0 as replacement
    total_likes = sum([post['like_count']
                       for post in user_feed if post['taken_at'] > startdate])
    total_comments = sum([post.get('comment_count', 0)
                          for post in user_feed if post['taken_at'] > startdate])

    return total_likes, total_comments


def update_stats_in_user_feed(user_feed):
    # split user feed into batches for threading
    post_batches = numpy.array_split(numpy.array(user_feed), number_of_threads)

    threads = []
    result = [{}] * len(post_batches)

    for i, posts in enumerate(post_batches):
        process = Thread(target=scrape_stats, args=[posts, result, i])
        # print("\n#"*2+"Thread #%s starting with "%(i))
        # print(posts)
        # print(result)
        process.start()
        threads.append(process)
    for process in threads:
        process.join()

    one_dimensional_result = make_two_dimensional_liste_one_dimensional(result)

    # print("\n#"*5+"This is the one dimensional result of the update_likes_comments_from_user_feed function"+"\n#"*5)
    # print(one_dimensional_result)
    return one_dimensional_result


def scrape_stats(post_batch, result, index):
    # print("\n#"*5+"#These are the single post batches a thread is runnig on\n"+"\n#"*5)
    # print(post)

    # setting up sessions for avoiding ssl problems
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    for post in post_batch:

        url = "https://instagram.com/p/" + str(post["code"])
        r = session.get(url).text

        # video posts need to be crawled differently
        if post["media_type"] == 2:
            #view_count = int(re.search('"userInteractionCount":"([0-9]+)"',r).group(1))
            # better use this because to many views result in abreviation
            view_count = int(
                re.search('"video_view_count":([0-9]+),', r).group(1))
            #post["like_count"] = int(re.search('"edge_media_preview_like":{"count":([0-9]+),',r).group(1))
            #post["comment_count"] = int(re.search('"commentCount":"([0-9]+)"',r).group(1))
            #print("%s has %s views, %s likes and %s comments"%(url,post["view_count"],post["like_count"],post["comment_count"]))
        # Photos and carousels can be treated the same way
        else:
            #post["like_count"] = int(re.search('"userInteractionCount":"([0-9]+)"',r).group(1))
            # better use this like count for videos use abreviations like 10k for too many likes
            post["like_count"] = int(
                re.search('"edge_media_preview_like":{"count":([0-9]+),', r).group(1))
            #post["comment_count"] = int(re.search('"commentCount":"([0-9]+)"',r).group(1))
            post["comment_count"] = int(
                re.search('"edge_media_to_parent_comment":{"count":([0-9]+),', r).group(1))
            #print("%s has %s likes and %s comments"%(url,post["like_count"],post["comment_count"]))

    result[index] = post_batch.tolist()
    """
    print("\n#"*5+"Thread #%s ended with "%(index))
    print("\n#"*1+"This is the resulitng post_batch")
    print(post_batch)
    print("\n#"*1+"This is the resulitng post_batch.tolist()")
    print(post_batch.tolist())
    print("\n#"*1+"This is the current result")
    print(result)
    """
    return True


def update_posts_in_last_x_days_in_user_feed(user_feed, days):
    # split user_feed into two lists
    latest_post_date = int(time.time()) - days*86400

    i = 0
    for post in user_feed:
        if post["taken_at"] > latest_post_date:
            i += 1
        else:
            break

    newer_posts = user_feed[0:i]
    older_posts = user_feed[i:len(user_feed)]

    print("Updating %s posts of the last %s days using %s threads" %
          (i, days, number_of_threads))
    update_stats_in_user_feed(newer_posts)

    return newer_posts+older_posts

def make_two_dimensional_liste_one_dimensional(list1):
    return [val for lst in list1 for val in lst]


if __name__ == '__main__':
    run()
