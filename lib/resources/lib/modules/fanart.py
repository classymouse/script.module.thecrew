# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file fanart.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2024, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

#cm - 2024/11/12 - new file
import json
import time
import traceback
import requests

from . import keys
from . import control
from .crewruntime import c

import sqlite3 as database
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry



#######cm#
# housekeeping
#
fanart_tv_user = c.get_setting('fanart.tv.user') or ''
fanart_tv_headers = {}
fanart_tv_headers['api-key'] = keys.fanart_key
if fanart_tv_user != '':
    fanart_tv_headers['client-key'] = fanart_tv_user

#######cm#
# constants
#
DAY = 86400
WEEK = 604800
TWOWEEKS = 1209600
MONTH = 2592000

#######cm#
# url's
#
fanart_tv_art_link = 'http://webservice.fanart.tv/v3/tv/%s'
fanart_movie_art_link = 'https://webservice.fanart.tv/v3/movies/%s'

#######cm#
# setting up
#
BASE_URL = 'https://api.trakt.tv'
CLIENT_ID = '482f9db52ee2611099ce3aa1abf9b0f7ed893c6d3c6b5face95164eac7b01f71'
CLIENT_SECRET = '80a2729728b53ba1cc38137b22f21f34d590edd35454466c4b8920956513d967'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

trakt_user = control.setting('trakt.user').strip()
session = requests.Session()
retries = Retry(total=3, backoff_factor=1)
session.mount(BASE_URL, HTTPAdapter(max_retries=retries))

def get_fanart_tv_art(tvdb, imdb = '0', lang='en', mediatype='tv'):

    """
    Gets fanart.tv artwork for a given tvdb or imdb id

    Args:
        tvdb (str): The TVDB ID of the tv show
        imdb (str, optional): The IMDB ID of the tv show. Defaults to '0'.
        lang (str, optional): The language to retrieve the artwork in. Defaults to 'en'.
        type (str, optional): The type of artwork to retrieve. Defaults to 'tv'.
            Valid options are 'tv' or 'movie'

    Returns:
        tuple: A tuple containing the following artwork in this order:
            poster, fanart, banner, landscape, clearlogo, clearart
            If type is 'movie', the last item is instead discart
    """

    zero_str = {}

    def _extract_artwork(art, key, lang):
        try:
            items = art.get(key, [])
            sorted_items = sorted(items, key=lambda x: (x.get('lang') != lang, x.get('lang') != 'en', x.get('lang') not in ['00', '']))
            return sorted_items[0].get('url', '0') if sorted_items else '0'
        except Exception:
            return '0'

    try:
        headers = {'api-key': keys.fanart_key}
        if fanart_tv_user:
            headers['client-key'] = fanart_tv_user


        if mediatype=='tv':
            if not tvdb or tvdb == '0':
                raise ValueError('Invalid TVDB ID')
            url = f'http://webservice.fanart.tv/v3/tv/{tvdb}'
        else:
            if not imdb or imdb == '0':
                raise ValueError('Invalid IMDB ID')
            url = f'http://webservice.fanart.tv/v3/movies/{imdb}'


        response = get_cached_fanart(tvdb, imdb, url, headers, 15)
        if response:
            art = response

        if response is None:
            return zero_str

        if 'status' in art and art.get('status') == 'error':
            return zero_str

    except ValueError as e:
        c.log(f'ValueError raised, returning zero_str. Error = {e}')
        return zero_str

    except Exception as e:
        c.log(f'Exception raised, returning zero_str. Error = {e}')
        return zero_str

    if mediatype == 'tv':
        poster = _extract_artwork(art, 'tvposter', lang)
        fanart = _extract_artwork(art, 'showbackground', lang)
        banner = _extract_artwork(art, 'tvbanner', lang)
        clearlogo = _extract_artwork(art, 'hdtvlogo' if 'hdtvlogo' in art else 'clearlogo', lang)
        clearart = _extract_artwork(art, 'hdclearart' if 'hdclearart' in art else 'clearart', lang)
        landscape = _extract_artwork(art, 'tvthumb' if 'tvthumb' in art else 'showbackground', lang)
        discart = '0'
    elif mediatype == 'movie':
        poster = _extract_artwork(art, 'movieposter', lang)
        fanart = _extract_artwork(art, 'moviebackground' if 'moviebackground' in art else 'moviethumb', lang)
        banner = _extract_artwork(art, 'moviebanner', lang)
        clearlogo = _extract_artwork(art, 'hdmovielogo', lang)
        clearart = _extract_artwork(art, 'hdmovieclearart', lang)
        landscape = _extract_artwork(art, 'moviethumb' if 'moviethumb' in art else 'moviebackground', lang)
        #discart = _extract_artwork(art, 'moviediscart', lang)
        discart = _extract_artwork(art, 'moviedisc', lang)
    else:
        return zero_str


    if mediatype == 'tv':
        return {
            'poster': poster, 'fanart': fanart, 'banner': banner, 'landscape': landscape,
            'clearlogo': clearlogo, 'clearart': clearart
            } #poster, fanart, banner, landscape, clearlogo, clearart
    else:
        return {
            'poster': poster, 'fanart': fanart, 'banner': banner, 'landscape': landscape,
            'clearlogo': clearlogo, 'clearart': clearart, 'discart': discart
            } #poster, fanart, banner, landscape, clearlogo, clearart, discart

def get_cached_fanart(tvdb, imdb, url, headers, timeout=30):
    try:
        if has_table('fanart_cache'):
            control.makeFile(control.dataPath)
            dbcon = database.connect(control.cacheFile)
            dbcur = dbcon.cursor()

            sql = f"SELECT * FROM fanart_cache WHERE url = '{url}' and added < {time.time() - TWOWEEKS}"
            dbcur.execute(sql)
            result = dbcur.fetchone()

            if result:
                #data in cache
                return json.loads(result[3])
            else:
                #no data in cache
                response = session.get(url, headers=headers, timeout=timeout)
                response.encoding = 'utf-8'
                txt = json.loads(response.text)

                if response.status_code == 200:
                    sql = "INSERT or REPLACE INTO fanart_cache (tvdb, imdb, url, data, added) Values (?,?,?,?,?)"

                    if isinstance(txt, dict):
                        txt = json.dumps(txt, indent=4, sort_keys=True)
                    dbcur.execute(sql, (tvdb, imdb, url, txt, int(time.time())))
                    dbcon.commit()
                    dbcon.close()
                    #return response
                    return txt
                else:
                    c.log(f"[CM Debug @ 181 in fanart.py] response.status_code = {response.status_code}, close db, return None")
                    dbcon.close()
                    return None
    except Exception as e:
        c.log(f'[CM Debug @ 200 in fanart.py]Exception raised. Error = {e}')
        dbcon.close()
        return None


def has_table(table):
    try:
        control.makeFile(control.dataPath)
        dbcon = database.connect(control.cacheFile)
        dbcur = dbcon.cursor()

        sql = f"create table if not exists {table} (tvdb text, imdb text, url text, data text, added text)"
        dbcur.execute(sql)

        sql =  f"SELECT count(*) as cnt FROM sqlite_master WHERE type='table' AND name='{table}'"
        dbcur.execute(sql)
        cnt = dbcur.fetchone()

        dbcon.close()

        return cnt
    except Exception:
        return False