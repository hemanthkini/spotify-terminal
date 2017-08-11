#!/usr/bin/env python3

import json
import requests
import requests_oauthlib
from oauthlib.oauth2 import MobileApplicationClient
from requests_oauthlib import OAuth2Session
import time
import sys
import os
import os.path

TOKEN_URL = 'https://accounts.spotify.com/api/token'
BASE_API_URL = 'https://api.spotify.com'

CREDENTIALS_PATH = os.path.expanduser("~") + '/.spotify-terminal/credentials'

# Supported commands.
# TODO move scopes here.
supported_commands = {
    'play': {'path': '/v1/me/player/play', 'type': 'put'},
    'pause': {'path': '/v1/me/player/pause', 'type': 'put'},
    'next': {'path': '/v1/me/player/next', 'type': 'post'},
    'previous': {'path': '/v1/me/player/previous', 'type': 'post'},
    'currently-playing': {'path': '	/v1/me/player/currently-playing', 'type': 'get'},
    'recently-played': {'path': '	/v1/me/player/recently-played', 'type': 'get'}

}

# Global request/oauth session.
spotify = None

def usage():
    print("Usage: spotify-terminal [command]")
    if not(os.path.isfile(CREDENTIALS_PATH)):
        print("Set up your ~/.spotify-terminal/credentials file with the template.")

def acquire_credentials():
    global spotify
    credentials = {}
    with open(CREDENTIALS_PATH, 'r') as f:
       credentials = json.load(f)

    # Error handle a missing credential file.
    scope = ['streaming',
    'playlist-read-private',
    'playlist-read-collaborative',
    'user-top-read',
    'user-read-email',
    'user-read-birthdate',
    'user-read-private',
    'user-read-recently-played',
    'user-read-currently-playing',
    'user-library-modify',
    'user-library-read',
    'user-follow-read',
    'user-follow-modify',
    'ugc-image-upload',
    'playlist-modify-private',
    'playlist-modify-public',
    'user-modify-playback-state',
    'user-read-playback-state'
   ]

    if not('expires_at' in credentials):

        oauth = OAuth2Session(credentials['client_id'],
       	    redirect_uri=credentials['redirect_uri'],
            scope=scope)
        authorization_url, state = oauth.authorization_url(
       		       'https://accounts.spotify.com/authorize')

        print('Please go to %s and authorize access.' % authorization_url)
        print('After authorizing, the browser will fail to connect. Copy the URL here.')
        authorization_response = input('Enter the full callback URL:\n')

        token = oauth.fetch_token(
            TOKEN_URL,
            authorization_response=authorization_response,
            client_secret=credentials['client_secret'])

        credentials.update(token)
        spotify = oauth
    else:
        token = {}
        token['access_token'] = credentials['access_token']
        token['refresh_token'] = credentials['refresh_token']
        token['token_type'] = credentials['token_type']
        token['expires_in'] = credentials['expires_in']
        if  (credentials['expires_at'] <= int(time.time())):
            print("Refreshing token")
            token['expires_in'] = -30

        extra = {}
        extra['client_id'] = credentials['client_id']
        extra['client_secret'] = credentials['client_secret']

        refresh_url = TOKEN_URL

        oauth = OAuth2Session(credentials['client_id'],
                             token=token,
                             auto_refresh_url=refresh_url,
                             auto_refresh_kwargs=extra,
                             token_updater=credentials.update)
            # token = oauth.get(refresh_url)
            # print(token.text)

        spotify = oauth

    with open(CREDENTIALS_PATH, 'w') as f:
        json.dump(credentials, f)

acquire_credentials()

args = sys.argv[1:]

if len(args) == 0:
    usage()
    exit()

command = args[0]

matching_command = [c for c in supported_commands.keys() if c.startswith(command)]
if len(matching_command) == 1:
    command = matching_command[0]
    command_str = 'print(spotify.' + supported_commands[command]['type'] + '(\'' + BASE_API_URL + supported_commands[command]['path'] + '\').text)'
    print(command_str)
    exec(command_str)
