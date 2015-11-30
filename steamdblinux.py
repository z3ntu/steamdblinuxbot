#!/usr/bin/python3

import config
import os
import requests
import json
import pickle
import tweepy

LINUX_GAMES_URL = "https://raw.githubusercontent.com/SteamDatabase/SteamLinux/master/GAMES.json"
# LINUX_GAMES_URL = "http://localhost/GAMES.json"
GAMES_URL = "http://api.steampowered.com/ISteamApps/GetAppList/v2"
DATA_PATH = os.path.expanduser('~') + "/.steamdblinux/"
SAVE_FILE = DATA_PATH + "save.db"


def main():
    auth = tweepy.OAuthHandler(config.twitter['consumer_key'], config.twitter['consumer_secret'])
    auth.set_access_token(config.twitter['access_token'], config.twitter['access_token_secret'])
    global twitter
    twitter = tweepy.API(auth)
    load_game_list()


def load_game_list():
    os.makedirs(DATA_PATH, exist_ok=True)
    # GET ALBUM LIST
    print("Loading game lists...")
    linux_games_raw = requests.get(LINUX_GAMES_URL)
    games_raw = requests.get(GAMES_URL)

    # PARSE RESPONSE INTO JSON
    linux_games = json.loads(linux_games_raw.text)
    games = json.loads(games_raw.text)

    # print(search(264340, games['applist']['apps']))

    existing_games = load_from_file(SAVE_FILE)
    real_linux_games = []
    for appid, data in linux_games.items():
        if isinstance(data, bool):
            real_linux_games.append(appid)

    new = list(set(real_linux_games) - set(existing_games))
    if new and len(new) < 20:
        print("new items")
        for appid in new:
            name = search(int(appid), games['applist']['apps'])
            send_tweet("New Game:\n" +
                       name + "\n" +
                       "steamdb.info/app/" + appid)
    elif new:
        print("skipping because too many new items")
    else:
        print("no new items")

    write_to_file(SAVE_FILE, real_linux_games)


def search(appid, apps):
    for app in apps:
        if app['appid'] == appid:
            return app['name']
    return "NO NAME FOUND"


def is_new_game(appid):
    print(appid)
    return True


def write_to_file(filename, list_to_save):
    print("Saving data to file...")
    with open(filename, 'wb') as f:
        pickle.dump(list_to_save, f)


def load_from_file(filename):
    print("Loading data from file...")
    if not os.path.isfile(filename):
        return []
    with open(filename, 'rb') as f:
        return pickle.load(f)


def send_tweet(text):
    if not config.debug:
        print("Sending tweet.")
        twitter.update_status(text)
    else:
        print("Not sending tweet because in Debug mode")


if __name__ == '__main__':
    main()
