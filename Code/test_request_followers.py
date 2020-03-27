import requests
import re

user = "rahelbaer"
url = 'https://www.instagram.com/' + user
r = requests.get(url).text
followers = re.search('"edge_followed_by":{"count":([0-9]+)}',r).group(1)

print(followers)
