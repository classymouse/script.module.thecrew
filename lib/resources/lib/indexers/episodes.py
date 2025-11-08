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
import os
import sys
import re
# cm - added temporarily
import time
import datetime
import json


import concurrent.futures
from contextlib import suppress
import traceback

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
from ..modules import crew_errors
from ..modules import fanart as fanart_tv

from ..modules.listitem import ListItemInfoTag
#from ..modules import log_utils
from ..modules.crewruntime import c



if c.is_orion_installed():
    from orion import *

ORION_INSTALLED = c.is_orion_installed()

params = dict(parse_qsl(sys.argv[2].replace('?', ''))) if len(sys.argv) > 1 else {}
action = params.get('action')


class Seasons:
    def __init__(self):
        self.list = []
        self.speedtest = {'start': time.perf_counter()}
        self.meta = {}

        self.session = requests.Session()

        self.tmdb_user = c.get_setting( 'tm.personal_user') or c.get_setting('tm.user') or keys.tmdb_key
        self.user = self.tmdb_user
        self.lang = control.apiLanguage()['tmdb']
        self.showunaired = c.get_setting('showunaired') or 'true'
        self.specials = c.get_setting('tv.specials') or 'true'
        self.show_fanart = c.get_setting('fanart') == 'true'

        self.today_date = datetime.date.today().strftime("%Y-%m-%d")
        self.tmdb_link = 'https://api.themoviedb.org/3/'
        self.tmdb_img_link = 'https://image.tmdb.org/t/p/%s%s'

        self.tmdb_show_link = f'{self.tmdb_link}tv/%s?api_key={self.tmdb_user}&language=%s&append_to_response=external_ids,aggregate_credits,content_ratings'
        self.tmdb_show_lite_link = f'{self.tmdb_link}tv/%s?api_key={self.tmdb_user}&language=en&append_to_response=external_ids'
        self.tmdb_by_imdb = f"{self.tmdb_link}find/%s?api_key={self.tmdb_user}&external_source=imdb_id&append_to_response=external_ids"
        self.tmdb_external_ids_by_tmdb = f'{self.tmdb_link}tv/%s/external_ids?api_key={self.tmdb_user}&language=en-US'
        self.tmdb_episode_link = f'{self.tmdb_link}tv/%s/season/%s/episode/%s?api_key={self.tmdb_user}&language={self.lang}&append_to_response=credits,images'

        self.tmdb_api_link = f'{self.tmdb_link}tv/%s?api_key={self.tmdb_user}&language={self.lang}&append_to_response=external_ids,aggregate_credits,content_ratings,external_ids'

        self.tmdb_networks_link = f'{self.tmdb_link}discover/tv?api_key={self.tmdb_user}&sort_by=popularity.desc&with_networks=%s&append_to_response=external_ids&page=1'
        self.tmdb_search_tvshow_link = f'{self.tmdb_link}search/tv?api_key={self.tmdb_user}&language=en-US&append_to_response=external_ids&query=%s&page=1'
        self.tmdb_info_tvshow_link = f'{self.tmdb_link}tv/%s?api_key={self.tmdb_user}&language=en-US&append_to_response=external_ids,images'

    def __del__(self):
        with suppress(Exception):
            self.session.close()

    def get(self, tvshowtitle, year, imdb, tmdb, meta=None, idx=True, create_directory=True):
        try:
            if idx is True:
                #self.list = cache.get(self.tmdb_list, 24, tvshowtitle, year, imdb, tmdb, meta)
                self.list = self.tmdb_list(tvshowtitle, year, imdb, tmdb, meta)
                if create_directory is True:
                    self.season_directory(self.list)
                return self.list
            else:
                self.list = self.tmdb_list(tvshowtitle, year, imdb, tmdb, meta)
            return self.list
        except Exception:
            pass


    def tmdb_list(self, tvshowtitle, year, imdb_id, tmdb_id, meta=None, lite=False):
        """
        Get a list of TV show seasons from TMDB.

        Cleaner logic, narrower exception handling and improved logging.
        Returns: self.list (list of season dicts)
        """

        # reset list for repeated calls
        self.list = []

        # Validate TMDB id early
        if tmdb_id in ('0', None, ''):
            raise ValueError('No valid TMDB id provided')

        # Build request URL
        try:
            if lite:
                url = self.tmdb_show_lite_link % tmdb_id
            else:
                lang = 'en' if self.lang == 'en' else self.lang
                url = self.tmdb_show_link % (tmdb_id, lang)
                if not lite and self.lang != 'en':
                    url = f'{url},translations'
        except Exception as e:
            c.log(f"[CM Debug @ tmdb_list] Failed to build TMDB URL: {e}")
            raise

        # Fetch show data from TMDB
        try:
            resp = self.session.get(url, timeout=16)
            resp.raise_for_status()
            item = resp.json()
        except requests.HTTPError as e:
            c.log(f"[CM Debug @ tmdb_list] TMDB HTTP error: {e} url={url}")
            raise
        except (ValueError, json.JSONDecodeError) as e:
            c.log(f"[CM Debug @ tmdb_list] TMDB returned invalid JSON: {e} url={url}")
            raise
        except requests.RequestException as e:
            c.log(f"[CM Debug @ tmdb_list] TMDB request failed: {e} url={url}")
            raise

        if not item:
            raise ValueError('Empty TMDB response')

        # Safe extraction helpers
        def _int_from(item, key, default=0):
            try:
                return int(item.get(key) or default)
            except Exception:
                return default

        def _first_in_list(val, default=45):
            try:
                if isinstance(val, list):
                    return val[0] if val else default
                return val or default
            except Exception:
                return default

        number_of_episodes = _int_from(item, 'number_of_episodes', 0)
        number_of_seasons = _int_from(item, 'number_of_seasons', 0)

        tvshowtitle = item.get('name') or tvshowtitle or '0'
        tagline = item.get('tagline') or '0'
        ext_ids = item.get('external_ids') or {}
        tvdb_id = ext_ids.get('tvdb') or '0'
        imdb_id = ext_ids.get('imdb_id') or imdb_id or '0'

        seasons_list = item.get('seasons') or []
        if self.specials == 'false':
            seasons_list = [s for s in seasons_list if s.get('season_number') != 0]

        # network/studio
        studio = '0'
        try:
            networks = item.get('networks') or []
            if networks:
                studio = networks[0].get('name') or '0'
        except Exception as e:
            c.log(f"[CM Debug @ tmdb_list] network extraction failed: {e}")

        # genres
        try:
            genres = item.get('genres') or []
            genre = ' / '.join([g.get('name', '') for g in genres]) if genres else '0'
        except Exception:
            genre = '0'

        # duration
        duration_val = _first_in_list(item.get('episode_run_time', 45), 45)
        try:
            duration = str(int(duration_val))
        except Exception:
            duration = '45'

        # MPAA / content ratings (try US first)
        mpaa = '0'
        try:
            c_ratings = (item.get('content_ratings') or {}).get('results') or []
            if c_ratings:
                us = [r.get('rating') for r in c_ratings if r.get('iso_3166_1') == 'US' and r.get('rating')]
                if us:
                    mpaa = us[0] or '0'
        except Exception:
            mpaa = '0'

        status = item.get('status') or '0'
        rating = str(item.get('vote_average') or 0)
        votes = str(item.get('vote_count') or 0)

        # cast extraction (non-fatal)
        cast = '0'
        try:
            cast_info, _, _ = self.get_cast(item)
            cast = cast_info or '0'
        except Exception as e:
            c.log(f"[CM Debug @ tmdb_list] get_cast failed: {e}")

        # overview / plot (with fallback translations if available)
        try:
            show_plot = item.get('overview') or c.lang(32623) or '0'
            show_plot = client.replaceHTMLCodes(c.ensure_str(show_plot, errors='replace'))
        except Exception:
            show_plot = c.lang(32623) or '0'

        if self.lang != 'en' and (not show_plot or show_plot == '0'):
            try:
                translations = (item.get('translations') or {}).get('translations', []) or []
                if translations:
                    show_plot = self.get_plot_fallback_item(translations)
            except Exception as e:
                c.log(f"[CM Debug @ tmdb_list] translation fallback failed: {e}")

        # artwork defaults
        banner = clearlogo = clearart = landscape = '0'
        try:
            if meta:
                _meta = json.loads(unquote_plus(meta))
                show_poster = _meta.get('poster', '0')
                fanart = _meta.get('fanart', '0')
                banner = _meta.get('banner', '0')
                clearlogo = _meta.get('clearlogo', '0')
                clearart = _meta.get('clearart', '0')
                landscape = _meta.get('landscape', '0')
            else:
                poster_path = item.get('poster_path') or ''
                show_poster = self.tmdb_img_link % (c.tmdb_postersize, poster_path) if poster_path else '0'

                fanart_path = item.get('backdrop_path') or ''
                fanart = self.tmdb_img_link % (c.tmdb_fanartsize, fanart_path) if fanart_path else '0'

                # fanart.tv fallback if tvdb available
            try:
                if int(self.show_fanart) != 1 or tvdb_id not in ('0', None, ''):
                    tv_fanart = cache.get(fanart_tv.get_fanart_tv_art, 72, tvdb_id)
                    if tv_fanart:
                        show_poster = tv_fanart.get('poster', show_poster)
                        fanart = tv_fanart.get('fanart') or fanart or '0'
                        banner = tv_fanart.get('banner', banner)
                        clearlogo = tv_fanart.get('clearlogo', clearlogo)
                        clearart = tv_fanart.get('clearart', clearart)
                        landscape = tv_fanart.get('landscape', landscape)
            except Exception as e:
                c.log(f"[CM Debug @ tmdb_list] fanart.tv lookup failed: {e}")
        except Exception as e:
            c.log(f"[CM Debug @ tmdb_list] artwork parsing failed: {e}")
            show_poster = '0'
            fanart = '0'

        # helper: date numeric comparator (YYYYMMDD as int)
        def _date_num(date_str):
            try:
                return int(re.sub('[^0-9]', '', str(date_str)))
            except Exception:
                return 0

        today_num = _date_num(self.today_date)

        # iterate seasons and build result entries
        for s in seasons_list:
            try:
                season_num_raw = s.get('season_number', 0)
                season = str(int(season_num_raw))
                premiered = s.get('air_date') or '0'

                # skip if not premiered and show not ended
                if status != 'Ended' and (not premiered or premiered == '0'):
                    continue

                unaired = 'false'
                if status != 'Ended' and premiered and premiered != '0':
                    premiered_num = _date_num(premiered)
                    if premiered_num > today_num:
                        unaired = 'true'
                        if self.showunaired != 'true':
                            continue

                plot = s.get('overview') or c.lang(32623) or '0'
                plot = client.replaceHTMLCodes(c.ensure_str(plot, errors='replace'))

                poster_path = s.get('poster_path') or ''
                poster = self.tmdb_img_link % (c.tmdb_postersize, poster_path) if poster_path else show_poster
                thumb = poster

                self.list.append({
                    'season': season,
                    'tvshowtitle': tvshowtitle,
                    'tagline': tagline,
                    'year': year,
                    'premiered': premiered,
                    'status': status,
                    'studio': studio,
                    'genre': genre,
                    'duration': duration,
                    'mpaa': mpaa,
                    'castwiththumb': cast,
                    'plot': plot,
                    'imdb': imdb_id,
                    'tmdb': str(tmdb_id),
                    'tvdb': tvdb_id,
                    'poster': thumb,
                    'fanart': fanart,
                    'banner': banner,
                    'clearlogo': clearlogo,
                    'thumb': thumb,
                    'clearart': clearart,
                    'landscape': landscape,
                    'seasons': number_of_seasons,
                    'episodes': number_of_episodes,
                    'rating': rating,
                    'votes': votes,
                    'unaired': unaired,
                })
            except Exception as e:
                failure = traceback.format_exc()
                c.log(f"[CM Debug @ tmdb_list] Skipping season due to error: {e}\n{failure}")
                continue

        return self.list

    def get_cast(self, item):
        """
        Populate a TV show item with additional metadata.
        """


        cast_list = item.get('aggregate_credits', {}).get('cast', [])[:30]
        cast_info = []
        for person in cast_list:
            icon = self.tmdb_img_link % (
                c.tmdb_profilesize, person['profile_path']
                ) if person['profile_path'] else ''
            cast_info.append({
                'name': person['name'],
                'role': person['roles'][0]['character'],
                'thumbnail': icon
            })

        crew_list = item.get('aggregate_credits', {}).get('crew', [])
        writers = [x['name'] for x in crew_list if 'Writer' in x.get('jobs', [])]
        directors = [x['name'] for x in crew_list if 'Director' in x.get('jobs', [])]

        writer = ' / '.join(writers) if writers else '0'
        director = ' / '.join(directors) if directors else '0'

        return cast_info, writer, director



    def get_plot_fallback_item(self, translations) -> str:
        """If the show plot is not available in the show's native language,
        get the English version of the show plot as a fallback."""

        fallback_item = [x['data'] for x in translations if x.get('iso_639_1') == 'en'][0]
        show_plot = fallback_item['overview'] or c.lang(32623)
        show_plot = client.replaceHTMLCodes(str(show_plot))

        return show_plot

    def super_info(self, i):
        """
        Populate an entry in self.list (index i) with enriched TMDB/episode metadata.
        Simplified by delegating to helper functions for clarity and speed.
        """
        try:
            item = self.list[i]
            is_episode = 'showimdb' in item

            # Step 1: Resolve and validate IDs
            ids = self._resolve_ids(item, is_episode)
            if not ids:
                return  # Skip if IDs can't be resolved

            show_imdb, show_tmdb, show_tvdb, show_trakt = ids

            # Step 2: Fetch TMDB data
            show_item, episode_item = self._fetch_tmdb_data(show_tmdb, item['season'], item['episode'])
            if not episode_item:
                return  # Skip if episode data unavailable

            # Step 3: Extract metadata
            metadata = self._extract_metadata(show_item, episode_item, item, show_imdb, show_tmdb, show_tvdb, show_trakt, is_episode)

            # Step 4: Handle artwork
            artwork = self._handle_artwork(show_tvdb, show_tmdb)
            metadata.update(artwork)

            # Step 5: Build and update the item
            enriched_item = self._build_enriched_item(metadata, item)
            self._update_list_entry(i, enriched_item)

            # Step 6: Append to meta cache
            self._append_meta(enriched_item, show_imdb, show_tmdb, show_tvdb, item.get('resume_point', '0.0'))

        except Exception as e:
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ super_info] Traceback: {failure}')
            c.log(f'[CM Debug @ super_info] Exception: {e}')

    def _resolve_ids(self, item, is_episode):
        """Resolve and validate IMDB/TMDB/TVDB/TRAKT IDs, fetching missing ones from TMDB."""
        try:
            if is_episode:
                show_imdb = item.get('showimdb', '0')
                show_tmdb = item.get('showtmdb', '0')
                show_tvdb = item.get('showtvdb', '0')
                show_trakt = item.get('showtrakt', '0')
            else:
                show_imdb = item.get('imdb', '0')
                show_tmdb = item.get('tmdb', '0')
                show_tvdb = item.get('tvdb', '0')
                show_trakt = item.get('trakt', '0')

            # Resolve missing TMDB from IMDB
            if show_tmdb == '0' and show_imdb != '0':
                try:
                    result = self.session.get(self.tmdb_by_imdb % show_imdb, timeout=15).json()
                    show_tmdb = str(result['tv_results'][0]['id']) if result.get('tv_results') else '0'
                except Exception:
                    pass

            # Resolve missing IMDB from TMDB
            if show_imdb == '0' and show_tmdb != '0':
                try:
                    result = self.session.get(self.tmdb_external_ids_by_tmdb % show_tmdb, timeout=15).json()
                    show_imdb = result.get('imdb_id', '0')
                except Exception:
                    pass

            # Resolve missing TVDB from TMDB
            if show_tvdb == '0' and show_tmdb != '0':
                try:
                    result = self.session.get(self.tmdb_external_ids_by_tmdb % show_tmdb, timeout=15).json()
                    show_tvdb = result.get('tvdb_id', '0')
                except Exception:
                    pass

            # Fail if no valid ID
            if show_tmdb in ('0', None) and show_imdb in ('0', None):
                return None

            return show_imdb, show_tmdb, show_tvdb, show_trakt
        except Exception as e:
            c.log(f'[CM Debug @ _resolve_ids] Exception: {e}')
            return None

    def _fetch_tmdb_data(self, show_tmdb, season, episode):
        """Fetch show and episode data from TMDB."""
        try:
            _id = show_tmdb
            en_url = self.tmdb_api_link % _id
            trans_url = f'{en_url},translations'
            url = en_url if self.lang == 'en' else trans_url
            show_item = self.session.get(url, timeout=15).json()

            episode_url = self.tmdb_episode_link % (show_tmdb, season, episode)
            episode_item = self.session.get(episode_url, timeout=15).json()

            return show_item, episode_item
        except Exception as e:
            c.log(f'[CM Debug @ _fetch_tmdb_data] Exception: {e}')
            return {}, {}

    def _extract_metadata(self, show_item, episode_item, item, show_imdb, show_tmdb, show_tvdb, show_trakt, is_episode):
        """Extract core metadata from TMDB responses."""
        try:
            show_title = item.get('tvshowtitle', '')
            title = item.get('title', '') or episode_item.get('name', '')
            season = item.get('season', '0')
            episode = item.get('episode', '0')
            year = item.get('year', '0')
            resume_point = item.get('resume_point', '0.0') or item.get('_resume_point', '0.0')

            # Normalize season/episode
            season = f"{int(season):01d}" if season and season != '0' else '0'
            episode = f"{int(episode):01d}" if episode and episode != '0' else '0'

            label = f"{show_title} : (S{season.zfill(2)}E{episode.zfill(2)})" if is_episode else show_title

            # Duration, status, premiered
            duration = episode_item.get('runtime') or episode_item.get('episode_run_time') or '45'
            status = show_item.get('status') or show_item.get('in_production', '0') or 'Ended'
            premiered = episode_item.get('air_date', '0')
            premiered = re.search(r'(\d{4}-\d{2}-\d{2})', premiered)
            premiered = premiered.group(1) if premiered else '0'

            # Genre, MPAA, rating, etc.
            genre = ' / '.join([d['name'] for d in show_item.get('genres', [])]) if show_item.get('genres') else '0'
            mpaa = show_item.get('mpaa', 'Not Rated')
            rating = str(show_item.get('vote_average', '0'))
            votes = str(show_item.get('vote_count', '0'))
            studio = next((c['name'] for c in show_item.get('production_companies', []) if c), '0')
            country = ' / '.join([c['name'] for c in show_item.get('production_countries', [])]) if show_item.get('production_countries') else '0'
            tagline = show_item.get('tagline', '0')

            # Trailer
            trailer = item.get('trailer', '')
            if not trailer:
                vids = episode_item.get('videos', {}).get('results', [])
                if vids:
                    trailer = vids[0].get('key', '')
                else:
                    show_vids = show_item.get('videos', {}).get('results', [])
                    if show_vids:
                        trailer = show_vids[0].get('key', '')

            # Plot
            in_widget = bool(c.is_widget_listing())
            plot = episode_item.get('overview') or show_item.get('overview', '0')
            plot = client.replaceHTMLCodes(plot) if plot else '0'

            # Crew
            crew = episode_item.get('credits', {}).get('crew', []) or show_item.get('crew', [])
            crew = [c for c in crew if c.get('job') in ('Director', 'Writer')]
            director = '/'.join([d['name'] for d in crew if d['job'] == 'Director']) or '0'
            writer = '/'.join([w['name'] for w in crew if d['job'] == 'Writer']) or '0'

            # Cast
            castwiththumb = []
            try:
                creds = episode_item.get('credits', {})
                cast = creds.get('cast', [])[:30] + creds.get('guest_stars', [])[:30]
                for person in cast:
                    profile_path = person.get('profile_path', '')
                    icon = self.tmdb_img_link % (c.tmdb_profilesize, profile_path) if profile_path else ''
                    castwiththumb.append({
                        'name': person.get('name', ''),
                        'role': person.get('character', ''),
                        'thumbnail': icon
                    })
            except Exception:
                pass

            # Unaired check
            unaired = ''
            if premiered != '0':
                premiered_num = int(re.sub('[^0-9]', '', premiered))
                today_num = int(re.sub('[^0-9]', '', str(self.today_date)))
                if premiered_num > today_num:
                    unaired = 'true'
                    if self.showunaired != 'true':
                        raise Exception('Unaired episode hidden')

            return {
                'title': title, 'season': season, 'episode': episode, 'year': year,
                'imdb': show_imdb, 'tmdb': show_tmdb, 'tvdb': show_tvdb, 'trakt': show_trakt,
                'status': status, 'studio': studio, 'premiered': premiered, 'genre': genre,
                'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa,
                'director': director, 'writer': writer, 'castwiththumb': castwiththumb,
                'plot': plot, 'tagline': tagline, 'country': country, 'trailer': trailer,
                'label': label, 'resume_point': resume_point, 'tvshowtitle': show_title,
                'unaired': unaired, 'in_widget': in_widget
            }
        except Exception as e:
            c.log(f'[CM Debug @ _extract_metadata] Exception: {e}')
            return {}

    def _handle_artwork(self, show_tvdb, show_tmdb):
        """Fetch artwork from fanart.tv and TMDB fallbacks."""
        try:
            poster = fanart = banner = landscape = clearlogo = clearart = '0'

            # Fanart.tv
            if show_tvdb and show_tvdb != '0':
                try:
                    tempart = fanart_tv.get_fanart_tv_art(tvdb=show_tvdb)
                    poster = tempart.get('poster', poster)
                    fanart = tempart.get('fanart', fanart)
                    banner = tempart.get('banner', banner)
                    landscape = tempart.get('landscape', landscape)
                    clearlogo = tempart.get('clearlogo', clearlogo)
                    clearart = tempart.get('clearart', clearart)
                except Exception:
                    pass

            # TMDB fallback
            if poster == '0':
                try:
                    p, f = self.get_tmdb_art(show_tmdb)
                    poster = p or poster
                    fanart = f or fanart
                except Exception:
                    pass

            # Default fallbacks
            if poster == '0':
                poster = c.addon_poster()
            if fanart == '0':
                fanart = c.addon_fanart()

            return {
                'poster': poster, 'fanart': fanart, 'banner': banner, 'landscape': landscape,
                'clearlogo': clearlogo, 'clearart': clearart, 'thumb': landscape or fanart
            }
        except Exception as e:
            c.log(f'[CM Debug @ _handle_artwork] Exception: {e}')
            return {'poster': '0', 'fanart': '0', 'banner': '0', 'landscape': '0', 'clearlogo': '0', 'clearart': '0', 'thumb': '0'}

    def _build_enriched_item(self, metadata, original_item):
        """Build the final enriched item dict."""
        try:
            return {
                'title': metadata['title'], 'originaltitle': metadata['title'], 'year': metadata['year'],
                'imdb': metadata['imdb'], 'tvdb': metadata['tvdb'], 'tmdb': metadata['tmdb'],
                'status': metadata['status'], 'studio': metadata['studio'], 'poster': metadata['poster'],
                'banner': metadata['banner'], 'fanart': metadata['fanart'], 'fanart2': metadata['fanart'],
                'landscape': metadata['landscape'], 'discart': metadata['clearart'], 'clearlogo': metadata['clearlogo'],
                'clearart': metadata['clearart'], 'premiered': metadata['premiered'], 'genre': metadata['genre'],
                'thumb': metadata['thumb'], 'in_widget': metadata['in_widget'], 'duration': metadata['duration'],
                'rating': metadata['rating'], 'votes': metadata['votes'], 'mpaa': metadata['mpaa'],
                'director': metadata['director'], 'writer': metadata['writer'], 'castwiththumb': metadata['castwiththumb'],
                'plot': metadata['plot'], 'tagline': metadata['tagline'], 'country': metadata['country'],
                'trailer': metadata['trailer'], 'label': metadata['label'], 'resume_point': metadata['resume_point'],
                'trakt': metadata['trakt'], '_last_watched': original_item.get('_last_watched', '0'),
                'tvshowtitle': metadata['tvshowtitle'], 'season': metadata['season'], 'episode': metadata['episode'],
                'action': original_item.get('action'), 'unaired': metadata['unaired'],
                '_sort_key': max(original_item.get('_last_watched', '0'), metadata['premiered'])
            }
        except Exception as e:
            c.log(f'[CM Debug @ _build_enriched_item] Exception: {e}')
            return {}

    def _update_list_entry(self, i, enriched_item):
        """Safely update self.list[i] with the enriched item."""
        try:
            if self.list and i < len(self.list):
                if self.list[i] is None or not isinstance(self.list[i], dict):
                    self.list[i] = enriched_item
                else:
                    self.list[i].update(enriched_item)
        except Exception as e:
            c.log(f'[CM Debug @ _update_list_entry] Exception: {e}')

    def _append_meta(self, enriched_item, show_imdb, show_tmdb, show_tvdb, resume_point):
        """Append to self.meta for caching."""
        try:
            meta_entry = {
                'imdb': show_imdb, 'tmdb': show_tmdb, 'tvdb': show_tvdb, 'lang': self.lang,
                'user': self.user, 'resume_point': resume_point, 'item': enriched_item
            }
            self.meta.append(meta_entry)
        except Exception as e:
            c.log(f'[CM Debug @ _append_meta] Exception: {e}')

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

    def get_tmdb_art(self, tmdb):
        try:
            url = self.tmdb_show_link % tmdb
            result = self.session.get(url, timeout=10).json()

            poster = self.tmdb_img_link.format('original', result['poster_path']) if 'poster_path' in result else '0'
            fanart = self.tmdb_img_link.format('original', result['background_path']) if 'background_path' in result else '0'

            return poster, fanart
        except Exception:
            pass


    def no_info(self, item):
        '''cm - placeholder for now '''
        return item


    def super_info_orig(self, i):
        """
        Filling missing pieces
        """

        try:
            item = self.list[i]

            is_episode = 'showimdb' in item


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

                # label = f'{show_title} : (S{season:02d}E{episode:02d})'
                label = f'{show_title} : (S{season.zfill(2)}E{episode.zfill(2)})'


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
                c.log(f"[CM Debug @ 2314 in episodes.py] url = {url}")
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
            trans_url = f'{en_url},translations'
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



            in_widget = bool(c.is_widget_listing())
            plot = episode_item['overview'] if episode_item.get('overview') else show_item.get('overview', '0')
            plot = client.replaceHTMLCodes(plot) if plot else '0'

            crew = episode_item.get('credits', {}).get('crew', []) if 'credits' in episode_item else show_item['crew'] if 'crew' in show_item else []

            crew = [c for c in crew if c['job'] in ['Director', 'Writer']] if crew else []

            director = writer = '0'

            if crew:
                director = [d for d in crew if d['job'] == 'Director']
                director = '/'.join([d['name'] for d in director])

                writer = [w for w in crew if w['job'] == 'Writer']
                writer = '/'.join([w['name'] for w in writer])

            castwiththumb = []
            try:
                creds = episode_item.get('credits', {})
                cast = creds.get('cast', [])[:30]
                guests = creds.get('guest_stars', [])[:30]
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
            if fanart == '0':
                fanart = c.addon_fanart()

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

            # ensure we don't attempt to subscript/modify a None entry
            if self.list and i < len(self.list):
                if self.list[i] is None or not isinstance(self.list[i], dict):
                    # replace the entry if it's None or not a dict
                    self.list[i] = item
                else:
                    try:
                        self.list[i].update(item)
                    except (ValueError, TypeError):
                        # fallback: if update fails for any reason, replace the entry
                        self.list[i] = item
                #c.log(f"[CM Debug @ 1482 in episodes.py] list[i] = {self.list[i]}")

            meta = {
                'imdb': show_imdb, 'tmdb': show_tmdb, 'tvdb': '0', 'lang': self.lang,
                'user': self.user, 'resume_point': resume_point, 'item': item
            }
            self.meta.append(meta)
        except Exception as e:
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1477 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1477 in episodes.py]Exception raised. Error = {e}')

    # ...existing code...

    def super_info(self, i):
        """
        Populate an entry in self.list (index i) with enriched TMDB/episode metadata.
        Simplified by delegating to helper functions for clarity and speed.
        """
        try:
            item = self.list[i]
            is_episode = 'showimdb' in item

            # Step 1: Resolve and validate IDs
            ids = self._resolve_ids(item, is_episode)
            if not ids:
                return  # Skip if IDs can't be resolved

            show_imdb, show_tmdb, show_tvdb, show_trakt = ids

            # Step 2: Fetch TMDB data
            show_item, episode_item = self._fetch_tmdb_data(show_tmdb, item['season'], item['episode'])
            if not episode_item:
                return  # Skip if episode data unavailable

            # Step 3: Extract metadata
            metadata = self._extract_metadata(show_item, episode_item, item, show_imdb, show_tmdb, show_tvdb, show_trakt, is_episode)

            # Step 4: Handle artwork
            artwork = self._handle_artwork(show_tvdb, show_tmdb)
            metadata.update(artwork)

            # Step 5: Build and update the item
            enriched_item = self._build_enriched_item(metadata, item)
            self._update_list_entry(i, enriched_item)

            # Step 6: Append to meta cache
            self._append_meta(enriched_item, show_imdb, show_tmdb, show_tvdb, item.get('resume_point', '0.0'))

        except Exception as e:
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ super_info] Traceback: {failure}')
            c.log(f'[CM Debug @ super_info] Exception: {e}')

    def _resolve_ids(self, item, is_episode):
        """Resolve and validate IMDB/TMDB/TVDB/TRAKT IDs, fetching missing ones from TMDB."""
        try:
            if is_episode:
                show_imdb = item.get('showimdb', '0')
                show_tmdb = item.get('showtmdb', '0')
                show_tvdb = item.get('showtvdb', '0')
                show_trakt = item.get('showtrakt', '0')
            else:
                show_imdb = item.get('imdb', '0')
                show_tmdb = item.get('tmdb', '0')
                show_tvdb = item.get('tvdb', '0')
                show_trakt = item.get('trakt', '0')

            # Resolve missing TMDB from IMDB
            if show_tmdb == '0' and show_imdb != '0':
                try:
                    result = self.session.get(self.tmdb_by_imdb % show_imdb, timeout=15).json()
                    show_tmdb = str(result['tv_results'][0]['id']) if result.get('tv_results') else '0'
                except Exception:
                    pass

            # Resolve missing IMDB from TMDB
            if show_imdb == '0' and show_tmdb != '0':
                try:
                    result = self.session.get(self.tmdb_external_ids_by_tmdb % show_tmdb, timeout=15).json()
                    show_imdb = result.get('imdb_id', '0')
                except Exception:
                    pass

            # Resolve missing TVDB from TMDB
            if show_tvdb == '0' and show_tmdb != '0':
                try:
                    result = self.session.get(self.tmdb_external_ids_by_tmdb % show_tmdb, timeout=15).json()
                    show_tvdb = result.get('tvdb_id', '0')
                except Exception:
                    pass

            # Fail if no valid ID
            if show_tmdb in ('0', None) and show_imdb in ('0', None):
                return None

            return show_imdb, show_tmdb, show_tvdb, show_trakt
        except Exception as e:
            c.log(f'[CM Debug @ _resolve_ids] Exception: {e}')
            return None

    def _fetch_tmdb_data(self, show_tmdb, season, episode):
        """Fetch show and episode data from TMDB."""
        try:
            _id = show_tmdb
            en_url = self.tmdb_api_link % _id
            trans_url = f'{en_url},translations'
            url = en_url if self.lang == 'en' else trans_url
            show_item = self.session.get(url, timeout=15).json()

            episode_url = self.tmdb_episode_link % (show_tmdb, season, episode)
            episode_item = self.session.get(episode_url, timeout=15).json()

            return show_item, episode_item
        except Exception as e:
            c.log(f'[CM Debug @ _fetch_tmdb_data] Exception: {e}')
            return {}, {}

    def _extract_metadata(self, show_item, episode_item, item, show_imdb, show_tmdb, show_tvdb, show_trakt, is_episode):
        """Extract core metadata from TMDB responses."""
        try:
            show_title = item.get('tvshowtitle', '')
            title = item.get('title', '') or episode_item.get('name', '')
            season = item.get('season', '0')
            episode = item.get('episode', '0')
            year = item.get('year', '0')
            resume_point = item.get('resume_point', '0.0') or item.get('_resume_point', '0.0')

            # Normalize season/episode
            season = f"{int(season):01d}" if season and season != '0' else '0'
            episode = f"{int(episode):01d}" if episode and episode != '0' else '0'

            label = f"{show_title} : (S{season.zfill(2)}E{episode.zfill(2)})" if is_episode else show_title

            # Duration, status, premiered
            duration = episode_item.get('runtime') or episode_item.get('episode_run_time') or '45'
            status = show_item.get('status') or show_item.get('in_production', '0') or 'Ended'
            premiered = episode_item.get('air_date', '0')
            premiered = re.search(r'(\d{4}-\d{2}-\d{2})', premiered)
            premiered = premiered.group(1) if premiered else '0'

            # Genre, MPAA, rating, etc.
            genre = ' / '.join([d['name'] for d in show_item.get('genres', [])]) if show_item.get('genres') else '0'
            mpaa = show_item.get('mpaa', 'Not Rated')
            rating = str(show_item.get('vote_average', '0'))
            votes = str(show_item.get('vote_count', '0'))
            studio = next((c['name'] for c in show_item.get('production_companies', []) if c), '0')
            country = ' / '.join([c['name'] for c in show_item.get('production_countries', [])]) if show_item.get('production_countries') else '0'
            tagline = show_item.get('tagline', '0')

            # Trailer
            trailer = item.get('trailer', '')
            if not trailer:
                vids = episode_item.get('videos', {}).get('results', [])
                if vids:
                    trailer = vids[0].get('key', '')
                else:
                    show_vids = show_item.get('videos', {}).get('results', [])
                    if show_vids:
                        trailer = show_vids[0].get('key', '')

            # Plot
            in_widget = bool(c.is_widget_listing())
            plot = episode_item.get('overview') or show_item.get('overview', '0')
            plot = client.replaceHTMLCodes(plot) if plot else '0'

            # Crew
            crew = episode_item.get('credits', {}).get('crew', []) or show_item.get('crew', [])
            crew = [c for c in crew if c.get('job') in ('Director', 'Writer')]
            director = '/'.join([d['name'] for d in crew if d['job'] == 'Director']) or '0'
            writer = '/'.join([w['name'] for w in crew if d['job'] == 'Writer']) or '0'

            # Cast
            castwiththumb = []
            try:
                creds = episode_item.get('credits', {})
                cast = creds.get('cast', [])[:30] + creds.get('guest_stars', [])[:30]
                for person in cast:
                    profile_path = person.get('profile_path', '')
                    icon = self.tmdb_img_link % (c.tmdb_profilesize, profile_path) if profile_path else ''
                    castwiththumb.append({
                        'name': person.get('name', ''),
                        'role': person.get('character', ''),
                        'thumbnail': icon
                    })
            except Exception:
                pass

            # Unaired check
            unaired = ''
            if premiered != '0':
                premiered_num = int(re.sub('[^0-9]', '', premiered))
                today_num = int(re.sub('[^0-9]', '', str(self.today_date)))
                if premiered_num > today_num:
                    unaired = 'true'
                    if self.showunaired != 'true':
                        raise Exception('Unaired episode hidden')

            return {
                'title': title, 'season': season, 'episode': episode, 'year': year,
                'imdb': show_imdb, 'tmdb': show_tmdb, 'tvdb': show_tvdb, 'trakt': show_trakt,
                'status': status, 'studio': studio, 'premiered': premiered, 'genre': genre,
                'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa,
                'director': director, 'writer': writer, 'castwiththumb': castwiththumb,
                'plot': plot, 'tagline': tagline, 'country': country, 'trailer': trailer,
                'label': label, 'resume_point': resume_point, 'tvshowtitle': show_title,
                'unaired': unaired, 'in_widget': in_widget
            }
        except Exception as e:
            c.log(f'[CM Debug @ _extract_metadata] Exception: {e}')
            return {}

    def _handle_artwork(self, show_tvdb, show_tmdb):
        """Fetch artwork from fanart.tv and TMDB fallbacks."""
        try:
            poster = fanart = banner = landscape = clearlogo = clearart = '0'

            # Fanart.tv
            if show_tvdb and show_tvdb != '0':
                try:
                    tempart = fanart_tv.get_fanart_tv_art(tvdb=show_tvdb)
                    poster = tempart.get('poster', poster)
                    fanart = tempart.get('fanart', fanart)
                    banner = tempart.get('banner', banner)
                    landscape = tempart.get('landscape', landscape)
                    clearlogo = tempart.get('clearlogo', clearlogo)
                    clearart = tempart.get('clearart', clearart)
                except Exception:
                    pass

            # TMDB fallback
            if poster == '0':
                try:
                    p, f = self.get_tmdb_art(show_tmdb)
                    poster = p or poster
                    fanart = f or fanart
                except Exception:
                    pass

            # Default fallbacks
            if poster == '0':
                poster = c.addon_poster()
            if fanart == '0':
                fanart = c.addon_fanart()

            return {
                'poster': poster, 'fanart': fanart, 'banner': banner, 'landscape': landscape,
                'clearlogo': clearlogo, 'clearart': clearart, 'thumb': landscape or fanart
            }
        except Exception as e:
            c.log(f'[CM Debug @ _handle_artwork] Exception: {e}')
            return {'poster': '0', 'fanart': '0', 'banner': '0', 'landscape': '0', 'clearlogo': '0', 'clearart': '0', 'thumb': '0'}

    def _build_enriched_item(self, metadata, original_item):
        """Build the final enriched item dict."""
        try:
            return {
                'title': metadata['title'], 'originaltitle': metadata['title'], 'year': metadata['year'],
                'imdb': metadata['imdb'], 'tvdb': metadata['tvdb'], 'tmdb': metadata['tmdb'],
                'status': metadata['status'], 'studio': metadata['studio'], 'poster': metadata['poster'],
                'banner': metadata['banner'], 'fanart': metadata['fanart'], 'fanart2': metadata['fanart'],
                'landscape': metadata['landscape'], 'discart': metadata['clearart'], 'clearlogo': metadata['clearlogo'],
                'clearart': metadata['clearart'], 'premiered': metadata['premiered'], 'genre': metadata['genre'],
                'thumb': metadata['thumb'], 'in_widget': metadata['in_widget'], 'duration': metadata['duration'],
                'rating': metadata['rating'], 'votes': metadata['votes'], 'mpaa': metadata['mpaa'],
                'director': metadata['director'], 'writer': metadata['writer'], 'castwiththumb': metadata['castwiththumb'],
                'plot': metadata['plot'], 'tagline': metadata['tagline'], 'country': metadata['country'],
                'trailer': metadata['trailer'], 'label': metadata['label'], 'resume_point': metadata['resume_point'],
                'trakt': metadata['trakt'], '_last_watched': original_item.get('_last_watched', '0'),
                'tvshowtitle': metadata['tvshowtitle'], 'season': metadata['season'], 'episode': metadata['episode'],
                'action': original_item.get('action'), 'unaired': metadata['unaired'],
                '_sort_key': max(original_item.get('_last_watched', '0'), metadata['premiered'])
            }
        except Exception as e:
            c.log(f'[CM Debug @ _build_enriched_item] Exception: {e}')
            return {}

    def _update_list_entry(self, i, enriched_item):
        """Safely update self.list[i] with the enriched item."""
        try:
            if self.list and i < len(self.list):
                if self.list[i] is None or not isinstance(self.list[i], dict):
                    self.list[i] = enriched_item
                else:
                    self.list[i].update(enriched_item)
        except Exception as e:
            c.log(f'[CM Debug @ _update_list_entry] Exception: {e}')

    def _append_meta(self, enriched_item, show_imdb, show_tmdb, show_tvdb, resume_point):
        """Append to self.meta for caching."""
        try:
            meta_entry = {
                'imdb': show_imdb, 'tmdb': show_tmdb, 'tvdb': show_tvdb, 'lang': self.lang,
                'user': self.user, 'resume_point': resume_point, 'item': enriched_item
            }
            self.meta.append(meta_entry)
        except Exception as e:
            c.log(f'[CM Debug @ _append_meta] Exception: {e}')

    # ...existing code...



    def fanart_tv_art(self, tvdb):
        artmeta = True
        try:
            fanart_tv_headers = {'api-key': keys.fanart_key}
            if not self.fanart_tv_user == '':
                fanart_tv_headers.update({'client-key': self.fanart_tv_user})

            art = client.request(self.fanart_tv_art_link % tvdb,
                                 headers=fanart_tv_headers, timeout='15', error=True)
            try:
                art = json.loads(art)
            except Exception:
                artmeta = False
        except Exception:
            artmeta = False

        if artmeta == False:
            pass

        poster = fanart = banner = landscape = clearlogo = clearart = '0'

        try:
            _poster = art['tvposter']
            _poster = [x for x in _poster if x.get('lang') == self.lang][::-1] + [x for x in _poster if x.get('lang') == 'en'][::-1] + [x for x in _poster if x.get('lang') in ['00', '']][::-1]
            _poster = _poster[0]['url']
            if _poster:
                poster = _poster
        except Exception:
            pass

        try:
            _fanart = art['showbackground']
            _fanart = [x for x in _fanart if x.get('lang') == self.lang][::-1] + [x for x in _fanart if x.get('lang') == 'en'][::-1] + [x for x in _fanart if x.get('lang') in ['00', '']][::-1]
            _fanart = _fanart[0]['url']
            if _fanart:
                fanart = _fanart
        except Exception:
            pass

        try:
            _banner = art['tvbanner']
            _banner = [x for x in _banner if x.get('lang') == self.lang][::-1] + [x for x in _banner if x.get('lang') == 'en'][::-1] + [x for x in _banner if x.get('lang') in ['00', '']][::-1]
            _banner = _banner[0]['url']
            if _banner:
                banner = _banner
        except Exception:
            pass

        try:
            if 'hdtvlogo' in art:
                _clearlogo = art['hdtvlogo']
            else:
                _clearlogo = art['clearlogo']
            _clearlogo = [x for x in _clearlogo if x.get('lang') == self.lang][::-1] + [x for x in _clearlogo if x.get('lang') == 'en'][::-1] + [x for x in _clearlogo if x.get('lang') in ['00', '']][::-1]
            _clearlogo = _clearlogo[0]['url']
            if _clearlogo:
                clearlogo = _clearlogo
        except Exception:
            pass

        try:
            if 'hdclearart' in art:
                _clearart = art['hdclearart']
            else:
                _clearart = art['clearart']
            _clearart = [x for x in _clearart if x.get('lang') == self.lang][::-1] + [x for x in _clearart if x.get('lang') == 'en'][::-1] + [x for x in _clearart if x.get('lang') in ['00', '']][::-1]
            _clearart = _clearart[0]['url']
            if _clearart:
                clearart = _clearart
        except Exception:
            pass

        try:
            if 'tvthumb' in art:
                _landscape = art['tvthumb']
            else:
                _landscape = art['showbackground']
            _landscape = [x for x in _landscape if x.get('lang') == self.lang][::-1] + [x for x in _landscape if x.get('lang') == 'en'][::-1] + [x for x in _landscape if x.get('lang') in ['00', '']][::-1]
            _landscape = _landscape[0]['url']
            if _landscape:
                landscape = _landscape
        except Exception:
            pass

        return poster, fanart, banner, landscape, clearlogo, clearart

    def season_directory(self, items):
        try:
            if not items:
                control.idle()

            sysaddon = sys.argv[0]
            syshandle = int(sys.argv[1])

            trakt_credentials = trakt.get_trakt_credentials_info()

            # non-fatal indicators fetch; if it fails we leave indicators as None
            indicators = None
            with suppress(Exception):
                indicators = playcount.getSeasonIndicators(items[0].get('imdb'))  # ['1']

            watched_menu = control.lang(32068) if trakt.getTraktIndicatorsInfo() is True else control.lang(32066)
            unwatched_menu = control.lang(32069) if trakt.getTraktIndicatorsInfo() is True else control.lang(32067)
            queue_menu = control.lang(32065)
            trakt_manager_menu = control.lang(32515)
            label_menu = control.lang(32055)
            play_random = control.lang(32535)
            add_to_library = control.lang(32551)

            # cm
            color_list = [
                32589, 32590, 32591, 32592, 32593,
                32594, 32595, 32596, 32597, 32598
            ]
            color_nr = color_list[int(c.get_setting('unaired.identify'))]
            unaired_color = re.sub(r"\][\w\s]*\[", "][I]%s[/I][", control.lang(int(color_nr)))

            if unaired_color == '':
                unaired_color = '[COLOR red][I]%s[/I][/COLOR]'

            for i in items:
                try:
                    label = f"{label_menu} {i.get('season')}"

                    if i.get('unaired') == 'true':
                        label = unaired_color % label

                    systitle = sysname = quote_plus(i.get('tvshowtitle', ''))

                    # NOTE: str() made fanart a tuple in some cases; keep defensive handling
                    poster = str(i.get('poster')) if i.get('poster') and i.get('poster') != '0' else c.addon_poster()

                    fanart = '0'
                    if isinstance(i.get('fanart'), tuple):
                        fanart = i.get('fanart')[0]
                    if fanart == '0':
                        fanart = str(i.get('fanart')) if i.get('fanart') and i.get('fanart') != '0' else c.addon_fanart()

                    banner = str(i.get('banner')) if i.get('banner') and i.get('banner') != '0' else c.addon_banner()

                    # fix typo: check 'landscape' key correctly
                    landscape = (
                        str(i.get('landscape')) if i.get('landscape') and i.get('landscape') != '0'
                        else fanart
                    )

                    clearlogo = (
                        str(i.get('clearlogo')) if i.get('clearlogo') and i.get('clearlogo') != '0'
                        else c.addon_clearlogo()
                    )
                    clearart = (
                        str(i.get('clearart')) if i.get('clearart') and i.get('clearart') != '0'
                        else c.addon_clearart()
                    )
                    discart = (
                        str(i.get('discart')) if i.get('discart') and i.get('discart') != '0'
                        else c.addon_discart()
                    )
                    duration = i.get('duration') if i.get('duration') and i.get('duration') != '0' else '45'
                    status = i.get('status') if 'status' in i else '0'

                    episode_meta = {
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

                    sysmeta = quote_plus(json.dumps(episode_meta))

                    imdb = i.get('imdb')
                    tvdb = i.get('tvdb')
                    tmdb = i.get('tmdb')
                    year = i.get('year')
                    season = i.get('season')

                    meta = {k: v for k, v in i.items() if v != '0'}
                    meta['code'] = imdb
                    meta['imdbnumber'] = imdb
                    meta['imdb_id'] = imdb
                    meta['tvdb_id'] = tvdb
                    meta['mediatype'] = 'tvshow'
                    meta['trailer'] = f'{sysaddon}?action=trailer&name={sysname}&imdb={imdb}&tmdb={tmdb}'

                    if 'duration' not in i or i.get('duration') == '0':
                        meta['duration'] = '45'

                    if meta.get('duration') != '0':
                        meta['duration'] = str(int(meta['duration']))

                    meta['duration'] = str(int(meta['duration']) * 60)

                    meta['genre'] = cleangenre.lang(meta.get('genre', ''), self.lang)

                    # silenced extraction for season year (non-fatal)
                    with suppress(Exception):
                        season_year = i.get('premiered') if i.get('premiered') and i.get('premiered') != '0' else i.get('year')
                        season_year = re.findall(r'(\d{4})', season_year)[0]
                        meta['year'] = str(season_year)

                    # silenced overlay calculation; merge dict updates using |=
                    with suppress(Exception):
                        overlay = int(playcount.getSeasonOverlay(indicators, season))
                        if overlay == 7:
                            meta.update({'playcount': 1, 'overlay': 7})
                        else:
                            meta.update({'playcount': 0, 'overlay': 6})

                    base_random = (
                        f'{sysaddon}?action=random&rtype=episode'
                        f'&tvshowtitle={systitle}&year={year}&imdb={imdb}'
                        f'&tmdb={tmdb}&season={season}'
                    )
                    cm = [
                        (play_random, f'RunPlugin({base_random})'),
                        (queue_menu, f'RunPlugin({sysaddon}?action=queueItem)'),
                    ]
                    base_watched = (
                        f'{sysaddon}?action=seasonPlaycount&name={systitle}&imdb={imdb}'
                        f'&tmdb={tmdb}&season={season}&query=7'
                    )
                    cm.append((watched_menu, f'RunPlugin({base_watched})'))

                    base_unwatched = (
                        f'{sysaddon}?action=seasonPlaycount&name={systitle}&imdb={imdb}'
                        f'&tmdb={tmdb}&season={season}&query=6'
                    )
                    cm.append((unwatched_menu, f'RunPlugin({base_unwatched})'))

                    if trakt_credentials:
                        trakt_mgr_cmd = (
                            f'RunPlugin({sysaddon}?action=traktManager&name={sysname}'
                            f'&tmdb={tmdb}&content=tvshow)'
                        )
                        cm.append((trakt_manager_menu, trakt_mgr_cmd))

                    library_cmd = (
                        f'RunPlugin({sysaddon}?action=tvshowToLibrary&tvshowtitle={systitle}'
                        f'&year={year}&imdb={imdb}&tmdb={tmdb})'
                    )
                    cm.append((add_to_library, library_cmd))

                    try:
                        item = control.item(label=label, offscreen=True)
                    except Exception:
                        item = control.item(label=label)

                    art = {}
                    thumb = meta.get('thumb') or fanart
                    art.update({
                        'icon': poster,
                        'banner': banner,
                        'poster': poster,
                        'tvshow.poster': poster,
                        'season.poster': poster,
                        'landscape': landscape,
                        'clearlogo': clearlogo,
                        'thumb': thumb,
                        'clearart': clearart,
                        'discart': discart
                    })
                    item.setArt(art)

                    cast_with_thumb = i.get('castwiththumb')
                    if cast_with_thumb and cast_with_thumb != '0':
                        meta['cast'] = cast_with_thumb

                    meta['art'] = art
                    meta['studio'] = c.string_split_to_list(meta.get('studio')) if 'studio' in meta else []
                    meta['genre'] = c.string_split_to_list(meta.get('genre')) if 'genre' in meta else []
                    meta['director'] = c.string_split_to_list(meta.get('director')) if 'director' in meta else []
                    meta['writer'] = c.string_split_to_list(meta.get('writer')) if 'writer' in meta else []

                    # Pass listitem to the infotagger module and specify tag type
                    info_tag = ListItemInfoTag(item, 'video')
                    infolabels = control.tagdataClean(meta)

                    info_tag.set_info(infolabels)
                    unique_ids = {'imdb': imdb, 'tmdb': str(tmdb)}
                    info_tag.set_unique_ids(unique_ids)
                    info_tag.set_info(infolabels)

                    if 'cast' in meta:
                        info_tag.set_cast(meta.get('cast'))
                    elif 'castwiththumb' in meta:
                        info_tag.set_cast(meta.get('castwiththumb'))
                    else:
                        info_tag.set_cast([])

                    stream_info = {'codec': 'h264'}
                    info_tag.add_stream_info('video', stream_info)  # (stream_details)
                    item.addContextMenuItems(cm)

                    url = (
                        f'{sysaddon}?action=episodes&tvshowtitle={systitle}&year={year}'
                        f'&imdb={imdb}&tmdb={tmdb}&meta={sysmeta}&season={season}'
                    )
                    c.log(f"[CM Debug @ 589 in episodes.py] additem with label = {label}")

                    control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
                except Exception as e:
                    failure = traceback.format_exc()
                    c.log(f'[CM Debug @ 557 in episodes.py]Traceback:: {failure}')
                    c.log(f'[CM Debug @ 558 in episodes.py]Exception raised. Error = {e}')


            # setting property is non-fatal; suppress related exceptions
            with suppress(Exception):
                control.property(syshandle, 'showplot', items[0]['plot'])

            control.content(syshandle, 'tvshows')
            control.directory(syshandle, cacheToDisc=True)
            views.set_view('seasons', {'skin.estuary': 55, 'skin.confluence': 500})
        except Exception as e:
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 826 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 826 in episodes.py]Exception raised. Error = {e}')


class episodes:
    def __init__(self):

        self.list = []
        self.blist = []
        self.meta = []

        self.speedtest_start = time.perf_counter()
        self.session = requests.Session()
        self.show_fanart = c.get_setting('fanart') == 'true'
        self.trakt_link = 'https://api.trakt.tv'
        self.tvmaze_link = 'https://api.tvmaze.com'
        self.datetime = datetime.datetime.now(datetime.timezone.utc)
        self.systime = self.datetime.strftime('%Y%m%d%H%M%S%f')
        self.today_date = self.datetime.strftime('%Y-%m-%d')
        self.trakt_user = c.get_setting('trakt.user').strip()
        self.showunaired = c.get_setting('showunaired') or 'true'
        self.specials = c.get_setting('tv.specials') or 'true'
        self.lang = control.apiLanguage()['tmdb'] or 'en'
        self.hq_artwork = c.get_setting('hq.artwork') or 'false'

        self.fanart_tv_user = c.get_setting('fanart.tv.user')
        self.tmdb_user = c.get_setting('tm.personal_user') or c.get_setting('tm.user') or keys.tmdb_key
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

        # fanart.tv API endpoint for TV show artwork
        self.fanart_tv_art_link = 'https://webservice.fanart.tv/v3/tv/%s'

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
        self.ondeck_link = f'{self.trakt_link}/sync/playback/episodes?limit=40'
        self.traktlists_link = f'{self.trakt_link}/users/me/lists'
        self.traktlikedlists_link = f'{self.trakt_link}/users/likes/lists?limit=1000000'
        self.traktlist_link = f'{self.trakt_link}/users/%s/lists/%s/items'
        self.show_watched_link = f'{self.trakt_link}shows/%s/progress/collection?hidden=%s&specials=%s&count_specials=%s'

    def __del__(self):
        self.session.close()

    def get(
        self,
        tvshowtitle,
        year,
        imdb_id,
        tmdb_id,
        meta,
        season=None,
        episode=None,
        include_episodes=True,
        create_directory=True
    ):
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

        url = (
            f"tvshowtitle={tvshowtitle}"
            f"&year={year}"
            f"&imdb_id={imdb_id}"
            f"&tmdb_id={tmdb_id}"
            f"&season={season}"
            f"&episode={episode}"
        )
        c.log(f"[CM Debug @ 816 in episodes.py] url = {url}, includes_episodes = {include_episodes}")

        if include_episodes:
            c.log(f"[CM Debug @ 818 in episodes.py] url = {url}")
            # self.list = self.tmdb_list(tvshowtitle, year, imdb_id, tmdb_id, season, meta)
            # self.list = cache.get(self.tmdb_list, 1, tvshowtitle, year, imdb_id, tmdb_id, season, meta)
            self.list = cache.get(
                self.tmdb_list,
                0,
                tvshowtitle,
                year,
                imdb_id,
                tmdb_id,
                season,
                meta
            )

            c.log(f"[CM Debug @ 851 in episodes.py] season = {season}, episode = {episode}")

            if season is not None and episode is not None:
                try:
                    c.log(
                        "[CM Debug @ 853 in episodes.py] title = "
                        f"{tvshowtitle}, year = {year}, imdb_id = {imdb_id}, "
                        f"tmdb_id = {tmdb_id}, season = {season}, episode = {episode}"
                    )

                    idxs= [
                        x
                        for x, y in enumerate(self.list)
                        if (
                            y.get('season') == str(season)
                            and y.get('episode') == str(episode)
                        )
                    ]

                    c.log(f"[CM Debug @ 870 in episodes.py] idxs = {idxs}")
                    if idxs:
                        idx = idxs[-1]
                        c.log(f"[CM Debug @ 866 in episodes.py] idx = {idx}")
                        self.list = [y for x, y in enumerate(self.list) if x >= idx]
                        self.list = sorted(
                            self.list,
                            key=lambda k: (int(k['season']), int(k['episode']))
                        )
                except Exception as e:
                    failure = traceback.format_exc()
                    c.log(f'[CM Debug @ 876 in episodes.py]Traceback:: {failure}')
                    c.log(f'[CM Debug @ 876 in episodes.py]Exception raised. Error = {e}')


            if create_directory:
                self.episodeDirectory(self.list)
        else:
            self.list = self.tmdb_list(
                tvshowtitle,
                year,
                imdb_id,
                tmdb_id,
                season,
                lite=True
            )

        return self.list

    def calendar(self, url, idx = True):
        try:
            return self._get_calendar(url, idx)
        except (AttributeError, ValueError, RuntimeError, requests.RequestException, crew_errors.TraktResourceError) as e:
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 884 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 884 in episodes.py]Exception raised. Error = {e}')
            return []



    def _get_calendar(self, url, idx):
        sortorder = c.get_setting('prgr.sortorder')
        c.log(f"[CM Debug @ 853 in episodes.py] url = {url}")

        # Define constants for magic strings
        url_elements = ['tvProgress', 'tvmaze']

        for element in url_elements:
            if element in url:
                break
        else:
            if not hasattr(self, f'{url}_link'):
                # Handle attribute error
                raise AttributeError(f"Attribute '{url}_link' does not exist")
            url = getattr(self, f'{url}_link')
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
            # self.blist = cache.get(self.trakt_progress_list, 720, url)
            # self.list = cache.get(self.trakt_progress_list, 0, url)
            c.log(f"[CM Debug @ 928 in episodes.py] starting with progress_link: url = {url}")
            self.list = self.trakt_progress_list(url)
            c.log(f"[CM Debug @ 930 in episodes.py] returning from progress_link: length self.list = {len(self.list)}, value idx = {idx}, sortorder = {sortorder}")


        elif url == self.ondeck_link:
            self.blist = cache.get(self.trakt_episodes_list, 720, url, self.trakt_user, self.lang)
            self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)
            c.log(f"[CM Debug @ 983 in episodes.py] self.list = {self.list}")
            # Ensure self.list is a valid list before sorting
            if isinstance(self.list, list) and self.list:
                self.list = sorted(self.list, key=lambda k: k.get('premiered', ''), reverse=True)
            else:
                self.list = []

        elif url == self.mycalendar_link:
            self._handle_trakt_episode_lists(url)
        elif url == self.added_link:
            self._handle_trakt_episode_lists(url)
        elif url == self.trakthistory_link:
            self.list = cache.get(self.trakt_episodes_list, 1, url, self.trakt_user, self.lang)
            self.list = sorted(self.list, key=lambda k: int(k['watched_at']), reverse=True)

        elif self.trakt_link in url and '/users/' in url:
            #self.list = cache.get(self.trakt_list, 0, url, self.trakt_user)
            self.list = self.trakt_list(url, self.trakt_user)
            self.list = self.list[::-1]

        elif self.trakt_link in url:
            self.list = cache.get(self.trakt_list, 1, url, self.trakt_user)

        elif self.tvmaze_link in url:
            self.list = cache.get(self.tvmaze_list, 1, url, False)



        if idx:
            self.worker(0)

        if sortorder == '0':
            if self.list and isinstance(self.list, list):
                self.list = sorted(self.list, key=lambda k: k.get('premiered', ''), reverse=True)
            else:
                self.list = []
        elif self.list and isinstance(self.list, list):
            for i in self.list:
                c.log(f"[CM Debug @ 970 in episodes.py] all keys in i = {repr(list(i.keys()))}")
                # c.log(f"[CM Debug @ 937 in episodes.py] _sort_key = {i['_sort_key']}")
            self.list = sorted(self.list, key=lambda k: k.get('_sort_key', ''), reverse=True)
        else:
            c.log("[CM Debug @ 941 in episodes.py] self.list is empty")
            c.infoDialog(f'self.list is empty, url = {url}', 'Error', icon='main_classy.png', time=5000, sound=False)

        self.episodeDirectory(self.list)
        return self.list

    # TODO Rename this here and in `calendar`
    def _handle_trakt_episode_lists(self, url):
        #self.blist = cache.get(self.trakt_episodes_list, 720, url, self.trakt_user, self.lang)
        self.blist = self.trakt_episodes_list(url, self.trakt_user, self.lang)
        #self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)
        self.list = self.trakt_episodes_list(url, self.trakt_user, self.lang)
        self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)
        #except Exception as e:
            #c.log(f"[CM Debug @ 885 in episodes.py] Exception: {e}")

    def widget(self):

        if trakt.getTraktIndicatorsInfo() is True:
            setting = c.get_setting('tv.widget.alt')
        else:
            setting = c.get_setting('tv.widget')

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
                name_month_int = int(_date.strftime('%m')) #cm - month as padded with 0 string starting with 01 = january
                name_day_int = _date.isoweekday() #cm - weekday as decimal int starting where 1 = monday

                part_a = days_list[name_day_int-1]
                part_b = f"{month_day_int} {months_list[name_month_int-1]} {year_int}"
                name = (control.lang(32062) % (part_a, part_b))
                url = self.calendar_link % (self.datetime - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                # self.list.append({'name': name, 'url': url, 'image': 'calendar.png', 'action': 'calendar'})

                if self.list is not None:
                    self.list.append({'name': name, 'url': url, 'image': 'calendar.png', 'action': 'calendar'})
                else:
                    self.list = [{'name': name, 'url': url, 'image': 'calendar.png', 'action': 'calendar'}]
            except Exception as e:
                c.log(f"[cm debug in episodes.py @ 726] error={e}")

        if idx is True:
            self.addDirectory(self.list)
        return self.list
    def userlists(self):
        userlists = []

        # ensure trakt credentials and get activity; return empty list early if no credentials
        if not trakt.get_trakt_credentials_info():
            return []

        try:
            activity = trakt.getActivity()
        except Exception as e:
            c.log(f"[CM Debug @ 1110 in episodes.py] Failed to get trakt activity: {e}")
            activity = 0

        def fetch_lists(link):
            try:
                # choose cache timeout based on activity freshness
                if activity <= cache.timeout(self.trakt_user_list, link, self.trakt_user):
                    return cache.get(self.trakt_user_list, 720, link, self.trakt_user) or []
                return cache.get(self.trakt_user_list, 0, link, self.trakt_user) or []
            except Exception as e:
                c.log(f"[CM Debug @ 1112 in episodes.py] Failed to fetch lists for {link}: {e}")
                return []

        # fetch both user lists and liked lists
        userlists.extend(fetch_lists(self.traktlists_link))
        userlists.extend(fetch_lists(self.traktlikedlists_link))

        # normalize and annotate each entry in-place
        self.list = []
        for idx, itm in enumerate(userlists):
            c.log(f"[CM Debug @ 1114 in episodes.py] item = {itm} of type {type(itm)}")
            try:
                itm_dict = dict(itm)
            except Exception:
                # fallback: wrap scalar values
                itm_dict = {'name': itm} if isinstance(itm, str) else {}
            itm_dict['image'] = 'userlists.png'
            itm_dict['action'] = 'calendar'
            self.list.append(itm_dict)

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
            if return_type == 'int':
                return sum(1 for _ in value)
            if return_type == 'list':
                return list(value.items())
            return dict(enumerate(value)) if return_type == 'dict' else value

        if key == '':
            # return all keys as values
            return [convert_to(return_type, result[k]) for k in result.keys()]
        value = result.get(key, default_value)
        return convert_to(return_type, value)

    def get_media_info_old(self, result, key, return_type='', default_value='0'):

        def check_numeric(value):
            return int(value) if value.isnumeric() else len(value)

        def get_list_from_dict(d):
            # d is expected to be a dict or iterable; return list of (key, value) pairs
            if isinstance(d, dict) and len(d.keys()) > 0:
                return list(d.items())
            # treat as iterable/list and convert to (keyN, value) pairs
            list_from_dict = []
            for x, item in enumerate(d):
                k = f'key{x}'
                list_from_dict.append((k, item))
            return list_from_dict


        def get_dict_from_list(l):
            # if it's already a dict-like with keys return its items, otherwise enumerate the list into a dict
            if isinstance(l, dict) and len(l.keys()) > 0:
                return list(l.items())
            return dict(enumerate(l))


        def get_key_info(result, key):
            if key not in result or result[key] is None:
                result[key] = default_value

            val = result[key]

            if isinstance(val, list) and return_type == 'dict':
                return get_dict_from_list(val)
            if isinstance(val, dict) and return_type == 'list':
                # check if key exists in dict
                return get_list_from_dict(val)
            if isinstance(val, str):
                return check_numeric(val) if return_type == 'int' else val
            return val

        if key == '':
            #return all keys as values
            r = []
            for k in result.keys():
                r.append(get_key_info(result, k))
            return r
        return get_key_info(result, key)

    def trakt_list(self, url, user, return_art=True):
        # sourcery skip: use-contextlib-suppress
        # sourcery skip: use-contextlib-suppress
        """
        Fetch a trakt list and parse items into a simplified itemlist.
        Refactored to reduce nesting and number of locals; narrower exception handling.
        """
        c.log(f"[CM Debug @ 1031 in episodes.py] inside trakt_list: url = {url}")

        # replace date[n] placeholders with actual dates (one-per-match)
        for i in re.findall(r'date\[(\d+)\]', url):
            repl_date = (self.datetime - datetime.timedelta(days=int(i))).strftime('%Y-%m-%d')
            url = url.replace(f'date[{i}]', repl_date)
            c.log(f'[CM DEBUG in episodes.py @ 713] url={url}')

        q = dict(parse_qsl(urlsplit(url).query))
        q['extended'] = 'full'
        q = urlencode(q).replace('%2C', ',')
        u = url.replace(f'?{urlparse(url).query}', '') + '?' + q

        try:
            items = trakt.getTraktAsJson(u)
        except (ValueError, requests.RequestException, crew_errors.TraktResourceError) as e:
            c.log(f"[CM Debug @ 1039 in episodes.py] Error fetching trakt items: {e}")
            return []

        if not items:
            return []

        itemlist = []

        def _parse_item(item):
            """Parse a single trakt item into the expected dict or return None on parse errors."""
            try:
                c.log(
                    "[CM Debug @ 1052 in episodes.py] item is of "
                    f"type {type(item)}\n\nitem = {item}"
                )

                # defaults
                poster = fanart = banner = landscape = clearlogo = clearart = '0'
                resume_point = item.get('progress', 0.0)

                # last_watched extraction
                last_watched = '0'
                ep_info = item.get('episode') or {}
                show_info = item.get('show') or {}
                if isinstance(ep_info, dict) and 'updated_at' in ep_info:
                    last_watched = ep_info.get('updated_at', '0')
                elif isinstance(show_info, dict) and 'updated_at' in show_info:
                    last_watched = show_info.get('updated_at', '0')

                # use `or` instead of conditional expression
                tvshowtitle = show_info.get('title') or '0'

                title = ep_info.get('title') if isinstance(ep_info, dict) else None
                if not title:
                    raise ValueError("Missing episode title")
                title = client.replaceHTMLCodes(title)

                # normalize season/episode numbers
                season_raw = ep_info.get('season')
                season = f'{int(season_raw):01d}' if season_raw is not None else '0'
                if season == '0' and self.specials != 'true':
                    raise ValueError("Specials disabled")

                episode_raw = ep_info.get('number')
                episode = f'{int(episode_raw):01d}' if episode_raw is not None else '0'
                if episode == '0':
                    raise ValueError("Invalid episode number")

                # ids
                ids = show_info.get('ids') or {}
                imdb = ids.get('imdb') or '0'
                if imdb != '0':
                    imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))

                tvdb = ids.get('tvdb', '0') or '0'
                if tvdb != '0':
                    tvdb = re.sub('[^0-9]', '', str(tvdb))

                tmdb = ids.get('tmdb', '0')
                if tmdb == '0' or not tmdb:
                    raise ValueError("Missing TMDB id")
                tmdb = str(tmdb)

                year = re.sub('[^0-9]', '', str(show_info.get('year', '0')))

                premiered = ep_info.get('first_aired', None)
                # guard against None when using regex
                try:
                    m = re.search(r'(\d{4}-\d{2}-\d{2})', premiered or '')
                    premiered = m[1] if m else '0'
                except (TypeError, AttributeError):
                    premiered = '0'

                studio = show_info.get('network') or '0'

                genre_list = show_info.get('genres') or '0'
                if genre_list != '0':
                    genre_list = [g.title() for g in genre_list]
                    genre = ' / '.join(genre_list)
                else:
                    genre = '0'

                duration = str(show_info.get('runtime') or '0')
                rating = str(ep_info.get('rating') or '0')
                votes = str(ep_info.get('votes') or '0')
                if votes != '0':
                    try:
                        votes = str(format(int(votes), ',d'))
                    except (ValueError, TypeError):
                        pass

                mpaa = show_info.get('certification') or '0'

                plot = ep_info.get('overview') or show_info.get('overview') or '0'
                if plot != '0':
                    plot = client.replaceHTMLCodes(plot)

                paused_at = item.get('paused_at', '0') or '0'
                if paused_at != '0':
                    paused_at = re.sub('[^0-9]+', '', paused_at)

                watched_at = item.get('watched_at', '0') or '0'
                if watched_at != '0':
                    watched_at = re.sub('[^0-9]+', '', watched_at)

                # localized title/plot
                if self.lang != 'en' and imdb != '0':
                    try:
                        trans = trakt.getTVShowTranslation(
                            imdb, lang=self.lang, season=season, episode=episode, full=True
                        )
                        if trans:
                            title = trans.get('title') or title
                            plot = trans.get('overview') or plot
                    except (crew_errors.TraktResourceError, ValueError, TypeError, requests.RequestException) as _e:
                        c.log(f"[CM Debug @ 1112 in episodes.py] Translation lookup failed: {_e}")

                # collect artwork if fanart is enabled
                if c.get_setting('fanart') == 'true' and return_art:
                    if tvdb != '0':
                        try:
                            tempart = fanart_tv.get_fanart_tv_art(tvdb=tvdb)
                            c.log(f"[CM Debug @ 1092 in episodes.py] tempart = {tempart}")
                            if tempart:
                                poster = tempart.get('poster', poster)
                                fanart = tempart.get('fanart', fanart)
                                banner = tempart.get('banner', banner)
                                landscape = tempart.get('landscape', landscape)
                                clearlogo = tempart.get('clearlogo', clearlogo)
                                clearart = tempart.get('clearart', clearart)
                        except (requests.RequestException, KeyError, TypeError) as _e:
                            c.log(f"[CM Debug @ 1104 in episodes.py] fanart_tv lookup failed: {_e}")

                    if poster == '0':
                        p, f = self.get_tmdb_art(tmdb)
                        poster = p or poster
                        if f and f != '0':
                            fanart = f
                            landscape = f

                return {
                    'title': title,
                    'season': season,
                    'episode': episode,
                    'tvshowtitle': tvshowtitle,
                    'year': year,
                    'premiered': premiered,
                    'status': 'Continuing',
                    'studio': studio,
                    'genre': genre,
                    'duration': duration,
                    'rating': rating,
                    'votes': votes,
                    'mpaa': mpaa,
                    'plot': plot,
                    'imdb': imdb,
                    'tvdb': tvdb,
                    'tmdb': tmdb,
                    'poster': poster,
                    'thumb': landscape,
                    'fanart': fanart,
                    'banner': banner,
                    'landscape': landscape,
                    'clearlogo': clearlogo,
                    'clearart': clearart,
                    'paused_at': paused_at,
                    'watched_at': watched_at,
                    '_last_watched': last_watched,
                    'resume_point': resume_point,
                }
            except (KeyError, TypeError, ValueError) as e:
                c.log(f"[CM Debug @ 1148 in episodes.py] Skipping item due to error: {e}")
                return None
            except Exception as e:
                c.log(f"[CM Debug @ 1152 in episodes.py] Unexpected error: {e}")
                return None

        for itm in items:
            parsed = _parse_item(itm)
            if parsed:
                itemlist.append(parsed)

        itemlist = itemlist[::-1]
        return itemlist

    def get_show_watched_progress(self, trakt_id, hidden=False, specials=False, count_specials=False):
        url = self.show_watched_link % (trakt_id, hidden, specials, count_specials)
        return trakt.getTraktAsJson(url)

    def episodes_progress_list(self):
        try:
            progress = trakt.get_trakt_progress('episode')
            c.log(f"[CM Debug @ 1379 in episodes.py] progress = \n\n\n=====================================================\n\n\n{progress}\n\n\n============================================\n\n\n")

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

                # Ensure result is a dict before checking keys to avoid 'in' on None or list
                if isinstance(result, dict):
                    episodes_aired = result.get('aired', '0')
                    episodes_watched = result.get('completed', '0')
                    next_episode = result.get('next_episode', None)
                else:
                    episodes_aired = '0'
                    episodes_watched = '0'
                    next_episode = None

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
                    'episodes_aired': episodes_aired, 'episodes_watched': episodes_watched,

                    })

            return self.list


        except Exception as e:
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1140 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1140 in episodes.py]Exception raised. Error = {e}')
            pass

    def trakt_progress_list(self, url):
        try:
            url += '?extended=full'
            result = trakt.getTraktAsJson(url)
            # c.log(f"[CM Debug @ 1432 in episodes.py] result = {result}")
            items = []
        except Exception as e:
            c.log(f"Exception 1 in trakt_progress_list: {e}")
            return
        sortorder = c.get_setting('prgr.sortorder')


        if not result:
            c.log(f"[CM Debug @ 1441 in episodes.py] \n\n\nif not result:\n\n\n{result}\n\n\n return self.list \n\n\n{self.list}")
            return self.list


        def add_item(item):
            try:
                c.log(f"[CM Debug @ 1447 in episodes.py] inside add_item: item = {item.get('show').get('title')}")
                add = True
                num_1, num_2 = 0, 0
                for i in range(len(item['seasons'])):
                    if item['seasons'][i]['number'] > 0:
                        num_1 += len(item['seasons'][i]['episodes'])
                num_2 = int(item['show']['aired_episodes'])

                if num_1 >= num_2:
                    c.log(f"[CM Debug @ 1466 in episodes.py] INFO: {item['show']['title']}: All episodes watched")
                    #! do not add, all episodes watched
                    add = False

                #cm calc max season and max episode in that season
                season = max(x['number'] for x in item['seasons'])
                max_season = 1 if season == 1 else season - 1
                episode = max(
                    x['number']
                    for x in item['seasons'][max_season]['episodes']
                )


                # season = str(item['seasons'][-1]['number'])
                # episode = [x for x in item['seasons'][-1]['episodes'] if 'number' in x]
                # episode = sorted(episode, key=lambda x: x['number'])
                # episode = str(episode[-1]['number'])

                tvshowtitle = item['show']['title']  # item.get('show').get('title')
                year = item['show']['year']  # year returns int
                imdb = item['show']['ids']['imdb'] or '0'  # returns str
                tvdb = str(item['show']['ids']['tvdb']) or '0' # returns int
                tmdb = str(item['show']['ids']['tmdb']) or '0' # returns int
                slug = item['show']['ids']['slug']
                trakt_id = item['show']['ids']['trakt']

                first_aired = item['show']['first_aired']


                if not tvshowtitle:
                    raise ValueError('No Title')
                else:
                    tvshowtitle = client.replaceHTMLCodes(tvshowtitle)

                trailer = str(item.get('show').get('trailer')) or '0'

                if int(year) > int(self.datetime.strftime('%Y')):
                    #!year is bigger than current year, future show and we're in progress so continue
                    c.log(f"[CM Debug @ 1538 in episodes.py] continue, year = {year}")
                    # add = False


                studio = str(item['show']['network']) or '0'
                duration = item['show']['runtime'] or 45
                if duration == 1: #trakt return 1 in some cases ??
                    duration = 60

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


                if add:
                    return{
                            'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, 'trakt_id': trakt_id,
                            'tvshowtitle': tvshowtitle, 'year': year, 'studio': studio, 'duration': duration,
                            'first_aired': first_aired, 'mpaa': mpaa, 'status': status, 'genre': genre,
                            'snum': season, 'enum': episode, 'trailer': trailer, 'season': season,
                            'episode': episode, 'sortorder': sortorder, 'action': 'episodes',
                            '_last_watched': last_watched, 'slug': slug, 'country': country,
                            'network': network, 'tagline': tagline, 'plot': plot,
                            '_sort_key': first_aired or '0',
                        }
                c.log(f"[CM Debug @ 1522 in episodes.py] value of add = {add},  skipping item.")
                return None
            except Exception as e:
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 1532 in episodes.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 1532 in episodes.py]Exception raised. Error = {e}')







        c.log(f"[CM Debug @ 1529 in episodes.py] len items = {len(result)}")


        try:
            # result = []


            # if items:
            max_threads = c.get_max_threads(len(result))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
                #futures = {executor.submit(self.super_info, i): item for item in items}
                futures = {executor.submit(add_item, item): item for item in result}

                # c.log(f"[CM Debug @ 1929 in episodes.py] futures = {futures}")

                for future in concurrent.futures.as_completed(futures):
                    i = futures[future]
                    try:
                        result = future.result()
                        # c.log(f"\n\n\n[CM Debug @ 1554 in episodes.py]added item = {result}\n\n\n")
                        items.append(result)

                    except Exception as exc:
                        import traceback
                        failure = traceback.format_exc()
                        c.log(f"Error processing item {i}: {exc}")
                    # c.log(f"[CM Debug @ 1560 in episodes.py] result = {result}")
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1599 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1600 in episodes.py]Exception raised. Error = {e}')

        c.log(f"[CM Debug @ 1565 in episodes.py] items = {items}")


        try:
            # result = cache.get(trakt.getTraktAsJson, 1, self.hiddenprogress_link)
            hidden_result = trakt.getTraktAsJson(self.hiddenprogress_link)
            for i in hidden_result:
                c.log(f"[CM Debug @ 1580 in episodes.py] hidden_result item = {i}")
            #result = cache.get(trakt.getTraktAsJson, 1, self.hiddenprogress_link)
            #c.log(f"\n\n[CM Debug @ 1029 in episodes.py] result = {result}\n\n")

            if not hidden_result:
                raise crew_errors.TraktResourceError(f'Resource is empty with url == {self.hiddenprogress_link}')

            if isinstance(hidden_result, dict) and 'status_code' in hidden_result and int(hidden_result['status_code'][0]) == 34:
                raise crew_errors.TraktResourceError(f'Resource status_code == 34 with url == {self.hiddenprogress_link}')

            # cm - removing all dupes
            mylist = [str(i['show']['ids']['tmdb']) for i in hidden_result]
            c.log(f"[CM Debug @ 1583 in episodes.py] mylist = {mylist}")
            result = list(dict.fromkeys(mylist))

            filtered_items = []
            for item in items:
                c.log(f"[CM Debug @ 1598 in episodes.py]\n\n\n=================================\n\n\nitem = {item}\n\n\n=================================\n\n\n")
                if item['tmdb'] not in result:
                    filtered_items.append(item)
            # items = filtered_items

            # filtered_items = [item for item in items if item['tmdb'] not in result]
            c.log(f"[CM Debug @ 1587 in episodes.py] items = {filtered_items}")



        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1595 in episodes.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1596 in episodes.py]Exception raised. Error = {e}')

        c.log(f"[CM Debug @ 1597 in episodes.py] aantal items = {len(items)}")
        items = items[:100]

        self.list = items
        # c.log(f"[CM Debug @ 1601 in episodes.py] self.list = {items}")
        return items


    def get_tmdb_art(self, tmdb):
        """Gets the tmdb art for a given tmdb id."""
        try:
            url = self.tmdb_show_link % tmdb
            result = self.session.get(url, timeout=10).json()

            poster = self.tmdb_img_link % (c.tmdb_postersize, result['poster_path']) if 'poster_path' in result else '0'
            fanart = self.tmdb_img_link % (c.tmdb_fanartsize, result['background_path']) if 'background_path' in result else '0'

            return poster, fanart
        except Exception:
            return '0', '0'

    def trakt_episodes_list(self, url, user, lang):

        # ensure self.list is always a list to avoid NoneType errors when appending
        self.list = []

        items = self.trakt_list(url, user, return_art=True)

        c.log(f"[CM Debug @ 1596 in episodes.py] items = {items}")

        def items_list(i):

            tmdb, imdb, tvdb = i['tmdb'], i['imdb'], i['tvdb']

            if (not tmdb or tmdb == '0') and imdb != '0':
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
                elif int(re.sub('[^0-9]', '', premiered)) > int(re.sub('[^0-9]', '', self.today_date)):
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


                plot = item['overview'] or (i['plot'] or 'The Crew - No plot Available')
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
                    raise ValueError()


                if (
                    limit is True
                    and 'scripted' not in item['show']['type'].lower()
                ):
                    raise ValueError()
                tvshowtitle = item['_links']['show']['name']
                if not tvshowtitle:
                    tvshowtitle = ''
                else:
                    tvshowtitle = client.replaceHTMLCodes(tvshowtitle)

                title = item['name']
                if not title:
                    raise ValueError('no title')
                title = client.replaceHTMLCodes(title)

                season = item['season']
                season = re.sub('[^0-9]', '', '%02d' % int(season))
                if not season:
                    raise ValueError('no season')

                episode = item['number']
                episode = re.sub('[^0-9]', '', '%02d' % int(episode))
                if episode == '0':
                    raise ValueError('episode = 0')

                tvshowtitle = item['show']['name']
                if not tvshowtitle:
                    raise ValueError('no tvshowtitle')
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
                    raise ValueError('no tvdb')
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
                poster = poster2 if poster2 != '0' else poster_medium if poster1 == '0' else poster1

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

        return itemlist[::-1]

    def tmdb_list(self, tvshowtitle, year, imdb, tmdb, season, meta=None, lite=False):
        """Gets a list of episodes for a given tvshow. The list is in descending order."""

        if tmdb == '0' and imdb != '0':
            # try to resolve tmdb id from imdb id; non-fatal so suppress detailed errors
            with suppress(Exception):
                url = self.tmdb_by_imdb % imdb
                resp = self.session.get(url, timeout=16)
                resp.raise_for_status()
                result = resp.json()
                if tv_results := result.get('tv_results') or []:
                    _id = tv_results[0].get('id')
                    tmdb = str(_id) if _id else '0'

        if tmdb == '0':
            # fallback: search TMDB by title (prefer exact cleaned match, otherwise use first result)
            try:
                qtitle = quote(tvshowtitle)
                url = self.search_link % qtitle
                if year:
                    url = f'{url}&first_air_date_year={str(year)}'

                resp = self.session.get(url, timeout=16)
                resp.raise_for_status()
                result = resp.json()
                results = result.get('results') or []

                if not results:
                    raise ValueError('No search results')

                if self.list:
                    # compare against the first existing list item's title (defensive)
                    existing_title = ''
                    if isinstance(self.list, list) and len(self.list) > 0 and isinstance(self.list[0], dict):
                        existing_title = self.list[0].get('title', '')
                    match = next(
                        (
                            r_item
                            for r_item in results
                            if cleantitle.get(r_item.get('name'))
                            == cleantitle.get(existing_title)
                        ),
                        None,
                    )
                    if match is None:
                        match = results[0]
                    show = match
                else:
                    match = next((r for r in results if cleantitle.get(r.get('name')) == cleantitle.get(tvshowtitle)), None)
                    show = match if match is not None else results[0]

                tmdb_id = show.get('id')
                tmdb = str(tmdb_id) if tmdb_id else '0'
            except (requests.RequestException, ValueError, KeyError, IndexError) as e:
                c.log(f"[CM Debug @ tmdb search] failed to find tmdb id: {e}")
                tmdb = '0'


        try:
            if tmdb == '0':
                raise Exception()


            #!missing studio, genre, mpaa

            episodes_url = self.tmdb_season_link % (tmdb, season, self.lang)
            episodes_lite_url = self.tmdb_season_lite_link % (tmdb, season)

            url = episodes_url if lite is False else episodes_lite_url
            r = self.session.get(url, timeout=10)
            r.raise_for_status()
            r.encoding = 'utf-8'
            result = r.json()


            episode_list = result['episodes']


            if self.specials == 'false':
                episode_list = [e for e in episode_list if e['season_number'] != 0]
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
                c.log(f"[CM Debug @ 1858 in episodes.py] _meta = {_meta}")
                poster = _meta['poster'] if poster == '0' else poster
                fanart = _meta['fanart'] if fanart == '0' else fanart
                thumb = _meta['thumb'] if 'thumb' in _meta else '0'
                banner = _meta['banner']
                clearlogo = _meta['clearlogo']
                clearart = _meta['clearart']
                landscape = _meta['landscape'] or thumb
                duration = _meta['duration']
                status = _meta['status']

            for item in episode_list:
                try:
                    season = str(item['season_number'])
                    episode = str(item['episode_number'])

                    title = item.get('name') or f'Episode {episode}'
                    label = title

                    premiered = item.get('air_date') or '0'

                    unaired = ''
                    if not premiered or premiered == '0':
                        pass
                    elif int(re.sub('[^0-9]', '', premiered)) > int(re.sub('[^0-9]', '', self.today_date)):
                        unaired = 'true'
                        if self.showunaired != 'true':
                            raise Exception('hide unaired episode')

                    still_path = item.get('still_path') if 'still_path' in item else None
                    if still_path:
                        thumb = self.tmdb_img_link % (c.tmdb_stillsize, still_path)
                    else:
                        thumb = landscape or fanart or '0'



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

                    studio = ''
                    genre = ''
                    mpaa = ''

                    tempdict ={
                                    'title': title, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': '0',
                                    'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle,
                                    'year': year, 'premiered': premiered, 'status': status,
                                    'studio': studio, 'genre': genre, 'duration': duration,
                                    'rating': rating, 'votes': votes, 'mpaa': mpaa,
                                    'plot': episodeplot, 'director': director, 'writer': writer,
                                    'castwiththumb': castwiththumb, 'unaired': unaired,
                                    'poster': poster, 'fanart': fanart, 'banner': banner,
                                    'thumb': thumb, 'clearlogo': clear_logo, 'clearart': clear_art,
                                    'landscape': landscape
                                    }

                    self.list.append(tempdict)
                # except Exception:
                #     pass
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
                    raise ValueError()


                if (
                    limit is True
                    and 'scripted' not in item['show']['type'].lower()
                ):
                    raise ValueError()
                tvshowtitle = item['_links']['show']['name']
                if not tvshowtitle:
                    tvshowtitle = ''
                else:
                    tvshowtitle = client.replaceHTMLCodes(tvshowtitle)

                title = item['name']
                if not title:
                    raise ValueError('no title')
                title = client.replaceHTMLCodes(title)

                season = item['season']
                season = re.sub('[^0-9]', '', '%02d' % int(season))
                if not season:
                    raise ValueError('no season')

                episode = item['number']
                episode = re.sub('[^0-9]', '', '%02d' % int(episode))
                if episode == '0':
                    raise ValueError('episode = 0')

                tvshowtitle = item['show']['name']
                if not tvshowtitle:
                    raise ValueError('no tvshowtitle')
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
                    raise ValueError('no tvdb')
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
                poster = poster2 if poster2 != '0' else poster_medium if poster1 == '0' else poster1

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

        return itemlist[::-1]

    def tmdb_list(self, tvshowtitle, year, imdb, tmdb, season, meta=None, lite=False):
        """Gets a list of episodes for a given tvshow. The list is in descending order."""

        if tmdb == '0' and imdb != '0':
            # try to resolve tmdb id from imdb id; non-fatal so suppress detailed errors
            with suppress(Exception):
                url = self.tmdb_by_imdb % imdb
                resp = self.session.get(url, timeout=16)
                resp.raise_for_status()
                result = resp.json()
                if tv_results := result.get('tv_results') or []:
                    _id = tv_results[0].get('id')
                    tmdb = str(_id) if _id else '0'

        if tmdb == '0':
            # fallback: search TMDB by title (prefer exact cleaned match, otherwise use first result)
            try:
                qtitle = quote(tvshowtitle)
                url = self.search_link % qtitle
                if year:
                    url = f'{url}&first_air_date_year={str(year)}'

                resp = self.session.get(url, timeout=16)
                resp.raise_for_status()
                result = resp.json()
                results = result.get('results') or []

                if not results:
                    raise ValueError('No search results')

                if self.list:
                    # compare against the first existing list item's title (defensive)
                    existing_title = ''
                    if isinstance(self.list, list) and len(self.list) > 0 and isinstance(self.list[0], dict):
                        existing_title = self.list[0].get('title', '')
                    match = next(
                        (
                            r_item
                            for r_item in results
                            if cleantitle.get(r_item.get('name'))
                            == cleantitle.get(existing_title)
                        ),
                        None,
                    )
                    if match is None:
                        match = results[0]
                    show = match
                else:
                    match = next((r for r in results if cleantitle.get(r.get('name')) == cleantitle.get(tvshowtitle)), None)
                    show = match if match is not None else results[0]

                tmdb_id = show.get('id')
                tmdb = str(tmdb_id) if tmdb_id else '0'
            except (requests.RequestException, ValueError, KeyError, IndexError) as e:
                c.log(f"[CM Debug @ tmdb search] failed to find tmdb id: {e}")
                tmdb = '0'


        try:
            if tmdb == '0':
                raise Exception()


            #!missing studio, genre, mpaa

            episodes_url = self.tmdb_season_link % (tmdb, season, self.lang)
            episodes_lite_url = self.tmdb_season_lite_link % (tmdb, season)

            url = episodes_url if lite is False else episodes_lite_url
            r = self.session.get(url, timeout=10)
            r.raise_for_status()
            r.encoding = 'utf-8'
            result = r.json()


            episode_list = result['episodes']


            if self.specials == 'false':
                episode_list = [e for e in episode_list if e['season_number'] != 0]
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
                c.log(f"[CM Debug @ 1858 in episodes.py] _meta = {_meta}")
                poster = _meta['poster'] if poster == '0' else poster
                fanart = _meta['fanart'] if fanart == '0' else fanart
                thumb = _meta['thumb'] if 'thumb' in _meta else '0'
                banner = _meta['banner']
                clearlogo = _meta['clearlogo']
                clearart = _meta['clearart']
                landscape = _meta['landscape'] or thumb
                duration = _meta['duration']
                status = _meta['status']

            for item in episode_list:
                try:
                    season = str(item['season_number'])
                    episode = str(item['episode_number'])

                    title = item.get('name') or f'Episode {episode}'
                    label = title

                    premiered = item.get('air_date') or '0'

                    unaired = ''
                    if not premiered or premiered == '0':
                        pass
                    elif int(re.sub('[^0-9]', '', premiered)) > int(re.sub('[^0-9]', '', self.today_date)):
                        unaired = 'true'
                        if self.showunaired != 'true':
                            raise Exception('hide unaired episode')

                    still_path = item.get('still_path') if 'still_path' in item else None
                    if still_path:
                        thumb = self.tmdb_img_link % (c.tmdb_stillsize, still_path)
                    else:
                        thumb = landscape or fanart or '0'



                    rating = str(item['vote_average']) or '0'
                    votes = str(item['vote_count']) or '0'
                    episodeplot = item['overview'] or '0'


                    # if not self.lang == 'en' and episodeplot == '0':
                       # try:
                        # en_item = en_result.get('episodes', [])
                        # episodeplot = en_item['overview']
                        # episodeplot = c.ensure_str(episodeplot, errors='replace')
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

                    studio = ''
                    genre = ''
                    mpaa = ''

                    tempdict ={
                                    'title': title, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': '0',
                                    'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle,
                                    'year': year, 'premiered': premiered, 'status': status,
                                    'studio': studio, 'genre': genre, 'duration': duration,
                                    'rating': rating, 'votes': votes, 'mpaa': mpaa,
                                    'plot': episodeplot, 'director': director, 'writer': writer,
                                    'castwiththumb': castwiththumb, 'unaired': unaired,
                                    'poster': poster, 'fanart': fanart, 'banner': banner,
                                    'thumb': thumb, 'clearlogo': clear_logo, 'clearart': clear_art,
                                    'landscape': landscape
                                    }

                    self.list.append(tempdict)
                # except Exception:
                #     pass
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
                    raise ValueError()


                if (
                    limit is True
                    and 'scripted' not in item['show']['type'].lower()
                ):
                    raise ValueError()
                tvshowtitle = item['_links']['show']['name']
                if not tvshowtitle:
                    tvshowtitle = ''
                else:
                    tvshowtitle = client.replaceHTMLCodes(tvshowtitle)

                title = item['name']
                if not title:
                    raise ValueError('no title')
                title = client.replaceHTMLCodes(title)

                season = item['season']
                season = re.sub('[^0-9]', '', '%02d' % int(season))
                if not season:
                    raise ValueError('no season')

                episode = item['number']
                episode = re.sub('[^0-9]', '', '%02d' % int(episode))
                if episode == '0':
                    raise ValueError('episode = 0')

                tvshowtitle = item['show']['name']
                if not tvshowtitle:
                    raise ValueError('no tvshowtitle')
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
                    raise ValueError('no tvdb')
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
                poster = poster2 if poster2 != '0' else poster_medium if poster1 == '0' else poster1

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

        return itemlist[::-1]

    def tmdb_list(self, tvshowtitle, year, imdb, tmdb, season, meta=None, lite=False):

        if tmdb == '0' and not imdb == '0':
            try:
                url = self.tmdb_by_imdb % imdb
                result = self.session.get(url, timeout=16).json()
                id = result['tv_results'][0]
                tmdb = id['id']
                if not tmdb:
                    tmdb = '0'
                else:
                    tmdb = str(tmdb)
            except Exception:
                pass

        if tmdb == '0':
            try:
                url = self.search_link % (urllib.parse.quote(
                    tvshowtitle)) + '&first_air_date_year=' + year
                result = self.session.get(url, timeout=16).json()
                results = result['results']
                show = [r for r in results if cleantitle.get(
                    r.get('name')) == cleantitle.get(self.list[i]['title'])][0]
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

            if lite == False:
                url = episodes_url
            else:
                url = episodes_lite_url

            r = self.session.get(url, timeout=10)
            r.raise_for_status()
            r.encoding = 'utf-8'
            result = r.json()

            episodes = result['episodes']

            if self.specials == 'false':
                episodes = [e for e in episodes if not e['season_number'] == 0]
            if not episodes:
                raise Exception()

            r_cast = result.get('aggregate_credits', {}).get('cast', [])

            poster_path = result.get('poster_path')
            if poster_path:
                poster = self.tmdb_img_link.format('w500', poster_path)
            else:
                poster = '0'

            fanart = banner = clearlogo = clearart = landscape = duration = status = '0'
            if meta:
                _meta = json.loads(urllib.parse.unquote_plus(meta))
                poster, fanart, banner, clearlogo, clearart, landscape, duration, status = _meta['poster'], _meta['fanart'], _meta['banner'], _meta['clearlogo'], _meta['clearart'], _meta['landscape'], _meta['duration'], _meta['status']

            for item in episodes:
                try:
                    season = str(item['season_number'])

                    episode = str(item['episode_number'])

                    title = item.get('name')
                    if not title:
                        title = 'Episode %s' % episode

                    label = title

                    premiered = item.get('air_date')
                    if not premiered:
                        premiered = '0'

                    unaired = ''
                    if not premiered or premiered == '0':
                        pass
                    elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                        unaired = 'true'
                        if self.showunaired != 'true':
                            raise Exception()

                    still_path = item.get('still_path')
                    if still_path:
                        thumb = self.tmdb_img_link.format('w300', still_path)
                    else:
                        thumb = '0'

                    try:
                        rating = str(item['vote_average'])
                    except Exception:
                        rating = ''
                    if not rating:
                        rating = '0'

                    try:
                        votes = str(item['vote_count'])
                    except Exception:
                        votes = ''
                    if not votes:
                        votes = '0'

                    try:
                        episodeplot = item['overview']
                    except Exception:
                        episodeplot = ''
                    if not episodeplot:
                        episodeplot = '0'

                    # if not self.lang == 'en' and episodeplot == '0':
                       # try:
                        # en_item = en_result.get('episodes', [])
                        # episodeplot = en_item['overview']
                        # episodeplot = six.ensure_str(episodeplot)
                       # except Exception:
                        # episodeplot = ''
                       # if not episodeplot: episodeplot = '0'

                    try:
                        r_crew = item['crew']
                        director = [
                            d for d in r_crew if d['job'] == 'Director']
                        director = ', '.join([d['name'] for d in director])
                        writer = [w for w in r_crew if w['job'] == 'Writer']
                        writer = ', '.join([w['name'] for w in writer])
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
                            icon = self.tmdb_img_link % (
                                'w185', _icon) if _icon else ''
                            castwiththumb.append(
                                {'name': person['name'], 'role': person['roles'][0]['character'], 'thumbnail': icon})
                    except Exception:
                        pass
                    if not castwiththumb:
                        castwiththumb = '0'

                    self.list.append({'title': title, 'label': label, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered,
                                      'rating': rating, 'votes': votes, 'director': director, 'writer': writer, 'castwiththumb': castwiththumb, 'duration': duration,
                                      'status': status, 'plot': episodeplot, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': '0', 'unaired': unaired, 'thumb': thumb, 'poster': poster,
                                      'fanart': fanart, 'banner': banner, 'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape})
                except Exception:
                    pass

            return self.list
        except Exception:
            return

    def fanart_tv_art(self, tvdb):
        artmeta = True
        try:
            fanart_tv_headers = {'api-key': keys.fanart_key}
            if not self.fanart_tv_user == '':
                fanart_tv_headers.update({'client-key': self.fanart_tv_user})

            art = client.request(self.fanart_tv_art_link % tvdb,
                                 headers=fanart_tv_headers, timeout='15', error=True)
            try:
                art = json.loads(art)
            except Exception:
                artmeta = False
        except Exception:
            artmeta = False

        if artmeta == False:
            pass

        poster = fanart = banner = landscape = clearlogo = clearart = '0'

        try:
            _poster = art['tvposter']
            _poster = [x for x in _poster if x.get('lang') == self.lang][::-1] + [x for x in _poster if x.get('lang') == 'en'][::-1] + [x for x in _poster if x.get('lang') in ['00', '']][::-1]
            _poster = _poster[0]['url']
            if _poster:
                poster = _poster
        except Exception:
            pass

        try:
            _fanart = art['showbackground']
            _fanart = [x for x in _fanart if x.get('lang') == self.lang][::-1] + [x for x in _fanart if x.get('lang') == 'en'][::-1] + [x for x in _fanart if x.get('lang') in ['00', '']][::-1]
            _fanart = _fanart[0]['url']
            if _fanart:
                fanart = _fanart
        except Exception:
            pass

        try:
            _banner = art['tvbanner']
            _banner = [x for x in _banner if x.get('lang') == self.lang][::-1] + [x for x in _banner if x.get('lang') == 'en'][::-1] + [x for x in _banner if x.get('lang') in ['00', '']][::-1]
            _banner = _banner[0]['url']
            if _banner:
                banner = _banner
        except Exception:
            pass

        try:
            if 'hdtvlogo' in art:
                _clearlogo = art['hdtvlogo']
            else:
                _clearlogo = art['clearlogo']
            _clearlogo = [x for x in _clearlogo if x.get('lang') == self.lang][::-1] + [x for x in _clearlogo if x.get('lang') == 'en'][::-1] + [x for x in _clearlogo if x.get('lang') in ['00', '']][::-1]
            _clearlogo = _clearlogo[0]['url']
            if _clearlogo:
                clearlogo = _clearlogo
        except Exception:
            pass

        try:
            if 'hdclearart' in art:
                _clearart = art['hdclearart']
            else:
                _clearart = art['clearart']
            _clearart = [x for x in _clearart if x.get('lang') == self.lang][::-1] + [x for x in _clearart if x.get('lang') == 'en'][::-1] + [x for x in _clearart if x.get('lang') in ['00', '']][::-1]
            _clearart = _clearart[0]['url']
            if _clearart:
                clearart = _clearart
        except Exception:
            pass

        try:
            if 'tvthumb' in art:
                _landscape = art['tvthumb']
            else:
                _landscape = art['showbackground']
            _landscape = [x for x in _landscape if x.get('lang') == self.lang][::-1] + [x for x in _landscape if x.get('lang') == 'en'][::-1] + [x for x in _landscape if x.get('lang') in ['00', '']][::-1]
            _landscape = _landscape[0]['url']
            if _landscape:
                landscape = _landscape
        except Exception:
            pass

        return poster, fanart, banner, landscape, clearlogo, clearart

    def episodeDirectory(self, items):
        if items == None or len(items) == 0:
            return

        # cm setting up
        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])

        addonPoster, addonBanner = control.addonPoster(), control.addonBanner()
        addonFanart, settingFanart = control.addonFanart(), control.setting('fanart')
        addonClearlogo, addonClearart = control.addonClearlogo(), control.addonClearart()
        addonDiscart = control.addonDiscart()

        traktCredentials = trakt.getTraktCredentialsInfo()

        #KodiVersion = control.getKodiVersion()

        isPlayable = True if not 'plugin' in control.infoLabel('Container.PluginName') else False

        indicators = playcount.getTVShowIndicators(refresh=True)

        try:
            multi = [i['tvshowtitle'] for i in items]
        except Exception:
            multi = []
        multi = len([x for y, x in enumerate(multi) if x not in multi[:y]])
        multi = True if multi > 1 else False

        try:
            sysaction = items[0]['action']
        except Exception:
            sysaction = ''

        isFolder = False if not sysaction == 'episodes' else True

        playbackMenu = control.lang(32063) if control.setting('hosts.mode') == '2' else control.lang(32064)
        watchedMenu = control.lang(32068) if traktCredentials == True else control.lang(32066)
        unwatchedMenu = control.lang(32069) if traktCredentials == True else control.lang(32067)
        queueMenu = control.lang(32065)
        traktManagerMenu = control.lang(32515)
        addToLibrary = control.lang(32551)
        infoMenu = control.lang(32101)
        clearProviders = control.lang(70014)
        tvshowBrowserMenu = control.lang(32071)

        # changed by cm -  22-4-2021
        colorlist = [32589, 32590, 32591, 32592, 32593, 32594, 32595, 32596, 32597, 32598]
        colornr = colorlist[int(control.setting('unaired.identify'))]
        unairedcolor = re.sub("\][\w\s]*\[", "][I]%s[/I][", control.lang(int(colornr)))

        # fixed by cm -  28-4-2021
        if unairedcolor == '':
            unairedcolor = '[COLOR red][I]%s[/I][/COLOR]'

        for i in items:
            try:
                if not 'label' in i:
                    i['label'] = i['title']

                if i['label'] == '0':
                    label = '%sx%02d : %s %s' % (i['season'], int(
                        i['episode']), 'Episode', i['episode'])
                else:
                    label = '(%sx%02d) : %s' % (
                        i['season'], int(i['episode']), i['label'])

                if multi == True:
                    label = '%s %s' % (i['tvshowtitle'], label)

                try:
                    if i['unaired'] == 'true':
                        label = unairedcolor % label

                except Exception:
                    pass

                imdb, tvdb, tmdb, year, season, episode = i['imdb'], i['tvdb'], i['tmdb'], i['year'], i['season'], i['episode']

                poster = i['poster'] if 'poster' in i and not i['poster'] == '0' else addonPoster
                fanart = i['fanart'] if 'fanart' in i and not i['fanart'] == '0' else addonFanart
                banner = i['banner'] if 'banner' in i and not i['banner'] == '0' else addonBanner
                landscape = i['landscape'] if 'landscape' in i and not i['landscape'] == '0' else fanart
                clearlogo = i['clearlogo'] if 'clearlogo' in i and not i['clearlogo'] == '0' else addonClearlogo
                clearart = i['clearart'] if 'clearart' in i and not i['clearart'] == '0' else addonClearart
                discart = i['discart'] if 'discart' in i and not i['discart'] == '0' else addonDiscart

                duration = i['duration'] if 'duration' in i and not i['duration'] == '0' else '45'
                status = i['status'] if 'status' in i else '0'

                s_meta = {'poster': poster, 'fanart': fanart, 'banner': banner, 'clearlogo': clearlogo, 'clearart': clearart,
                          'discart': discart, 'landscape': landscape, 'duration': duration, 'status': status}

                seasons_meta = quote_plus(json.dumps(s_meta))

                systitle = quote_plus(i['title'])
                systvshowtitle = quote_plus(i['tvshowtitle'])
                syspremiered = quote_plus(i['premiered'])

                systrailer = quote_plus(i['trailer']) if 'trailer' in i else '0'

                sysyear = re.findall('(\d{4})', i['premiered'])[0]

                meta = dict((k, v) for k, v in list(i.items()) if not v == '0')

                if i.get('season') == '0':
                    meta.update({'season': '0'})
                meta.update({'mediatype': 'episode'})
                meta.update({'code': tmdb})
                meta.update({'imdb_id': imdb})
                meta.update({'tmdb_id': tmdb})
                if systrailer == '0':
                    meta.update({'trailer': '%s?action=trailer&name=%s&imdb=%s&tmdb=%s&season=%s&episode=%s' % (
                        sysaddon, systvshowtitle, imdb, tmdb, season, episode)})
                else:
                    meta.update({'trailer': '%s?action=trailer&name=%s&url=%s&imdb=%s&tmdb=%s' % (
                        sysaddon, systvshowtitle, systrailer, imdb, tmdb)})

                try:
                    meta.update({'duration': str(int(duration) * 60)})
                except Exception:
                    pass

                try:
                    meta.update( {'genre': cleangenre.lang(meta['genre'], self.lang)})
                except Exception:
                    pass

                try:
                    meta.update( {'year': re.findall('(\d{4})', i['premiered'])[0]})
                except Exception:
                    pass

                try:
                    meta.update({'title': i['label']})
                except Exception:
                    pass

                try:
                    meta.update({'tvshowyear': i['year']})
                except Exception:
                    pass

                meta.update({'poster': poster, 'fanart': fanart, 'banner': banner, 'landscape': landscape, 'clearlogo': clearlogo, 'clearart': clearart, 'discart': discart})
                sysmeta = quote_plus(json.dumps(meta))

                url = '%s?action=play1&title=%s&year=%s&imdb=%s&tmdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&t=%s' % (sysaddon, systitle, year, imdb, tmdb, season, episode, systvshowtitle, syspremiered, sysmeta, self.systime)
                sysurl = quote_plus(url)

                if isFolder == True:
                    url = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&meta=%s&season=%s&episode=%s' % (sysaddon, systvshowtitle, year, imdb, tmdb, seasons_meta, season, episode)

                cm = []
                cm.append(
                    (queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                if multi == True:
                    cm.append((tvshowBrowserMenu, 'Container.Update(%s?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&meta=%s,return)' % (sysaddon, systvshowtitle, year, imdb, tmdb, seasons_meta)))

                try:
                    overlay = int(playcount.getEpisodeOverlay(
                        indicators, imdb, tmdb, season, episode))
                    if overlay == 7:
                        cm.append((unwatchedMenu, 'RunPlugin(%s?action=episodePlaycount&imdb=%s&tmdb=%s&season=%s&episode=%s&query=6)' % (sysaddon, imdb, tmdb, season, episode)))
                        meta.update({'playcount': 1, 'overlay': 7})
                    else:
                        cm.append((watchedMenu, 'RunPlugin(%s?action=episodePlaycount&imdb=%s&tmdb=%s&season=%s&episode=%s&query=7)' % (sysaddon, imdb, tmdb, season, episode)))
                        meta.update({'playcount': 0, 'overlay': 6})
                except Exception:
                    pass

                if traktCredentials == True:
                    cm.append((traktManagerMenu, 'RunPlugin(%s?action=traktManager&name=%s&tmdb=%s&content=tvshow)' % (sysaddon, systvshowtitle, tmdb)))

                if isFolder == False:
                    cm.append((playbackMenu, 'RunPlugin(%s?action=alterSources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))

                cm.append((addToLibrary, 'RunPlugin(%s?action=tvshowToLibrary&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, systvshowtitle, year, imdb, tmdb)))

                cm.append(
                    (clearProviders, 'RunPlugin(%s?action=clearSources)' % sysaddon))

                try:
                    item = control.item(label=label, offscreen=True)
                except Exception:
                    item = control.item(label=label)

                art = {}

                thumb = meta.get('thumb', '') or fanart

                art.update({'icon': thumb, 'thumb': thumb, 'banner': banner, 'poster': thumb, 'tvshow.poster': poster,
                           'season.poster': poster, 'landscape': landscape, 'clearlogo': clearlogo, 'clearart': clearart, 'discart': discart})

                if settingFanart == 'true':
                    art.update({'fanart': fanart})

                castwiththumb = i.get('castwiththumb')
                if castwiththumb and not castwiththumb == '0':
                    item.setCast(castwiththumb)
                    # meta.update({'cast': castwiththumb})

                item.setArt(art)
                item.addContextMenuItems(cm)
                if isPlayable:
                    item.setProperty('IsPlayable', 'true')

                offset = bookmarks.get('episode', imdb, season, episode, True)
                if float(offset) > 120:
                    percentPlayed = int(
                        float(offset) / float(meta['duration']) * 100)
                    item.setProperty('resumetime', str(offset))
                    item.setProperty('percentplayed', str(percentPlayed))

                item.setProperty('imdb_id', imdb)
                item.setProperty('tmdb_id', tmdb)
                item.setProperty('tvdb_id', tvdb)
                try:
                    item.setUniqueIDs({'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb})
                except Exception:
                    pass

                item.setInfo(type='Video', infoLabels=control.metadataClean(meta))

                video_streaminfo = {'codec': 'h264'}
                item.addStreamInfo('video', video_streaminfo)

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)
            except Exception:
                pass

        control.content(syshandle, 'episodes')
        control.directory(syshandle, cacheToDisc=True)

    def addDirectory(self, items, queue=False):
        if items == None or len(items) == 0:
            control.idle()
            sys.exit()

        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])
        addonFanart, addonThumb, artPath = control.addonFanart(), control.addonThumb(), control.artPath()
        queueMenu = control.lang(32065)

        for i in items:
            try:
                name = i['name']

                if i['image'].startswith('http'):
                    thumb = i['image']
                elif not artPath == None:
                    thumb = os.path.join(artPath, i['image'])
                else:
                    thumb = addonThumb

                url = f"{sysaddon}?action={i['action']}"
                try:
                    url += f"&url={quote_plus(i['url'])}"
                except Exception:
                    pass

                cm = []

                if queue == True:
                    cm.append(
                        (queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                try:
                    item = control.item(label=name, offscreen=True)
                except Exception:
                    item = control.item(label=name)

                item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': addonFanart})

                item.addContextMenuItems(cm)

                control.addItem(handle=syshandle, url=url,listitem=item, isFolder=True)
            except Exception:
                pass

        control.content(syshandle, 'addons')
        control.directory(syshandle, cacheToDisc=True)
