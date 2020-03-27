import requests
import re
url = 'https://www.instagram.com/p/B8t4aOXiTqw/'
def scrape_likes_comments(url):
    r = requests.get(url).text
    likes = int(re.search('"userInteractionCount":"([0-9]+)"',r).group(1))
    comments = int(re.search('"commentCount":"([0-9]+)"',r).group(1))
    return likes, comments

print(scrape_likes_comments(url))