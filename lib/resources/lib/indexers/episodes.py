# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 * @package plugin.video.thecrew2
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ***********************************************************
'''

# CM - 01/09/2023

# cm - testfile VS without mocking (just useless)

import os
import sys
import re
# cm - added temporarily
import time
import datetime
import json

import concurrent.futures

#import xbmc
#import zipfile
#import base64


# cm - we need to remove the six lib
#import six

from urllib.parse import quote, quote_plus, unquote_plus, parse_qsl, urlsplit, urlencode, urlparse
import requests

from ..modules import trakt
from ..modules import keys
from ..modules import bookmarks
from ..modules import cleantitle
from ..modules import cleangenre
from ..modules import control
from ..modules import metacache
from ..modules import client
from ..modules import cache
from ..modules import playcount
from ..modules import workers
from ..modules import views
from ..modules import utils
from ..modules import fanart as fanart_tv

from ..modules.listitem import ListItemInfoTag
#from ..modules import log_utils
from ..modules.crewruntime import c


try:
    from orion import *
    orion_installed = True
except:
    orion_installed = False

params = dict(parse_qsl(sys.argv[2].replace('?', ''))) if len(sys.argv) > 1 else {}
action = params.get('action')


class seasons:
    def __init__(self):
        self.list = []
        self.speedtest = {}
        self.speedtest['start'] = time.perf_counter()

        self.session = requests.Session()

        self.tmdb_user = control.setting( 'tm.personal_user') or control.setting('tm.user') or keys.tmdb_key
        self.user = self.tmdb_user
        self.lang = control.apiLanguage()['tmdb']
        self.showunaired = control.setting('showunaired') or 'true'
        self.specials = control.setting('tv.specials') or 'true'

        self.today_date = datetime.date.today().strftime("%Y-%m-%d")
        self.tmdb_link = 'https://api.themoviedb.org/3/'
        self.tmdb_img_link = 'https://image.tmdb.org/t/p/%s%s'

        self.tmdb_show_link = (f'{self.tmdb_link}tv/%s?api_key={self.tmdb_user}&language=%s&append_to_response=external_ids,aggregate_credits,content_ratings')
        self.tmdb_show_lite_link = (f'{self.tmdb_link}tv/%s?api_key={self.tmdb_user}&language=en&append_to_response=external_ids')
        self.tmdb_by_imdb = (f'{self.tmdb_link}find/%s?api_key={self.tmdb_user}&external_source=imdb_id&append_to_response=external_ids')

        self.tmdb_api_link = (f'{self.tmdb_link}tv/%s?api_key={self.tmdb_user}&language={self.lang}&append_to_response=external_ids,aggregate_credits,content_ratings,external_ids')
        self.tmdb_networks_link = (f'{self.tmdb_link}discover/tv?api_key={self.tmdb_user}&sort_by=popularity.desc&with_networks=%s&append_to_response=external_ids&page=1')
        self.tmdb_search_tvshow_link = (f'{self.tmdb_link}search/tv?api_key={self.tmdb_user}&language=en-US&append_to_response=external_ids&query=%s&page=1')
        self.tmdb_info_tvshow_link = (f'{self.tmdb_link}tv/%s?api_key={self.tmdb_user}&language=en-US&append_to_response=external_ids,images')

    def __del__(self):
        try:
            self.session.close()
        except Exception:
            pass

    def get(self, tvshowtitle, year, imdb, tmdb, meta=None, idx=True, create_directory=True):
        try:
            if idx is True:
                c.log(f"[CM Debug @ 101 in episodes.py] title = {tvshowtitle}, year = {year}, imdb = {imdb}, tmdb = {tmdb}, meta = {meta}")
                #self.list = cache.get(self.tmdb_list, 24, tvshowtitle, year, imdb, tmdb, meta)
                self.list = self.tmdb_list(tvshowtitle, year, imdb, tmdb, meta)
                if create_directory is True:
                    self.seasonDirectory(self.list)
                return self.list
            else:
                self.list = self.tmdb_list(tvshowtitle, year, imdb, tmdb, meta)
            return self.list
        except Exception:
            pass


    def tmdb_list(self, tvshowtitle, year, imdb_id, tmdb_id, meta=None, lite=False):
        """Get a list of TV show seasons from TMDB.

        url = "https://api.themoviedb.org/3/tv/79744?append_to_response=external_ids&language=en-US"

        "external_ids": {
            "imdb_id": "tt7587890",
            "tvdb_id": 350665,

        }
        """

        try:
            if tmdb_id == '0':
                raise Exception()

            if self.lang == 'en':
                item = self.session.get(self.tmdb_show_link % (tmdb_id, 'en'), timeout=16).json()
            elif lite is True:
                item = self.session.get(self.tmdb_show_lite_link % tmdb_id, timeout=16).json()
            else:
                item = self.session.get(self.tmdb_show_link % (tmdb_id, self.lang) + ',translations', timeout=16).json()
            #c.log(f"\n\n\n=============================\nitem from TMDB\n===================================\n\n\n[CM Debug @ 130 in episodes.py] TVShow item\n\n\n{repr(item)}")

            dict_keys = item.keys()
            c.log(f"[CM Debug @ 132 in episodes.py] dict_keys = {dict_keys}")

            number_of_episodes = item.get('number_of_episodes', 0)
            number_of_seasons = item.get('number_of_seasons', 0)


            tvshowtitle = item.get('name', 'No TVShow Title - The Crew')
            tagline = item.get('tagline', '0')
            tvdb_id = item.get('external_ids', {}).get('tvdb', '0')
            imdb_id = item.get('external_ids', {}).get('imdb_id', '0')


            if item is None:
                raise Exception()

            seasons_list = item.get('seasons', [])

            if self.specials == 'false':
                seasons_list = [s for s in seasons_list if not s['season_number'] == 0]

            studio = item.get('networks')[0].get('name', '0')

            genres = item.get('genres', [])
            genre = ' / '.join([d['name'] for d in genres]) if genres else '0'
            popularity = item.get('popularity', '0')

            #duration = item.get('episode_run_time', [])[0] or 45
            #duration = item.get('episode_run_time', []) or 45
            duration = item.get('episode_run_time', 45)
            c.log(f"[CM Debug @ 164 in episodes.py] the duration of {tvshowtitle} is of type({type(duration)}) and the value is {duration}")
            if isinstance(duration, list):
                duration = duration[0] if len(duration) > 0 else 45
            duration = str(duration)

            c_ratings = item.get('content_ratings').get('results') or None
            mpaa = [d['rating'] for d in c_ratings if d['iso_3166_1'] == 'US'] if c_ratings else '0'
            if mpaa and mpaa != '0':
                mpaa = mpaa[0]

            #status = item.get('status', '0')
            status = item.get('status', '0')

            #"status": "Ended",
            #"tagline": "Tough enough for Texas.",
            #"type": "Scripted",
            #"vote_average": 8.051,
            #"vote_count": 1136,

            rating = str(item['vote_average']) or '0'
            rating = str(item.get('vote_average', 0))
            votes = str(item['vote_count']) or '0'


            cast = []
            try:
                credits_list = item.get('aggregate_credits', {}).get('cast', [])[:30]
                for person in credits_list:
                    icon = self.tmdb_img_link % (
                        c.tmdb_profilesize, person['profile_path']
                        ) if person['profile_path'] else ''
                    cast.append({
                        'name': person['name'],
                        'role': person['roles'][0]['character'],
                        'thumbnail': icon
                    })
                crew_list = item.get('aggregate_credits').get('crew', [])
                writer = [x['name'] for x in crew_list if x['jobs']['job'] == 'Writer']
                director = [x['name'] for x in crew_list if x['jobs']['job'] == 'Director']

                writer = ' / '.join(writer) if writer else '0'
                director = ' / '.join(director) if director else '0'


            except Exception as e:
                c.log(f"[CM Debug @ 185 in episodes.py] Exception raised in tmdb_list: {e}")
                pass
            if not cast:
                cast = '0'

            show_plot = c.lang(32623) if 'overview' not in item or not item['overview'] else item['overview']
            show_plot = client.replaceHTMLCodes(c.ensure_str(show_plot, errors='replace'))

            if not self.lang == 'en' and show_plot == '0':
                try:
                    translations = item.get('translations', {}).get('translations', [])
                    fallback_item = [x['data'] for x in translations if x.get('iso_639_1') == 'en'][0]
                    show_plot = fallback_item['overview']
                    show_plot = client.replaceHTMLCodes(str(show_plot))
                except Exception:
                    pass

            unaired = ''
            banner = clearlogo = clearart = landscape = '0'

            if meta:
                c.log(f"[CM Debug @ 227 in episodes.py] meta = {meta}")
                _meta = json.loads(unquote_plus(meta))
                show_poster = _meta['poster'],
                fanart = _meta['fanart'],
                c.log(f"[CM Debug @ 238 in episodes.py] fanart = {fanart}")
                banner = _meta['banner'],
                clearlogo = _meta['clearlogo'],
                clearart = _meta['clearart'],
                landscape = _meta['landscape']
            else:
                poster_path = item.get('poster_path', '')
                if poster_path:
                    show_poster = self.tmdb_img_link % (c.tmdb_postersize, poster_path)
                else:
                    show_poster = '0'


                fanart_path = item.get('backdrop_path', '')
                if fanart_path:
                    fanart = self.tmdb_img_link % (c.tmdb_fanartsize, fanart_path)
                else:
                    fanart = '0'

                tv_fanart = fanart_tv.get_fanart_tv_art(tvdb=tvdb_id)
                if tv_fanart:

                    c.log(f"[CM Debug @ 254 in episodes.py] tv_fanart =  {type(tv_fanart)}, data = {tv_fanart}")

                    show_poster = tv_fanart.get('poster', '0')
                    fanart = tv_fanart['fanart'] or '0'
                    #fanart = self.tmdb_img_link.format(c.tmdb_fanartsize, fanart_path)
                    banner = tv_fanart.get('banner', '0')
                    clearlogo = tv_fanart.get('clearlogo', '0')
                    clearart = tv_fanart.get('clearart', '0')
                    landscape = tv_fanart.get('landscape', '0')


        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 245 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 245 in episodes.py]Exception raised. Error = {e}')
            pass
        #except Exception as e:
            #c.log(f"Exception raised in tmdb_list part 2: {e}")
        c.log(f"[CM Debug @ 254 in episodes.py] status = {status}")

        for i in seasons_list:
            try:
                c.log(f"[CM Debug @ 228 in episodes.py] repr(item) = {repr(i)}")
                #raise Exception()
                season = str(int(i['season_number']))
                unaired = 'false'

                premiered = i.get('air_date', '0')
                if status == 'Ended':
                    pass
                elif not premiered or premiered == '0':
                    raise Exception()
                elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    unaired = 'true'
                    if self.showunaired != 'true':
                        raise Exception()

                plot = c.lang(32623) if 'overview' not in i or not i['overview'] else i['overview']
                plot = client.replaceHTMLCodes(c.ensure_str(plot, errors='replace'))

                poster_path = i.get('poster_path', '')
                if poster_path:
                    poster = self.tmdb_img_link % (c.tmdb_postersize, poster_path)
                else:
                    poster = show_poster

                thumb = poster


                self.list.append({'season': season, 'tvshowtitle': tvshowtitle, 'tagline': tagline,
                                    'year': year, 'premiered': premiered, 'status': status,
                                    'studio': studio, 'genre': genre, 'duration': duration,
                                    'mpaa': mpaa, 'castwiththumb': cast,
                                    'plot': plot, 'imdb': imdb_id, 'tmdb': tmdb_id,
                                    'tvdb': tvdb_id, 'poster': poster, 'fanart': fanart,
                                    'banner': banner, 'clearlogo': clearlogo, 'thumb': thumb,
                                    'clearart': clearart, 'landscape': landscape,
                                    'seasons': number_of_seasons, 'episodes': number_of_episodes,
                                    'rating': rating, 'votes': votes, 'unaired': unaired})
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 282 in episodes.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 282 in episodes.py]Exception raised. Error = {e}')
                pass

        return self.list


    def super_info(self, i):
        try:
            return i
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 333 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 333 in episodes.py]Exception raised. Error = {e}')
            pass

    def tmdb_list_backup(self, tvshowtitle, year, imdb, tmdb, meta, lite=False):
        try:

            tvdb = '0'
            if tmdb is None:
                tmdb = '0'

            if tmdb == '0' and not imdb == '0':
                try:
                    url = self.tmdb_by_imdb % imdb
                    result = self.session.get(url, timeout=15).json()
                    _id = result.get('tv_results', [])[0]
                    tmdb = _id.get('id')
                    #tmdb = '0' if not tmdb else str(tmdb)
                    tmdb = str(tmdb) if tmdb else '0'
                except Exception:
                    pass

            if imdb == '0' or tmdb == '0' or tvdb == '0':
                try:
                    ids_from_trakt = trakt.SearchTVShow(tvshowtitle, year, full=False)[0]
                    ids_from_trakt = ids_from_trakt.get('show')
                    if imdb == '0':
                        imdb = ids_from_trakt.get('ids', {}).get('imdb', '0')
                        if imdb != '0':
                            imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))
                    if tmdb == '0':
                        tmdb = ids_from_trakt.get('ids', {}).get('tmdb', '0')
                        if tmdb != '0':
                            tmdb = str(tmdb)
                    if tvdb == '0':
                        tvdb = ids_from_trakt.get('ids', {}).get('tvdb', '0')
                        if tvdb != '0':
                            tvdb = str(tvdb)
                except Exception:
                    pass

        except Exception as e:
            c.log(f"[CM Debug @ 158 in episodes.py] Exception raised in tmdb_list: {e}")
            return
        try:
            if tmdb == '0':
                raise Exception()
            if self.lang == 'en':
                item = self.session.get(
                    self.tmdb_show_link % (tmdb, 'en'), timeout=16).json()
            elif lite is True:
                item = self.session.get(
                    self.tmdb_show_lite_link % tmdb, timeout=16).json()
            else:
                item = self.session.get(
                    self.tmdb_show_link % (tmdb, self.lang) + ',translations', timeout=16).json()

            if item is None:
                raise Exception()


            c.log(f"[CM Debug @ 177 in episodes.py] item = {item}")

            _seasons = item['seasons']

            if self.specials == 'false':
                _seasons = [s for s in _seasons if not s['season_number'] == 0]

            studio = item['networks'][0]['name'] or '0'

            genres = item['genres'] or '0'
            if genres != '0':
                genre = [d['name'] for d in genres]
                genre = ' / '.join(genre)

            c.log(f"[CM Debug @ 365 in episodes.py] item runtime = {item['episode_run_time']}")

            duration = item['episode_run_time'][0] if 'episode_run_time' in item and item['episode_run_time'] else '45'
            duration = str(duration)


            m = item['content_ratings']['results'] or '0'
            if m != '0':
                mpaa = [d['rating'] for d in m if d['iso_3166_1'] == 'US'][0]
            else:
                mpaa = '0'

            status = item['status'] or '0'


            castwiththumb = []
            try:
                cast = item['aggregate_credits']['cast'][:30]
                for person in cast:
                    _icon = person['profile_path']
                    icon = self.tmdb_img_link % (c.tmdb_profilesize, _icon) if _icon else ''
                    castwiththumb.append(
                        {
                            'name': person['name'],
                            'role': person['roles'][0]['character'],
                            'thumbnail': icon
                        })
            except Exception:
                pass
            if not castwiththumb:
                castwiththumb = '0'

            show_plot = 'The Crew - No Plot Available' if 'overview' not in item or not item['overview'] else item['overview']
            show_plot = client.replaceHTMLCodes(c.ensure_str(show_plot, errors='replace'))

            if not self.lang == 'en' and show_plot == '0':
                try:
                    translations = item.get('translations', {})
                    translations = translations.get('translations', [])
                    fallback_item = [x['data'] for x in translations if x.get('iso_639_1') == 'en'][0]
                    show_plot = fallback_item['overview']
                    show_plot = client.replaceHTMLCodes(str(show_plot))
                except Exception:
                    pass

            unaired = ''

            banner = clearlogo = clearart = landscape = '0'

            if meta:
                _meta = json.loads(unquote_plus(meta))
                show_poster = _meta['poster'],
                fanart = _meta['fanart'],
                banner = _meta['banner'],
                clearlogo = _meta['clearlogo'],
                clearart = _meta['clearart'],
                landscape = _meta['landscape']
            else:
                poster_path = item['poster_path'] if 'poster_path' in item else ''

                if poster_path:
                    show_poster = self.tmdb_img_link % (c.tmdb_postersize, poster_path)
                else:
                    show_poster = '0'

                fanart_path = item['backdrop_path'] if 'backdrop_path' in item else ''

                if fanart_path:
                    fanart = self.tmdb_img_link % (c.tmdb_fanartsize, fanart_path)
                else:
                    fanart = '0'

        except Exception as e:
            c.log(f"Exception raised in tmdb_list part 2: {e}")
            pass


        for item in _seasons:
            try:
                season = str(int(item['season_number']))
                unaired = 'false'

                premiered = item.get('air_date', '0')
                if status == 'Ended':
                    pass
                elif not premiered or premiered == '0':
                    raise Exception()
                elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    unaired = 'true'
                    if self.showunaired != 'true':
                        raise Exception()

                plot = 'The Crew - No Plot Available' if 'overview' not in item or\
                    not item['overview'] else item['overview']
                plot = client.replaceHTMLCodes(c.ensure_str(plot, errors='replace'))


                poster_path = item['poster_path'] if 'poster_path' in item else ''
                if poster_path:
                    poster = self.tmdb_img_link % (c.tmdb_postersize, poster_path)
                else:
                    poster = show_poster

                self.list.append({'season': season, 'tvshowtitle': tvshowtitle,
                                    'year': year, 'premiered': premiered, 'status': status,
                                    'studio': studio, 'genre': genre, 'duration': duration,
                                    'mpaa': mpaa, 'castwiththumb': castwiththumb,
                                    'plot': plot, 'imdb': imdb, 'tmdb': tmdb,
                                    'tvdb': tvdb, 'poster': poster, 'fanart': fanart,
                                    'banner': banner, 'clearlogo': clearlogo,
                                    'clearart': clearart, 'landscape': landscape,
                                    'unaired': unaired})
            except Exception:
                pass

        return self.list




    def worker(self, level = 0):
        """
        Worker for episodes. This function is used in multiple places in the CM codebase.
        It takes a list of episodes and fetches the metadata for each episode in parallel.
        The function can be used to fetch the metadata for a list of episodes with or without info.
        If level is 0, the function fetches all the metadata for each episode.
        If level is 1, the function only fetches the title, year, season, episode and tvshowtitle.
        The function returns a list of metadata for each episode.
        """
        try:
            total = len(self.list)

            if total == 0:
                control.infoDialog('List returned no relevant results [worker episodes]', icon='INFO', sound=False)
                return

            for i in range(total):
                self.list[i].update({'metacache': False})

            self.list = metacache.fetch(self.list, self.lang, self.user)

            try:
                result = []
                #cm - changed worker 21-04-2025
                #cm - changed worker 27-04-2025 - added max threads/fixed steps
                with concurrent.futures.ThreadPoolExecutor(max_workers=c.get_max_threads(total, 50)) as executor:
                    futures = {executor.submit(self.super_info, i): i for i in range(total)}

                    #c.log(f"[CM Debug @ 1287 in episodes.py] futures = {futures}")

                    for future in concurrent.futures.as_completed(futures):
                        i = futures[future]
                        try:
                            result.append(future.result())
                            if(len(result) == total):
                                c.log(f"[CM Debug @ 1291 in episodes.py] completed all {len(result)} futures in worker for super_info")
                        except Exception as e:
                            c.log(f"[CM Debug @ 1296 in episodes.py] Exception raised. Error = {e}")

                if self.meta:
                    metacache.insert(self.meta)

            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 1303 in episodes.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 1304 in episodes.py]Exception raised. Error = {e}')
                pass
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1309 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1310 in episodes.py]Exception raised. Error = {e}')
            pass



    def seasonDirectory(self, items):
        try:

            c.log(f"[CM Debug @ 587 in episodes.py] inside seasonDirectory, len(items) = {len(items)}")
            if items is None or len(items) == 0:
                control.idle()
                # sys.exit()

            sysaddon = sys.argv[0]
            syshandle = int(sys.argv[1])

            #c.log(f"[CM Debug @ 311 in episodes.py] items = {items}")

            traktCredentials = trakt.getTraktCredentialsInfo()

            try:
                indicators = playcount.getSeasonIndicators(items[0]['imdb'])#['1']
            except Exception as e:
                pass

            watchedMenu = control.lang(32068) if trakt.getTraktIndicatorsInfo() is True else control.lang(32066)
            unwatchedMenu = control.lang(32069) if trakt.getTraktIndicatorsInfo() is True else control.lang(32067)
            queueMenu = control.lang(32065)
            traktManagerMenu = control.lang(32515)
            labelMenu = control.lang(32055)
            playRandom = control.lang(32535)
            addToLibrary = control.lang(32551)


            # changed by CM -  22-4-2021
            colorlist = [32589, 32590, 32591, 32592, 32593, 32594, 32595, 32596, 32597, 32598]
            colornr = colorlist[int(control.setting('unaired.identify'))]
            unairedcolor = re.sub(r"\][\w\s]*\[", "][I]%s[/I][", control.lang(int(colornr)))

            # fixed by CM -  28-4-2021
            if unairedcolor == '':
                unairedcolor = '[COLOR red][I]%s[/I][/COLOR]'

            c.log(f"[CM Debug @ 622 in episodes.py] items = {items[0]}")

            for i in items:
                try:
                    c.log(f"\n\n\n[CM Debug @ 627 in episodes.py] item = {i}\n\n\n============================================\n\n\n")
                    label = (f"{labelMenu} {i['season']}")

                    try:
                        if i['unaired'] == 'true':
                            label = unairedcolor % label
                    except Exception:
                        pass

                    systitle = sysname = quote_plus(i['tvshowtitle'])



                    # !warning change!!
                    # TODO str() maakt dat er bij fanart iets fout gaat, ondrzoeken! (niet bij poster), tuple bij fanart
                    poster = str(i['poster']) if 'poster' in i and not i['poster'] == '0' else c.addon_poster()
                    fanart = '0'
                    if isinstance(i['fanart'], tuple):
                        fanart = i['fanart'][0]
                    if fanart == '0':
                        fanart = str(i['fanart']) if 'fanart' in i and not i['fanart'] == '0' else c.addon_fanart()

                    c.log(f"[CM Debug @ 564 in episodes.py] i want to know the type of fanart. It is = {type(fanart)}")

                    c.log(f"[CM Debug @ 568 in episodes.py] fanart = {fanart} and type = {type(fanart)}")
                    banner = str(i['banner']) if 'banner' in i and not i['banner'] == '0' else c.addon_banner()
                    landscape = str(i['landscape']) if 'landscpape' in i and not i['landscape'] == '0' else fanart
                    clearlogo = str(i['clearlogo']) if 'clearlogo' in i and not i['clearlogo'] == '0' else c.addon_clearlogo()
                    clearart = str(i['clearart']) if 'clearart' in i and not i['clearart'] == '0' else c.addon_clearart()

                    discart = str(i['discart']) if 'discart' in i and not i['discart'] == '0' else c.addon_discart()

                    duration = i['duration'] if 'duration' in i and not i['duration'] == '0' else '45'
                    status = i['status'] if 'status' in i else '0'

                    episode_meta = {'poster': poster, 'fanart': fanart, 'banner': banner,
                                    'clearlogo': clearlogo, 'clearart': clearart, 'discart': discart,
                                    'landscape': landscape, 'duration': duration, 'status': status}

                    sysmeta = quote_plus(json.dumps(episode_meta))

                    imdb, tvdb, tmdb, year, season = i['imdb'], i['tvdb'], i['tmdb'], i['year'], i['season']

                    meta = dict((k, v) for k, v in iter(i.items()) if not v == '0')
                    meta['code'] = imdb
                    meta['imdbnumber'] = imdb
                    meta['imdb_id'] = imdb
                    meta['tvdb_id'] = tvdb
                    meta['mediatype'] = 'tvshow'
                    meta['trailer'] = f'{sysaddon}?action=trailer&name={sysname}&imdb={imdb}&tmdb={tmdb}'


                    if 'duration' not in i or i['duration'] == '0':
                        meta['duration'] = '45'

                    if meta['duration'] != '0':
                        #meta['duration'] = str(int(meta['duration']) * 60)
                        meta['duration'] = str(int(meta['duration']))

                    try:
                        meta['genre'] = cleangenre.lang(meta['genre'], self.lang)
                    except Exception:
                        pass
                    try:
                        seasonYear = i['premiered']
                        seasonYear = re.findall(r'(\d{4})', seasonYear)[0]
                        seasonYear = str(seasonYear)
                        meta['year'] = seasonYear
                    except Exception:
                        pass

                    try:
                        overlay = int(playcount.getSeasonOverlay(indicators, season))
                        if overlay == 7:
                            meta.update({'playcount': 1, 'overlay': 7})
                        else:
                            meta.update({'playcount': 0, 'overlay': 6})
                    except Exception:
                        pass

                    cm = []
                    cm.append((playRandom, f'RunPlugin({sysaddon}?action=random&rtype=episode&tvshowtitle={systitle}&year={year}&imdb={imdb}&tmdb={tmdb}&season={season})'))
                    cm.append((queueMenu, f'RunPlugin({sysaddon}?action=queueItem)'))

                    #if
                    cm.append((watchedMenu, f'RunPlugin({sysaddon}?action=tvPlaycount&name={systitle}&imdb={imdb}&tmdb={tmdb}&season={season}&query=7)'))
                    cm.append((unwatchedMenu, f'RunPlugin({sysaddon}?action=tvPlaycount&name={systitle}&imdb={imdb}&tmdb={tmdb}&season={season}&query=6)'))

                    if traktCredentials:
                        cm.append((traktManagerMenu, f'RunPlugin({sysaddon}?action=traktManager&name={sysname}&tmdb={tmdb}&content=tvshow)'))

                    cm.append((addToLibrary, f'RunPlugin({sysaddon}?action=tvshowToLibrary&tvshowtitle={systitle}&year={year}&imdb={imdb}&tmdb={tmdb})'))

                    try:
                        item = control.item(label=label, offscreen=True)
                    except Exception:
                        item = control.item(label=label)


                    art = {}
                    thumb = meta.get('thumb') or fanart

                    #c.log(f"[CM Debug @ 469 in episodes.py] poster = {type(poster)} and banner = {type(banner)} and fanart = {type(fanart)} and thumb = {type(thumb)} and landscape = {type(landscape)} and clearlogo = {type(clearlogo)} and clearart = {type(clearart)} and discart = {type(discart)}")

                    art.update({
                        'icon': poster,
                        #'thumb': poster,
                        'banner': banner,
                        'poster': poster,
                        'tvshow.poster': poster,
                        'season.poster': poster,
                        'landscape': landscape,
                        'clearlogo': clearlogo,
                        'thumb': thumb,
                        #'clearart': clearart,
                        #'discart': discart
                    })
                    #if setting_fanart == 'true':
                        #art['fanart'] = fanart


                    #if setting_fanart == 'true':
                        #art['fanart'] = fanart

                    item.setArt(art)


                    castwiththumb = i.get('castwiththumb')
                    if castwiththumb and not castwiththumb == '0':
                        #item.setCast(castwiththumb)
                        meta['cast'] = castwiththumb

                    meta['art'] = art

                    #c.log(f"[CM Debug @ 498 in episodes.py] type art = {type(art)}")
                    #item.setArt(art)
                    #item.setArt(meta['art'])

                    info_tag = ListItemInfoTag(item, 'video')
                    infolabels = control.tagdataClean(meta)

                    #infolabels.update({'genre': genres, 'studio': studios, 'country': countries})

                    info_tag.set_info(infolabels)
                    unique_ids = {'imdb': imdb, 'tmdb': str(tmdb)}
                    info_tag.set_unique_ids(unique_ids)

                    if 'cast' in meta:
                        cast = meta.get('cast')
                        info_tag.set_cast(cast)
                    elif 'castwiththumb' in meta:
                        cast = meta.get('castwiththumb')
                        info_tag.set_cast(cast)
                    else:
                        info_tag.set_cast([])

                    meta['studio'] = c.string_split_to_list(meta['studio']) if 'studio' in meta else []
                    meta['genre'] = c.string_split_to_list(meta['genre']) if 'genre' in meta else []
                    meta['director'] = c.string_split_to_list(meta['director']) if 'director' in meta else []
                    meta['writer'] = c.string_split_to_list(meta['writer']) if 'writer' in meta else []

                    # Pass listitem to the infotagger module and specify tag type
                    info_tag = ListItemInfoTag(item, 'video')
                    infolabels = control.tagdataClean(meta)

                    info_tag.set_info(infolabels)
                    unique_ids = {'imdb': imdb, 'tmdb': str(tmdb)}
                    info_tag.set_unique_ids(unique_ids)
                    info_tag.set_cast(meta.get('cast', []))

                    stream_info = {'codec': 'h264'}
                    info_tag.add_stream_info('video', stream_info)  # (stream_details)
                    item.addContextMenuItems(cm)

                    url = f'{sysaddon}?action=episodes&tvshowtitle={systitle}&year={year}&imdb={imdb}&tmdb={tmdb}&meta={sysmeta}&season={season}'
                    c.log(f"[CM Debug @ 800 in episodes.py]additem with label = {label}")


                    control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
                except Exception as e:
                    import traceback
                    failure = traceback.format_exc()
                    c.log(f'[CM Debug @ 557 in episodes.py]Traceback:: {failure}')
                    c.log(f'[CM Debug @ 558 in episodes.py]Exception raised. Error = {e}')


            try:
                control.property(syshandle, 'showplot', items[0]['plot'])
            except Exception:
                pass

            control.content(syshandle, 'tvshows')
            control.directory(syshandle, cacheToDisc=True)
            c.log(f"[CM Debug @ 818 in episodes.py] after ending control.directory(syshandle, cacheToDisc=True)")
            views.set_view('seasons', {'skin.estuary': 55, 'skin.confluence': 500})
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 826 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 826 in episodes.py]Exception raised. Error = {e}')
            pass


class episodes:
    def __init__(self):
        self.list = []
        self.blist = []
        self.meta = []

        self.speedtest_start = time.perf_counter()
        self.session = requests.Session()
        self.showFanart = control.setting('fanart') == 'true'
        self.trakt_link = 'https://api.trakt.tv'
        self.tvmaze_link = 'https://api.tvmaze.com'
        self.datetime = datetime.datetime.now(datetime.timezone.utc)
        self.systime = self.datetime.strftime('%Y%m%d%H%M%S%f')
        self.today_date = self.datetime.strftime('%Y-%m-%d')
        self.trakt_user = control.setting('trakt.user').strip()
        self.showunaired = control.setting('showunaired') or 'true'
        self.specials = control.setting('tv.specials') or 'true'
        self.lang = control.apiLanguage()['tmdb'] or 'en'
        self.hq_artwork = control.setting('hq.artwork') or 'false'

        self.fanart_tv_user = control.setting('fanart.tv.user')
        self.tmdb_user = control.setting('tm.personal_user') or control.setting('tm.user') or keys.tmdb_key
        self.user = self.tmdb_user


        self.tmdb_img_link = 'https://image.tmdb.org/t/p/%s%s'
        self.tmdb_link = 'https://api.themoviedb.org/3/'

        self.tmdb_show_link = f'{self.tmdb_link}tv/%s?api_key={self.tmdb_user}'
        self.tmdb_season_link = f'{self.tmdb_link}tv/%s/season/%s?api_key={self.tmdb_user}&language=%s&append_to_response=aggregate_credits'
        self.tmdb_season_lite_link = f'{self.tmdb_link}tv/%s/season/%s?api_key={self.tmdb_user}&language={self.lang}'
        self.tmdb_episode_link = f'{self.tmdb_link}tv/%s/season/%s/episode/%s?api_key={self.tmdb_user}&language={self.lang}&append_to_response=credits,images'
        self.tmdb_by_imdb = f'{self.tmdb_link}find/%s?api_key={self.tmdb_user}&external_source=imdb_id'
        self.search_link = f'{self.tmdb_link}search/tv?api_key={self.tmdb_user}&language=en-US&query=%s&page=1'
        self.tmdb_external_ids_by_tmdb = f'{self.tmdb_link}tv/%s/external_ids?api_key={self.tmdb_user}&language=en-US'
        self.tmdb_api_link = f'{self.tmdb_link}tv/%s?api_key={self.tmdb_user}&language={self.lang}&append_to_response=credits,images,ratings,external_ids,videos,translations'

        #self.fanart_tv_art_link = 'http://webservice.fanart.tv/v3/tv/%s'

        # self.added_link = 'https://api.tvmaze.com/schedule'
        self.added_link = f'{self.trakt_link}/calendars/my/shows/date[5]/6/'
        self.calendar_link = 'https://api.tvmaze.com/schedule?date=%s&country=US'
        # https://api.trakt.tv/calendars/all/shows/date[30]/31 #use this for new episodes?
        # self.mycalendar_link = f'{self.trakt_link}/calendars/my/shows/date[29]/60/'
        # go back 30 and show all shows aired until tomorrow
        self.mycalendar_link = f'{self.trakt_link}/calendars/my/shows/date[30]/31/'
        self.trakthistory_link = f'{self.trakt_link}/users/me/history/shows?limit=40'
        self.progress_link = f'{self.trakt_link}/users/me/watched/shows'
        #self.progress_link = 'https://trakt.tv/users/me/progress/watched/activity?hide_completed=true'
        self.hiddenprogress_link = f'{self.trakt_link}/users/hidden/progress_watched?limit=1000&type=show'
        self.onDeck_link = f'{self.trakt_link}/sync/playback/episodes?limit=40'
        self.traktlists_link = f'{self.trakt_link}/users/me/lists'
        self.traktlikedlists_link = f'{self.trakt_link}/users/likes/lists?limit=1000000'
        self.traktlist_link = f'{self.trakt_link}/users/%s/lists/%s/items'
        self.show_watched_link = f'{self.trakt_link}shows/%s/progress/collection?hidden=%s&specials=%s&count_specials=%s'

    def __del__(self):
        self.session.close()

    def get(self, tvshowtitle, year, imdb_id, tmdb_id, meta, season=None, episode=None, include_episodes=True, create_directory=True):
        """
        Get episodes for a TV show.

        Args:
            tvshowtitle (str): The title of the TV show.
            year (int): The year the TV show was released.
            imdb_id (str): The IMDB ID of the TV show.
            tmdb_id (str): The TMDB ID of the TV show.
            meta (dict): The metadata of the TV show.
            season (int or None): The season to retrieve. If None, all seasons are retrieved.
            episode (int or None): The episode to retrieve. If None, all episodes are retrieved.
            include_episodes (bool): If True, include episodes in the results.
            create_directory (bool): If True, create a directory for the episodes.

        Returns:
            list: A list of episodes.
        """
        try:
            if include_episodes:
                #self.list = cache.get(self.tmdb_list, 1, tvshowtitle, year, imdb_id, tmdb_id, season, meta)
                self.list = cache.get(self.tmdb_list, 0, tvshowtitle, year, imdb_id, tmdb_id, season, meta)
                if season is not None and episode is not None:
                    c.log(f"[CM Debug @ 831 in episodes.py] title = {tvshowtitle}, year = {year}, imdb_id = {imdb_id}, tmdb_id = {tmdb_id}, season = {season}, episode = {episode}")
                    #idx = [x for x, y in enumerate(self.list) if y['season'] == str(season) and y['episode'] == str(episode)][-1]
                    idx = [x for x, y in enumerate(self.list) if y['season'] == str(season) and y['episode'] == str(episode)][-1]
                    c.log(f"[CM Debug @ 834 in episodes.py] idx = {idx}")
                    self.list = [y for x, y in enumerate(self.list) if x >= idx]

                if create_directory:
                    self.episodeDirectory(self.list)
            else:
                self.list = self.tmdb_list(tvshowtitle, year, imdb_id, tmdb_id, season, lite=True)

            return self.list
        except Exception:
            raise

    def calendar(self, url, idx = True):
        try:
            sortorder = c.get_setting('prgr.sortorder')
            c.log(f"[CM Debug @ 853 in episodes.py] url = {url}")

            elements = ['tvProgress', 'tvmaze']
            for i in elements:
                if i in url:
                    break

            #if  any(elem in url for elem in elements):
                #pass
            else:
                url = getattr(self, url + '_link')
                c.log(f"[CM Debug @ 862 in episodes.py] url = {url}")

                ####cm#
                # Making it possible to use date[xx] in url's where xx is a str(int)
                for i in re.findall(r'date\[(\d+)\]', url):
                    url = url.replace(
                        f'date[{i}]',
                        (self.datetime - datetime.timedelta(days=int(i))).strftime('%Y-%m-%d')
                        )


            if url == 'tvProgress':
                #self.list = cache.get(self.episodes_progress_list, 0)
                self.list = self.episodes_progress_list()
                #c.log(f"[CM Debug @ 879 in episodes.py] self.list = {self.list}")





            if url == self.progress_link:
                self.blist = cache.get(self.trakt_progress_list, 720, url)
                self.list = cache.get(self.trakt_progress_list, 0, url)
                c.log(f"[CM Debug @ 885 in episodes.py] url = {url}")


            elif url == self.onDeck_link:
                self.blist = cache.get(self.trakt_episodes_list, 720, url, self.trakt_user, self.lang)
                self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)
                #self.list = self.list[::-1]
                #self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)

            elif url == self.mycalendar_link:
                #self.blist = cache.get(self.trakt_episodes_list, 720, url, self.trakt_user, self.lang)
                self.blist = self.trakt_episodes_list(url, self.trakt_user, self.lang)
                #self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)
                self.list = self.trakt_episodes_list(url, self.trakt_user, self.lang)
                self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)

            elif url == self.added_link:
                #self.blist = cache.get(self.trakt_episodes_list, 720, url, self.trakt_user, self.lang)
                self.blist = self.trakt_episodes_list(url, self.trakt_user, self.lang)
                #self.list = cache.get( self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)
                self.list = self.trakt_episodes_list(url, self.trakt_user, self.lang)
                self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)

            elif url == self.trakthistory_link:
                self.list = cache.get(self.trakt_episodes_list, 1, url, self.trakt_user, self.lang)
                self.list = sorted(self.list, key=lambda k: int(k['watched_at']), reverse=True)

            elif self.trakt_link in url and '/users/' in url:
                #self.list = cache.get(self.trakt_list, 0, url, self.trakt_user)
                self.list = self.trakt_list(url, self.trakt_user)
                self.list = self.list[::-1]

            elif self.trakt_link in url:
                self.list = cache.get(self.trakt_list, 1, url, self.trakt_user)

            elif self.tvmaze_link in url and url == self.added_link:
                urls = [i['url'] for i in self.calendars(idx=False)][:5]
                for url in urls:
                    self.list += self.tvmaze_list(url, True)

            elif self.tvmaze_link in url:
                self.list = cache.get(self.tvmaze_list, 1, url, False)

            if idx:
                self.worker(0)

            #if '_sort_key' in self.list[0]:
                #self.list = sorted(self.list, key=lambda k: k['_sort_key'], reverse=True)
            #elif 'premiered' in self.list[0]:
                #self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)
            if sortorder == '0':
                self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)
            else:
                for i in self.list:
                    c.log(f"[CM Debug @ 937 in episodes.py] _sork_key = {i['_sort_key']}")
                self.list = sorted(self.list, key=lambda k: k['_sort_key'], reverse=True)

            self.episodeDirectory(self.list)
            return self.list
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 884 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 884 in episodes.py]Exception raised. Error = {e}')
            pass
        #except Exception as e:
            #c.log(f"[CM Debug @ 885 in episodes.py] Exception: {e}")

    def widget(self):

        if trakt.getTraktIndicatorsInfo() is True:
            setting = control.setting('tv.widget.alt')
        else:
            setting = control.setting('tv.widget')

        if setting == '2':
            self.calendar(self.progress_link)
        elif setting == '3':
            self.calendar(self.mycalendar_link)
        else:
            self.calendar(self.added_link)

    def calendars(self, idx=True):
        months_list = control.lang(32060).split('|')
        days_list = control.lang(32061).split('|')

        for i in range(30): # cm - we go back 30 days
            try:
                _date = (self.datetime - datetime.timedelta(days=i))
                year_int = _date.strftime('%Y')
                month_day_int = _date.strftime('%d') #cm - day of month zero padded
                name_month_int = int(_date.strftime('%m')) #cm - month as padded with  0 string starting with 01 = january
                name_day_int = _date.isoweekday() #cm - weekday as decimal int starting where 1 = monday

                part_a = days_list[name_day_int-1]
                part_b = f"{month_day_int} {months_list[name_month_int-1]} {year_int}"
                name = (control.lang(32062) % (part_a, part_b))
                url = self.calendar_link % (self.datetime - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                self.list.append({'name': name, 'url': url, 'image': 'calendar.png', 'action': 'calendar'})
            except Exception as e:
                c.log(f"[cm debug in episodes.py @ 726] error={e}")

        if idx is True:
            self.addDirectory(self.list)
        return self.list

    def userlists(self):
        userlists = []
        try:

            if trakt.getTraktCredentialsInfo() is False:
                raise Exception()
            activity = trakt.getAllActivity()
        except Exception:
            pass

        try:
            if trakt.getTraktCredentialsInfo() is False:
                raise Exception()
            try:
                if activity > cache.timeout(self.trakt_user_list, self.traktlists_link, self.trakt_user):
                    raise Exception()
                userlists += cache.get(self.trakt_user_list,  720, self.traktlists_link, self.trakt_user)
            except Exception:
                userlists += cache.get(self.trakt_user_list, 0, self.traktlists_link, self.trakt_user)
        except Exception:
            pass
        try:
            self.list = []
            if trakt.getTraktCredentialsInfo() is False:
                raise Exception()
            try:
                if activity > cache.timeout(self.trakt_user_list, self.traktlikedlists_link, self.trakt_user):
                    raise Exception()
                userlists.append(cache.get(self.trakt_user_list, 720, self.traktlikedlists_link, self.trakt_user))
            except Exception:
                userlists.append(cache.get(self.trakt_user_list, 0, self.traktlikedlists_link, self.trakt_user))
        except Exception:
            pass

        self.list = userlists
        for x, item in enumerate(self.list):
            c.log(f"[CM Debug @ 1114 in episodes.py] item = {item} of type {type(item)}")
            item = dict(item)
            #item is a dictionary so adding to a dict:
            item['image'] = 'userlists.png'
            item['action'] = 'calendar'
            # self.list[x].update({'image': 'userlists.png', 'action': 'calendar'})
            # item.update({'image': 'userlists.png', 'action': 'calendar'})

        self.addDirectory(self.list, queue=True)
        return self.list

    def get_media_info(self, result, key, return_type='', default_value='0'):
        """
        Returns a value from a dictionary based on the key.
        If the value is a list or dictionary, it can be converted to a string or integer.
        If the value is a string and the return type is int, it will be converted to an integer.
        :param result: The dictionary to retrieve the value from.
        :param key: The key to retrieve the value for.
        :param return_type: The type to return the value as. Options are str, int, list, dict.
        :param default_value: The value to return if the key is not found.
        :return: The value from the dictionary.
        """

        def convert_to(return_type, value):
            if return_type == 'str':
                return ' / '.join(map(str, value))
            elif return_type == 'int':
                return sum(1 for _ in value)
            elif return_type == 'list':
                return list(value.items())
            elif return_type == 'dict':
                return dict(enumerate(value))
            else:
                return value

        if key == '':
            # return all keys as values
            return [convert_to(return_type, result[k]) for k in result.keys()]
        else:
            value = result.get(key, default_value)
            return convert_to(return_type, value)

    def get_media_info_old(self, result, key, return_type='', default_value='0'):

        def check_numeric(value):
            if value.isnumeric():
                return int(value)
            return len(value)

        def get_list_from_dict(dict):
            #check if key exists in dict
            if len(result[key].keys() > 0):
                #dict has key/value pairs
                list_from_dict = list(result[key].items())
                return list_from_dict
            else:
                #dict has no key/value pairs
                list_from_dict = []
                for x, item in enumerate(result[key]):
                    k = f'key{x}'
                    list_from_dict.append((k, item))
                return list_from_dict


        def get_dict_from_list(list):
            dict_from_list = []
            #check if key exists in dict
            if len(result[key].keys() > 0):
                dict_from_list = list(result[key].items())
                return dict_from_list
            else:
                #dict has no key/value pairs
                dict_from_list = dict(enumerate(result[key]))
                return dict_from_list


        def get_key_info(result, key):
            if result[key] is None:
                result[key] = default_value
            elif isinstance(result[key], (dict, list)):
                if return_type == '':
                    return result[key]
                if return_type == 'str':
                    return ' / '.join(result[key])
                if return_type == 'int':
                    return check_numeric(result[key])
                if return_type == 'list':
                    return result.items()


            if isinstance(result[key], list):
                if return_type == 'dict':
                    return get_dict_from_list(result[key])
            if isinstance(result[key], dict):
                if return_type == 'list':
                    #check if key exists in dict
                    return get_list_from_dict(result[key])



            elif isinstance(result[key], str):
                if return_type == '':
                    return result[key]
                if return_type == 'int':
                    return check_numeric(result[key])

                return result[key]
            return

        if key == '':
            #return all keys as values
            for k in result.keys():
                r = []
                r.append = get_key_info(result, k)
            return r
        else:
            return get_key_info(result, key)

    def trakt_list(self, url, user, return_art=True):
        try:
            c.log(f"[CM Debug @ 1031 in episodes.py] inside trakt_list: url = {url}")
            for i in re.findall(r'date[(\d+)]', url):
                url = url.replace(
                    f'date[{i}]',
                    (self.datetime - datetime.timedelta(days=int(i))).strftime(
                        '%Y-%m-%d'
                    ),
                )
                #url = url.replace('date[%s]' % i, (self.datetime - datetime.timedelta(days=int(i))).strftime('%Y-%m-%d'))
                c.log(f'[CM DEBUG in episodes.py @ 713] url={url}')

            q = dict(parse_qsl(urlsplit(url).query))
            q.update({'extended': 'full'})
            q = (urlencode(q)).replace('%2C', ',')
            u = url.replace('?' + urlparse(url).query, '') + '?' + q

            itemlist = []
            items = trakt.getTraktAsJson(u)
        except Exception:
            return []

        if items is None:
            return []

        for item in items:
            try:
                c.log(f"[CM Debug @ 1052 in episodes.py] item is of type {type(item)}\n\nitem = {item}")
                #item is a dictionary

                resume_point = item.get('progress', 0.0)
                last_watched = item['episode']['updated_at'] if 'updated_at' in item['episode'] else item['show']['updated_at'] if 'updated_at' in item['show'] else '0'


                tvshowtitle = item['show']['title'] or '0'

                title = item['episode']['title']
                if not title:
                    raise Exception()
                title = client.replaceHTMLCodes(title)

                season = item['episode']['season']
                season = re.sub('[^0-9]', '', '%01d' % int(season))
                if season == '0' and self.specials != 'true':
                    raise Exception()

                episode = item['episode']['number']
                episode = re.sub('[^0-9]', '', '%01d' % int(episode))
                if episode == '0':
                    raise Exception()

                imdb = item['show']['ids']['imdb']
                if not imdb:
                    imdb = '0'
                else:
                    imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))

                tvdb = item['show']['ids']['tvdb'] or '0'
                if tvdb != '0':
                    tvdb = re.sub('[^0-9]', '', str(tvdb))

                tmdb = item['show']['ids']['tmdb']
                if not tmdb:
                    raise Exception()
                tmdb = str(tmdb)

                year = item['show']['year']
                year = re.sub('[^0-9]', '', str(year))

                premiered = item['episode']['first_aired']
                try:
                    premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
                except Exception:
                    premiered = '0'

                studio = item['show']['network'] or '0'

                genre = item['show']['genres'] or '0'
                if genre != '0':
                    genre = [i.title() for i in genre]
                    genre = ' / '.join(genre)

                duration = str(item['show']['runtime']) or '0' #duration in minutes
                rating = str(item['episode']['rating']) or '0'
                votes = str(item['episode']['votes']) or '0'

                if votes != '0':
                    votes = str(format(int(votes), ',d'))

                mpaa = item['show']['certification'] if 'certification' in item['show'] else '0'

                plot = item['episode']['overview'] or item['show']['overview'] or '0'

                if plot != '0':
                    plot = client.replaceHTMLCodes(plot)

                paused_at = item.get('paused_at', '0') or '0'
                if paused_at != '0':
                    paused_at = re.sub('[^0-9]+', '', paused_at)

                watched_at = item.get('watched_at', '0') or '0'
                if watched_at != '0':
                    watched_at = re.sub('[^0-9]+', '', watched_at)

                try:
                    if self.lang == 'en':
                        raise Exception()

                    item = trakt.getTVShowTranslation(imdb, lang=self.lang, season=season, episode=episode,  full=True)

                    title = item.get('title') or title
                    plot = item.get('overview') or plot

                except Exception:
                    pass

                if control.setting('fanart') == 'true' and return_art is True:
                    if not tvdb == '0':
                        tempart = fanart_tv.get_fanart_tv_art(tvdb=tvdb)
                        c.log(f"[CM Debug @ 1092 in episodes.py] tempart = {tempart}")
                        if tempart:
                            poster = tempart['poster']
                            fanart = tempart['fanart']
                            banner = tempart['banner']
                            landscape = tempart['landscape']
                            clearlogo = tempart['clearlogo']
                            clearart = tempart['clearart']


                    if poster == '0':
                        poster, fanart = self.get_tmdb_art(tmdb)
                        landscape = fanart
                else:
                    poster = fanart = banner = landscape = clearlogo = clearart = '0'

                itemlist.append({
                                'title': title, 'season': season, 'episode': episode,
                                'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered,
                                'status': 'Continuing', 'studio': studio, 'genre': genre,
                                'duration': duration, 'rating': rating, 'votes': votes,
                                'mpaa': mpaa, 'plot': plot, 'imdb': imdb, 'tvdb': tvdb,
                                'tmdb': tmdb, 'poster': poster, 'thumb': landscape,
                                'fanart': fanart, 'banner': banner, 'landscape': landscape,
                                'clearlogo': clearlogo, 'clearart': clearart,
                                'paused_at': paused_at, 'watched_at': watched_at, '_last_watched': last_watched,
                                'resume_point': resume_point
                                })
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 933 in episodes.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 933 in episodes.py]Exception raised. Error = {e}')
                pass

        itemlist = itemlist[::-1]
        return itemlist

    def get_show_watched_progress(self, trakt_id, hidden=False, specials=False, count_specials=False):
        url = self.show_watched_link % (trakt_id, hidden, specials, count_specials)
        result = trakt.getTraktAsJson(url)
        return result

    def episodes_progress_list(self):
        try:
            progress = trakt.get_trakt_progress('episode')

            for item in progress:
                c.log(f"[CM Debug @ 1168 in episode.py] item = \n\n\n=====================================================\n\n\n{item}\n\n\n============================================\n\n\n")

                tmdb = str(item['tmdb'])
                tvdb = str(item['tvdb'])
                imdb = item['imdb']
                trakt_id = str(item['trakt'])

                showtmdb = str(item['showtmdb'])
                showtvdb = str(item['showtvdb'])
                showimdb = item['showimdb']
                showtrakt = str(item['showtrakt'])

                result = self.get_show_watched_progress(showtrakt)
                episodes_aired = result['aired']
                episodes_watched = result['completed']
                next_episode = result['next_episode']

                c.log(f"[CM Debug @ 1216 in episodes.py] next_episodes = {repr(next_episode)}")

                #duration = item['show']['runtime']
                #tagline = item['show']['tagline']
                #plot = item['show']['overview']


                tvshowtitle = item['tvshowtitle']
                last_played = item['last_played']

                title = item['title']
                season = item['season']
                episode = item['episode']
                # !warning, resume_point is a float, percentage played!
                resume_point = item['resume_point']
                year = item['year']
                mediatype = item['media_type']
                action = 'episode'


                self.list.append({
                    'title': title, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb,
                    'trakt': trakt_id, 'showimdb': showimdb, 'showtmdb': showtmdb,
                    'showtvdb': showtvdb, 'showtrakt': showtrakt,
                    'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle,
                    'resume_point': resume_point, 'year': year, '_last_watched': last_played,
                    'mediatype': mediatype, 'action': action, 'next_episode': next_episode,
                    'episodes_aired': episodes_aired, 'episodes_watched': episodes_watched
                    })

            return self.list


        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1140 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1140 in episodes.py]Exception raised. Error = {e}')
            pass

    def trakt_progress_list(self, url):
        try:
            url += '?extended=full'
            result = trakt.getTraktAsJson(url)
            items = []
        except Exception as e:
            c.log(f"Exception 1 in trakt_progress_list: {e}")
            return
        sortorder = control.setting('prgr.sortorder')

        for item in result:
            try:
                c.log(f"\n\n\n[CM Debug @ 2047 in episodes.py] item = {item}\n\n\n")

                num_1 = 0
                for i in range(len(item['seasons'])):
                    if item['seasons'][i]['number'] > 0:
                        num_1 += len(item['seasons'][i]['episodes'])
                num_2 = int(item['show']['aired_episodes'])

                #cm calc max season and max episode in that season
                max_season = max([x['number'] for x in item['seasons']])
                max_episode = max([x['number'] for x in item['seasons'][max_season-1]['episodes']])
                #c.log(f"[CM Debug @ 1150 in episodes.py] {item['show']['title']} has max_season = {max_season} and max_episode = {max_episode}")

                if num_1 >= num_2:
                    #c.log(f"[CM Debug @ 961 in episodes.py] all episodes wathed from {item['show']['title']}")
                    # cm - all episodes watched
                    #raise Exception('All episodes watched')
                    # cm but i still need all info though ??
                    #cm if i have watched all episodes of a show, the status won't change anymore
                    # cm so i can create a fetch info from db instead of trakt but for now i won't
                    #
                    # cm - i will just skip the show
                    t = item['show']['title']
                    raise Exception(f'{t}: All episodes watched')
                    #pass

                season = str(item['seasons'][-1]['number'])
                episode = [x for x in item['seasons'][-1]['episodes'] if 'number' in x]
                episode = sorted(episode, key=lambda x: x['number'])
                episode = str(episode[-1]['number'])

                tvshowtitle = item['show']['title']  # item.get('show']'title')
                year = item['show']['year']  # year returns int
                imdb = item['show']['ids']['imdb'] or '0'  # returns str
                tvdb = str(item['show']['ids']['tvdb']) or '0' # returns int
                tmdb = str(item['show']['ids']['tmdb']) or '0' # returns int
                slug = item['show']['ids']['slug']
                trakt_id = item['show']['ids']['trakt']

                first_aired = item['show']['first_aired']

                if not tvshowtitle:
                    raise Exception('No Title')
                else:
                    tvshowtitle = client.replaceHTMLCodes(tvshowtitle)

                trailer = str(item.get('show').get('trailer')) or '0'

                if int(year) > int(self.datetime.strftime('%Y')):
                    raise Exception()

                studio = str(item['show']['network']) or '0'
                duration = item['show']['runtime'] or 45
                if duration == 1: #trakt return 1 in some cases ??
                    duration = 45

                tagline = item['show']['tagline'] or '0'
                tagline = client.replaceHTMLCodes(tagline)
                plot = item['show']['overview'] or '0'
                plot = client.replaceHTMLCodes(plot)
                country = item['show']['country'].upper() or '0'
                network = item['show']['network'] or '0'


                mpaa = item['show']['certification'] or '0'
                status = item['show']['status'] or '0'
                genre = item['show']['genres'] or '0'
                if genre != '0':
                    genre = '/'.join(genre)

                last_watched = item['last_watched_at'] or '0'

                items.append(
                    {
                        'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, 'trakt_id': trakt_id,
                        'tvshowtitle': tvshowtitle, 'year': year, 'studio': studio, 'duration': duration,
                        'first_aired': first_aired, 'mpaa': mpaa, 'status': status, 'genre': genre,
                        'snum': season, 'enum': episode, 'trailer': trailer, 'season': season,
                        'episode': episode, 'sortorder': sortorder, 'action': 'episodes',
                        '_last_watched': last_watched, 'slug': slug, 'country': country,
                        'network': network, 'tagline': tagline, 'plot': plot
                    })
            except Exception as e:
                #c.log(f"[CM Debug @ 1208 in episodes.py] error = {e}")
                pass

        try:
            result = trakt.getTraktAsJson(self.hiddenprogress_link)
            #result = cache.get(trakt.getTraktAsJson, 1, self.hiddenprogress_link)
            #c.log(f"\n\n[CM Debug @ 1029 in episodes.py] result = {result}\n\n")

            if 'status_code' in result and int(result['status_code'][0]) == 34:
                raise Exception(f'Resource status_code == 34 with url == {self.hiddenprogress_link}')

            # cm - removing all dupes
            mylist = [str(i['show']['ids']['tmdb']) for i in result]
            result = list(dict.fromkeys(mylist))

            items = [i for i in items if i['tmdb'] not in result]
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1040 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1040 in episodes.py]Exception raised. Error = {e}')
            pass
        c.log(f"[CM Debug @ 1451 in episodes.py] aantal items = {len(items)}")
        #items = items[:100]

        self.list = items
        return self.list

    def get_tmdb_art(self, tmdb):
        try:
            url = self.tmdb_show_link % tmdb
            result = self.session.get(url, timeout=10).json()

            poster = self.tmdb_img_link % (c.tmdb_postersize, result['poster_path']) if 'poster_path' in result else '0'
            fanart = self.tmdb_img_link % (c.tmdb_fanartsize, result['background_path']) if 'background_path' in result else '0'

            return poster, fanart
        except Exception:
            pass

    def trakt_episodes_list(self, url, user, lang):

        items = self.trakt_list(url, user, return_art=False)

        c.log(f"[CM Debug @ 1247 in episodes.py] items = {items}")

        def items_list(i):

            tmdb, imdb, tvdb = i['tmdb'], i['imdb'], i['tvdb']

            if (not tmdb or tmdb == '0') and not imdb == '0':
                try:
                    url = self.tmdb_by_imdb % imdb
                    result = self.session.get(url, timeout=16).json()
                    tv_results = result.get('tv_results', [])[0]
                    tmdb = tv_results.get('id')
                    if not tmdb:
                        tmdb = '0'
                    else:
                        tmdb = str(tmdb)
                except Exception:
                    pass

            try:
                item = [x for x in self.blist if x['tmdb'] == tmdb and x['season'] == i['season'] and x['episode'] == i['episode']][0]

                if item['poster'] == '0':
                    raise Exception()
                self.list.append(item)
                return
            except Exception:
                pass

            try:
                if tmdb == '0':
                    raise Exception()

                url = self.tmdb_episode_link % (tmdb, i['season'], i['episode'])
                item = self.session.get(url, timeout=10).json()

                title = item['name']
                if not title:
                    title = '0'
                else:
                    title = client.replaceHTMLCodes(str(title))

                season = item['season_number']
                # season = '%01d' % season
                season = f"{int(season):01d}"
                if int(season) == 0 and self.specials != 'true':
                    raise Exception()

                episode = item['episode_number']
                # episode = '%01d' % episode
                episode = f"{int(episode):01d}"

                tvshowtitle = i['tvshowtitle']
                premiered = i['premiered']

                unaired = ''
                if not premiered or premiered == '0':
                    pass
                elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    unaired = 'true'
                    if self.showunaired != 'true':
                        raise Exception('hide unaired episode')

                status = i['status']
                duration = i['duration']
                mpaa = i['mpaa']
                studio = i['studio']
                genre = i['genre']
                year = i['year']
                rating = i['rating']
                votes = i['votes']

                thumb = self.tmdb_img_link % (c.tmdb_stillsize, item['still_path']) if item['still_path'] else '0'


                plot = item['overview'] if item['overview'] else i['plot'] or 'The Crew - No plot Available'
                plot = client.replaceHTMLCodes(c.ensure_str(plot, errors='replace'))


                if 'crew' in item:
                    r_crew = item['crew']

                    director = [d for d in r_crew if d['job'] == 'Director']
                    director = ', '.join([d['name'] for d in director])

                    writer = [w for w in r_crew if w['job'] == 'Writer']
                    writer = ', '.join([w['name'] for w in writer])



                castwiththumb = []
                if item['credits'] and 'cast' in item['credits']:

                    r_cast = item['credits']['cast'][:30]
                    for person in r_cast:
                        _icon = person['profile_path']
                        icon = self.tmdb_img_link % (c.tmdb_profilesize, _icon) if _icon else ''
                        castwiththumb.append(
                                    {
                                        'name': person['name'],
                                        'role': person['character'],
                                        'thumbnail': icon
                                    })
                    if not castwiththumb:
                        castwiththumb = '0'

                paused_at = i.get('paused_at', '0')
                watched_at = i.get('watched_at', '0')

                if tvdb != '0':
                    artwork = fanart_tv.get_fanart_tv_art(tvdb=tvdb)
                    poster = artwork.get('poster', '0')
                    fanart = artwork.get('fanart', '0')
                    banner = artwork.get('banner', '0')
                    landscape = artwork.get('landscape', '0')
                    clear_logo = artwork.get('clearlogo', '0')
                    clear_art = artwork.get('clearart', '0')

                    c.log(f"[CM Debug @ 1409 in episodes.py] poster = {poster}, fanart = {fanart}, banner = {banner}, landscape = {landscape}, clearlogo = {clear_logo}, clearart = {clear_art}")

                fanart1 = '0'
                if poster == '0':
                    poster, fanart1 = self.get_tmdb_art(tmdb)

                if fanart == '0':
                    fanart = fanart1

                landscape = fanart if thumb == '0' else thumb

                return{'title': title, 'season': season, 'episode': episode,
                                    'tvshowtitle': tvshowtitle, 'year': year,
                                    'premiered': premiered, 'status': status, 'studio': studio,
                                    'genre': genre, 'duration': duration, 'rating': rating,
                                    'votes': votes, 'mpaa': mpaa, 'director': director,
                                    'writer': writer, 'castwiththumb': castwiththumb, 'plot': plot,
                                    'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, 'poster': poster,
                                    'banner': banner, 'fanart': fanart, 'thumb': thumb,
                                    'clearlogo': clear_logo, 'clearart': clear_art,
                                    'landscape': landscape, 'paused_at': paused_at,
                                    'unaired': unaired, 'watched_at': watched_at, '_last_watched': watched_at}
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 1430 in episodes.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 1430 in episodes.py]Exception raised. Error = {e}')
                pass
            #except Exception as e:
                #c.log(f"[CM Debug @ 1372 in episodes.py] exception: {e}")


        # items = items[:100]
        # return items

        try:
            result = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(items)) as executor:
                #futures = {executor.submit(self.super_info, i): item for item in items}
                futures = {executor.submit(items_list, i): i for i in items}

                c.log(f"[CM Debug @ 1929 in episodes.py] futures = {futures}")

                for future in concurrent.futures.as_completed(futures):
                    i = futures[future]
                    try:
                        result = future.result()
                        self.list.append(result)

                    except Exception as exc:
                        c.log(f"Error processing item {i}: {exc}")
                    c.log(f"[CM Debug @ 1846 in episodes.py] result = {result}")
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1850 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1851 in episodes.py]Exception raised. Error = {e}')
            pass
        c.log(f"[CM Debug @ 1853 in episodes.py] self.list = {self.list}")

        return self.list

    def trakt_user_list(self, url, user):
        try:
            items = trakt.getTraktAsJson(url)
        except Exception:
            pass

        for item in items:
            try:
                try:
                    name = item['list']['name']
                except Exception:
                    name = item['name']
                name = client.replaceHTMLCodes(name)

                try:
                    url = (trakt.slug(item['list']['user']['username']), item['list']['ids']['slug'])
                except Exception:
                    url = ('me', item['ids']['slug'])
                url = self.traktlist_link % url

                self.list.append({'name': name, 'url': url, 'context': url})
            except Exception:
                pass

        self.list = sorted(self.list, key=lambda k: utils.title_key(k['name']))
        return self.list

    def tvmaze_list(self, url, limit):
        try:
            itemlist = []
            items = self.session.get(url, timeout=10).json()
        except Exception:
            return

        for item in items:
            try:
                c.log(f"[CM Debug @ 1783 in episodes.py] \n\ntvmaze item = \n\n{item}\n\n\n")
                if 'english' not in item['show']['language'].lower():
                    raise Exception()


                if (
                    limit is True
                    and 'scripted' not in item['show']['type'].lower()
                ):
                    raise Exception()
                tvshowtitle = item['_links']['show']['name']
                if not tvshowtitle:
                    tvshowtitle = ''
                else:
                    tvshowtitle = client.replaceHTMLCodes(tvshowtitle)

                title = item['name']
                if not title:
                    raise Exception('no title')
                title = client.replaceHTMLCodes(title)

                season = item['season']
                season = re.sub('[^0-9]', '', '%02d' % int(season))
                if not season:
                    raise Exception('no season')

                episode = item['number']
                episode = re.sub('[^0-9]', '', '%02d' % int(episode))
                if episode == '0':
                    raise Exception('episode = 0')

                tvshowtitle = item['show']['name']
                if not tvshowtitle:
                    raise Exception('no tvshowtitle')
                tvshowtitle = client.replaceHTMLCodes(tvshowtitle)

                year = item['show']['premiered']
                year = re.findall(r'(\d{4})', year)[0]

                imdb = item['show']['externals']['imdb']
                if not imdb:
                    imdb = '0'
                else:
                    imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))

                tvdb = item['show']['externals']['thetvdb']
                if not tvdb:
                    raise Exception('no tvdb')
                tvdb = re.sub('[^0-9]', '', str(tvdb))

                poster_medium = item['show']['image']['medium'] if 'medium' in item['show']['image'] else '0'

                poster1 = '0'
                try:
                    poster1 = item['show']['image']['original']
                except Exception:
                    poster1 = '0'
                if not poster1:
                    poster1 = '0'

                try:
                    thumb1 = item['show']['image']['original']
                except Exception:
                    thumb1 = '0'

                try:
                    thumb2 = item['image']['original']
                except Exception:
                    thumb2 = '0'

                if not thumb2:
                    thumb = thumb1
                else:
                    thumb = thumb2
                if not thumb:
                    thumb = '0'

                premiered = item['airdate']
                try:
                    premiered = re.findall(r'(\d{4}-\d{2}-\d{2})', premiered)[0]
                except Exception:
                    premiered = '0'

                try:
                    studio = item['show']['network']['name']
                except Exception:
                    studio = '0'
                if studio is None:
                    studio = '0'

                try:
                    genre = item['show']['genres']
                except Exception:
                    genre = '0'
                genre = [i.title() for i in genre]
                if genre == []:
                    genre = '0'
                genre = ' / '.join(genre)

                try:
                    duration = item['show']['runtime']
                except Exception:
                    duration = '0'
                if duration is None:
                    duration = '0'
                duration = str(duration)

                try:
                    rating = item['show']['rating']['average']
                except Exception:
                    rating = '0'
                if rating is None or rating == '0.0':
                    rating = '0'
                rating = str(rating)
                rating = c.ensure_str(rating)

                votes = '0'

                try:
                    plot = item['show']['summary']
                except Exception:
                    plot = '0'
                if not plot:
                    plot = '0'
                plot = re.sub('<.+?>|</.+?>|\n', '', plot)
                plot = client.replaceHTMLCodes(plot)

                poster2 = fanart = banner = landscape = clearlogo = clearart = '0'

                if not tvdb == '0':
                    tempart =fanart_tv.get_fanart_tv_art(tvdb=tvdb)
                    poster2 = tempart.get('poster', '0')
                    fanart = tempart.get('fanart', '0')
                    banner = tempart.get('banner', '0')
                    landscape = tempart.get('landscape', '0')
                    clearlogo = tempart.get('clearlogo', '0')
                    clearart = tempart.get('clearart', '0')

                #poster = poster2 if not poster2 == '0' else poster1 if not poster1 == '0' else poster_medium
                poster = poster2 if not poster2 == '0' else poster_medium if poster1 == '0' else poster1

                itemlist.append({'title': title, 'season': season, 'episode': episode,
                                'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered,
                                    'status': 'Continuing', 'studio': studio, 'genre': genre,
                                    'duration': duration, 'rating': rating, 'votes': votes,
                                    'plot': plot, 'imdb': imdb, 'tvdb': tvdb, 'tmdb': '0',
                                    'thumb': thumb, 'poster': poster, 'banner': banner,
                                    'fanart': fanart, 'clearlogo': clearlogo, 'clearart': clearart,
                                    'landscape': landscape})
            except Exception:
                pass

        itemlist = itemlist[::-1]

        return itemlist

    def tmdb_list(self, tvshowtitle, year, imdb, tmdb, season, meta=None, lite=False):

        if tmdb == '0' and not imdb == '0':
            try:
                url = self.tmdb_by_imdb % imdb
                result = self.session.get(url, timeout=16).json()
                _id = result['tv_results'][0]
                tmdb = _id['id']

                tmdb = str(tmdb) if tmdb else '0'
            except Exception:
                pass

        if tmdb == '0':
            try:
                url = self.search_link % (quote(tvshowtitle)) + '&first_air_date_year=' + year
                result = self.session.get(url, timeout=16).json()
                results = result['results']
                show = [r for r in results if cleantitle.get(r.get('name')) == cleantitle.get(self.list[i]['title'])][0]
                tmdb = show['id']
                if not tmdb:
                    tmdb = '0'
                else:
                    tmdb = str(tmdb)
            except Exception:
                pass

        try:
            if tmdb == '0':
                raise Exception()

            episodes_url = self.tmdb_season_link % (tmdb, season, self.lang)
            episodes_lite_url = self.tmdb_season_lite_link % (tmdb, season)

            if lite is False:
                url = episodes_url
            else:
                url = episodes_lite_url

            r = self.session.get(url, timeout=10)
            r.raise_for_status()
            r.encoding = 'utf-8'
            result = r.json()

            episode_list = result['episodes']

            if self.specials == 'false':
                episode_list = [e for e in episode_list if not e['season_number'] == 0]
            if not episode_list:
                raise Exception()

            r_cast = result.get('aggregate_credits', {}).get('cast', [])

            poster_path = result.get('poster_path')
            if poster_path:
                poster = self.tmdb_img_link % (c.tmdb_postersize, poster_path)
            else:
                poster = '0'

            fanart = banner = clearlogo = clearart = landscape = duration = status = '0'
            if meta:
                _meta = json.loads(unquote_plus(meta))
                poster = _meta['poster']
                fanart = _meta['fanart']
                banner = _meta['banner']
                clearlogo = _meta['clearlogo']
                clearart = _meta['clearart']
                landscape = _meta['landscape']
                duration = _meta['duration']
                status = _meta['status']

            for item in episode_list:
                try:
                    #c.log(f'[CM DEBUG in episodes.py @ 1550] item={item}')
                    season = str(item['season_number'])
                    episode = str(item['episode_number'])

                    title = item.get('name') or f'Episode {episode}'
                    label = title

                    premiered = item.get('air_date') or '0'

                    unaired = ''
                    if not premiered or premiered == '0':
                        pass
                    elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                        unaired = 'true'
                        if self.showunaired != 'true':
                            raise Exception()

                    still_path = item.get('still_path') if 'still_path' in item else None
                    if still_path:
                        thumb = self.tmdb_img_link % (c.tmdb_stillsize, still_path)
                    else:
                        thumb = landscape or fanart or '0'

                    #c.log(f"[CM Debug @ 1546 in episodes.py] thumb = {thumb}")


                    rating = str(item['vote_average']) or '0'
                    votes = str(item['vote_count']) or '0'
                    episodeplot = item['overview'] or '0'


                    # if not self.lang == 'en' and episodeplot == '0':
                       # try:
                        # en_item = en_result.get('episodes', [])
                        # episodeplot = en_item['overview']
                        # episodeplot = c.ensure_str(episodeplot)
                       # except Exception:
                        # episodeplot = ''
                       # if not episodeplot: episodeplot = '0'

                    try:
                        r_crew = item['crew']

                        director = [d for d in r_crew if d['job'] == 'Director']
                        director = '/'.join([d['name'] for d in director])

                        writer = [w for w in r_crew if w['job'] == 'Writer']
                        writer = '/'.join([w['name'] for w in writer])

                    except Exception:
                        director = writer = ''
                    if not director:
                        director = '0'
                    if not writer:
                        writer = '0'

                    castwiththumb = []
                    try:
                        for person in r_cast[:30]:
                            _icon = person['profile_path']
                            icon = self.tmdb_img_link % (c.tmdb_profilesize, _icon) if _icon else ''
                            castwiththumb.append({
                                'name': person['name'],
                                'role': person['roles'][0]['character'],
                                'thumbnail': icon
                                })
                    except Exception:
                        pass
                    if not castwiththumb:
                        castwiththumb = '0'

                    self.list.append({
                                    'title': title, 'label': label, 'season': season,
                                    'episode': episode, 'tvshowtitle': tvshowtitle,
                                    'year': year, 'premiered': premiered,
                                    'rating': rating, 'votes': votes,
                                    'director': director, 'writer': writer,
                                    'castwiththumb': castwiththumb, 'duration': duration,
                                    'status': status, 'plot': episodeplot,
                                    'imdb': imdb, 'tmdb': tmdb, 'tvdb': '0',
                                    'thumb': thumb, 'poster': poster, 'unaired': unaired,
                                    'fanart': fanart, 'banner': banner, 'clearlogo': clearlogo,
                                    'clearart': clearart, 'landscape': landscape
                                    })
                except Exception:
                    pass

            return self.list
        except Exception:
            return


    def worker(self, level = 0):
        """
        Worker for episodes. This function is used in multiple places in the CM codebase.
        It takes a list of episodes and fetches the metadata for each episode in parallel.
        The function can be used to fetch the metadata for a list of episodes with or without info.
        If level is 0, the function fetches all the metadata for each episode.
        If level is 1, the function only fetches the title, year, season, episode and tvshowtitle.
        The function returns a list of metadata for each episode.
        """
        try:
            total = len(self.list)

            if total == 0:
                control.infoDialog('List returned no relevant results [worker episodes]', icon='INFO', sound=False)
                return

            for i in range(total):
                self.list[i].update({'metacache': False})

            self.list = metacache.fetch(self.list, self.lang, self.user)

            try:
                result = []
                #cm - changed worker 21-04-2025
                #cm - changed worker 27-04-2025 - added max threads/fixed steps
                with concurrent.futures.ThreadPoolExecutor(max_workers=c.get_max_threads(total, 50)) as executor:
                    if level == 1:
                        futures = {executor.submit(self.no_info, i): i for i in range(total)}
                    else:
                        futures = {executor.submit(self.super_info, i): i for i in range(total)}

                    #c.log(f"[CM Debug @ 1287 in episodes.py] futures = {futures}")

                    for future in concurrent.futures.as_completed(futures):
                        i = futures[future]
                        try:
                            result.append(future.result())
                            #if(len(result) == total):
                                #c.log(f"[CM Debug @ 1291 in episodes.py] completed all {len(result)} futures in worker for super_info")
                        except Exception as e:
                            c.log(f"[CM Debug @ 1296 in episodes.py] Exception raised. Error = {e}")

                if self.meta:
                    metacache.insert(self.meta)

            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 1303 in episodes.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 1304 in episodes.py]Exception raised. Error = {e}')
                pass
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1309 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1310 in episodes.py]Exception raised. Error = {e}')
            pass

    def no_info(self, item):
        try:
            return item
        except:
            pass

    def super_info(self, i):
        """
        Filling missing pieces
        """

        try:
            item = self.list[i]

            if 'showimdb' in item:
                is_episode = True
            else:
                is_episode = False

            if is_episode:
                show_imdb = item['showimdb']
                show_tmdb = item['showtmdb']
                show_tvdb = item['showtvdb']
                show_trakt = item['showtrakt']

                show_title = item['tvshowtitle']
                title = item['title']
                season = item['season']
                episode = item['episode']
                year = item['year']

                season = f'{int(season):01d}' if int(season) > 0 else season
                episode = f'{int(episode):01d}' if int(episode) > 0 else episode

                label = f'{show_title} : (S{season:02d}E{episode:02d})'


            else:
                show_imdb = item['imdb']
                show_tmdb = item['tmdb']
                show_tvdb = item['tvdb']
                show_trakt = item['trakt'] if 'trakt' in item else '0'

                show_title = item['tvshowtitle']
                c.log(f"[CM Debug @ 1338 in episodes.py] tvshowtitle = {show_title}")
                title = item['title'] if 'title' in item else ''
                season = item['season']
                episode = item['episode']
                year = item['year']

                label = f'{show_title}'

            resume_point = item['resume_point'] if 'resume_point' in item else '0.0'

            if show_tmdb == '0' and show_imdb != '0':
                # get external id's from tmdb (by series ID)
                url = self.tmdb_by_imdb % show_imdb
                result = self.session.get(url, timeout=15).json()
                show_tmdb = result['tv_results'][0]['id']

            if show_imdb == '0' and show_tmdb != '0':
                # get external id's from tmdb (by series ID)
                url = self.tmdb_external_ids_by_tmdb % show_tmdb
                result = self.session.get(url, timeout=15).json()
                show_imdb = result['imdb_id']

            if show_tvdb == '0' and show_tmdb != '0':
                # get external id's from tmdb (by series ID)
                url = self.tmdb_external_ids_by_tmdb % show_tmdb
                result = self.session.get(url, timeout=15).json()
                show_tvdb = result['tvdb_id']

            _id = show_tmdb if show_tmdb != '0' else show_imdb
            if _id in ['0', None]:
                raise Exception()

            en_url = self.tmdb_api_link % _id
            trans_url = en_url + ',translations'
            url = en_url if self.lang == 'en' else trans_url
            show_item = self.session.get(url, timeout=15).json()
            c.log(f"[CM Debug @ 1359 in episodes.py] videos = {show_item['videos']['results']}")



            episode_url = self.tmdb_episode_link % (show_tmdb, season, episode)
            episode_item = self.session.get(episode_url, timeout=15).json()
            #c.log(f"[CM Debug @ 1376 in episodes.py] episode_item = {episode_item}")


            if not episode_item:
                raise Exception('No episode result')

            if not title:
                title = episode_item['name']


            duration = episode_item['runtime'] or '45'
            status = show_item['status'] or '0'
            if status == '0':
                status = show_item['in_production'] if 'in_production' in show_item else '0'
                if status == '0':
                    status = 'Ended'

            premiered = episode_item['air_date']
            premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(premiered)[0]

            thumb = landscape = '0'

            if 'still_path' in episode_item:
                landscape = episode_item['still_path']
                landscape = self.tmdb_img_link % ('original', landscape)
                thumb = landscape

            genre = ' / '.join([d['name'] for d in show_item.get('genres', [])]) if show_item.get('genres') else '0'
            mpaa = show_item.get('mpaa', 'Not Rated')
            rating = show_item.get('vote_average', '0')
            votes = show_item.get('vote_count', '0')
            studio = next((c['name'] for c in show_item.get('production_companies', []) if c), '') or '0'
            country = ' / '.join([c['name'] for c in show_item.get('production_countries', [])]) if show_item.get('production_countries') else '0'
            tagline = show_item.get('tagline', '0')

            trailer = ''

            if 'trailer' in item:
                trailer = item['trailer']
            elif 'videos' in episode_item and episode_item['videos'] and 'results' in episode_item['videos'] and episode_item['videos']['results']:
                trailer = episode_item.get('videos').get('results')[0].get('key', '0')
            if 'videos' in show_item and show_item['videos'] and 'results' in show_item['videos'] and show_item['videos']['results']:
                trailer = show_item.get('videos', {}).get('results', [{}])[0].get('key', '0')



            in_widget = False
            if c.is_widget_listing():
                in_widget = True

            plot = episode_item['overview'] if episode_item.get('overview') else show_item.get('overview', '0')
            plot = client.replaceHTMLCodes(plot) if plot else '0'

            crew = episode_item.get('credits', {}).get('crew', []) if 'credits' in episode_item else show_item['crew'] if 'crew' in show_item else []

            if crew:
                crew = [c for c in crew if c['job'] in ['Director', 'Writer']]
            else:
                crew = []

            director = writer = '0'

            if crew:
                director = [d for d in crew if d['job'] == 'Director']

                director = '/'.join([d['name'] for d in director])

                writer = [w for w in crew if w['job'] == 'Writer']
                writer = '/'.join([w['name'] for w in writer])

            castwiththumb = []
            try:
                credits = episode_item.get('credits', {})
                cast = credits.get('cast', [])[:30]
                guests = credits.get('guest_stars', [])[:30]
                cast.extend(guests)
                for person in cast:
                    profile_path = person.get('profile_path', '')
                    icon = self.tmdb_img_link % (c.tmdb_profilesize, profile_path) if profile_path else ''
                    castwiththumb.append({
                        'name': person.get('name', ''),
                        'role': person.get('character', ''),
                        'thumbnail': icon
                    })
            except Exception as e:
                c.log(f"[CM Debug @ 1453 in episodes.py] Exception in cast in super_info: {e}")
                castwiththumb = []

            unaired = ''
            if int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                unaired = 'true'
                if self.showunaired != 'true':
                    raise Exception()

            poster = fanart = banner = landscape = clearlogo = clearart = '0'

            if show_tvdb and show_tvdb != '0':
                tempart = fanart_tv.get_fanart_tv_art(tvdb=show_tvdb)
                poster = tempart.get('poster', '0')
                fanart = tempart.get('fanart', '0')
                banner = tempart.get('banner', '0')
                landscape = tempart.get('landscape', '0')
                clearlogo = tempart.get('clearlogo', '0')
                clearart = tempart.get('clearart', '0')

            if poster == '0':
                poster, fanart = self.get_tmdb_art(show_tmdb)

            if poster == '0':
                poster = c.addon_poster()

            action = item.get('action', None)
            # label = item['label', 'No Label']
            resume_point = item.get('_resume_point', None)
            show_trakt = item.get('trakt', None)

            item = {
                'title': title, 'originaltitle': title, 'year': year, 'imdb': show_imdb,
                'tvdb': show_tvdb, 'tmdb': show_tmdb, 'status': status, 'studio': studio,
                'poster': poster, 'banner': banner, 'fanart': fanart, 'fanart2': fanart,
                'landscape': landscape, 'discart': clearart, 'clearlogo': clearlogo,
                'clearart': clearart, 'premiered': premiered, 'genre': genre, 'thumb': thumb,
                'in_widget': in_widget, 'duration': duration, 'rating': rating, 'votes': votes,
                'mpaa': mpaa, 'director': director, 'writer': writer, 'castwiththumb': castwiththumb,
                'plot': plot, 'tagline': tagline, 'country': country, 'trailer': '',
                'label': label, 'resume_point': resume_point, 'trakt': show_trakt,
                '_last_watched': item['_last_watched'], 'tvshowtitle': show_title, 'season': season,
                'episode': episode, 'action': action, 'unaired': unaired, 'trailer:': trailer,
                '_sort_key': max(item['_last_watched'], premiered)
            }

            self.list[i].update(item)
            #c.log(f"[CM Debug @ 1482 in episodes.py] list[i] = {self.list[i]}")

            meta = {
                'imdb': show_imdb, 'tmdb': show_tmdb, 'tvdb': '0', 'lang': self.lang,
                'user': self.user, 'resume_point': resume_point, 'item': item
            }
            self.meta.append(meta)
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1477 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1477 in episodes.py]Exception raised. Error = {e}')
            pass
        #except Exception as e:
            #c.log(f"[CM Debug @ 1479 in episodes.py] Exception raised. Error = {e}")










    def episodeDirectory(self, items):
        if not items:
            c.infoDialog(heading = control.lang(32326), message = '**' + control.lang(32088))
            return

        sys_addon = sys.argv[0]
        sys_handle = int(sys.argv[1])

        addon_poster, addon_banner = c.addon_poster(), c.addon_banner()
        addon_fanart, use_fanart = c.addon_fanart(), control.setting('fanart') == 'true'
        addon_clearlogo, addon_clearart = c.addon_clearlogo(), c.addon_clearart()
        addon_discart, addon_thumb = c.addon_discart(), c.addon_thumb()
        trakt_credentials = trakt.getTraktCredentialsInfo()
        indicators = playcount.get_tvshow_indicators(refresh=True)

        try:
            multi = [i['tvshowtitle'] for i in items]
            #c.log(f"[CM Debug @ 2027 in episodes.py] multi = {multi}")
        except Exception:
            multi = []
        multi = len([x for y, x in enumerate(multi) if x not in multi[:y]]) >= 1

        #c.log(f"[CM Debug @ 2032 in episodes.py] multi = {multi}")

        try:
            sys_action = items[0]['action']
        except Exception:
            sys_action = ''

        is_folder = sys_action == 'episodes'

        color_list = [32589, 32590, 32591, 32592, 32593, 32594, 32595, 32596, 32597, 32598]
        color_number = color_list[int(control.setting('unaired.identify'))]
        unaired_color = control.lang(color_number)
        unaired_color = re.sub(r"\][\w\s]*\[", "][I]%s[/I][", unaired_color)

        for item in items:
            try:
                meta = {k: v for k, v in item.items() if v != '0'}

                label = item['label'] if 'label' in item else item['title']

                if 'unaired' in item and item['unaired'] == 'true':
                    label = unaired_color % label

                imdb_id = item['imdb']
                tmdb_id = item['tmdb']
                year = item['year']
                season = item['season']
                episode = item['episode']

                poster = item.get('poster', addon_poster)
                fanart = item.get('fanart') if item.get('fanart') != '0' else addon_fanart
                banner = item.get('banner', addon_banner)
                landscape = item.get('landscape', fanart)
                clearlogo = item.get('clearlogo', addon_clearlogo)
                clearart = item.get('clearart', addon_clearart)
                discart = item.get('discart', addon_discart)
                thumb = item.get('thumb', addon_thumb)
                plot = item.get('plot', c.lang(32089))

                duration = item.get('duration', 45)
                duration = str(int(duration) * 60)

                status = item.get('status', '0')

                # !cm -warning: resume_point = percentage, float!
                if 'resume_point' in item and item['resume_point'] not in [None, '0', 0, '0.0', 0.0]:
                    c.log(f"[CM Debug @ 2496 in episodes.py] resume_point = {item['resume_point']} of type = {type(item['resume_point'])}")
                else:
                    item['resume_point'] = '0.0'
                    c.log(f"[CM Debug @ 2496 in episodes.py] newly created resume_point = {item['resume_point']} of type = {type(item['resume_point'])}")

                res_point = meta['resume_point'] if 'resume_point' in meta else 0

                c.log(f"[CM Debug @ 2497 in episodes.py] res_point = {res_point} of type = {type(res_point)}")
                resume_point = float(res_point)
                offset = 0.0

                if not resume_point:
                    resume_point= float(bookmarks.get('episode', imdb=imdb_id, tmdb=tmdb_id, season=season, episode=episode, local=True))

                if 'duration' in meta and meta['duration'] != '0':
                    offset = float(int(meta['duration']) * (resume_point / 100)) #= float(int(7200) * (4.39013/100)) = 315.0 with playing time = 7200 secs om 4.3 % of the movie
                elif 'duration' in item and item['duration'] != '0':
                    offset = float(int(item['duration']) * (resume_point / 100)) #= float(int(7200) * (4.39013/100)) = 315.0 with playing time = 7200 secs om 4.3 % of the movie
                else:
                    offset = 0.0
                    meta['duration'] = duration

                if resume_point:
                    #resume_point = percentage_played so remaining = 100 - percentage_played
                    #percentage_played = resume_point
                    remaining = float(100 - resume_point) #percentage
                    remaining_minutes = float(remaining/100 * float(meta['duration']))
                    label += f' [COLOR gold]({int(remaining_minutes)} min. remaining)[/COLOR] '

                trailer_meta = {
                    'imdb': imdb_id,
                    'tmdb': tmdb_id,
                    'season': season,
                    'episode': episode,
                    'trailer': item.get('trailer', '0'),
                    'poster': poster,
                    'fanart': fanart,
                    'mediatype': 'episode'
                }

                trailer_meta = quote_plus(json.dumps(trailer_meta))

                meta.update({
                    'poster': poster,
                    'fanart': fanart,
                    'banner': banner,
                    'clearlogo': clearlogo,
                    'clearart': clearart,
                    'discart': discart,
                    'landscape': landscape,
                    'duration': duration,
                    'status': status
                })

                seasons_meta = quote_plus(json.dumps(meta))

                title = quote_plus(item['title'])
                tvshowtitle = quote_plus(item['tvshowtitle']) if 'tvshowtitle' in item else title
                premiered = quote_plus(item['premiered'])
                # c.log(f"\n\n\n[CM Debug @ 2662 in episodes.py] premiered = {premiered} \n\n\n")
                trailer = quote_plus(item.get('trailer', '0'))
                year = item.get('year', '0')
                if year == '0' and 'premiered' in item:
                    year = re.findall(r'(\d{4})', item['premiered'])[0]



                meta['offset'] = offset
                meta['resume_point'] = resume_point
                meta['dev'] = 'Classy'
                meta['mediatype'] = 'episode'
                meta['code'] = tmdb_id
                meta['imdb_id'] = imdb_id
                meta['tmdb_id'] = tmdb_id
                meta['tvdb_id'] = item.get('tvdb', '')
                meta['genre'] = cleangenre.lang(item.get('genre', ''), self.lang)
                meta['year'] = year
                meta['title'] = item['title']
                meta['tvshowyear'] = item['year']

                if trailer == '0':
                    meta['trailer'] = f'{sys_addon}?action=trailer&name={tvshowtitle}&imdb={imdb_id}&tmdb={tmdb_id}&season={season}&episode={episode}&mediatype=episode&meta={trailer_meta}'
                else:
                    meta['trailer'] = f'{sys_addon}?action=trailer&name={tvshowtitle}&url={trailer}&imdb={imdb_id}&tmdb={tmdb_id}&mediatype=episode&meta={trailer_meta}'


                sys_meta = quote_plus(json.dumps(meta))

                url = f'{sys_addon}?action=play&title={title}&year={year}&imdb={imdb_id}&tmdb={tmdb_id}&season={season}&episode={episode}&tvshowtitle={tvshowtitle}&premiered={premiered}&meta={sys_meta}&t={self.systime}'
                sys_url = quote_plus(url)

                if is_folder:
                    url = f'{sys_addon}?action=episodes&tvshowtitle={tvshowtitle}&year={year}&imdb={imdb_id}&tmdb={tmdb_id}&meta={seasons_meta}&season={season}&episode={episode}'

                cm = [(control.lang(32065), f'RunPlugin({sys_addon}?action=queueItem)')]

                if multi: # Browse series
                    if c.is_widget_listing():
                        #cm.append((control.lang(32071), f'RunPlugin({sys_addon}?action=seasons&tvshowtitle={tvshowtitle}&year={year}&imdb={imdb_id}&tmdb={tmdb_id}&meta={seasons_meta},return)'))
                        cm.append((control.lang(32071), f'{sys_addon}?action=seasons&tvshowtitle={tvshowtitle}&year={year}&imdb={imdb_id}&tmdb={tmdb_id}&meta={seasons_meta},return'))
                    else:
                        cm.append((control.lang(32071), f'Container.Update({sys_addon}?action=seasons&tvshowtitle={tvshowtitle}&year={year}&imdb={imdb_id}&tmdb={tmdb_id}&meta={seasons_meta},return)'))

                try:
                    overlay = int(playcount.get_episode_overlay(indicators, imdb_id, tmdb_id, season, episode))
                    if overlay == 7:
                        cm.append((control.lang(32069), f'RunPlugin({sys_addon}?action=episodePlaycount&imdb={imdb_id}&tmdb={tmdb_id}&season={season}&episode={episode}&query=6)'))
                        meta.update({'playcount': 1, 'overlay': 7})
                    else:
                        cm.append((control.lang(32068), f'RunPlugin({sys_addon}?action=episodePlaycount&imdb={imdb_id}&tmdb={tmdb_id}&season={season}&episode={episode}&query=7)'))
                        meta.update({'playcount': 0, 'overlay': 6})
                except Exception:
                    pass

                if trakt_credentials:
                    cm.append((control.lang(32515), f'RunPlugin({sys_addon}?action=traktManager&name={tvshowtitle}&tmdb={tmdb_id}&content=tvshow)'))

                if not is_folder:
                    cm.append((control.lang(32063), f'RunPlugin({sys_addon}?action=alterSources&url={sys_url}&meta={sys_meta})'))
                cm.append((control.lang(32551), f'RunPlugin({sys_addon}?action=tvshowToLibrary&tvshowtitle={tvshowtitle}&year={year}&imdb={imdb_id}&tmdb={tmdb_id})'))
                cm.append((control.lang(32098), f'RunPlugin({sys_addon}?action=clearSources)'))



                art = {
                    'icon': thumb,
                    'thumb': thumb,
                    'banner': banner,
                    'poster': thumb,
                    'fanart': fanart,
                    'tvshow.poster': poster,
                    'season.poster': poster,
                    'landscape': landscape,
                    'clearlogo': clearlogo,
                    'clearart': clearart,
                    'discart': discart
                }

                castwiththumb = item.get('castwiththumb')
                if castwiththumb and castwiththumb != '0':
                    meta['cast'] = castwiththumb

                liz = control.item(label=label, offscreen=True)
                liz.setArt(art)


                if is_folder:
                    liz.setProperty('IsPlayable', 'true')

                meta['studio'] = c.string_split_to_list(meta['studio']) if 'studio' in meta else []
                meta['genre'] = c.string_split_to_list(meta['genre']) if 'genre' in meta else []
                meta['director'] = c.string_split_to_list(meta['director']) if 'director' in meta else []
                meta['writer'] = c.string_split_to_list(meta['writer']) if 'writer' in meta else []

                meta.update({'offset': offset})
                meta.update({'resume_point': resume_point})


                # Pass listitem to the infotagger module and specify tag type
                info_tag = ListItemInfoTag(liz, 'video')
                infolabels = control.tagdataClean(meta)

                info_tag.set_info(infolabels)
                unique_ids = {'imdb': imdb_id, 'tmdb': str(tmdb_id)}
                info_tag.set_unique_ids(unique_ids)
                info_tag.set_cast(meta.get('cast', []))

                if(offset > 0):
                    info_tag.set_resume_point(meta, 'offset', 'duration', False)

                #stream_info =
                info_tag.add_stream_info('video', {'codec': 'h264'})  # (stream_details)
                liz.addContextMenuItems(cm)

                control.addItem(handle=sys_handle, url=url, listitem=liz, isFolder=is_folder)
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 2308 in episodes.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 2308 in episodes.py]Exception raised. Error = {e}')
                pass

        control.content(sys_handle, 'episodes')
        control.directory(sys_handle, cacheToDisc=True)

    def addDirectory(self, items, queue=False):
        if items is None or len(items) == 0:
            control.idle()
            sys.exit()

        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])
        addon_fanart, addon_thumb, art_path = c.addon_fanart(), c.addon_thumb(), c.get_art_path()
        queueMenu = control.lang(32065)

        for i in items:
            try:
                #c.log(f'[CM DEBUG in episodes.py @ 1982] type i={type(i)}')
                name = i['name']

                if i['image'].startswith('http'):
                    thumb = i['image']
                elif art_path is not None:
                    thumb = os.path.join(art_path, i['image'])
                else:
                    thumb = addon_thumb
                #c.log(f"[CM Debug @ 1992 in episodes.py] thumb={thumb}")

                url = f"{sysaddon}?action={i['action']}"
                try:
                    url += f"&url={quote_plus(i['url'])}"
                except Exception:
                    pass

                cm = []

                if queue is True:
                    cm.append((queueMenu, f'RunPlugin({sysaddon}?action=queueItem)'))

                try:
                    item = control.item(label=name, offscreen=True)
                except Exception:
                    item = control.item(label=name)

                item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': addon_fanart})

                item.addContextMenuItems(cm)

                control.addItem(handle=syshandle, url=url,listitem=item, isFolder=True)
            except Exception:
                pass

        control.content(syshandle, 'addons')
        control.directory(syshandle, cacheToDisc=True)
