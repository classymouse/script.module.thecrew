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
import time
import json

from urllib.parse import urljoin, quote_plus
import requests

from . import cache
from . import cleandate
from . import client
from . import control
from . import utils
from .crewruntime import c



BASE_URL = 'https://api.trakt.tv'
V2_API_KEY = '482f9db52ee2611099ce3aa1abf9b0f7ed893c6d3c6b5face95164eac7b01f71'
CLIENT_SECRET = '80a2729728b53ba1cc38137b22f21f34d590edd35454466c4b8920956513d967'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

trakt_user = control.setting('trakt.user').strip()

def get_trakt(url, post=None):
    try:
        url = urljoin(BASE_URL, url)
        post = json.dumps(post) if post else None
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-key': V2_API_KEY,
            'trakt-api-version': '2'
            }

        if getTraktCredentialsInfo():
            headers.update({
            'Authorization': 'Bearer %s' %
            control.setting('trakt.token')
            })

        if not post:
            r = requests.get(url, headers=headers, timeout=30)
        else:
            r = requests.post(url, data=post, headers=headers, timeout=30)

        r.encoding = 'utf-8'

        resp_code = str(r.status_code)
        resp_header = r.headers
        result = r.text

        if resp_code in ['423', '500', '502', '503', '504', '520', '521', '522', '524']:
            c.log(f'Trakt Error:{resp_code}')
            control.infoDialog('Trakt Error: ' + resp_code, sound=True)
            return
        elif resp_code in ['429']:
            c.log(f'Trakt Rate Limit Reached: {resp_code}')
            control.infoDialog('Trakt Rate Limit Reached: ' + resp_code, sound=True)
            return
        elif resp_code in ['404']:
            c.log(f'Trakt error: Object Not Found :{resp_code}')
            return

        if resp_code not in ['401', '403', '405']:
            return result, resp_header

        oauth = urljoin(BASE_URL, '/oauth/token')
        opost = {
                    'client_id': V2_API_KEY,
                    'client_secret': CLIENT_SECRET,
                    'redirect_uri': REDIRECT_URI,
                    'grant_type': 'refresh_token',
                    'refresh_token': control.setting('trakt.refresh')
                }

        # result = client.request(oauth, post=json.dumps(opost), headers=headers)
        # result = utils.json_loads_as_str(result)

        result = requests.post(oauth, data=json.dumps(opost), headers=headers, timeout=30).json()
        c.log('Trakt token refresh: ' + repr(result))

        token, refresh = result['access_token'], result['refresh_token']

        control.setSetting(id='trakt.token', value=token)
        control.setSetting(id='trakt.refresh', value=refresh)

        headers['Authorization'] = f'Bearer {token}'

        # result = client.request(url, post=post, headers=headers, output='extended', error=True)
        # result = utils.byteify(result)
        # return result[0], result[2]

        if not post:
            r = requests.get(url, headers=headers, timeout=30)
        else:
            r = requests.post(url, data=post, headers=headers, timeout=30)
        r.encoding = 'utf-8'
        return r.text, r.headers

    except Exception as e:
        c.log(f'Unknown Trakt Error: {e}', 1)


def getTraktAsJson(url, post=None):
    try:
        r, res_headers = get_trakt(url, post)
        r = utils.json_loads_as_str(r)
        if 'X-Sort-By' in res_headers and 'X-Sort-How' in res_headers:
            r = sort_list(res_headers['X-Sort-By'], res_headers['X-Sort-How'], r)
        return r
    except Exception as e:
        c.log('getTraktAsJson Error: ' + str(e))
        pass

def authTrakt():
    try:
        if getTraktCredentialsInfo() is True:
            if control.yesnoDialog(control.lang(32511) + '[CR]' + control.lang(32512), heading='Trakt'):
                control.setSetting(id='trakt.user', value='')
                control.setSetting(id='trakt.token', value='')
                control.setSetting(id='trakt.refresh', value='')
            raise Exception()

        result = getTraktAsJson('/oauth/device/code', {'client_id': V2_API_KEY})
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
                        'client_id': V2_API_KEY,
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
                    'trakt-api-key': V2_API_KEY,
                    'trakt-api-version': 2,
                    'Authorization': f'Bearer {token}'
                }

        result = client.request(urljoin(BASE_URL, '/users/me'), headers=headers)
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
    user = trakt_user
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



def get_trakt_addon_movie_info():
    """
    Check if Trakt is enabled and authorized in the Trakt addon.
    """
    try:
        scrobble = control.addon('script.trakt').getSetting('scrobble_movie')
    except LookupError:
        scrobble = ''
    try:
        exclude_http = control.addon('script.trakt').getSetting('ExcludeHTTP')
    except LookupError:
        exclude_http = ''
    try:
        authorization = control.addon('script.trakt').getSetting('authorization')
    except LookupError:
        authorization = ''

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
            k = control.keyboard('', t) ; k.doModal()

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


def sort_list(sort_key, sort_direction, list_data):
    reverse = False if sort_direction == 'asc' else True
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


def getActivity():
    try:
        i = getTraktAsJson('/sync/last_activities')

        activity = []
        activity.append(i['movies']['collected_at'])
        activity.append(i['episodes']['collected_at'])
        activity.append(i['movies']['watchlisted_at'])
        activity.append(i['shows']['watchlisted_at'])
        activity.append(i['seasons']['watchlisted_at'])
        activity.append(i['episodes']['watchlisted_at'])
        activity.append(i['lists']['updated_at'])
        activity.append(i['lists']['liked_at'])
        activity = [int(cleandate.iso_2_utc(i)) for i in activity]
        activity = sorted(activity, key=int)[-1]

        return activity
    except:
        pass


def getWatchedActivity():
    try:
        i = getTraktAsJson('/sync/last_activities')

        activity = []
        activity.append(i['movies']['watched_at'])
        activity.append(i['episodes']['watched_at'])
        activity = [int(cleandate.iso_2_utc(i)) for i in activity]
        activity = sorted(activity, key=int)[-1]

        return activity
    except:
        pass


def cachesyncMovies(timeout=0):
    indicators = cache.get(syncMovies, timeout, trakt_user)
    return indicators


def timeoutsyncMovies():
    timeout = cache.timeout(syncMovies, trakt_user)
    return timeout


def syncMovies(user):
    try:
        if getTraktCredentialsInfo() is False:
            return
        indicators = getTraktAsJson('/users/me/watched/movies')
        indicators = [i['movie']['ids'] for i in indicators]
        indicators = [str(i['imdb']) for i in indicators if 'imdb' in i]
        return indicators
    except:
        pass


def cachesyncTVShows(timeout=0):
    indicators = cache.get(syncTVShows, timeout, trakt_user)
    return indicators


def timeoutsyncTVShows():
    timeout = cache.timeout(syncTVShows, trakt_user)
    if not timeout:
        timeout = 0
    return timeout


def syncTVShows(user):
    try:
        if getTraktCredentialsInfo() is False:
            return
        indicators = getTraktAsJson('/users/me/watched/shows?extended=full')
        indicators = [(i['show']['ids']['tmdb'], i['show']['aired_episodes'], sum([[(s['number'], e['number']) for e in s['episodes']] for s in i['seasons']], [])) for i in indicators]
        indicators = [(str(i[0]), int(i[1]), i[2]) for i in indicators]
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
        indicators = ['%01d' % int(i[0]) for i in indicators if False not in i[1]]
        return indicators
    except:
        pass


def syncTraktStatus():
    try:
        cachesyncMovies()
        cachesyncTVShows()
        control.infoDialog(control.lang(32092))
    except:
        control.infoDialog('Trakt sync failed')



def markMovieAsWatched(imdb):
    if not imdb.startswith('tt'):
        imdb = 'tt' + imdb
    return get_trakt('/sync/history', {"movies": [{"ids": {"imdb": imdb}}]})[0]


def markMovieAsNotWatched(imdb):
    if not imdb.startswith('tt'):
        imdb = 'tt' + imdb
    return get_trakt('/sync/history/remove', {"movies": [{"ids": {"imdb": imdb}}]})[0]


def markTVShowAsWatched(imdb):
    return get_trakt('/sync/history', {"shows": [{"ids": {"imdb": imdb}}]})[0]


def markTVShowAsNotWatched(imdb):
    return get_trakt('/sync/history/remove', {"shows": [{"ids": {"imdb": imdb}}]})[0]


def markEpisodeAsWatched(imdb, season, episode):
    season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
    return get_trakt('/sync/history', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"imdb": imdb}}]})[0]


def markEpisodeAsNotWatched(imdb, season, episode):
    season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
    return get_trakt('/sync/history/remove', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"imdb": imdb}}]})[0]


def scrobbleMovie(imdb, watched_percent, action):
    if not imdb.startswith('tt'):
        imdb = 'tt' + imdb
    return get_trakt(f'/scrobble/{action}', {"movie": {"ids": {"imdb": imdb}}, "progress": watched_percent})[0]


def scrobbleEpisode(imdb, season, episode, watched_percent, action):
    if not imdb.startswith('tt'):
        imdb = 'tt' + imdb
    season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
    return get_trakt(f'/scrobble/{action}', {"show": {"ids": {"imdb": imdb}}, "episode": {"season": season, "number": episode}, "progress": watched_percent})[0]


def getMovieTranslation(id, lang, full=False):
    url = f'/movies/{id}/translations/{lang}'
    try:
        item = getTraktAsJson(url)[0]
        return item if full else item.get('title')
    except:
        pass


def getTVShowTranslation(_id, lang, season=None, episode=None, full=False):
    if season and episode:
        url = f'/shows/{_id}/seasons/{season}/episodes/{episode}/translations/{lang}'
    else:
        url = f'/shows/{id}/translations/{lang}'

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
