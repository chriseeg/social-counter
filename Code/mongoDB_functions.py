from datetime import datetime, timedelta
import pymongo
import ciso8601


client_adress = "mongodb://localhost:27017/"


def initialize_db():
    print("MongoDB initialized")
    client = pymongo.MongoClient(client_adress)
    db = client.socialcounter_db
    return db

################################################################


def write_insta_posts_to_mongodb(collection, posts):
    # takes a list of instagram posts in original formatting and writes it into the mongoDB collection

    if type(posts) is not list:
        posts = [posts]

    insertion_count = 0
    update_count = 0

    for post in posts:
        """
        try:
            view_count = post["view_count"]
        except:
            view_count = 0
        post_id = post["id"]
        taken_at = datetime.fromtimestamp(post["taken_at"]).strftime('%Y-%m-%d %H:%M:%S')
        clean_post = {
            "_id": post_id,
            "platform": "instagram",
            "url": "https://www.instagram.com/p/" + post["code"],
            "username": post["user"]["username"],
            "taken_at": ciso8601.parse_datetime(str(taken_at)),
            "comment_count": post["comment_count"],
            "like_count": post["like_count"],
            "media_type": post["media_type"],
            "view_count": view_count
        }
        """

        # check if post exists in db
        if collection.find({'_id': {"$in": [post["_id"]]}}).count() == 0:
            # insert post if new
            collection.insert_one(post)
            insertion_count += 1
        else:
            # update existing post
            collection.update_one(
                {"_id": post["_id"]},
                {
                    "$set": {
                        "like_count": post["like_count"],
                        "comment_count": post["comment_count"],
                        "view_count": post["view_count"]
                    }
                }
            )
            update_count += 1

    #print("Instagram Posts written to MongoDB " + collection.name +
    #      ": {} inserted, {} updated".format(insertion_count, update_count))

    return insertion_count, update_count


def write_fb_posts_to_mongodb(collection, posts):
    # takes a list of enriched fb posts (or one post) and writes it into the mongoDB collection

    if type(posts) is not list:
        posts = [posts]

    insertion_count = 0
    update_count = 0

    # new_ids = [p["_id"] for p in posts] #evtl löschen
    for post in posts:
        post_id = post["_id"]
        # check if post exists in db
        if collection.find({'_id': {"$in": [post_id]}}).count() == 0:
            # insert post if new
            collection.insert_one(post)
            insertion_count += 1
        else:
            # update existing post
            collection.update_one(
                {"_id": post_id},
                {
                    "$set": {
                        "like_count": post["like_count"],
                        "comment_count": post["comment_count"]
                    }
                }
            )
            update_count += 1

    print("Facebook Posts written to MongoDB " + collection.name +
          ": {} inserted, {} updated".format(insertion_count, update_count))
    return True

################################################################


def write_insta_page_stats_to_mongodb():
    # TODO

    return ""


def write_fb_page_stats_to_mongodb():
    # TODO

    return ""

################################################################

# TODO: create same functions for facebook

def last_insta_posts_by_days(collection, no_of_days):
    today = datetime.now()
    date_threshold = today - timedelta(days=no_of_days)
    print(date_threshold)
    result_mdb = collection.find(
        {
            "taken_at": {
                "$gte": date_threshold
            },
            "platform": "instagram"
        },
        {
            "_id": 1.0,
            "url": 1.0
        })
    result_list = [p for p in result_mdb]
    return list(result_list)


def last_insta_posts_by_posts(collection, no_of_posts):
    result_mdb = collection.find(
        {
            "platform": "instagram"
        },
        {
            "_id": 1.0,
            "url": 1.0
        }
    ).sort(
        "taken_at", -1
    ).limit(no_of_posts)
    result_list = [p for p in result_mdb]
    return list(result_list)

################################################################


def get_total_post_counts(collection, instagram=True, facebook=True, start_date="2000-12-24"):
    platforms = []
    if instagram:
        platforms.append("instagram")
    if facebook:
        platforms.append("facebook")
    pipeline = [
        {
            "$match": {
                'taken_at': {'$gte': ciso8601.parse_datetime(start_date)}
            }
        },
        {
            "$group": {
                "_id": "$platform", "total_like_count": {"$sum": "$like_count"},
                "total_comment_count": {"$sum": "$comment_count"},
                "total_view_count": {"$sum": "$view_count"}
            }
        }
    ]

    result = tuple(collection.aggregate(pipeline))

    total_like_count = int(sum(p["total_like_count"]
                               for p in result if p["_id"] in platforms))
    total_comment_count = int(sum(p["total_comment_count"]
                                  for p in result if p["_id"] in platforms))
    total_view_count = int(sum(p["total_view_count"]
                               for p in result if p["_id"] in platforms))

    return total_like_count, total_comment_count, total_view_count


def get_total_post_count_single(collection, variable="like", instagram=True, facebook=True, start_date="2000-12-24"):
    # Variable must have the same value as in MongoDB, eg. "like", "comment", "view"

    platforms = []
    if instagram:
        platforms.append("instagram")
    if facebook:
        platforms.append("facebook")
    pipeline = [
        {
            "$match": {
                'taken_at': {'$gte': ciso8601.parse_datetime(start_date)}
            }
        },
        {
            "$group": {
                "_id": "$platform",
                       "total_count": {
                           "$sum": "${}_count".format(variable)
                       },
            }
        }
    ]
    result = tuple(collection.aggregate(pipeline))

    total_count = int(sum(p["total_count"]
                          for p in result if p["_id"] in platforms))
    return total_count


def get_total_post_like_count(collection, instagram=True, facebook=True, start_date="2000-12-24"):
    variable = "like"
    return get_total_post_count_single(collection, variable, instagram, facebook, start_date)


def get_total_post_comment_count(collection, instagram=True, facebook=True, start_date="2000-12-24"):
    variable = "comment"
    return get_total_post_count_single(collection, variable, instagram, facebook, start_date)


def get_total_post_view_count(collection, instagram=True, facebook=True, start_date="2000-12-24"):
    variable = "view"
    return get_total_post_count_single(collection, variable, instagram, facebook, start_date)


def get_total_page_follower_count(collection, instagram=True, facebook=True):
    # TODO
    return ""


DB = initialize_db()
print(last_insta_posts_by_posts(DB.posts, 10))
#print(last_insta_posts_bydays(DB.posts, 50))
# print(get_total_like_count(DB.posts))
# print(get_total_comment_count(DB.posts))
# print(get_total_view_count(DB.posts))
