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
import urllib
import requests
import contextlib

from urllib.parse import urljoin, quote_plus

import json

from . import cache
from . import cleandate
from . import client
from . import control
from . import log_utils
from . import utils
from .crewruntime import c



BASE_URL = 'https://api.trakt.tv'
V2_API_KEY = '482f9db52ee2611099ce3aa1abf9b0f7ed893c6d3c6b5face95164eac7b01f71'
CLIENT_SECRET = '80a2729728b53ba1cc38137b22f21f34d590edd35454466c4b8920956513d967'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

def __getTrakt(url, post=None):
    try:
        url = urljoin(BASE_URL, url)
        post = json.dumps(post) if post else None
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-key': V2_API_KEY,
            'trakt-api-version': '2'
            }

        if getTraktCredentialsInfo():
            #headers.update({
            #'Authorization': 'Bearer %s' %
            #control.setting('trakt.token')
            #})
            ctrltoken = control.setting('trakt.token')
            headers['Authorization'] = f'Bearer {ctrltoken}'

        # result = client.request(url, post=post, headers=headers, output='extended', error=True)
        # result = utils.byteify(result)
        # resp_code = result[1]
        # resp_header = result[2]
        # result = result[0]

        if not post:
            r = requests.get(url, headers=headers, timeout=30)
        else:
            r = requests.post(url, data=post, headers=headers, timeout=30)

        r.encoding = 'utf-8'

        resp_code = str(r.status_code)
        resp_header = r.headers
        result = r.text

        #if resp_code in ['423', '500', '502', '503', '504', '520', '521', '522', '524']:
        if resp_code in {
            '423',
            '500',
            '502',
            '503',
            '504',
            '520',
            '521',
            '522',
            '524',
        }:
            c.log(f'Trakt Error: {resp_code}')
            control.infoDialog(f'Trakt Error: {resp_code}', sound=True)
            return
        elif resp_code in {'429'}:
            c.log(f'Trakt Rate Limit Reached:{resp_code}')
            control.infoDialog(f'Trakt Rate Limit Reached: {resp_code}', sound=True)
            c.log(f"[CM Debug @ 96 in trakt.py] headers = {resp_header}")
            if 'Retry-After' in resp_header:
                c.log(f"[CM Debug @ 97 in trakt.py] Retry-After = {resp_header['Retry-After']}")
                time.sleep(int(resp_header['Retry-After']))
                __getTrakt(url, post)
            return
        elif resp_code in {'404'}:
            c.log(f'Trakt error: Object Not Found : {resp_code}')
            return

        if resp_code not in {
            '401',
            '403',
            '405'
        }:
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
        c.log(f'Trakt token refresh: {repr(result)}')

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
        r, res_headers = __getTrakt(url, post)
        r = utils.json_loads_as_str(r)
        if 'X-Sort-By' in res_headers and 'X-Sort-How' in res_headers:
            r = sort_list(res_headers['X-Sort-By'], res_headers['X-Sort-How'], r)
        return r
    except Exception as e:
        c.log('getTraktAsJson Error: ' + str(e))
        pass

def authTrakt():
    try:
        if getTraktCredentialsInfo() == True:
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
                if progressDialog.iscanceled(): break

                time.sleep(1)
                if not float(i) % interval == 0: raise Exception()
                r = getTraktAsJson('/oauth/device/token', {'client_id': V2_API_KEY, 'client_secret': CLIENT_SECRET, 'code': device_code})
                if 'access_token' in r: break
            except Exception:
                pass

        try:
            progressDialog.close()
        except Exception:
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
        #authed = '' if user == '' else 'yes'

        control.setSetting(id='trakt.user', value=user)
        control.setSetting(id='trakt.token', value=token)
        control.setSetting(id='trakt.refresh', value=refresh)
        raise Exception()
    except Exception:
        control.openSettings('3.1')


def getTraktCredentialsInfo():
    user = control.setting('trakt.user').strip()
    token = control.setting('trakt.token')
    refresh = control.setting('trakt.refresh')
    if (user == '' or token == '' or refresh == ''): return False
    return True


def getTraktIndicatorsInfo():
    indicators = control.setting('indicators') if getTraktCredentialsInfo() is False else control.setting('indicators.alt')
    #indicators = True if indicators == '1' else False
    indicators = indicators == '1'
    return indicators


def getTraktAddonMovieInfo():
    try:
        scrobble = control.addon('script.trakt').getSetting('scrobble_movie')
    except Exception:
        scrobble = ''
    try:
        ExcludeHTTP = control.addon('script.trakt').getSetting('ExcludeHTTP')
    except Exception:
        ExcludeHTTP = ''
    try:
        authorization = control.addon('script.trakt').getSetting('authorization')
    except Exception:
        authorization = ''
    if scrobble == 'true' and ExcludeHTTP == 'false' and not authorization == '':
        return True
    else:
        return False


def getTraktAddonEpisodeInfo():
    try:
        scrobble = control.addon('script.trakt').getSetting('scrobble_episode')
    except Exception:
        scrobble = ''
    try:
        ExcludeHTTP = control.addon('script.trakt').getSetting('ExcludeHTTP')
    except Exception:
        ExcludeHTTP = ''
    try:
        authorization = control.addon('script.trakt').getSetting('authorization')
    except Exception:
        authorization = ''
    if scrobble == 'true' and ExcludeHTTP == 'false' and not authorization == '':
        return True
    else:
        return False


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
            #lists[i] = ((control.lang(32521) % lists[i][0]), '/users/me/lists/%s/items' % lists[i][1])
            lists[i] = (
                control.lang(32521) % lists[i][0],
                f'/users/me/lists/{lists[i][1]}/items',
            )

        for i in range(1, len(lists), 2):
            #lists[i] = ((control.lang(32522) % lists[i][0]), '/users/me/lists/%s/items/remove' % lists[i][1])
            lists[i] = (
                control.lang(32522) % lists[i][0],
                f'/users/me/lists/{lists[i][1]}/items/remove',
            )

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

            result = __getTrakt('/users/me/lists', post={"name": new, "privacy": "private"})[0]

            try:
                slug = utils.json_loads_as_str(result)['ids']['slug']
            except Exception:
                return control.infoDialog(control.lang(32515), heading=str(name), sound=True, icon='ERROR')

            result = __getTrakt(items[select][1] % slug, post=post)[0]
        else:
            result = __getTrakt(items[select][1], post=post)[0]

        icon = control.infoLabel('ListItem.Icon') if result is not None else 'ERROR'

        control.infoDialog(control.lang(32515), heading=str(name), sound=True, icon=icon)
    except Exception:
        return


def slug(name):
    name = name.strip()
    name = name.lower()
    name = re.sub('[^a-z0-9_]', '-', name)
    name = re.sub('--+', '-', name)
    if name.endswith('-'):
        name = name.rstrip('-')
    return name


def sort_list(sort_key, sort_direction, list_data):
    reverse = False if sort_direction == 'asc' else True
    if sort_key == 'rank':
        return sorted(list_data, key=lambda x: x['rank'], reverse=reverse)
    elif sort_key == 'added':
        return sorted(list_data, key=lambda x: x['listed_at'], reverse=reverse)
    elif sort_key == 'title':
        return sorted(list_data, key=lambda x: utils.title_key(x[x['type']].get('title')), reverse=reverse)
    elif sort_key == 'released':
        return sorted(list_data, key=lambda x: _released_key(x[x['type']]), reverse=reverse)
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


def _released_key(item):
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
    except Exception:
        pass


def getWatchedActivity():
    try:
        i = getTraktAsJson('/sync/last_activities')

        activity = []
        activity.append(i['movies']['watched_at'])
        activity.append(i['episodes']['watched_at'])
        activity = [int(cleandate.iso_to_utc(i)) for i in activity]
        activity = sorted(activity, key=int)[-1]

        return activity
    except Exception:
        pass


def cachesyncMovies(timeout=0):
    indicators = cache.get(syncMovies, timeout, control.setting('trakt.user').strip())
    return indicators


def timeoutsyncMovies():
    timeout = cache.timeout(syncMovies, control.setting('trakt.user').strip()) or 0
    return timeout


def syncMovies(user):
    try:
        if getTraktCredentialsInfo() is False: return
        indicators = getTraktAsJson('/users/me/watched/movies')
        indicators = [i['movie']['ids'] for i in indicators]
        indicators = [str(i['imdb']) for i in indicators if 'imdb' in i]
        return indicators
    except Exception:
        pass


def cachesyncTVShows(timeout=0):
    indicators = cache.get(syncTVShows, timeout, control.setting('trakt.user').strip())
    return indicators


def timeoutsyncTVShows():
    timeout = cache.timeout(syncTVShows, control.setting('trakt.user').strip()) or 0
    return timeout


def syncTVShows(user):
    try:
        if getTraktCredentialsInfo() is False: return
        indicators = getTraktAsJson('/users/me/watched/shows?extended=full')
        indicators = [(i['show']['ids']['tmdb'], i['show']['aired_episodes'], sum([[(s['number'], e['number']) for e in s['episodes']] for s in i['seasons']], [])) for i in indicators]
        indicators = [(str(i[0]), int(i[1]), i[2]) for i in indicators]
        return indicators
    except Exception:
        pass


def syncSeason(imdb):
    try:
        if getTraktCredentialsInfo() is False:
            return
        indicators = getTraktAsJson(f'/shows/{imdb}/progress/watched?specials=false&hidden=false')
        indicators = indicators['seasons']
        indicators = [(i['number'], [x['completed'] for x in i['episodes']]) for i in indicators]
        return ['%01d' % int(i[0]) for i in indicators if False not in i[1]]
    except Exception:
        pass


def syncTraktStatus():
    try:
        cachesyncMovies()
        cachesyncTVShows()
        control.infoDialog(control.lang(32092))
    except Exception as e:
        control.infoDialog(f'Trakt sync failed: {e}')



def markMovieAsWatched(imdb):
    if not imdb.startswith('tt'):
        imdb = f'tt{imdb}'
    return __getTrakt('/sync/history', {"movies": [{"ids": {"imdb": imdb}}]})[0]


def markMovieAsNotWatched(imdb):
    if not imdb.startswith('tt'):
        imdb = f'tt{imdb}'
    return __getTrakt('/sync/history/remove', {"movies": [{"ids": {"imdb": imdb}}]})[0]


def markTVShowAsWatched(imdb):
    return __getTrakt('/sync/history', {"shows": [{"ids": {"imdb": imdb}}]})[0]


def markTVShowAsNotWatched(imdb):
    return __getTrakt('/sync/history/remove', {"shows": [{"ids": {"imdb": imdb}}]})[0]


def markEpisodeAsWatched(imdb, season, episode):
    season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
    return __getTrakt('/sync/history', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"imdb": imdb}}]})[0]


def markEpisodeAsNotWatched(imdb, season, episode):
    c.log(f"[CM Debug @ 497 in trakt.py] imdb = {imdb} | season = {season} | episode = {episode}")
    season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
    return __getTrakt('/sync/history/remove', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"imdb": imdb}}]})[0]


def scrobbleMovie(imdb, watched_percent, action):
    """
    Scrobble a movie in trakt.tv.

    :param imdb: The imdb id of the movie
    :param watched_percent: The percentage of the movie that has been watched
    :param action: The action to perform, either 'start' or 'stop'
    :return: The response from trakt.tv
    :rtype: dict
    """
    if not imdb.startswith('tt'):
        imdb = f'tt{imdb}'
    return __getTrakt(
        f'/scrobble/{action}',
        {"movie": {"ids": {"imdb": imdb}}, "progress": watched_percent},
    )[0]


def scrobbleEpisode(imdb, season, episode, watched_percent, action):
    """
    Scrobble an episode in trakt.tv.

    :param imdb: The imdb id of the TV show
    :param season: The season number of the episode
    :param episode: The episode number of the episode
    :param watched_percent: The percentage of the episode that has been watched
    :param action: The action to perform, either 'start' or 'stop'
    :return: The response from trakt.tv
    :rtype: dict
    """
    if not imdb.startswith('tt'):
        imdb = f'tt{imdb}'
    season, episode = int('%01d' % int(season)), int('%01d' % int(episode))

    return __getTrakt(
        f'/scrobble/{action}',
        {
            "show": {"ids": {"imdb": imdb}},
            "episode": {"season": season, "number": episode},
            "progress": watched_percent,
        },
    )[0]

def getMovieTranslation(id, lang, full=False):
    """
    Retrieve the translation for a movie from trakt.tv.

    Args:
        id (str): The ID of the movie.
        lang (str): The language code for the translation.
        full (bool, optional): Whether to return the full translation object or just the title. Defaults to False.

    Returns:
        dict or str: The full translation object if `full` is True, otherwise the translated title. Returns None if an error occurs.
    """
    url = f'/movies/{id}/translations/{lang}'


    with contextlib.suppress(Exception):
        item = getTraktAsJson(url)[0]
        return item if full else item.get('title')



def getTVShowTranslation(id, lang, season=None, episode=None, full=False):
    """
    Retrieve the translation for a TV show from trakt.tv.

    Args:
        id (str): The ID of the TV show.
        lang (str): The language code for the translation.
        season (int, optional): The season number of the translation. Defaults to None.
        episode (int, optional): The episode number of the translation. Defaults to None.
        full (bool, optional): Whether to return the full translation object or just the title.
        Defaults to False.

    Returns:
        dict or str: The full translation object if `full` is True, otherwise the translated title.
        Returns None if an error occurs.
    """
    if season and episode:
        url = f'/shows/{id}/seasons/{season}/episodes/{episode}/translations/{lang}'
    else:
        url = f'/shows/{id}/translations/{lang}'

    try:
        item = getTraktAsJson(url)[0]
        return item if full else item.get('title')
    except Exception:
        pass


def getMovieAliases(id):
    """
    Get a list of aliases for a movie.

    Args:
        id (str): The id of the movie.

    Returns:
        list: A list of aliases for the movie.
    """
    try:
        return getTraktAsJson(f'/movies/{id}/aliases')
    except Exception:
        return []


def getTVShowAliases(id):
    """
    Get a list of aliases for a TV show.

    Parameters
    ----------
    id : str
        The Trakt id of the TV show.

    Returns
    -------
    A list of dictionaries, each containing the aliases for the TV show in a particular country.
    """

    try:
        return getTraktAsJson(f'/shows/{id}/aliases')
    except Exception:
        return []


def getMovieSummary(id, full=True):
    """
    Get the summary for a movie.

    Parameters
    ----------
    id : str
        The Trakt id of the movie.
    full : bool
        If True, the full summary will be returned. Otherwise, a limited summary will be returned.

    Returns
    -------
    The summary as a dictionary.
    """
    try:
        url = f'/movies/{id}'
        if full:
            url += '?extended=full'
        return getTraktAsJson(url)
    except Exception:
        return


def getTVShowSummary(_id, full=True):
    """
    Get the summary for a TV show.

    Parameters
    ----------
    _id : str
        The Trakt id of the TV show.
    full : bool
        If True, the full summary will be returned. Otherwise, a limited summary will be returned.

    Returns
    -------
    The summary as a dictionary.
    """
    try:
        url = f'/shows/{_id}'
        if full:
            url += '?extended=full'
        return getTraktAsJson(url)
    except Exception:
        return


def getPeople(id, content_type, full=True):
    """
    Get the people associated with a movie or TV show.

    Parameters
    ----------
    id : str
        The Trakt id of the movie or TV show.
    content_type : str
        The type of content, either 'movies' or 'shows'.
    full : bool
        If True, the full people information will be returned. Otherwise, a limited summary will
        be returned.

    Returns
    -------
    A dictionary containing the people information.
    """
    try:
        url = f'/{content_type}/{id}/people'
        if full:
            url += '?extended=full'
        return getTraktAsJson(url)
    except Exception:
        return


def SearchAll(title, year, full=True):
    """
    Search trakt.tv for a movie or TV show.

    Parameters
    ----------
    title : str
        The title of the movie or TV show to search for.
    year : int
        The year the movie or TV show was released. If specified, the search will be limited to
        that year.
    full : bool
        If True, the full search results will be returned (default True).

    Returns
    -------
    The search results as a list of dictionaries.
    """
    try:
        return SearchMovie(title, year, full) + SearchTVShow(title, year, full)
    except Exception:
        return


def SearchMovie(title, year, full=True):
    """
    Search trakt.tv for a movie.

    Parameters
    ----------
    title : str
        The title of the movie to search for.
    year : int
        The year the movie was released. If specified, the search will be limited to that year.
    full : bool
        If True, the full search results will be returned (default True).

    Returns
    -------
    The search results as a list of dictionaries.
    """
    try:
        url = f'/search/movie?query={quote_plus(title)}'

        if year:
            url += f'&year={year}'
        if full:
            url += '&extended=full'
        return getTraktAsJson(url)
    except Exception:
        return


def SearchTVShow(title, year, full=True):
    """
    Search trakt.tv for a tv show.

    Parameters
    ----------
    title : str
        The title of the show to search for.
    year : int
        The year the show was released. If specified, the search will be limited to that year.
    full : bool
        If True, the full search results will be returned (default True).

    Returns
    -------
    The search results as a list of dictionaries.
    """
    try:
        url = f'/search/show?query={quote_plus(title)}'

        if year:
            url += f'&year={year}'
        if full:
            url += '&extended=full'
        return getTraktAsJson(url)
    except Exception:
        return

def IdLookup(content, _type, type_id):
    """
    Lookup trakt.tv ids for a given id.

    Parameters
    ----------
    content : str
        The type of content to look up. One of 'movie', 'show', 'episode', 'person'.
    _type : str
        The type of id to look up. One of 'imdb', 'tmdb', 'tvdb', 'tvrage'.
    type_id : str
        The id to look up.

    Returns
    -------
    A dictionary of trakt.tv ids for the given id.
    """
    try:
        r = getTraktAsJson(f'/search/{_type}/{type_id}?type={content}')
        return r[0].get(content, {}).get('ids', [])
    except Exception:
        return {}

def getGenre(content, _type, type_id):
    """
    Lookup the genres for a given id.

    Parameters
    ----------
    content : str
        The type of content to look up. One of 'movie', 'show', 'episode', 'person'.
    _type : str
        The type of id to look up. One of 'imdb', 'tmdb', 'tvdb', 'tvrage'.
    type_id : str
        The id to look up.

    Returns
    -------
    The genres as a list of strings.
    """
    try:
        r = f'/search/{_type}/{type_id}?type={content}&extended=full'
        r = getTraktAsJson(r)
        r = r[0].get(content, {}).get('genres', [])
        return r
    except Exception:
        return []

def getEpisodeRating(imdb, season, episode):
    """
    Get the rating and votes for a given episode.

    Parameters
    ----------
    imdb : str
        The IMDB ID of the show.
    season : int
        The season number of the episode.
    episode : int
        The episode number of the episode.

    Returns
    -------
    A tuple of two strings. The first string is the rating as a string, and the second string is the number of votes as a string.
    """
    try:
        if not imdb.startswith('tt'):
            imdb = f'tt{imdb}'
        url = f'/shows/{imdb}/seasons/{season}/episodes/{episode}/ratings'
        r = getTraktAsJson(url)
        r1 = r.get('rating', '0')
        r2 = r.get('votes', '0')
        return str(r1), str(r2)
    except Exception:
        return
