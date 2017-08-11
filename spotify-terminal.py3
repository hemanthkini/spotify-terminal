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
    'play': {
        'path': '/v1/me/player/play',
        'type': 'put',
        'scopes': ['user-modify-playback-state'],
        'takes_arguments': False,
        'requires_arguments': False
    },
    'pause': {
        'path': '/v1/me/player/pause',
        'type': 'put',
        'scopes': ['user-modify-playback-state'],
        'takes_arguments': False,
        'requires_arguments': False
    },
    'shuffle': {
        'path': '/v1/me/player/shuffle',
        'type': 'put',
        'scopes': ['user-modify-playback-state'],
        'takes_arguments': True,
        'requires_arguments': False,
        'arguments': [
            {
                'parameter': 'state',
                'values': [
                    {'value': 'true', 'user_words': ['true', 'on']},
                    {'value': 'false', 'user_words': ['false', 'off']}
                ],
                'required': True,
                'default_value': 'true'
            }
        ]
    },
    'repeat': {
        'path': '/v1/me/player/repeat',
        'type': 'put',
        'scopes': ['user-modify-playback-state'],
        'takes_arguments': True,
        'requires_arguments': False,
        'arguments': [
            {
                'parameter': 'state',
                'values': [
                    {'value': 'track', 'user_words': ['true', 'on', 'one', 'track']},
                    {'value': 'off', 'user_words': ['false', 'off', 'none']},
                    {'value': 'context', 'user_words': ['context', 'all']}
                ],
                'required': True,
                'default_value': 'track'
            }
        ]
    },
    'next': {
        'path': '/v1/me/player/next',
        'type': 'post',
        'scopes': ['user-modify-playback-state'],
        'takes_arguments': False,
        'requires_arguments': False
    },
    'previous': {
        'path': '/v1/me/player/previous',
        'type': 'post',
        'scopes': ['user-modify-playback-state'],
        'takes_arguments': False,
        'requires_arguments': False
    },
    'currently-playing': {
        'path': '	/v1/me/player/currently-playing',
        'type': 'get',
        'scopes': ['user-read-currently-playing', 'user-read-playback-state'],
        'takes_arguments': False,
        'requires_arguments': False
    },
    'recently-played': {
        'path': '	/v1/me/player/recently-played',
        'type': 'get',
        'scopes': ['user-read-recently-played'],
        'takes_arguments': False,
        'requires_arguments': False
    }
}

extra_scopes = [
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

# Compute all scopes.
all_values = list(supported_commands.values())
all_command_scopes = map(lambda command_entry: command_entry['scopes'], all_values)
command_scopes = []
for sublist in all_command_scopes:
    for scope in sublist:
        if not(scope in command_scopes):
            command_scopes.append(scope)
for scope in extra_scopes:
    if not(scope in command_scopes):
        command_scopes.append(scope)
scopes = command_scopes

# Global request/oauth session.
spotify = None

def usage():
    print("Usage: spotify-terminal [command]")
    if not(os.path.isfile(CREDENTIALS_PATH)):
        print("Set up your ~/.spotify-terminal/credentials file with the template.")

def add_defaults_to_params(command, params):
    if (supported_commands[command]['takes_arguments']):
        for argument in supported_commands[command]['arguments']:
            if argument['required'] and not(argument['parameter'] in params):
                params[argument['parameter']] = argument['default_value']
    return params

def apply_args(command, params, args):
    for arg in args:
        if ':' in arg or '=' in arg:
            # TODO
            pass
        else:
            # Return a list of matching arguments with values whose user keywords
            # match this word.
            matching_arguments = list(map(
                lambda argument_entry:  argument_entry if len(list(filter(
                    lambda value_entry: arg in value_entry['user_words'],
                    argument_entry['values']
                ))) > 0 else None,
                supported_commands[command]['arguments']
            ))
            if len(matching_arguments) == 0:
                print("No matching arguments for " + arg)
                exit()
            if len(matching_arguments) > 1:
                print("Ambiguous argument for '" + arg + "'")
                exit()

            # Grab the matching value entry in the matching argument.
            # Assumed that multiple values don't share keywords.
            # IE you can't have repeat all and repeat one both map to 'repeatsome'.
            argument_entry = matching_arguments[0]
            print(argument_entry)
            value = list(filter(
                lambda value_entry: arg in value_entry['user_words'],
                argument_entry['values']
            ))
            params[argument_entry['parameter']] = value[0]['value']
    return params

def acquire_credentials():
    global spotify
    global scopes
    credentials = {}
    with open(CREDENTIALS_PATH, 'r') as f:
       credentials = json.load(f)

    # Error handle a missing credential file.
    if not('expires_at' in credentials) or set(scopes) != set(credentials['scope']):
        # Get credentials for the first time
        new_credentials = {}
        new_credentials['client_id'] = credentials['client_id']
        new_credentials['client_secret'] = credentials['client_secret']
        new_credentials['redirect_uri'] = credentials['redirect_uri']

        credentials = new_credentials

        oauth = OAuth2Session(credentials['client_id'],
       	    redirect_uri=credentials['redirect_uri'],
            scope=scopes)
        authorization_url, state = oauth.authorization_url(
       		       'https://accounts.spotify.com/authorize')

        print('Please go to %s and authorize access.' % authorization_url)
        print('After authorizing, the browser will fail to connect. Copy the URL here.')
        authorization_response = input('Enter the full callback URL:\n')

        token = oauth.fetch_token(
            TOKEN_URL,
            authorization_response=authorization_response,
            client_secret=credentials['client_secret'])

        print(token)
        credentials.update(token)
        credentials.update({'scope': scopes})
        spotify = oauth
    else:
        # Some form of credentials exist
        token = {}
        token['access_token'] = credentials['access_token']
        token['refresh_token'] = credentials['refresh_token']
        token['token_type'] = credentials['token_type']
        token['expires_in'] = credentials['expires_in']

        # Refresh credentials if expired
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

        spotify = oauth

    # Save refreshed credentials
    with open(CREDENTIALS_PATH, 'w') as f:
        json.dump(credentials, f)

acquire_credentials()

args = sys.argv[1:]

if len(args) == 0:
    usage()
    exit()

command = args[0]

matching_commands = [c for c in supported_commands.keys() if c.startswith(command)]
# The user command only matches one command
if len(matching_commands) == 1:
    command = matching_commands[0]
    # Single word command
    if (len(args) == 1):
        if (supported_commands[command]['requires_arguments']):
            print("This command requires arguments.")
            exit()

        params = {}
        params = add_defaults_to_params(command, params)
        print(params)
        command_str = ''
        if (params == {}):
            command_str = 'print(spotify.' + supported_commands[command]['type'] + '(\'' + BASE_API_URL + supported_commands[command]['path'] + '\').text)'
        else:
            command_str = 'print(spotify.' + supported_commands[command]['type'] + '(\'' + BASE_API_URL + supported_commands[command]['path'] + '\', params=params).text)'
        print(command_str)
        exec(command_str)
    # Multi word command
    else:
        if (not(supported_commands[command]['takes_arguments'])):
            print("This command doesn't take arguments.")
            exit()
        remaining_args = args[1:]

        params = {}
        params = apply_args(command, params, remaining_args)
        params = add_defaults_to_params(command, params)
        print(params)
        command_str = 'print(spotify.' + supported_commands[command]['type'] + '(\'' + BASE_API_URL + supported_commands[command]['path'] + '\', params=params).text)'
        print(command_str)
        exec(command_str)


else:
    print('Ambiguous command, matches [' + ', '.join(matching_commands) + ']')
