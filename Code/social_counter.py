import mongoDB_functions

import instapy

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
            mf.write_insta_posts_to_mongodb(userfeed, DB.test_collection)
            print("Getting rid of extra data")
            user_feed = keep_only_interesting_data_from_feed(user_feed)
            #print("\n###"*5+"This is the user feed"+"\n###"*5)
            #print(user_feed)
            i+=1

        if i%50 == 0:
            user_feed = update_posts_in_last_x_days_in_user_feed(user_feed,28)
            
        if i%10 == 0:
            user_feed = update_posts_in_last_x_days_in_user_feed(user_feed,14)
            
        else:
            #divide user feed in small batches for threading
            #url_batches = numpy.array_split(numpy.array(urls),number_of_threads)
            #using user feed to crawl post urls. No API login required
            user_feed = update_posts_in_last_x_days_in_user_feed(user_feed, 2)
            #print("\n######"*5+"This is the new user feed"+"\n#####"*5)
            #print(user_feed)
        
        #startdate = "2020-03-13"
        #startdate = ciso8601.parse_datetime(startdate)
        # to get time in seconds:
        #startdate=int(time.mktime(ciso8601.parse_datetime(startdate).timetuple()))

        print("Counting Likes and Comments")
        #likes_comments = count_likes_and_comments_from_user_feed(user_feed)
        likes_comments = count_likes_and_comments_from_user_feed(user_feed)
        likes = str(likes_comments[0])
        
        #aufbereitung der zahl muss noch optimiert werden
        if len(likes)<8:
            likes = " "*(8-len(likes))+likes
        
        comments = likes_comments[1]
        endtime = time.time()
        print("This took %0.2f seconds" %(endtime-starttime))
        
        i += 1
        print('Going to {}'.format(likes))
        status = s.set_text(str(likes))
        time.sleep(1)
        #update_likes_comments_from_user_feed(new_user_feed)

if __name__ == '__main__':
    # Initialization
    target_username = "weihnachtenneuerleben"
    number_of_threads = 1

    insta_username, insta_password = load_config("config.json")
    insta_api = insta_initialize(insta_username, insta_password)
    insta_user_id = insta_get_user_id(target_username)
    
    DB = mf.initialize_db()
    
    run()