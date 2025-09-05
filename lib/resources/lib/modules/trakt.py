# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * Genesis Add-on
 * Copyright (C) 2015 lambda
 *
 * - Mofidied by The Crew
 *
 * @file trakt.py
 * @package script.module.thecrew
 *
 * @copyright 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

import re
import os
import time
import json
from datetime import datetime, timedelta

from urllib.parse import urljoin, quote_plus
import sqlite3 as database
from sqlite3 import OperationalError,Error

import requests

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import cache
from . import cleandate
from . import client
from . import control
from . import utils
from .crewruntime import c

trakt_endpoints = {
    'settings': {

    },
    'shows': {

    },
    'movies': {
    }

}

trakt_response_codes = {
    '200': 'Success',
    '201': 'Success - new resource created (POST)',
    '204': 'Success - no content to return (DELETE)',
    '400': 'Bad Request - request couldn\'t be parsed',
    '401': 'Unauthorized - OAuth must be provided',
    '403': 'Forbidden - invalid API key or unapproved app',
    '404': 'Not Found - method exists but no record found',
    '405': 'Method Not Found - method doesn\'t exist',
    '409': 'Conflict - resource already created',
    '412': 'Precondition Failed - use application/json content type',
    '420': 'Account Limit Exceeded - list count, item count, etc',
    '422': 'Unprocessable Entity - validation errors',
    '423': 'Locked User Account - have the user contact support',
    '426': 'VIP Only - user must upgrade to VIP',
    '429': 'Rate Limit Exceeded',
    '500': 'Server Error - please open a support ticket',
    '502': 'Service Unavailable - server overloaded (try again in 30s)',
    '503': 'Service Unavailable - server overloaded (try again in 30s)',
    '504': 'Service Unavailable - server overloaded (try again in 30s)',
    '520': 'Service Unavailable - Cloudflare error',
    '521': 'Service Unavailable - Cloudflare error',
    '522': 'Service Unavailable - Cloudflare error',
}





BASE_URL = 'https://api.trakt.tv/'
CLIENT_ID = '482f9db52ee2611099ce3aa1abf9b0f7ed893c6d3c6b5face95164eac7b01f71'
CLIENT_SECRET = '80a2729728b53ba1cc38137b22f21f34d590edd35454466c4b8920956513d967'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

TRAKTUSER = control.setting('trakt.user').strip()
session = requests.Session()
retries = Retry(total=3, backoff_factor=0.5)
session.mount(BASE_URL, HTTPAdapter(max_retries=retries))
# For debug purposes only

def get_trakt(url, post=None):
    """
    Make a request to the Trakt API
    """
    try:
        c.log(f"[CM Debug @ 88 in trakt.py] url = {url} | post = {post}")
        if not url.startswith('http'):
            c.log(f"[CM Debug @ 91 in trakt.py] url does not start with http, joining with BASE_URL")
            #
            url = urljoin(BASE_URL, url)
            c.log(f"[CM Debug @ 94 in trakt.py] url after join = {url}")
        elif(url.find('api.trakt.tv/')):
            #! we have already an api url
            pass
        else:
            u = url.split('/', 3)[3]
            url = urljoin(BASE_URL, u) if len(u) > 0 else urljoin(BASE_URL, '/')
        c.log(f"[CM Debug @ 99 in trakt.py] url = {url}")
        post = json.dumps(post) if post else None
        c.log(f"[CM Debug @ 101 in trakt.py] post = {post}")
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-key': CLIENT_ID,
            'trakt-api-version': '2'
        }

        if getTraktCredentialsInfo():
            headers['Authorization'] = f'Bearer {control.setting("trakt.token")}'

        #response = requests.get(url, headers=headers, timeout=30) if not post else\
                    #requests.post(url, data=post, headers=headers, timeout=30)
        response = session.post(url, data=post, headers=headers, timeout=30) if post else session.get(url, headers=headers, timeout=30)

        response.encoding = 'utf-8'
        status_code = str(response.status_code)

        if not response:
            status_code = str(response.status_code)
            msg_handler(url, response, status_code, post, headers)

        if not status_code or not status_code.startswith('2'):
            msg_handler(url, response, status_code, post, headers)

        return response.text, response.headers
    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 94 in trakt.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 94 in trakt.py]Exception raised. Error = {e}')
        pass

def msg_handler(url, response, status_code, post, headers):
    if status_code in ['401', '403', '405']:
        try:
            _extracted_refresh_token(headers, url, post)
            # response = requests.post(url, data=post, headers=headers, timeout=30) if post else requests.get(url, headers=headers, timeout=30)
            # response = session.post(url, data=post, headers=headers, timeout=30) if post else session.get(url, headers=headers, timeout=30)
            get_trakt(url, post)


        except Exception as e:
            control.infoDialog(f'Unknown Trakt Error: {e}', sound=True)
            c.log(f'Exception raised in msg_handler: {e}', 1)
            return

    elif not response:# or status_code.startswith('5') and not status_code.startswith('4')
        control.infoDialog(f'Trakt Server didn\'t respond, {trakt_response_codes[status_code]}', sound=True)
        return
    elif isinstance(response, str) and '<html' in response:
        control.infoDialog(f'A Trakt Server Problem occurred, code: {status_code}', sound=True)
        c.log(f'A Trakt Server Problem occurred, code: {status_code}')
        return
    elif status_code == '423':
        control.infoDialog(trakt_response_codes[status_code], sound=True)
        c.log(f"Trakt status = {trakt_response_codes[status_code]}")
        return
    elif status_code in ['429']:
        if 'Retry-After' in headers:
            retry_time = headers['Retry-After']
            control.infoDialog(f'Trakt Rate Limit Reached, waiting for {retry_time} seconds', sound=True)
            control.sleep((int(retry_time) + 1) * 1000)
            c.log(f"Trakt Rate Limit Reached, waiting for {retry_time} seconds\n{trakt_response_codes[status_code]}")
            return get_trakt(url, post)
        else:
            control.infoDialog('Trakt Rate Limit Reached', sound=True)
        return
    elif status_code in ['404']:
        #c.log(f"trakt status = {trakt_response_codes[status_code]} with url = {url}")
        c.log(f"trakt status = {trakt_response_codes[status_code]}")
        return
    elif status_code:
        c.log(f"trakt status = {trakt_response_codes[status_code]}")
        return
    else:
        return



def _extracted_refresh_token(headers, url, post) -> None:
    oauth = urljoin(BASE_URL, '/oauth/token')
    opost = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'refresh_token',
        'refresh_token': control.setting('trakt.refresh')
    }
    # response = requests.post(oauth, data=json.dumps(opost), headers=headers, timeout=30).json()
    response = session.post(oauth, data=json.dumps(opost), headers=headers, timeout=30).json()
    c.log(f"[CM Debug @ 160 in trakt.py] response of type {type(response)}\n\n{response}")
    token, refresh = response['access_token'], response['refresh_token']
    control.setSetting(id='trakt.token', value=token)
    control.setSetting(id='trakt.refresh', value=refresh)
    headers['Authorization'] = f'Bearer {token}'
    return


def getTraktAsJson(url, post=None):
    """
    Make a request to the Trakt API and return the response as a JSON string.

    Args:
        url (str): The endpoint URL to make the Trakt API request.
        post (dict, optional): The data to post to the API if making a POST request. Defaults to None.

    Returns:
        str: The JSON response from the API as a string. The response is sorted if the headers contain
        'X-Sort-By' and 'X-Sort-How'. Returns None if there is an error or if the API response is None.

    Logs:
        Exceptions and errors encountered during the API call and JSON conversion are logged.
    """

    try:
        if isinstance(url, str):
            result = get_trakt(url, post) if post else get_trakt(url)
            # c.log(f"[CM Debug @ 224 in trakt.py] result from url = {url} is of type {type(result)}\n\nresult = {result}")
        else:
            # c.log(f"[CM Debug @ 225 in trakt.py] url is not a string: {url}")
            return None

        if result:
            return _extracted_from_getTraktAsJson(result)
        # Handle the case where get_trakt returns None
        c.log('getTraktAsJson Error: get_trakt returned None')
        return None
    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 225 in trakt.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 225 in trakt.py]Exception raised. Error = {e}')
        pass



def _extracted_from_getTraktAsJson(result):
    resp, res_headers = result
    # c.log(f"[CM Debug @ 230 in trakt.py] response type: {type(resp)}\n\nresponse = {resp}")
    # resp = utils.json_loads_as_str(resp)
    resp = json.loads(resp) if isinstance(resp, str) else resp
    if 'X-Sort-By' in res_headers and 'X-Sort-How' in res_headers:
        resp = sort_list(res_headers['X-Sort-By'], res_headers['X-Sort-How'], resp)
    return resp
    #except Exception as e:
        #c.log('getTraktAsJson Error: ' + str(e))
        #pass





def getTraktAsJsonDisabled(url, post=None):
    try:
        if post is not None:
            r, res_headers = get_trakt(url, post)
        elif isinstance(url, str):
            r, res_headers = get_trakt(url)
        r, res_headers = get_trakt(url, post)
        r = utils.json_loads_as_str(r)
        if 'X-Sort-By' in res_headers and 'X-Sort-How' in res_headers:
            r = sort_list(res_headers['X-Sort-By'], res_headers['X-Sort-How'], r)
        return r
    except Exception as e:
        c.log('getTraktAsJson Error: ' + str(e))
        pass

def auth_trakt():
    try:
        if getTraktCredentialsInfo() is True:
            if control.yesnoDialog(control.lang(32511) + '[CR]' + control.lang(32512), heading='Trakt'):
                control.setSetting(id='trakt.user', value='')
                control.setSetting(id='trakt.token', value='')
                control.setSetting(id='trakt.refresh', value='')
            raise Exception()

        result = getTraktAsJson('/oauth/device/code', {'client_id': CLIENT_ID})
        c.log(f"[CM Debug @ 278 in trakt.py] result of authTrakt is of type {type(result)}\n\nresult = {result}")
        verification_url = control.lang(32513) % result['verification_url']
        user_code = control.lang(32514) % result['user_code']
        expires_in = int(result['expires_in'])
        device_code = result['device_code']
        interval = result['interval']

        progressDialog = control.progressDialog
        progressDialog.create('Trakt')

        for i in range(0, expires_in):
            try:
                percent = int(100 * float(i) / int(expires_in))
                progressDialog.update(max(1, percent), verification_url + '[CR]' + user_code)
                if progressDialog.iscanceled():
                    break

                time.sleep(1)
                if not float(i) % interval == 0:
                    raise Exception()
                r = getTraktAsJson(
                        '/oauth/device/token',
                    {
                        'client_id': CLIENT_ID,
                        'client_secret': CLIENT_SECRET,
                        'code': device_code
                    })
                if 'access_token' in r:
                    break
            except:
                pass

        try:
            progressDialog.close()
        except:
            pass

        token, refresh = r['access_token'], r['refresh_token']

        headers = {
                    'Content-Type': 'application/json',
                    'trakt-api-key': CLIENT_ID,
                    'trakt-api-version': 2,
                    'Authorization': f'Bearer {token}'
                }

        result = client.request(urljoin(BASE_URL, '/users/me'), headers=headers)
        c.log(f"[CM Debug @ 310 in trakt.py] result of new auth was {result} of type {type(result)}")
        result = utils.json_loads_as_str(result)

        user = result['username']
        authed = '' if user == '' else str('yes')

        control.setSetting(id='trakt.user', value=user)
        control.setSetting(id='trakt.token', value=token)
        control.setSetting(id='trakt.refresh', value=refresh)
        raise Exception()
    except:
        control.openSettings('3.1')

def getTraktCredentialsInfo():
    user = TRAKTUSER
    token = control.setting('trakt.token')
    refresh = control.setting('trakt.refresh')
    if (user == '' or token == '' or refresh == ''):
        return False
    return True

#cm - indicators
def getTraktIndicatorsInfo():
    indicator_setting = control.setting('indicators')
    alternative_indicator_setting = control.setting('indicators.alt')
    indicators = alternative_indicator_setting if getTraktCredentialsInfo() else indicator_setting
    return indicators == '1'

def use_trakt_bookmarks():
    if getTraktIndicatorsInfo():
        setting = c.get_setting('indicators.alt')
        if setting == '32314':
            return False
        return True
    return False

def get_trakt_addon_movie_info():
    """
    Check if Trakt is enabled and authorized in the Trakt addon.
    """
    if not c.addon_exists('script.trakt'):
        return False


    try:
        scrobble = control.addon('script.trakt').getSetting('scrobble_movie') or ''
        exclude_http = control.addon('script.trakt').getSetting('ExcludeHTTP') or ''
        authorization = control.addon('script.trakt').getSetting('authorization') or ''
    except LookupError as e:
        c.log(f"[CM Debug @ 309 in trakt.py] Lookuperror in get_trakt_addon_movie_info. Error = {e}")
    except Exception as e:
        c.log(f"[CM Debug @ 311 in trakt.py] Exception in get_trakt_addon_movie_info. Error = {e}")
        return False

    c.log(f"[CM Debug @ 314 in trakt.py] scrobble = {scrobble} | exclude_http = {exclude_http} | authorization = {authorization}")

    return scrobble == 'true' and exclude_http == 'false' and authorization

def getTraktAddonEpisodeInfo():
    """
    Check if Trakt is enabled and authorized in the Trakt addon for episodes.
    """
    try:
        scrobble = control.addon('script.trakt').getSetting('scrobble_episode') == 'true'
        exclude_http = control.addon('script.trakt').getSetting('ExcludeHTTP') == 'false'
        authorization = control.addon('script.trakt').getSetting('authorization') != ''
    except LookupError:
        return False
    return scrobble and exclude_http and authorization

def manager(name, imdb, tmdb, content):
    try:
        post = {"movies": [{"ids": {"imdb": imdb}}]} if content == 'movie' else {"shows": [{"ids": {"tmdb": tmdb}}]}

        items = [(control.lang(32516), '/sync/collection')]
        items += [(control.lang(32517), '/sync/collection/remove')]
        items += [(control.lang(32518), '/sync/watchlist')]
        items += [(control.lang(32519), '/sync/watchlist/remove')]
        items += [(control.lang(32520), '/users/me/lists/%s/items')]

        result = getTraktAsJson('/users/me/lists')
        lists = [(i['name'], i['ids']['slug']) for i in result]
        lists = [lists[i//2] for i in range(len(lists)*2)]

        for i in range(0, len(lists), 2):
            lists[i] = ((control.lang(32521) % lists[i][0]), f'/users/me/lists/{lists[i][1]}/items')

        for i in range(1, len(lists), 2):
            lists[i] = ((control.lang(32522) % lists[i][0]), f'/users/me/lists/{lists[i][1]}/items/remove')
        items += lists

        select = control.selectDialog([i[0] for i in items], control.lang(32515))

        if select == -1:
            return
        elif select == 4:
            t = control.lang(32520)
            k = control.keyboard('', t)
            k.doModal()

            new = k.getText() if k.isConfirmed() else None
            if (new is None or new == ''):
                return

            result = get_trakt('/users/me/lists', post={"name": new, "privacy": "private"})[0]

            try:
                slug = utils.json_loads_as_str(result)['ids']['slug']
            except:
                return control.infoDialog(control.lang(32515), heading=str(name), sound=True, icon='ERROR')

            result = get_trakt(items[select][1] % slug, post=post)[0]
        else:
            result = get_trakt(items[select][1], post=post)[0]

        icon = control.infoLabel('ListItem.Icon') if result is not None else 'ERROR'

        control.infoDialog(control.lang(32515), heading=str(name), sound=True, icon=icon)
    except:
        return

def slug(title):
    title = title.strip().lower()
    title = re.sub('[^a-z0-9_]', '-', title)
    title = re.sub('-{2,}', '-', title)
    return title.rstrip('-')

def sort_list(sort_key, sort_direction, list_data) -> list:
    """
    Sort a list of trakt items based on the given key and direction.

    Args:
        sort_key (str): The key to sort the list by. Options are:
            'rank', 'added', 'title', 'released', 'runtime', 'popularity',
            'percentage', 'votes'.
        sort_direction (str): The direction to sort the list. Options are:
            'asc' or 'desc'.
        list_data (list): The list of trakt items to sort.

    Returns:
        list: The sorted list of trakt items.
    """
    reverse = sort_direction != 'asc'
    if sort_key == 'rank':
        return sorted(list_data, key=lambda x: x['rank'], reverse=reverse)
    elif sort_key == 'added':
        return sorted(list_data, key=lambda x: x['listed_at'], reverse=reverse)
    elif sort_key == 'title':
        return sorted(list_data, key=lambda x: utils.title_key(x[x['type']].get('title')), reverse=reverse)
    elif sort_key == 'released':
        return sorted(list_data, key=lambda x: released_key(x[x['type']]), reverse=reverse)
    elif sort_key == 'runtime':
        return sorted(list_data, key=lambda x: x[x['type']].get('runtime', 0), reverse=reverse)
    elif sort_key == 'popularity':
        return sorted(list_data, key=lambda x: x[x['type']].get('votes', 0), reverse=reverse)
    elif sort_key == 'percentage':
        return sorted(list_data, key=lambda x: x[x['type']].get('rating', 0), reverse=reverse)
    elif sort_key == 'votes':
        return sorted(list_data, key=lambda x: x[x['type']].get('votes', 0), reverse=reverse)
    else:
        return list_data

def released_key(item):
    if 'released' in item:
        return item['released'] or '0'
    elif 'first_aired' in item:
        return item['first_aired'] or '0'
    else:
        return 0

def getActivity() -> int:
    try:
        i = getTraktAsJson('/sync/last_activities')

        if i and isinstance(i, dict):
            movies = i.get('movies', {})
            episodes = i.get('episodes', {})
            shows = i.get('shows', {})
            seasons = i.get('seasons', {})
            lists = i.get('lists', {})

            activity = [
                movies.get('collected_at', 0),
                movies.get('watchlisted_at', 0),
                # shows.get('collected_at', 0),
                shows.get('watchlisted_at', 0),
                episodes.get('collected_at', 0),
                episodes.get('watchlisted_at', 0),
                seasons.get('watchlisted_at', 0),
                lists.get('updated_at', 0),
                lists.get('liked_at', 0),
            ]
            activity = [int(cleandate.new_iso_to_utc(i)) for i in activity]
            activity = sorted(activity, key=int)[-1]


            # activity = [
            #     # i.get('movies')['collected_at'],
            #     # i["movies"]["collected_at"],
            #     # i['episodes']['collected_at'],
            #     # i['movies']['watchlisted_at'],
            #     # i['shows']['watchlisted_at'],
            #     *(
            #         i['seasons']['watchlisted_at'],
            #         # i['episodes']['watchlisted_at'],
            #         i['lists']['updated_at'],
            #         i['lists']['liked_at'],
            #     ),
            # ]
        #activity = [int(cleandate.iso_to_utc(i)) for i in activity]
            # activity = [cleandate.new_iso_to_utc(i) for i in activity]
            # activity = sorted(activity, key=int)[-1]
        else:
            activity = 0

        c.log(f"[CM Debug @ 551 in trakt.py] activity = {activity}")

        return activity
    except ValueError:
        return 0

def getWatchedActivity():
    try:
        i = getTraktAsJson('/sync/last_activities')

        c.log(f"[CM Debug @ 425 in trakt.py] i = {i}")

        activity = []
        activity.append(i['movies']['watched_at'])
        activity.append(i['episodes']['watched_at'])
        #activity = [cleandate.iso_to_utc(i) for i in activity]
        activity = [cleandate.new_iso_to_utc(i) for i in activity]
        #c.log(f"[CM Debug @ 431 in trakt.py] activity = {activity}")
        activity = sorted(activity, key=int)[-1]

        return activity

    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 435 in trakt.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 435 in trakt.py]Exception raised. Error = {e}')
        pass
    #except:
    #    pass

def cachesyncMovies(timeout=0):
    indicators = cache.get(syncMovies, timeout, TRAKTUSER)
    return indicators

def timeoutsyncMovies():
    timeout = cache.timeout(syncMovies, TRAKTUSER)
    return timeout

def syncMovies(user):
    try:
        if getTraktCredentialsInfo() is False:
            c.log("[CM Debug @ 449 in trakt.py] getTraktCredentialsInfo is false")
            return
        indicators = getTraktAsJson('/users/me/watched/movies')
        #c.log(f"[CM Debug @ 452 in trakt.py] indicators = {indicators}")
        indicators = [i['movie']['ids'] for i in indicators]
        indicators = [str(i['imdb']) for i in indicators if 'imdb' in i]
        return indicators
    except:
        pass


def cachesyncTVShows(timeout=0):
    #indicators = cache.get(syncTVShows, timeout, trakt_user)
    indicators = syncTVShows(0)
    #c.log(f"[CM Debug @ 463 in trakt.py] indicators = {indicators}")
    return indicators


def timeoutsyncTVShows():
    timeout = cache.timeout(syncTVShows, TRAKTUSER)
    #c.log(f"[CM Debug @ 499 in trakt.py] timeout = {timeout}")
    if not timeout:
        timeout = 0
    return timeout

def syncTVShows(user):
    try:
        if not getTraktCredentialsInfo():
            c.log("[CM Debug @ 474 in trakt.py] getTraktCredentialsInfo is false")
            return
        #c.log("[CM Debug @ 475 in trakt.py] getTraktCredentialsInfo is true")
        watched_shows = getTraktAsJson('/users/me/watched/shows?extended=full')
        #c.log(f"[CM Debug @ 476 in trakt.py] watched_shows = {watched_shows}")
        indicators = [(show['show']['ids']['tmdb'], show['show']['aired_episodes'], [(s['number'], e['number']) for s in show['seasons'] for e in s['episodes']]) for show in watched_shows]
        #c.log(f"[CM Debug @ 478 in trakt.py] indicators = {indicators}")
        indicators = [(str(tmdb_id), aired_episodes, watched_episodes) for tmdb_id, aired_episodes, watched_episodes in indicators]
        #c.log(f"[CM Debug @ 480 in trakt.py] indicators = {indicators}")
        return indicators
    except:
        pass


def syncTVShows2(user):
    try:
        if getTraktCredentialsInfo() is False:
            c.log("[CM Debug @ 475 in trakt.py] getTraktCredentialsInfo is false")
            return
        indicators = getTraktAsJson('/users/me/watched/shows?extended=full')
        #c.log(f"[CM Debug @ 478 in trakt.py] indicators = {indicators}")
        indicators = [(i['show']['ids']['tmdb'], i['show']['aired_episodes'], sum([[(s['number'], e['number']) for e in s['episodes']] for s in i['seasons']], [])) for i in indicators]
        #c.log(f"[CM Debug @ 480 in trakt.py] indicators = {indicators}")
        indicators = [(str(i[0]), int(i[1]), i[2]) for i in indicators]
        #c.log(f"[CM Debug @ 482 in trakt.py] indicators = {indicators}")
        return indicators
    except:
        pass


def syncSeason(imdb):
    try:
        if getTraktCredentialsInfo() is False:
            return
        indicators = getTraktAsJson(f'/shows/{imdb}/progress/watched?specials=false&hidden=false')
        indicators = indicators['seasons']
        indicators = [(i['number'], [x['completed'] for x in i['episodes']]) for i in indicators]
        #indicators = ['%01d' % int(i[0]) for i in indicators if False not in i[1]]
        indicators = [f"{int(i[0]):01d}" for i in indicators if False not in i[1]]
        return indicators
    except:
        pass


def syncTraktStatus(silent=False):
    try:
        cachesyncMovies()
        cachesyncTVShows()
        if not silent:
            control.infoDialog(control.lang(32092))
    except:
        control.infoDialog('Trakt sync failed')

##########################################
# Movies
##########################################
def markMovieAsWatched(key, media_id):
    if not imdb.startswith('tt'):
        imdb = 'tt' + imdb
    return get_trakt('/sync/history', {"movies": [{"ids": {key: media_id}}]})[0]

def markMovieAsNotWatched(key, media_id):
    if not imdb.startswith('tt'):
        imdb = 'tt' + imdb
    return get_trakt('/sync/history/remove', {"movies": [{"ids": {key: media_id}}]})[0]


###########################################
# TV Shows
###########################################
def markTVShowAsNotWatched(key, media_id):
    return get_trakt('/sync/history/remove', {"shows": [{"ids": {key: media_id}}]})[0]

def markTVShowAsWatched(key, media_id):
    return get_trakt('/sync/history/', {"shows": [{"ids": {key: media_id}}]})[0]


#############################################
# Seasons
#############################################
def markSeasonAsWatched(key, media_id, season):
    c.log(f"[CM Debug @ 578 in trakt.py] season not watched = {season} with key = {key} and media_id = {media_id}")
    return get_trakt('/sync/history', {"shows": [{"seasons": [{"number": int(season)}], "ids": {key:  media_id}}]})[0]

def markSeasonAsNotWatched(key, media_id, season):
    return get_trakt('/sync/history/remove', {"shows": [{"seasons": [{"number": int(season)}], "ids": {key: media_id}}]})[0]

#############################################
# Episodes
#############################################
def markEpisodeAsWatched(key, media_id, season, episode):
    season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
    #season, episode = int(f'{season:01d}'), int(f'{episode:01d}')
    return get_trakt('/sync/history', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {key: media_id}}]})[0]

def markEpisodeAsNotWatched(key, media_id, season, episode):
    season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
    season, episode = int(f'{int(season):01d}'), int(f'{int(episode):01d}')
    return get_trakt('/sync/history/remove', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {key: media_id}}]})[0]


##############################################
# Scrobble
##############################################
def scrobbleMovie(imdb, watched_percent, action):
    try:
        if not imdb.startswith('tt'):
            imdb = 'tt' + imdb
        c.log(f"[CM Debug @ 496 in trakt.py]inside trakt.scrobbleMovie | imdb = {imdb} | watched_percent = {watched_percent} | action = {action}")
        r = get_trakt(f'/scrobble/{action}', {"movie": {"ids": {"imdb": imdb}}, "progress": watched_percent})
        update_progress(imdb=imdb, progress=watched_percent)
        c.log(f"[CM Debug @ 498 in trakt.py] r = {r}")
        #return get_trakt(f'/scrobble/{action}', {"movie": {"ids": {"imdb": imdb}}, "progress": watched_percent})[0]
        return r
    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 511 in trakt.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 511 in trakt.py]Exception raised. Error = {e}')
        pass


def scrobbleEpisode(imdb, season, episode, watched_percent, action):
    try:
        if not imdb.startswith('tt'):
            imdb = 'tt' + imdb


        season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
        #return get_trakt(f'/scrobble/{action}', {"show": {"ids": {"imdb": imdb}}, "episode": {"season": season, "number": episode}, "progress": watched_percent})[0]


        season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
        c.log(f"[CM Debug @ 631 in trakt.py]inside trakt.scrobbleEpisode | imdb = {imdb} | season = {season} | episode = {episode} | watched_percent = {watched_percent} | action = {action}")
        r = get_trakt(f'/scrobble/{action}', {"show": {"ids": {"imdb": imdb}}, "episode": {"season": season, "number": episode}, "progress": watched_percent})
        update_progress(imdb=imdb, season=season, episode=episode, progress=watched_percent)
        c.log(f"[CM Debug @ 522 in trakt.py] r = {r}")
        #return get_trakt(f'/scrobble/{action}', {"show": {"ids": {"imdb": imdb}}, "episode": {"season": season, "number": episode}, "progress": watched_percent})[0]
        return r
    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 535 in trakt.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 535 in trakt.py]Exception raised. Error = {e}')
        pass









def getMovieTranslation(_id, lang, full=False):
    url = f'/movies/{_id}/translations/{lang}'
    try:
        item = getTraktAsJson(url)[0]
        return item if full else item.get('title')
    except:
        pass


def getTVShowTranslation(_id, lang, season=None, episode=None, full=False):
    if season and episode:
        url = f'/shows/{_id}/seasons/{season}/episodes/{episode}/translations/{lang}'
    else:
        url = f'/shows/{_id}/translations/{lang}'

    try:
        item = getTraktAsJson(url)[0]
        return item if full else item.get('title')
    except:
        pass


def getMovieAliases(_id):
    try:
        return getTraktAsJson(f'/movies/{_id}/aliases')
    except:
        return []


def getTVShowAliases(_id):
    try:
        return getTraktAsJson(f'/shows/{_id}/aliases')
    except:
        return []


def getMovieSummary(_id, full=True):
    try:
        url = f'/movies/{_id}'
        if full:
            url += '?extended=full'
        return getTraktAsJson(url)
    except:
        return


def getTVShowSummary(_id, full=True):
    try:
        url = f'/shows/{_id}'
        if full:
            url += '?extended=full'
        return getTraktAsJson(url)
    except:
        return


def getPeople(_id, content_type, full=True):
    try:
        url = f'/{content_type}/{_id}/people'
        if full:
            url += '?extended=full'
        return getTraktAsJson(url)
    except:
        return


def SearchAll(title, year, full=True):
    try:
        return SearchMovie(title, year, full) + SearchTVShow(title, year, full)
    except:
        return


def SearchMovie(title, year, full=True):
    try:
        title = quote_plus(title)
        url = f'/search/movie?query={title}'

        if year:
            url += f'&year={year}'
        if full:
            url += '&extended=full'
        return getTraktAsJson(url)
    except:
        return


def SearchTVShow(title, year, full=True):
    try:
        title = quote_plus(title)
        url = f'/search/show?query={title}'

        if year:
            url += f'&year={year}'
        if full:
            url += '&extended=full'
        return getTraktAsJson(url)
    except:
        return

def IdLookup(content, _type, type_id):
    try:
        r = getTraktAsJson(f'/search/{_type}/{type_id}?type={content}')
        return r[0].get(content, {}).get('ids', [])
    except:
        return {}

def getGenre(content, _type, type_id):
    try:
        r = f'/search/{_type}/{type_id}?type={content}&extended=full'
        c.log(f"[CM Debug @ 597 in trakt.py] r = {r}")
        r = getTraktAsJson(r)
        r = r[0].get(content, {}).get('genres', [])
        return r
    except:
        return []

def getEpisodeRating(imdb, season, episode):
    try:
        if not imdb.startswith('tt'):
            imdb = 'tt' + imdb
        url = f'/shows/{imdb}/seasons/{season}/episodes/{episode}/ratings'
        r = getTraktAsJson(url)
        r1 = r.get('rating', '0')
        r2 = r.get('votes', '0')
        return str(r1), str(r2)
    except:
        return







####################################################################################################
# Database - 25-11-2024
#
# cm new from here to add functions for syncing with trakt
#
####################################################################################################
sql_dict = {
    'sql_create_movies_collection' :
        'CREATE TABLE IF NOT EXISTS movies_collection (last_collected_at TEXT, last_updated_at TEXT, Title TEXT, Year INT, trakt INT, slug TEXT, imdb TEXT, tmdb INT, UNIQUE(trakt, imdb, tmdb));',
    'sql_create_shows_collection' :
        'CREATE TABLE IF NOT EXISTS shows_collection (last_collected_at TEXT, last_updated_at TEXT, Title TEXT, Year INT, trakt INT, slug TEXT, tvdb INT, imdb TEXT, tmdb INT, tvrage TEXT, UNIQUE(trakt, tvdb, imdb, tmdb));',
    'sql_create_seasons_collection' :
        'CREATE TABLE IF NOT EXISTS seasons_collection (trakt INT, tvdb INT, imdb TEXT, tmdb INT, season INT, episode INT, collected_at TEXT);',
    'sql_create_trakt_progress' :
        'CREATE TABLE progress (media_type text not null, trakt integer primary key, imdb text, tmdb integer, tvdb integer, showtrakt integer, showimdb text, showtmdb integer, showtvdb integer, season integer, episode integer, resume_point real, curr_time text, last_played text, resume_id integer, tvshowtitle text, title text, year integer)',
    'sql_insert_trakt_progress' :
        'INSERT OR REPLACE INTO progress (media_type, trakt, imdb, tmdb, tvdb, showtrakt, showimdb, showtmdb, showtvdb, season, episode, resume_point, curr_time, last_played, resume_id, tvshowtitle, title, year) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?, ?, ?, ?) ',
    'sql_create_service' :
        'CREATE TABLE IF NOT EXISTS service(setting TEXT, value TEXT, UNIQUE(setting));',
    'sql_update_service' :
        'UPDATE service SET value = ? where setting = ?',

    'sql_create_sync_data' :
        'CREATE TABLE sync_data (media_type TEXT NOT NULL, name TEXT NOT NULL, date TEXT);',
    'sql_insert_sync_data' :
        'INSERT OR REPLACE INTO sync_data (media_type, name, date) VALUES (?,?,?)',
    'sql_select_sync_data' :
        'SELECT date FROM sync_data WHERE media_type = ? AND name = ?',
    'sql_delete_sync_data' :
        'DELETE FROM sync_data WHERE media_type = ? AND name = ?',
    'sql_create_trakt_watched' :
        'CREATE TABLE IF NOT EXISTS watched (media_type text not null, trakt integer, tvdb integer, imdb TEXT, tmdb integer, season integer, episode integer, last_played text, title text, unique(media_type, trakt, season, episode))',
    'sql_insert_trakt_watched' :
        'INSERT OR REPLACE INTO watched (media_type, trakt, tvdb, imdb, tmdb, season, episode, last_played, title) VALUES (?,?,?,?,?,?,?,?,?)',
}

def syncTrakt() -> None:
    """
    Syncs Kodi status with Trakt.tv
    """
    if not control.player.isPlayingVideo():
        c.infoDialog('Syncing with Trakt', 'Please wait', icon='main_classy.png', sound=False)
    else:
        c.log('Syncing with Trakt', 1)
    try:
        fill_progress_table()
        fill_trakt_watched()

        #endpoint = 'sync/watched/movies'

        _types = ['movies', 'episodes']
        start = '2016-06-01T00:00:00.000Z'
        end = cleandate.now_to_iso()
        for _type in _types:
            endpoint = f'/sync/history/{_type}?start_at={start}&end_at={end}'
            result = getTraktAsJson(endpoint)

            # TODO: add a function to insert into the database, nothing happens with result
            # TODO: add a fill_history function

        sync_last_activities()

        if not control.player.isPlayingVideo():
            return c.infoDialog('Syncing with Trakt Finished', 'Please wait', icon='main_classy.png', sound=False)
        else:
            c.log('Syncing with Trakt Finished', 1)
    except OperationalError as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 854 in trakt.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 855 in trakt.py]Exception raised. Error = {e}')

    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 860 in trakt.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 861 in trakt.py]Exception raised. Error = {e}')



def get_show_extended_info(trakt_id):
    endpoint = f'/shows/{trakt_id}?extended=full'
    return getTraktAsJson(endpoint)

def fill_progress_table() -> None:
    """
    Fetches progress from trakt and inserts/updates it in the database (trakt_progress).
    This includes movies and episodes.
    """
    start, end = get_start_end(diff=365)
    endpoint = f'sync/playback/movie?extended=full&start_at={start}&end_at={end}'

    if result := getTraktAsJson(endpoint):
        if not table_exists('trakt_progress'):
            create_table('trakt_progress')

        for item in result:
            media_type = item.get('type')
            progress = item.get('progress')
            ids = item.get(media_type).get('ids')
            trakt_id = ids.get('trakt')
            tvdb_id = ids.get('tvdb')
            tmdb_id = ids.get('tmdb')
            imdb_id = ids.get('imdb')
            year = item.get(media_type).get('year')
            title = item.get(media_type).get('title')
            season = item.get(media_type).get('season') if media_type == 'episode' else 0
            episode = item.get(media_type).get('number') if media_type == 'episode' else 0
            current_time = get_now_in_iso()
            last_played = item.get('paused_at')
            resume_id = item.get('id')

            if 'show' in item:
                tvshowtitle = item.get('show').get('title')
                show_trakt_id = item.get('show').get('ids').get('trakt')
                show_imdb_id = item.get('show').get('ids').get('imdb')
                show_tmdb_id = item.get('show').get('ids').get('tmdb')
                show_tvdb_id = item.get('show').get('ids').get('tvdb')
            else:
                tvshowtitle = ''
                show_trakt_id = 0
                show_imdb_id = 0
                show_tmdb_id = 0
                show_tvdb_id = 0

            insert_trakt_progress(
                media_type,
                trakt_id,
                imdb_id,
                tmdb_id,
                tvdb_id,
                show_trakt_id,
                show_imdb_id,
                show_tmdb_id,
                show_tvdb_id,
                season,
                episode,
                progress,
                current_time,
                last_played,
                resume_id,
                tvshowtitle,
                title,
                year,
            )

def update_progress_in_database(imdb_id: str = '', trakt_id: int = 0, tmdb_id: int = 0, season: int = 0, episode: int = 0, progress: int = 0) -> None:
    """
    Updates progress in the trakt sync database.
    """
    try:
        connection = get_connection(control.traktsyncFile, return_as_dict=True)
        cursor = connection.cursor()

        conditions = [
            f"imdb = '{imdb_id}'" if imdb_id else None,
            f"trakt = {trakt_id}" if trakt_id else None,
            f"tmdb = {tmdb_id}" if tmdb_id else None,
            f"season = {season} and episode = {episode}" if season and episode else None,
        ]

        conditions = [condition for condition in conditions if condition]


        sql = 'UPDATE progress SET resume_point = ? WHERE ' + ' and '.join(conditions)
        cursor.execute(sql, (progress,))
        connection.commit()
        cursor.close()
        connection.close()
    except OperationalError as e:
        c.log(f"[CM Debug @ 1080 in trakt.py] operational error in update_progress_in_database: {e}")


def fill_trakt_watched() -> None:
    """
    Fetches watched from trakt and inserts/updates it in the database (trakt_watched).
    This includes movies and episodes.
    """
    try:
        dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
        dbcur = get_connection_cursor(dbcon)


        _types = ['movies', 'shows']

        for _type in _types:
            endpoint = f'sync/watched/{_type}'
            if result := getTraktAsJson(endpoint):
                if not table_exists('trakt_watched'):
                    create_table('trakt_watched')

                for item in result:
                    media_type = _type
                    if media_type == 'movies':
                        media_type = 'movie'
                    if media_type == 'shows':
                        media_type = 'show'
                    trakt_id = item[media_type]['ids']['trakt']
                    tvdb_id = item[media_type]['ids'].get('tvdb', 0)
                    imdb_id = item[media_type]['ids'].get('imdb')
                    tmdb_id = item[media_type]['ids'].get('tmdb')
                    title = item[media_type]['title']

                    if media_type == 'movie':
                        seasons = 0
                        episode = 0
                        last_watched_at = item['last_watched_at']
                        dbcur.execute(sql_dict['sql_insert_trakt_watched'], (media_type, trakt_id, tvdb_id, imdb_id, tmdb_id, seasons, episode, last_watched_at, title))
                    else:
                        for season in item['seasons']:
                            season_nr = season['number']
                            for episodes in season['episodes']:
                                episode_nr = episodes['number']
                                last_watched_at = episodes['last_watched_at']
                                dbcur.execute(sql_dict['sql_insert_trakt_watched'], (media_type, trakt_id, tvdb_id, imdb_id, tmdb_id, season_nr, episode_nr, last_watched_at, title))

                dbcon.commit()
                dbcur.close()
                dbcon.close()

    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 1133 in trakt.py] Traceback:: {failure}')
        c.log(f'[CM Debug @ 1134 in trakt.py] Exception raised. Error = {e}')



def fill_trakt_watched_orig() -> None:
    try:

        _types = ['movies', 'shows']
        #_types = ['shows']

        for _type in _types:
            c.log(f"[CM Debug @ 927 in trakt.py]type = {_type} with type = {type(_type)}")
            endpoint = f'sync/watched/{_type}'
            result = getTraktAsJson(endpoint)
            #c.log(f"[CM Debug @ 827 in trakt.py] result = {result}")
            if result:
                if _type == 'movies':
                    indicators = [i['movie']['ids']['tmdb'] for i in result]
                    c.log(f"[CM Debug @ 831 in trakt.py] indicators = {indicators}")
                #else:
                    #indicators = [(show['show']['ids']['tmdb'], show['show']['aired_episodes'], [(s['number'], e['number']) for s in show['seasons'] for e in s['episodes']]) for show in result]
                    #c.log(f"[CM Debug @ 834 in trakt.py] indicator shows = {indicators}")
                if not table_exists('trakt_watched'):
                    create_table('trakt_watched')


                dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
                dbcur = get_connection_cursor(dbcon)

                for item in result:
                    media_type = _type
                    trakt_id = item.get(_type).get('ids').get('trakt')
                    tvdb_id = item.get(_type).get('ids').get('tvdb') or 0
                    imdb_id = item.get(_type).get('ids').get('imdb')
                    tmdb_id = item.get(_type).get('ids').get('tmdb')
                    title = item.get(_type).get('title')


                    if _type == 'movies':
                        seasons = 0
                        episode = 0
                        last_watched_at = item.get('last_watched_at')
                        dbcur.execute(sql_dict['sql_insert_trakt_watched'], (media_type, trakt_id, tvdb_id, imdb_id, tmdb_id, seasons, episode, last_watched_at, title))
                    else:
                        seasons = item.get('seasons')
                        c.log(f"[CM Debug @ 959 in trakt.py] seasons = {seasons}")
                        for season in seasons:
                            season_nr = season.get('number')
                            c.log(f"[CM Debug @ 961 in trakt.py] season = {season_nr}")
                            for episodes in season:
                                episode_nr = episodes.get('number')
                                c.log(f"[CM Debug @ 964 in trakt.py] episode_nr = {episode_nr}")
                                for item in episodes.get('episodes'):
                                    c.log(f"[CM Debug @ 965 in trakt.py] item = {item}")
                                    last_watched_at = item.get('last_watched_at')
                                    c.log(f"[CM Debug @ 858 in trakt.py]===> last_watched = {last_watched_at}")
                                    dbcur.execute(sql_dict['sql_insert_trakt_watched'], (media_type, trakt_id, tvdb_id, imdb_id, tmdb_id, season_nr, episode_nr, last_watched_at, title))

                dbcon.commit()
                dbcur.close()
                dbcon.close()

    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 980 in trakt.py] Traceback:: {failure}')
        c.log(f'[CM Debug @ 981 in trakt.py] Exception raised. Error = {e}')
        pass






def sync_last_activities():
    #sync last activities
    i = getTraktAsJson('/sync/last_activities')
    _all = i.get('all')
    _crew = cleandate.now_to_iso()#last run

    #c.log(f"[CM Debug @ 851 in trakt.py] all = {_all} and crew = {_crew}")
    update_service(_all, _crew)
    #c.log(f"[CM Debug @ 853 in trakt.py] i = {repr(i)}")
    #activity = []
    #activity = [cleandate.new_iso_to_utc(i) for i in activity]
    #activity = sorted(activity, key=int)[-1]



def update_service(_all, _crew):
    try:
        dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
        dbcur = get_connection_cursor(dbcon)
        d = {'all':_all, 'crew_last_sync': _crew}

        if not table_exists('service'):
            create_table('service')

        for k,v in d.items():
            sql = sql_dict['sql_update_service']
            #sql = sql_dict['sql_update_service']
            #c.log(f"[CM Debug @ 880 in trakt.py] sql = {sql}")
            #dbcur.execute(sql, (_all, _crew))
            dbcur.execute(sql, (v, k))
        dbcon.commit()
        dbcur.close()
        dbcon.close()
    except Exception as e:
        c.log(f"[CM Debug @ 831 in trakt.py] Exception raised. Error = {e}")


def insert_trakt_progress(media_type, trakt, imdb, tmdb, tvdb, showtrakt, showimdb, showtmdb, showtvdb, season, episode, resume_point, curr_time, last_played, resume_id, tvshowtitle, title, year):
    dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
    dbcur = get_connection_cursor(dbcon)
    sql = sql_dict['sql_insert_trakt_progress']
    dbcur.execute(sql, (media_type, trakt, imdb, tmdb, tvdb, showtrakt, showimdb, showtmdb, showtvdb, season, episode, resume_point, curr_time, last_played, resume_id, tvshowtitle, title, year))
    dbcon.commit()
    dbcur.close()
    dbcon.close()


def get_start_end(diff):
    """
    Returns a tuple of two strings representing the ISO 8601
    formatted dates for the current date and the date a given
    number of days in the past.

    :param diff: the number of days ago to calculate the start date
    :return: a tuple of two strings, (start, end)
    """
    start = datetime.now() - timedelta(days=diff)
    start = start.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return quote_plus(start), quote_plus(end)

def get_now_in_iso():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")

def get_connection(file, return_as_dict=False):
    """
    Establishes a connection to a SQLite database file

    :param file: the path to the SQLite database file
    :param return_as_dict: if True, the row factory will be set to return results as dictionaries
    :return: a database connection object
    """
    try:

        if not os.path.isfile(control.dataPath):
            control.makeFile(control.dataPath)

        dbcon = database.connect(file)
        dbcon.execute('PRAGMA page_size = 32768')
        dbcon.execute('PRAGMA cache_size = 10000000')
        dbcon.execute('PRAGMA mmap_size = 30000000000')
        #dbcon.execute('PRAGMA journal_mode = OFF')
        dbcon.execute('PRAGMA journal_mode = MEMORY')
        dbcon.execute('PRAGMA temp_store = MEMORY')
        dbcon.execute('PRAGMA synchronous = OFF')

        if return_as_dict:
            dbcon.row_factory = _dict_factory
        return dbcon
    except Exception as e:
        c.log(f"Error getting database connection: {e}")
        return None

def get_connection_cursor(db_connection):
    """
    Returns a database cursor object from a connection
    :param db_connection: a database connection object
    :return: a database cursor object
    """
    if db_connection is None:
        c.log("Database connection is None")
        return None

    try:
        return db_connection.cursor()
    except Exception as e:
        c.log(f"Error getting database cursor: {e}")
        return None


def open_connection(file = control.traktsyncFile):
    """
    Opens a connection to a SQLite database file

    :param file: the path to the SQLite database file
    :return: a database connection object
    """
    conn = get_connection(file)
    cursor = get_connection_cursor(conn)
    return None if conn is None or cursor is None else (conn, cursor)

def commit(db_connection) -> None:
    _commit(db_connection)

def close_connection(db_connection):
    """
    Closes a database connection

    :param db_connection: a database connection object
    """
    if db_connection is not None:
        db_connection.close()
    else:
        c.log("Database connection is None")


def _commit(db_connection):
    """
    Commits the current transaction to the database.

    :param db_connection: a database connection object
    Logs an error if the connection is None or if an exception occurs during commit.
    """
    if db_connection is None:
        c.log("Database connection is None")
        return
    else:
        c.log("Database connection is not None")
    try:
        if db_connection is not None:
            c.log(f"Database connection is of type(): {type(db_connection)}")
            db_connection.commit()
            c.log("Database connection is initialized")
        else:
            c.log("Database connection is not initialized")
    except AttributeError:
        c.log("Database connection does not have a connection attribute")
    except Exception as e:
        c.log(f"Error committing to the database: {e}")



def _dict_factory(cursor, row):
    """
    A factory function that constructs a dictionary from a SQLite query result.
    :param cursor: a SQLite cursor object
    :param row: a row from the SQLite query result
    :return: a dictionary where the keys are the column names and the values are the corresponding
    :values from the row
    """
    if cursor is None or row is None:
        raise ValueError("cursor and row must not be None")

    row_dict = {}
    for index, column in enumerate(cursor.description):
        try:
            row_dict[column[0]] = row[index]
        except Exception as e:
            c.log(f"Error constructing dictionary from SQLite query result: {e}")
    return row_dict

####
# end of core database functions


def get_db_connection(file=control.traktsyncFile, return_as_dict=True):
    """
    Returns a database connection and cursor for the specified SQLite file.

    Attempts to establish a connection and retrieve a cursor; returns (None, None) if unsuccessful.

    Args:
        file (str): Path to the SQLite database file.
        return_as_dict (bool): If True, rows are returned as dictionaries.

    Returns:
        tuple: (database connection, database cursor) or (None, None) if connection fails.
    """
    try:
        dbcon = get_connection(file, return_as_dict)
        dbcur = get_connection_cursor(dbcon)

        # check if we have a valid connection and cursor
        if dbcur and dbcon:
            return dbcon, dbcur
        c.log("Error: dbcur or dbcon is None, cannot create connection")
        return None, None

    except (database.Error, database.OperationalError) as e:
        c.log(f"Error getting database connection: {e}")
        return None, None

####
# start of trakt functions

def check_sync_tables():
    """
    Checks if the trakt sync tables exist and creates them if not.
    """
    try:
        #fetch activities
        last_activities = getTraktAsJson('/sync/last_activities')
        c.log(f"[CM Debug @ 741 in trakt.py] last_activities = type(last_activities) = {type(last_activities)} and content = {last_activities}")

        if last_activities:
            create_trakt_tables(last_activities)
        else:
            c.log("Error: last_activities is None")
    except Exception as e:
        c.log(f"Error checking sync tables: {e}")



def fetch_last_service(fetch_all=False):
    """
    Retrieves the last sync timestamp from the trakt sync database.

    Args:
        fetch_all (bool): If True, fetches all rows from the table, otherwise just the first row.

    Returns:
        The last sync timestamp (or all timestamps if fetch_all is True)
    """
    try:
        dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
        dbcur = get_connection_cursor(dbcon)

        if fetch_all:
            sql = 'SELECT value FROM service where setting = "crew_last_sync"'
            dbcur.execute(sql)
            r = dbcur.fetchall()
        else:
            sql = 'SELECT value FROM service where setting = "crew_last_sync"'
            dbcur.execute(sql)
            r = dbcur.fetchone()
        return r

    except Exception as e:
        c.log(f"Error fetching last sync timestamp: {e}")
        return None
    finally:
        dbcon.close()




def fetch_last_activity(fetch_all=True):
    try:
        dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
        dbcur = get_connection_cursor(dbcon)

        if all:
            sql = 'SELECT value FROM service where setting = "all"'
            dbcur.execute(sql)
            r = dbcur.fetchall()
        else:
            sql = 'SELECT value FROM service where setting = "all"'
            dbcur.execute(sql)
            r = dbcur.fetchone()
        return r
    except Exception as e:
        c.log(f"Error fetching last activity: {e}")
        return None
    finally:
        dbcon.close()




def create_trakt_tables(last_activities):
    """
    Creates the tables in the trakt sync database if they don't exist
    """
    try:
        dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
        dbcur = get_connection_cursor(dbcon)

        if dbcur and dbcon: #check if we have a valid connection and cursor
            for key, val in last_activities.items():
                if isinstance(val, str):
                    if not table_exists('service'):
                        sql = "CREATE TABLE IF NOT EXISTS service(setting TEXT, value TEXT, UNIQUE(setting));"
                        dbcur.execute(sql)

                    sql = f"INSERT OR REPLACE INTO service Values ('{key}', '{val}')"
                    dbcur.execute(sql)

                elif isinstance(val, dict):
                    if not table_exists(key):
                        sql = f"CREATE TABLE IF NOT EXISTS {key} (setting TEXT, value TEXT, UNIQUE(setting));"
                        dbcur.execute(sql)

                    for k, v in val.items():
                        sql = f"INSERT OR REPLACE INTO {key} Values ('{k}', '{v}')"
                        dbcur.execute(sql)

                    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
                    sql = f"INSERT OR REPLACE INTO service Values ('crew_last_sync', '{timestamp}')"
                    dbcur.execute(sql)
        else:
            c.log("Error: dbcur or dbcon is None, cannot create trakt tables")
            return

    except Exception as e:
        c.log(f'Exception in create_trakt_tables(last_activities): Error = {e}')
    finally:
        dbcon.commit()
        dbcon.close()

def create_table(name='', query = ''):

    try:
        if not name and not query:
            c.log(f"Trying to create table in trakt::create_table without name or query. name = {name}, query = {query}, returning")
            return

        dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
        dbcur = get_connection_cursor(dbcon)

        if f'sql_create_{name}' in sql_dict:

            sql = sql_dict[f'sql_create_{name}']
            if dbcur:
                dbcur.execute(sql)
            c.log(f"[CM Debug @ 1444 in trakt.py] sql = {sql}")
        elif query:
            if query.lower().startswith('create table'):
                if dbcur:
                    dbcur.execute(query)
            else:
                c.log(f"Trying to use invalid query in trakt::create_table, query = {query}, returning")

        #no return here, gracefully close the connection

        if dbcon:
            dbcon.commit()
            dbcon.close()

    except OperationalError as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 1463 in trakt.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 1464 in trakt.py]Exception raised. Error = {e}')
        c.log(f"[CM Debug @ 1465 in trakt.py] SQL Operational Error: {e}")

    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 987 in trakt.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 988 in trakt.py]Exception raised. Error = {e}')




def get_trakt_collection(media_type="all") -> None:
    try:
        do_commit = False

        if media_type in ['movies', 'all']:
            if not table_exists('movies_collection'):
                sql = sql_dict['sql_create_movies_collection']
                dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
                dbcur = get_connection_cursor(dbcon)
                dbcur.execute(sql)
                do_commit = True
            movie_collection = getTraktAsJson('/sync/collection/movies')
            insert_collection(movie_collection, 'movies')

        if media_type in ['shows', 'all']:
            if not table_exists('shows_collection'):
                sql = sql_dict['sql_create_shows_collection']
                c.log(f"[CM Debug @ 893 in trakt.py] sql is of type: {type(sql)} and = {sql}")
                dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
                dbcur = get_connection_cursor(dbcon)
                dbcur.execute(sql)
                if not table_exists('seasons_collection'):
                    sql = sql_dict['sql_create_seasons_collection']
                    dbcur.execute(sql)
                do_commit = True
            show_collection = getTraktAsJson('/sync/collection/shows')
            insert_collection(show_collection, 'shows')

        if do_commit:
            dbcon.commit()

    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 839 in trakt.py]Traceback:: {failure}')

        c.log(f'[CM Debug @ 839 in trakt.py]Exception raised. Error = {e}')
    finally:
        if do_commit:
            dbcon.close()
        c.infoDialog('trakt collection updated', icon="main_orangehat.png", time=2000)

def get_collection(media_type, trakt_id=0, imdb_id='', tmdb_id=0):
    """
    Retrieves collection entries from the trakt sync database for the specified media type and identifiers.

    Args:
        media_type (str): The type of media to retrieve, either 'movies' or 'shows'.
        trakt_id (int, optional): The trakt ID for the media. Defaults to 0.
        imdb_id (str, optional): The IMDb ID for the media. Defaults to an empty string.
        tmdb_id (int, optional): The TMDb ID for the media. Defaults to 0.

    Returns:
        list: A list of rows from the database matching the specified identifiers.
    """
    try:

        if media_type not in ['movies', 'shows']:
            c.log(f"[CM Debug @ 1607 in trakt.py] media_type = {media_type}, not in ['movies', 'shows'], returning")
            return
        if not table_exists(f"{media_type}_collection"):
            c.log(f"[CM Debug @ 1608 in trakt.py] table doesn't exist, creating {media_type}_collection with sql = {sql_dict[f'sql_create_{media_type}_collection']}")
            create_table(f"{media_type}_collection", sql_dict[f"sql_create_{media_type}_collection"])
        query = []
        media_type = media_type.lower()
        c.log(f"[CM Debug @ 1609 in trakt.py] media_type = {media_type}, trakt_id = {trakt_id}, imdb_id = {imdb_id}, tmdb_id = {tmdb_id}")


        if trakt_id == 0 and imdb_id == '' and tmdb_id == 0:
            sql = f"SELECT * FROM {media_type}_collection"
            c.log(f"[CM Debug @ 1614 in trakt.py] sql is of type: {type(sql)} and = {sql}")
        else:
            if trakt_id != 0:
                query.append(f"trakt = {trakt_id}")
            if imdb_id != '':
                query.append(f"imdb = '{imdb_id}'")
            if tmdb_id != 0:
                query.append(f"tmdb = {tmdb_id}")
            sql = f"SELECT * FROM {media_type}_collection WHERE {' AND '.join(query)}"
        c.log(f"[CM Debug @ 1224 in trakt.py] sql is of type: {type(sql)} and = {sql}")
        dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
        dbcur = get_connection_cursor(dbcon)
        dbcur.execute(sql)
        rows = dbcur.fetchall()

        dbcon.commit()

        if len(rows) > 0:
            return rows
        else:
            return

    except OperationalError as e:
        c.log(f'Exception raised in get_collection. Error = {e}')
    except Exception as e:
        c.log(f'Exception raised in get_collection. Error = {e}')
    finally:
        dbcur.close()
        dbcon.close()




def get_collection_orig(media_type, trakt=0, imdb='', tmdb=0):
    """
    Retrieves collection entries from the trakt sync database for the specified media type and identifiers.

    Args:
        mediatype (str): The type of media to retrieve, either 'movies' or 'shows'.
        trakt (int, optional): The trakt ID for the media. Defaults to 0.
        imdb (str, optional): The IMDb ID for the media. Defaults to an empty string.
        tmdb (int, optional): The TMDb ID for the media. Defaults to 0.

    Returns:
        list: A list of rows from the database matching the specified identifiers.
    """
    try:
        sql = ''
        if media_type == 'movies':
            if trakt == 0 and imdb == '' and tmdb == 0:
                sql = "SELECT * FROM movies_collection"
            elif imdb == '' and tmdb == 0:
                sql = f"SELECT * FROM movies_collection WHERE trakt = {trakt}"
            elif trakt == 0 and tmdb == 0:
                sql = f"SELECT * FROM movies_collection WHERE imdb = '{imdb}'"
            elif trakt == 0 and imdb == '':
                sql = f"SELECT * FROM movies_collection WHERE tmdb = {tmdb}"
            elif trakt == 0:
                sql = f"SELECT * FROM movies_collection WHERE imdb = '{imdb}' AND tmdb = {tmdb}"
            elif imdb == '':
                sql = f"SELECT * FROM movies_collection WHERE trakt = {trakt} AND tmdb = {tmdb}"
            else:
                sql = f"SELECT * FROM movies_collection WHERE trakt = {trakt} OR imdb = '{imdb}' OR tmdb = {tmdb}"
        elif media_type == 'shows':
            sql = f"SELECT * FROM shows_collection WHERE trakt = '{trakt}' AND imdb = '{imdb}' AND tmdb = '{tmdb}'"
        c.log(f"[CM Debug @ 934 in trakt.py] sql is of type: {type(sql)} and = {sql}")
        dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
        dbcur = get_connection_cursor(dbcon)
        dbcur.execute(sql)
        return dbcur.fetchall()
    except Exception as e:
        c.log(f'Exception raised in get_collection. Error = {e}')







def table_exists(table_name) -> bool:
    """
    Checks if a table exists in the trakt sync database.

    Args:
        table_name (str): The name of the table to check.

    Returns:
        bool: True if the table exists, False if it does not.
    """
    try:
        dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
        dbcur = get_connection_cursor(dbcon)

        sql = f"SELECT count(*) as aantal FROM sqlite_master WHERE type='table' AND name='{table_name}'"
        dbcur.execute(sql)
        row = dbcur.fetchone()
        if row['aantal'] == 0:
            return False
        else:
            return True

    except Exception as e:
        c.log(f'Exception raised in tables_exists. Error = {e}')
        return False


def insert_collection(collection, mediatype):
    try:
        table_name = ''

        if mediatype == 'movies':
            table_name = 'movies_collection'
        elif mediatype == 'shows':
            table_name = 'shows_collection'

        #check if table exists
        dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
        dbcur = get_connection_cursor(dbcon)
        if not table_exists(table_name):
            sql = sql_dict[f'sql_create_{table_name}']
            dbcur.execute(sql)
            dbcon.commit()

        for item in collection:
            if mediatype == 'movies':
                last_collected_at = item['collected_at']
                last_updated_at = item['updated_at']
                title = item['movie']['title']
                year = item['movie']['year']
                trakt = item['movie']['ids']['trakt']
                slug = item['movie']['ids']['slug']
                imdb = item['movie']['ids']['imdb']
                tmdb = item['movie']['ids']['tmdb']

                sql = f"INSERT OR REPLACE INTO '{table_name}' Values ('{last_collected_at}', '{last_updated_at}', '{title}', {year}, {trakt}, '{slug}', '{imdb}', {tmdb})"
                dbcur.execute(sql)
                dbcon.commit()

            elif mediatype == 'shows':
                trakt = item['show']['ids']['trakt']
                imdb = item['show']['ids']['imdb']
                tmdb = item['show']['ids']['tmdb']
                title = item['show']['title']
                year = item['show']['year']



        c.log(f"[CM Debug @ 839 in trakt.py] collection = {collection}")
        c.log(f"[CM Debug @ 839 in trakt.py] collection = {table_name}")

    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 839 in trakt.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 839 in trakt.py]Exception raised. Error = {e}')
        pass

# TODO needs to be implemented
def sync_collection(collection):
    try:
        c.log(f"[CM Debug @ 833 in trakt.py] collection = {collection}")

    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 857 in trakt.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 858 in trakt.py]Exception raised. Error = {e}')
        pass



def get_trakt_progress(media_type: str, trakt_id: int = 0) -> list:
    """
    Retrieves progress entries from the trakt sync database for the specified media type and ID.

    Args:
        media_type (str): The type of media to retrieve, either 'movies' or 'shows'.
        trakt_id (int, optional): The ID of the media to retrieve. Defaults to 0.

    Returns:
        list: A list of rows from the database matching the specified media type and ID.
    """
    try:
        dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
        dbcur = get_connection_cursor(dbcon)
        sql = f"SELECT * FROM progress WHERE media_type = '{media_type}'"
        c.log(f"[CM Debug @ 1431 in trakt.py] sql = {sql}")
        if trakt_id:
            sql += f" AND trakt_id = {trakt_id}"

        c.log(f"[CM Debug @ 1616 in trakt.py] sql is of type: {type(sql)} and = {sql}")

        dbcur.execute(sql)
        c.log(f"[CM Debug @ 1620 in trakt.py] sql is of type: {type(sql)} and = {sql}")
        rows = dbcur.fetchall()
        dbcon.commit()

        return rows

    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 1250 in trakt.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 1251 in trakt.py]Exception raised. Error = {e}')
        results = []








def update_trakt_sync_table(key, value):
    """
    Updates the value in the trakt sync table
    """
    dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
    dbcur = get_connection_cursor(dbcon)
    sql = "INSERT OR REPLACE INTO service Values (?, ?)"
    dbcur.execute(sql, (key, value))
    _commit(dbcon)

def get_trakt_sync_value(key):
    """
    Returns the value from the trakt sync table for the given key
    """
    dbcon = get_connection(control.traktsyncFile, return_as_dict=True)
    dbcur = get_connection_cursor(dbcon)
    sql = "SELECT value FROM service WHERE setting = ?"
    result = dbcur.execute(sql, (key,))
    value = result.fetchone()
    return value[0] if value else None
