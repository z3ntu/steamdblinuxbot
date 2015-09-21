#!/usr/bin/env python
# -*- coding: utf-8 -*-

# steamDB linux monitor bot

import time, os.path, urllib2, codecs
import tweepy
from BeautifulSoup import BeautifulSoup
from BeautifulSoup import BeautifulStoneSoup

# store security-sensitive config data in a file that's not in source control
# variables expected: api_key, api_secret, access_token, access_token_secret
# create these at https://dev.twitter.com
# make sure application's access level is "read and write"
execfile('./keys.py')
auth = tweepy.OAuthHandler(api_key, api_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

LOCAL_DATA_FILE = 'steamlinux.html'
DATA_URL = 'http://steamdb.info/linux'
#STEAM_URL_BASE = 'http://store.steampowered.com/app/'
STEAM_URL_BASE = 'http://steamdb.info/app/'
# max # of posts to make in one run
POST_LIMIT = 50
# seconds to wait between multiple posts in one run
POST_DELAY = 20

LOG = True

class Game:
    "simple struct for a game DB entry"
    strformat = 'id: %s\nname: %s\nstatus: %s\n-------------'
    def __init__(self, id, name, status):
        self.id = id
        self.name = name
        self.status = status
    def __str__(self):
        return self.strformat % (self.id, self.name, self.status)

def get_gamelist(soup):
    "big gross ball of weirdness, highly dependent on steamDB's HTML vagaries"
    # build list of app ids
    appids = []
    for link in soup.findAll('a'):
        if link.get('href') and link.get('href').startswith('/app/'):
            appids.append(link.string)
    # match app ids to game data
    games = []
    i = 0
    cells = soup.findAll('td')
    for cell in cells:
        cell_links = cell.findAll('a')
        if len(cell_links) == 0:
            i += 1
            continue
        linktxt = cell_links[0].string
        for id in appids:
            if linktxt and id == linktxt:
                gamename = cells[i+1].string
                # if tag has sub-tags, assume second eg:
                # <td>Cakewalk Loop Manager <i>(APPLICATION)</i></td>
                if not gamename:
                    if cells[i+1].contents[1].string:
                        gamename = cells[i+1].contents[0] + cells[i+1].contents[1].string
                    else:
                        gamename = cells[i+1].contents[0]
                # convert HTML chars, eg &amp;
                # couldn't figure out BeautifulSoup's intended method :/
                replacements = {'&amp;':'&', '&quot;':'"', '&apos;':"'",
                                '&#039;':"'", '&ccedil;':'c', '&trade;':'(tm)'
                            }
                for k in replacements:
                    gamename = gamename.replace(k, replacements[k])
                # snip name after last line break (price info)
                gamename = gamename[:gamename.rfind('\n')] + '\n'
                status = cells[i+3].string
                # "game works" usually enclosed in a span
                if not status:
                    status_tag = cells[i+3].findAll('span')
                    # or sometimes it's not? steamDB html might have changed
                    if len(status_tag) > 0:
                        status = status_tag[0].string
                    else:
                        status = 'Game Works'
                games.append(Game(id, gamename, status))
        i += 1
    return games

if LOG:
    print('current time: %s' % time.ctime(time.time()))
    t = time.ctime(os.path.getmtime(LOCAL_DATA_FILE))
    print('last checked: %s' % t)

# get old data from local version of page written out last run
page_data = open(LOCAL_DATA_FILE)
soup = BeautifulSoup(page_data)
page_data.close()
old_games = get_gamelist(soup)

# fetch new data from web
# use a custom header to get around 403 Forbidden
header = { 'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)' }
req = urllib2.Request(DATA_URL, None, header)
page_data = urllib2.urlopen(req).read()
# write data over old file
new_page = open(LOCAL_DATA_FILE, 'w')
new_page.write(page_data)
new_page.close()
soup = BeautifulSoup(page_data)
new_games = get_gamelist(soup)

# check for status changes between old and new data
posts = []
found_change = False
for newgame in new_games:
    found_game = False
    for oldgame in old_games:
        if newgame.id == oldgame.id:
            found_game = True
            # only post about existing games that have been confirmed to work
            if newgame.status != oldgame.status and newgame.status == 'Game Works':
                found_change = True 
                new_post = '%s: %s ' % (newgame.status, newgame.name)
                new_post += STEAM_URL_BASE + newgame.id
                #new_post += ' (was: %s)' % oldgame.status
                posts.append(new_post) # comment to disable Game Works posts
    if not found_game:
        found_change = True
        new_post = 'New Game: %s ' % newgame.name
        new_post += STEAM_URL_BASE + newgame.id
        posts.append(new_post)

# report
if not found_change:
    if LOG: print('%s: no changes found.' % time.ctime(time.time()))
else:
    print('change(s) found! current time: %s' % time.ctime(time.time()))
    # if something goes wrong and list is absurdly long, snip it
    if len(posts) > POST_LIMIT:
        posts = posts[:POST_LIMIT]
    for post in posts:
        post_txt = codecs.encode(str(post), 'ascii', 'replace')
        print(post_txt)
        api.update_status(post)
        # wait good n long before posting in case we have a lot
        time.sleep(POST_DELAY)
