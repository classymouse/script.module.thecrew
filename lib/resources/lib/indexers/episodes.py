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
import requests

#import xbmc
#import zipfile
#import base64


# cm - we need to remove the six lib
#import six

from urllib.parse import quote, quote_plus, unquote_plus, parse_qsl, urlsplit, urlencode, urlparse

from ..modules import trakt
from ..modules import keys
from ..modules import bookmarks
from ..modules import cleantitle
from ..modules import cleangenre
from ..modules import control
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
        self.tmdb_img_link = 'https://image.tmdb.org/t/p/{}{}'

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

    def get(self, tvshowtitle, year, imdb, tmdb, meta=None, season=None, episode=None, idx=True, create_directory=True):
        try:
            if idx is True:
                self.list = cache.get(self.tmdb_list, 24, tvshowtitle, year, imdb, tmdb, meta)
                #self.list = self.tmdb_list(tvshowtitle, year, imdb, tmdb, meta)
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
        #try:
            #if tmdb_id is None:
            #    tmdb_id = '0'

            #if tmdb_id == '0' and not imdb_id == '0':
            #    try:
            #        result = self.session.get(self.tmdb_by_imdb % imdb_id, timeout=15).json()
            #        tmdb_id = str(result.get('tv_results', [])[0].get('id', '0'))
            #    except Exception:
            #        pass


            #if imdb_id == '0' or tmdb_id == '0':
            #    try:
            #        ids_from_trakt = trakt.SearchTVShow(tvshowtitle, year, full=False)[0].get('show', {})
            #        if imdb_id == '0':
            #            imdb_id = ids_from_trakt.get('ids', {}).get('imdb', '0')
            #            if imdb_id != '0':
            #                imdb_id = 'tt' + re.sub('[^0-9]', '', str(imdb_id))
            #        if tmdb_id == '0':
            #            tmdb_id = ids_from_trakt.get('ids', {}).get('tmdb', '0')
            #            if tmdb_id != '0':
            #                tmdb_id = str(tmdb_id)
            #    except Exception:
            #        pass

        #except Exception as e:
        #    c.log(f"Exception raised in tmdb_list part 1: {e}")
        #    return

        try:
            if tmdb_id == '0':
                raise Exception()

            if self.lang == 'en':
                item = self.session.get(self.tmdb_show_link % (tmdb_id, 'en'), timeout=16).json()
            elif lite is True:
                item = self.session.get(self.tmdb_show_lite_link % tmdb_id, timeout=16).json()
            else:
                item = self.session.get(self.tmdb_show_link % (tmdb_id, self.lang) + ',translations', timeout=16).json()

            tvdb_id = item.get('external_ids', {}).get('tvdb', '0')


            if item is None:
                raise Exception()

            seasons_list = item.get('seasons', [])

            if self.specials == 'false':
                seasons_list = [s for s in seasons_list if not s['season_number'] == 0]

            studio = item.get('networks', [])[0].get('name', '0')

            genres = item.get('genres', [])
            genre = ' / '.join([d['name'] for d in genres]) if genres else '0'

            duration = item.get('episode_run_time', [])[0] or '45'
            duration = str(duration)

            c_ratings = item.get('content_ratings', {}).get('results', [])
            mpaa = [d['rating'] for d in c_ratings if d['iso_3166_1'] == 'US'][0] if c_ratings else '0'

            status = item.get('status', '0')

            cast = []
            try:
                credits_list = item.get('aggregate_credits', {}).get('cast', [])[:30]
                for person in credits_list:
                    icon = self.tmdb_img_link.format(
                        c.tmdb_profilesize, person['profile_path']
                        ) if person['profile_path'] else ''
                    cast.append({
                        'name': person['name'],
                        'role': person['roles'][0]['character'],
                        'thumbnail': icon
                    })
            except Exception:
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
                _meta = json.loads(unquote_plus(meta))
                show_poster = _meta['poster'],
                fanart = _meta['fanart'],
                banner = _meta['banner'],
                clearlogo = _meta['clearlogo'],
                clearart = _meta['clearart'],
                landscape = _meta['landscape']
            else:
                poster_path = item.get('poster_path', '')
                if poster_path:
                    show_poster = self.tmdb_img_link.format(c.tmdb_postersize, poster_path)
                else:
                    show_poster = '0'

                fanart_path = item.get('backdrop_path', '')
                if fanart_path:
                    fanart = self.tmdb_img_link.format(c.tmdb_fanartsize, fanart_path)
                else:
                    fanart = '0'

                tv_fanart = fanart_tv.get_fanart_tv_art(tvdb=tvdb_id)
                if tv_fanart:
                    banner = tv_fanart.get('banner', '0')
                    clearlogo = tv_fanart.get('clearlogo', '0')
                    clearart = tv_fanart.get('clearart', '0')
                    landscape = tv_fanart.get('landscape', '0')



        except Exception as e:
            c.log(f"Exception raised in tmdb_list part 2: {e}")


        for item in seasons_list:
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

                plot = c.lang(32623) if 'overview' not in item or not item['overview'] else item['overview']
                plot = client.replaceHTMLCodes(c.ensure_str(plot, errors='replace'))

                poster_path = item.get('poster_path', '')
                if poster_path:
                    poster = self.tmdb_img_link.format(c.tmdb_postersize, poster_path)
                else:
                    poster = show_poster

                self.list.append({'season': season, 'tvshowtitle': tvshowtitle,
                                    'year': year, 'premiered': premiered, 'status': status,
                                    'studio': studio, 'genre': genre, 'duration': duration,
                                    'mpaa': mpaa, 'castwiththumb': cast,
                                    'plot': plot, 'imdb': imdb_id, 'tmdb': tmdb_id,
                                    'tvdb': '0', 'poster': poster, 'fanart': fanart,
                                    'banner': banner, 'clearlogo': clearlogo,
                                    'clearart': clearart, 'landscape': landscape,
                                    'unaired': unaired})
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 282 in episodes.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 282 in episodes.py]Exception raised. Error = {e}')
                pass

        return self.list



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
                    icon = self.tmdb_img_link.format(c.tmdb_profilesize, _icon) if _icon else ''
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
                    show_poster = self.tmdb_img_link.format(c.tmdb_postersize, poster_path)
                else:
                    show_poster = '0'

                fanart_path = item['backdrop_path'] if 'backdrop_path' in item else ''

                if fanart_path:
                    fanart = self.tmdb_img_link.format(c.tmdb_fanartsize, fanart_path)
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
                    poster = self.tmdb_img_link.format(c.tmdb_postersize, poster_path)
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


    def seasonDirectory(self, items):
        if items is None or len(items) == 0:
            control.idle()
            # sys.exit()

        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])

        #c.log(f"[CM Debug @ 311 in episodes.py] items = {items}")

        traktCredentials = trakt.getTraktCredentialsInfo()

        try:
            indicators = playcount.getSeasonIndicators(items[0]['imdb'])
        except Exception:
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

        c.log(f"[CM Debug @ 347 in episodes.py] items = {items[0]}")

        for i in items:
            try:
                c.log(f"[CM Debug @ 342 in episodes.py] poster = i['poster'] = {i['poster']} and background = i['fanart'] = {i['fanart']}")


                label = (f"{labelMenu} {i['season']}")

                try:
                    if i['unaired'] == 'true':
                        label = unairedcolor % label
                except Exception:
                    pass

                systitle = sysname = quote_plus(i['tvshowtitle'])

                poster = str(i['poster']) if 'poster' in i and not i['poster'] == '0' else c.addon_poster()
                fanart = str(i['fanart']) if 'fanart' in i and not i['fanart'] == '0' else c.addon_fanart()
                c.log(f"[CM Debug @ 359 in episodes.py] i want to know the type of fanart. It is = {type(fanart)}")
                fanart_converted = c.string_to_tuple(fanart)
                c.log(f"[CM Debug @ 359 in episodes.py] fanart_converted = {fanart_converted}")

                c.log(f"[CM Debug @ 359 in episodes.py] fanart = {fanart[0]}")
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
                    'thumb': poster,
                    'banner': c.addon_banner(),
                    'poster': poster,
                    'tvshow.poster': poster,
                    'season.poster': poster,
                    'landscape': landscape,
                    'clearlogo': c.addon_clearlogo(),
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

                #c.log(f"[CM Debug @ 1924 in episodes.py] infolabels={infolabels}")

                #c.log(f'[CM DEBUG in episodes.py @ 533] imdb = {imdb}, season = {season}')
                #c.log(f"[CM DEBUG in episodes.py @ 534] infolabels={infolabels}")

                info_tag.set_info(infolabels)
                unique_ids = {'imdb': imdb, 'tmdb': str(tmdb)}
                info_tag.set_unique_ids(unique_ids)
                info_tag.set_cast(meta.get('cast', []))

                stream_info = {'codec': 'h264'}
                info_tag.add_stream_info('video', stream_info)  # (stream_details)
                item.addContextMenuItems(cm)

                url = f'{sysaddon}?action=episodes&tvshowtitle={systitle}&year={year}&imdb={imdb}&tmdb={tmdb}&meta={sysmeta}&season={season}'


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

        control.content(syshandle, 'seasons')
        control.directory(syshandle, cacheToDisc=True)
        views.set_view('seasons', {'skin.estuary': 55, 'skin.confluence': 500})


class episodes:
    def __init__(self):
        self.list = []
        self.blist = []

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


        self.tmdb_img_link = 'https://image.tmdb.org/t/p/{}{}'
        self.tmdb_link = 'https://api.themoviedb.org/3/'

        self.tmdb_show_link = f'{self.tmdb_link}tv/%s?api_key={self.tmdb_user}'
        self.tmdb_season_link = f'{self.tmdb_link}tv/%s/season/%s?api_key={self.tmdb_user}&language=%s&append_to_response=aggregate_credits'
        self.tmdb_season_lite_link = f'{self.tmdb_link}tv/%s/season/%s?api_key={self.tmdb_user}&language={self.lang}'
        self.tmdb_episode_link = f'{self.tmdb_link}tv/%s/season/%s/episode/%s?api_key={self.tmdb_user}&language={self.lang}&append_to_response=credits,images'
        self.tmdb_by_imdb = f'{self.tmdb_link}find/%s?api_key={self.tmdb_user}&external_source=imdb_id'
        self.search_link = f'{self.tmdb_link}search/tv?api_key={self.tmdb_user}&language=en-US&query=%s&page=1'

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
                    c.log(f"[CM Debug @ 808 in episodes.py] title = {tvshowtitle}, year = {year}, imdb_id = {imdb_id}, tmdb_id = {tmdb_id}, season = {season}, episode = {episode}")
                    #idx = [x for x, y in enumerate(self.list) if y['season'] == str(season) and y['episode'] == str(episode)][-1]
                    idx = [x for x, y in enumerate(self.list) if y['season'] == str(season) and y['episode'] == str(episode)][-1]
                    c.log(f"[CM Debug @ 796 in episodes.py] idx = {idx}")
                    self.list = [y for x, y in enumerate(self.list) if x >= idx]

                if create_directory:
                    self.episodeDirectory(self.list)
            else:
                self.list = self.tmdb_list(tvshowtitle, year, imdb_id, tmdb_id, season, lite=True)

            return self.list
        except Exception:
            raise


    def calendar(self, url):
        try:
            c.log(f"[CM Debug @ 811 in episodes.py] url = {url}")

            elements = ['tvProgress', 'tvmaze']
            for i in elements:
                if i in url:
                    c.log(f"[CM Debug @ 816 in episodes.py] {i} in url {url}")
                    break

            #if  any(elem in url for elem in elements):
                #pass
            else:
                url = getattr(self, url + '_link')
                c.log(f"[CM Debug @ 816 in episodes.py] url = {url}")

                ####cm#
                # Making it possible to use date[xx] in url's where xx is a str(int)
                for i in re.findall(r'date\[(\d+)\]', url):
                    url = url.replace(
                        f'date[{i}]',
                        (self.datetime - datetime.timedelta(days=int(i))).strftime('%Y-%m-%d')
                        )


            if url == 'tvProgress':
                c.log(f"[CM Debug @ 823 in episodes.py] url = {url}")
                self.list = cache.get(self.trakt_tvprogress, 0)


            if url == self.progress_link:
                self.blist = cache.get(self.trakt_progress_list, 720, url)
                self.list = []
                self.list = cache.get(self.trakt_progress_list, 0, url)

            elif url == self.onDeck_link:
                self.blist = cache.get(self.trakt_episodes_list, 720, url, self.trakt_user, self.lang)
                self.list = []
                self.list = cache.get(self.trakt_episodes_list, 1, url, self.trakt_user, self.lang)
                #self.list = self.list[::-1]
                self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)

            elif url == self.mycalendar_link:
                #self.blist = cache.get(self.trakt_episodes_list, 720, url, self.trakt_user, self.lang)
                self.blist = self.trakt_episodes_list(url, self.trakt_user, self.lang)
                self.list = []
                #self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)
                self.list = self.trakt_episodes_list(url, self.trakt_user, self.lang)
                self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)

            elif url == self.added_link:
                #self.blist = cache.get(self.trakt_episodes_list, 720, url, self.trakt_user, self.lang)
                self.blist = self.trakt_episodes_list(url, self.trakt_user, self.lang)
                self.list = []
                #self.list = cache.get( self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)
                self.list = self.trakt_episodes_list(url, self.trakt_user, self.lang)
                self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)

            elif url == self.trakthistory_link:
                self.list = cache.get(self.trakt_episodes_list, 1, url, self.trakt_user, self.lang)
                self.list = sorted(self.list, key=lambda k: int( k['watched_at']), reverse=True)

            elif self.trakt_link in url and '/users/' in url:
                #self.list = cache.get(self.trakt_list, 0, url, self.trakt_user)
                self.list = self.trakt_list(url, self.trakt_user)
                self.list = self.list[::-1]

            elif self.trakt_link in url:
                self.list = cache.get(self.trakt_list, 1, url, self.trakt_user)

            elif self.tvmaze_link in url and url == self.added_link:
                urls = [i['url'] for i in self.calendars(idx=False)][:5]
                self.list = []
                for url in urls:
                    self.list += self.tvmaze_list(url, True)

            elif self.tvmaze_link in url:
                self.list = cache.get(self.tvmaze_list, 1, url, False)

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
        #for i in range(len(self.list)):
            #self.list[i].update({'image': 'userlists.png', 'action': 'calendar'})

        for item in self.list:
            item.update({'image': 'userlists.png', 'action': 'calendar'})
        self.addDirectory(self.list, queue=True)
        return self.list

    def trakt_list(self, url, user, return_art=True):
        try:
            c.log(f"[CM Debug @ 810 in episodes.py] url = {url}")
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
            return

        for item in items:
            try:
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
                                'paused_at': paused_at, 'watched_at': watched_at
                                })
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 933 in episodes.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 933 in episodes.py]Exception raised. Error = {e}')
                pass

        itemlist = itemlist[::-1]
        return itemlist


    def trakt_tvprogress(self):
        try:
            progress = trakt.get_trakt_progress('episode')

            c.log(f"[CM Debug @ 923 in episodes.py] progress = {progress}")

            for item in progress:
                c.log(f"[CM Debug @ 894 in episode.py] item = {item}")

                tmdb = str(item['tmdb'])
                tvdb = str(item['tvdb'])
                imdb = item['imdb']
                trakt_id = str(item['trakt'])
                title = item['title']
                season = item['season']
                episode = item['episode']
                resume_point = item['resume_point']
                year = item['year']


                self.list.append({
                                'title': title, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb,
                                'trakt': trakt_id, 'season': season, 'episode': episode,
                                'resume_point': resume_point, 'year': year

                                })
            c.log(f"[CM Debug @ 950 in episodes.py] self.list = {self.list}")

            for item in self.list:
                c.log(f"[CM Debug @ 954 in episodes.py] item = {item}")

            return self.list
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1140 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1140 in episodes.py]Exception raised. Error = {e}')
            pass


    def episode_superinfo(self, item):
        try:
            if not item:
                return
            if item['season'] == '0':
                raise ValueError()
            if item['episode'] == '0':
                raise ValueError()

            tmdb = item['tmdb'] if 'tmdb' in item else 0
            if tmdb != 0:
                c.log(f"[CM Debug @ 1165 in episodes.py] tmdb = {tmdb}")



















            return item
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1157 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1157 in episodes.py]Exception raised. Error = {e}')
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
                #c.log(f"[CM Debug @ 961 in episodes.py] item={item}")
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

                first_aired = item['show']['first_aired']

                tvshowtitle = item['show']['title']  # item.get('show']'title')
                if not tvshowtitle:
                    raise Exception('No Title')
                else:
                    tvshowtitle = client.replaceHTMLCodes(tvshowtitle)

                trailer = str(item.get('show').get('trailer')) or '0'
                year = item['show']['year']  # year returns int
                if int(year) > int(self.datetime.strftime('%Y')):
                    raise Exception()

                imdb = item['show']['ids']['imdb'] or '0'  # returns str
                tvdb = str(item['show']['ids']['tvdb']) or '0' # returns int
                tmdb = str(item['show']['ids']['tmdb']) or '0' # returns int
                studio = str(item['show']['network']) or '0'
                duration = item['show']['runtime'] or '0'

                mpaa = item['show']['certification'] or '0'
                status = item['show']['status'] or '0'
                genre = item['show']['genres'] or '0'
                if genre != '0':
                    genre = '/'.join(genre)

                last_watched = item['last_watched_at'] or '0'

                items.append(
                    {
                        'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, 'tvshowtitle': tvshowtitle,
                        'year': year, 'studio': studio, 'duration': duration,
                        'first_aired': first_aired, 'mpaa': mpaa, 'status': status, 'genre': genre,
                        'snum': season, 'enum': episode, 'trailer': trailer,
                        '_last_watched': last_watched
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

        #except Exception as e:
            #c.log(f"[CM Debug @ 1038 in episodes.py] Exception raised. Error = {e}")


        def items_list(i):

            try:
                tmdb = i['tmdb']
                imdb = i['imdb']
                tvdb = i['tvdb']

                if (not tmdb or tmdb == '0') and not imdb == '0':
                    try:
                        url = self.tmdb_by_imdb % imdb
                        result = self.session.get(url, timeout=10).json()
                        tv_result = result.get('tv_results', [])[0]
                        tmdb = tv_result.get('id')

                        #tmdb = '0' if not tmdb else str(tmdb)
                        tmdb = str(tmdb) if tmdb else '0'
                    except Exception:
                        pass

                try:
                    item = [
                        x for x in self.blist
                        if x['tmdb'] == tmdb and
                        x['snum'] == i['snum'] and
                        x['enum'] == i['enum']
                        ][0]
                    item['action'] = 'episodes'
                    self.list.append(item)
                    return
                except Exception:
                    pass

                try:

                    if tmdb == '0':
                        raise Exception('tmdb = 0')

                    cur_episode = int(i['enum'])
                    cur_season = int(i['snum'])


                    _episode = str(int(i['enum']) + 1)
                    _season = str(int(i['snum']) + 1)

                    ended = False

                    if i['status'].lower() in ['canceled', 'ended']:
                        ended = True
                        #c.log(f"[CM Debug @      in episodes.py] title = {i['tvshowtitle']} and current episode = {cur_episode} and current season = {cur_season}")
                        #raise Exception(f"Show {i['tvshowtitle']} has ended or canceled")

                    item = []
                    #if not ended:
                    url = self.tmdb_episode_link % (tmdb, i['snum'], _episode)
                    item = self.session.get(url, timeout=10).json()
                    if item.get('status_code') == 34:
                        url2 = self.tmdb_episode_link % (tmdb, _season, '1')
                        item = self.session.get(url2, timeout=10).json()

                        if item.get('status_code') == 34:
                            raise Exception()


                    in_widget = 'false'
                    if c.is_widget_listing():
                        in_widget = 'false'

                    tvshowtitle = i['tvshowtitle']
                    year = i['year']
                    mpaa = i['mpaa']
                    studio = i['studio']
                    genre = i['genre']
                    status = i['status']
                    trailer = i['trailer']
                    if trailer in ['0', 'None', None]:
                        trailer = '0'
                    duration = i['duration']

                    c.log(f"[CM Debug @ 1103 in episodes.py] inside def progress_list. Duration = {duration}")

                    title = item['name'] if 'name' in item else tvshowtitle
                    unaired = ''

                    #if ended:
                        #c.log(f"[CM Debug @ 1121 in episodes.py] premiered could be i = {i}")
                        #premiered = i['first_aired'] if 'first_aired' in i else '0'
                    #else:
                    premiered = item['first_aired'] if 'first_aired' in item else item['air_date'] if 'air_date' in item else '0'

                    if not premiered or premiered == '0':
                        pass
                    elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                        unaired = 'true'
                        if self.showunaired != 'true':
                            raise Exception()

                    season = item['season_number'] if 'season_number' in item else '0'

                    if int(season) == 0 and self.specials != 'true':
                        raise Exception('season == 0 and specials != true')
                    season = f'{int(season):01d}' if int(season) > 0 else season
                    s_season = f'{int(season):02d}' if int(season) > 0 else season

                    episode = item['episode_number'] if 'episode_number' in item else '0'
                    episode = f'{int(episode):01d}' if int(episode) > 0 else episode
                    s_episode = f'{int(episode):02d}' if int(episode) > 0 else episode

                    label = f'{tvshowtitle} : (S{s_season}E{s_episode})'
                    c.log(f"[CM Debug @ 1316 in episodes.py] lavel = {label}")

                    if 'still_path' in item and item['still_path'] not in [None, '']:
                        thumb = self.tmdb_img_link.format(c.tmdb_stillsize, item['still_path'])
                    else:
                        thumb = c.addon_thumb()

                    rating = str(item['vote_average']) if 'vote_average' in item else '0'
                    votes = str(item['vote_count']) if 'vote_count' in item else '0'

                    plot = c.lang(32623) if 'overview' not in item or not item['overview'] else item['overview']
                    plot = client.replaceHTMLCodes(plot) if plot else '0'

                    r_crew = item['crew'] if 'crew' in item else []

                    if r_crew:
                        r_crew = [c for c in r_crew if c['job'] in ['Director', 'Writer']]
                        c.log(f"[CM Debug @ 1151 in episodes.py] r_crew = {r_crew}")
                    else:
                        r_crew = []

                    director = writer = '0'

                    if r_crew:
                        director = [d for d in r_crew if d['job'] == 'Director']

                        director = '/'.join([d['name'] for d in director])

                        writer = [w for w in r_crew if w['job'] == 'Writer']
                        writer = '/'.join([w['name'] for w in writer])

                    #except Exception:
                    #    director = writer = ''
                    #if not director:
                    #    director = '0'
                    #if not writer:
                    #    writer = '0'

                    castwiththumb = []
                    try:
                        r_cast = item['credits']['cast'][:30]
                        for person in r_cast:
                            _icon = person['profile_path']
                            icon = self.tmdb_img_link.format(c.tmdb_profilesize, _icon) if _icon else ''
                            castwiththumb.append(
                                {
                                    'name': person['name'],
                                    'role': person['character'],
                                    'thumbnail': icon
                                })
                    except Exception:
                        pass
                    if not castwiththumb:
                        castwiththumb = '0'

                    poster = fanart = banner = landscape = clearlogo = clearart = '0'

                    c.log(f"[CM Debug @ 1207 in episodes.py] tvdb = {tvdb}")

                    if tvdb and tvdb != '0':
                        tempart = fanart_tv.get_fanart_tv_art(tvdb=tvdb)
                        poster = tempart.get('poster', '0')
                        fanart = tempart.get('fanart', '0')
                        banner = tempart.get('banner', '0')
                        landscape = tempart.get('landscape', '0')
                        clearlogo = tempart.get('clearlogo', '0')
                        clearart = tempart.get('clearart', '0')
                        c.log(f"[CM Debug @ 1175 in episodes.py] tvdb = {tvdb}, tempart = {repr(tempart)}")

                    if poster == '0':
                        poster, fanart = self.get_tmdb_art(tmdb)

                    c.log(f"[CM Debug @ 1179 in episodes.py] appending to list with poster = {poster}")

                    self.list.append({
                        'title': title, 'season': season, 'episode': episode,
                        'tvshowtitle': tvshowtitle, 'year': year,
                        'premiered': premiered, 'studio': studio,
                        'genre': genre, 'status': status, 'duration': duration,
                        'rating': rating, 'votes': votes, 'mpaa': mpaa,
                        'director': director, 'writer': writer, 'in_widget': in_widget,
                        'castwiththumb': castwiththumb, 'plot': plot,
                        'trailer': trailer, 'poster': poster, 'banner': banner,
                        'fanart': fanart, 'thumb': thumb, 'clearlogo': clearlogo,
                        'clearart': clearart, 'landscape': landscape,
                        'snum': i['snum'], 'enum': i['enum'], 'action': 'episodes',
                        '_last_watched': i['_last_watched'], 'unaired': unaired,
                        'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb,
                        '_sort_key': max(i['_last_watched'], premiered), 'label': label
                        })



                except Exception as e:
                    if e not in ['Exception', '', None] :

                        import traceback
                        failure = traceback.format_exc()
                        if failure not in ['Exception', '', None]:
                            #c.log(f'[CM Debug @ 1230 in episodes.py]e.args:: {repr(e)}')
                            c.log(f'[CM Debug @ 1231 in episodes.py]Traceback:: {failure}')
                            c.log(f'[CM Debug @ 1232 in episodes.py]Exception raised. Error = {e}')
                    #except Exception as e:
                    #    c.log(f"[CM Debug @ 1205 in episodes.py] Exception error {e} in progress items_list: i = {i} with item = {item}")
                    #    pass


            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 1086 in episodes.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 1086 in episodes.py]Exception raised. Error = {e}')



            #except Exception as e:
                #c.log(f"[CM Debug @ 1087 in episodes.py] Exception error {e} in progress")

        c.log(f"[CM Debug @ 1451 in episodes.py] aantal items = {len(items)}")
        #items = items[:100]

        try:
            threads = []
            for i in items:
                threads.append(workers.Thread(items_list, i))

            for i in threads:
                i.start()
            for i in threads:
                i.join()
        except Exception:
            pass

        try:
            if sortorder == '0':
                self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)
            else:
                self.list = sorted(self.list, key=lambda k: k['_sort_key'], reverse=True)
        except Exception:
            pass

        return self.list

    def get_tmdb_art(self, tmdb):
        try:
            url = self.tmdb_show_link % tmdb
            result = self.session.get(url, timeout=10).json()

            poster = self.tmdb_img_link.format(c.tmdb_postersize, result['poster_path']) if 'poster_path' in result else '0'
            fanart = self.tmdb_img_link.format(c.tmdb_fanartsize, result['background_path']) if 'background_path' in result else '0'

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
                item = [x for x in self.blist if x['tmdb'] == tmdb and x['season']
                        == i['season'] and x['episode'] == i['episode']][0]

                if item['poster'] == '0':
                    raise Exception()
                self.list.append(item)
                return
            except Exception:
                pass

            try:
                if tmdb == '0':
                    raise Exception()

                url = self.tmdb_episode_link % (
                    tmdb, i['season'], i['episode'])
                item = self.session.get(url, timeout=10).json()

                title = item['name']
                if not title:
                    title = '0'
                else:
                    title = client.replaceHTMLCodes(str(title))

                season = item['season_number']
                season = '%01d' % season
                if int(season) == 0 and self.specials != 'true':
                    raise Exception()

                episode = item['episode_number']
                episode = '%01d' % episode

                tvshowtitle = i['tvshowtitle']
                premiered = i['premiered']

                unaired = ''
                if not premiered or premiered == '0':
                    pass
                elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    unaired = 'true'
                    if self.showunaired != 'true':
                        raise Exception('unaired is False')




                status = i['status']
                duration = i['duration']
                mpaa = i['mpaa']
                studio = i['studio']
                genre = i['genre']
                year = i['year']
                rating = i['rating']
                votes = i['votes']

                thumb = self.tmdb_img_link.format(c.tmdb_stillsize, item['still_path']) if item['still_path'] else '0'


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
                        icon = self.tmdb_img_link.format(c.tmdb_profilesize, _icon) if _icon else ''
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

                if not tvdb == '0':
                    tempart = fanart_tv.get_fanart_tv_art(tvdb=tvdb)
                    poster = tempart.get('poster', '0')
                    fanart = tempart.get('fanart', '0')
                    banner = tempart.get('banner', '0')
                    landscape = tempart.get('landscape', '0')
                    clearlogo = tempart.get('clearlogo', '0')
                    clearart = tempart.get('clearart', '0')

                    c.log(f"[CM Debug @ 1409 in episodes.py] poster = {poster}, fanart = {fanart}, banner = {banner}, landscape = {landscape}, clearlogo = {clearlogo}, clearart = {clearart}")

                fanart1 = '0'
                if poster == '0':
                    poster, fanart1 = self.get_tmdb_art(tmdb)

                if fanart == '0':
                    fanart = fanart1

                landscape = fanart if thumb == '0' else thumb

                self.list.append({'title': title, 'season': season, 'episode': episode,
                                    'tvshowtitle': tvshowtitle, 'year': year,
                                    'premiered': premiered, 'status': status, 'studio': studio,
                                    'genre': genre, 'duration': duration, 'rating': rating,
                                    'votes': votes, 'mpaa': mpaa, 'director': director,
                                    'writer': writer, 'castwiththumb': castwiththumb, 'plot': plot,
                                    'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, 'poster': poster,
                                    'banner': banner, 'fanart': fanart, 'thumb': thumb,
                                    'clearlogo': clearlogo, 'clearart': clearart,
                                    'landscape': landscape, 'paused_at': paused_at,
                                    'unaired': unaired, 'watched_at': watched_at})
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 1430 in episodes.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 1430 in episodes.py]Exception raised. Error = {e}')
                pass
            #except Exception as e:
                #c.log(f"[CM Debug @ 1372 in episodes.py] exception: {e}")


        items = items[:100]

        threads = []
        for i in items:
            threads.append(workers.Thread(items_list, i))
        for i in threads:
            i.start()

        for i in threads:
            i.join()

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
                    url = (trakt.slug(
                        item['list']['user']['username']), item['list']['ids']['slug'])
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
                poster = self.tmdb_img_link.format(c.tmdb_postersize, poster_path)
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
                        thumb = self.tmdb_img_link.format(c.tmdb_stillsize, still_path)
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
                #c.log(f"[CM Debug @ 2048 in episodes.py] item = {item}")
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

                duration = item.get('duration', '45')
                duration = str(int(duration) * 60)
                #c.log(f"[CM Debug @ 2172 in episodes.py] duration = {duration} with title = {item['title']} and season = {item['season']} and episode = {item['episode']}")
                status = item.get('status', '0')


                meta = {
                    'poster': poster,
                    'fanart': fanart,
                    'banner': banner,
                    'clearlogo': clearlogo,
                    'clearart': clearart,
                    'discart': discart,
                    'landscape': landscape,
                    'duration': duration,
                    'status': status
                }

                seasons_meta = quote_plus(json.dumps(meta))

                title = quote_plus(item['title'])
                tvshowtitle = quote_plus(item['tvshowtitle']) if 'tvshowtitle' in item else title
                premiered = quote_plus(item['premiered'])
                trailer = quote_plus(item.get('trailer', '0'))
                year = item.get('year', '0')
                if year == '0' and 'premiered' in item:
                    year = re.findall(r'(\d{4})', item['premiered'])[0]



                meta = {k: v for k, v in item.items() if v != '0'}
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
                    meta['trailer'] = f'{sys_addon}?action=trailer&name={tvshowtitle}&imdb={imdb_id}&tmdb={tmdb_id}&season={season}&episode={episode}&mediatype=episode&meta={seasons_meta}'
                else:
                    meta['trailer'] = f'{sys_addon}?action=trailer&name={tvshowtitle}&url={trailer}&imdb={imdb_id}&tmdb={tmdb_id}&mediatype=episode&meta={seasons_meta}'


                sys_meta = quote_plus(json.dumps(meta))

                url = f'{sys_addon}?action=play&title={title}&year={year}&imdb={imdb_id}&tmdb={tmdb_id}&season={season}&episode={episode}&tvshowtitle={tvshowtitle}&premiered={premiered}&meta={sys_meta}&t={self.systime}'
                sys_url = quote_plus(url)

                if is_folder:
                    url = f'{sys_addon}?action=episodes&tvshowtitle={tvshowtitle}&year={year}&imdb={imdb_id}&tmdb={tmdb_id}&meta={seasons_meta}&season={season}&episode={episode}'

                cm = [(control.lang(32065), f'RunPlugin({sys_addon}?action=queueItem)')]

                if multi:
                    cm.append((control.lang(32071), f'Container.Update({sys_addon}?action=seasons&tvshowtitle={tvshowtitle}&year={year}&imdb={imdb_id}&tmdb={tmdb_id}&meta={seasons_meta},return)'))

                try:
                    overlay = int(playcount.get_episode_overlay(indicators, imdb_id, tmdb_id, season, episode))
                    if overlay == 7:
                        cm.append((control.lang(32069), f'RunPlugin({sys_addon}?action=episodePlaycount&imdb={imdb_id}&tmdb={tmdb_id}&season={season}&episode={episode}&query=6)'))
                        meta.update({'playcount': 1, 'overlay': 7})
                    else:
                        cm.append((control.lang(32068), f'RunPlugin({sys_addon}?action=episodePlaycount&imdb={imdb_id}&tmdb={tmdb_id}&season={season}&episode={episode}&query=7)'))
                        meta.update({'playcount': 0, 'overlay': 4})
                except Exception:
                    pass

                if trakt_credentials:
                    cm.append((control.lang(32515), f'RunPlugin({sys_addon}?action=traktManager&name={tvshowtitle}&tmdb={tmdb_id}&content=tvshow)'))

                if not is_folder:
                    cm.append((control.lang(32063), f'RunPlugin({sys_addon}?action=alterSources&url={sys_url}&meta={sys_meta})'))
                cm.append((control.lang(32551), f'RunPlugin({sys_addon}?action=tvshowToLibrary&tvshowtitle={tvshowtitle}&year={year}&imdb={imdb_id}&tmdb={tmdb_id})'))
                cm.append((control.lang(32098), f'RunPlugin({sys_addon}?action=clearSources)'))

                liz = control.item(label=label, offscreen=True)

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

                liz.setArt(art)

                castwiththumb = item.get('castwiththumb')
                if castwiththumb and castwiththumb != '0':
                    meta['cast'] = castwiththumb

                if is_folder:
                    liz.setProperty('IsPlayable', 'true')


                #not all episodes have an imdb id, all do have a tmdb id

                offset = bookmarks.get('episode', imdb=imdb_id, tmdb=tmdb_id, season=season, episode=episode, local=False)
                #c.log(f"[CM Debug @ 2159 in episodes.py] offset = {offset}")
                meta.update({'offset': offset})

                meta['studio'] = c.string_split_to_list(meta['studio']) if 'studio' in meta else []
                meta['genre'] = c.string_split_to_list(meta['genre']) if 'genre' in meta else []
                meta['director'] = c.string_split_to_list(meta['director']) if 'director' in meta else []
                meta['writer'] = c.string_split_to_list(meta['writer']) if 'writer' in meta else []

                info_tag = ListItemInfoTag(liz, 'video')
                infolabels = control.tagdataClean(meta)

                info_tag.set_info(infolabels)
                unique_ids = {'imdb': imdb_id, 'tmdb': str(tmdb_id)}
                info_tag.set_unique_ids(unique_ids)
                info_tag.set_cast(meta.get('cast', []))

                if offset > 0:
                    info_tag.set_resume_point(meta, 'offset', 'duration', False)

                stream_info = {'codec': 'h264'}
                info_tag.add_stream_info('video', stream_info)
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
