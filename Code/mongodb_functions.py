import pymongo

client_adress = "mongodb://localhost:27017/"


def initialize_db():
    print("MongoDB initialized")
    client = pymongo.MongoClient(client_adress)
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


def write_fb_posts_to_mongodb(posts, collection, raw_values=False):
    # TODO
    return ""

def write_insta_page_stats_to_mongodb():
    # TODO
    return ""

def write_fb_page_stats_to_mongodb():
    # TODO
    return ""

def get_total_counts(collection, instagram=True, facebook=True):
    platforms = []
    if instagram:
        platforms.append("instagram")
    if facebook:
        platforms.append("facebook")
    pipeline = [{
        "$group": {"_id": "$platform",
                   "total_like_count": {"$sum": "$like_count"},
                   "total_comment_count": {"$sum": "$comment_count"},
                   "total_view_count": {"$sum": "$view_count"}
                   }}]
    result = tuple(collection.aggregate(pipeline))
    print(result)

    total_like_count = int(sum(p["total_like_count"]
                           for p in result if p["_id"] in platforms))
    total_comment_count = int(sum(p["total_comment_count"]
                              for p in result if p["_id"] in platforms))
    total_view_count = int(sum(p["total_view_count"]
                           for p in result if p["_id"] in platforms))

    return (total_like_count, total_comment_count, total_view_count)


def get_total_single_count(collection, variable, instagram=True, facebook=True):
    # Variable must have the same value as in MongoDB, eg. "like_count"

    platforms = []
    if instagram:
        platforms.append("instagram")
    if facebook:
        platforms.append("facebook")
    pipeline = [{
        "$group": {"_id": "$platform",
                   "total_count": {"$sum": "${}_count".format(variable)},
                   }}]
    result = tuple(collection.aggregate(pipeline))

    total_count = int(sum(p["total_count"]
                      for p in result if p["_id"] in platforms))
    return total_count


def get_total_like_count(collection, instagram=True, facebook=True):
    variable = "like"
    return get_total_single_count(collection, variable, instagram, facebook)


def get_total_comment_count(collection, instagram=True, facebook=True):
    variable = "comment"
    return get_total_single_count(collection, variable, instagram, facebook)


def get_total_view_count(collection, instagram=True, facebook=True):
    variable = "view"
    return get_total_single_count(collection, variable, instagram, facebook)

def get_total_follower_count(collection, instagram=True, facebook=True):
    # TODO
    return ""


db = initialize_db()
print(get_total_like_count(db.posts))
print(get_total_comment_count(db.posts))
print(get_total_view_count(db.posts))
