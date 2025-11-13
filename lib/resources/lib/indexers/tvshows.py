# -*- coding: utf-8 -*-
# pylint: disable=W0703
'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file tvshows.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

import os
import sys
import re
import datetime
import json
import concurrent.futures

import sqlite3 as database
from sqlite3 import OperationalError
from urllib.parse import quote, quote_plus, parse_qsl, urlparse, urlsplit, urlencode

import requests

from ..modules import trakt
from ..modules import keys
from ..modules import cleantitle
from ..modules import cleangenre
from ..modules import control
from ..modules import client
from ..modules import cache
from ..modules import metacache
from ..modules import playcount
from ..modules import workers
from ..modules import utils
from ..modules import fanart as fanart_tv
from ..indexers import navigator
from ..modules.listitem import ListItemInfoTag
from ..modules.crewruntime import c



# safely parse query params from sys.argv[2] (ensure index exists)
# params = dict(parse_qsl(sys.argv[2].replace('?',''))) if len(sys.argv) > 1 else {}
query = sys.argv[2] if len(sys.argv) > 2 else ''
params = dict(parse_qsl(query.lstrip('?')))
action = params.get('action')


class TVshows:
    '''
    tvshows class
    '''
    def __init__(self):
        self.list = []

        self.session = requests.Session()
        #self.artwork = artwork.artwork()

        self.imdb_link = 'https://www.imdb.com'
        self.trakt_link = 'https://api.trakt.tv'
        self.tvmaze_link = 'https://www.tvmaze.com'
        self.tmdb_link = 'https://api.themoviedb.org/3'
        self.logo_link = 'https://i.imgur.com/'
        self.logo_link = 'https://image.tmdb.org/t/p/original'
        self.tvdb_key = control.setting('tvdb.user')
        if self.tvdb_key == '' or self.tvdb_key is None:
            self.tvdb_key = keys.tvdb_key

        #cm - correct and current date & time of the user, not utcnow with timedelta-5
        self.datetime = datetime.datetime.now()
        self.year = self.datetime.strftime('%Y')
        self.count = int(control.setting('page.item.limit'))
        self.items_per_page = str(control.setting('items.per.page')) or '20'
        self.trailer_source = control.setting('trailer.source') or '2'
        self.country = control.setting('official.country') or 'US'
        self.lang = control.apiLanguage()['tmdb'] or 'en'


        self.today_date = self.datetime.strftime('%Y-%m-%d')
        self.specials = control.setting('tv.specials') or 'true'
        self.showunaired = control.setting('showunaired') or 'true'
        self.hq_artwork = control.setting('hq.artwork') or 'true'

        ####cm##
        # users & keys
        #
        self.fanart_tv_user = control.setting('fanart.tv.user')
        self.trakt_user = control.setting('trakt.user').strip()
        self.imdb_user = control.setting('imdb.user').replace('ur', '')
        self.fanart_tv_user = control.setting('fanart.tv.user')
        self.tmdb_user = control.setting('tm.personal_user') or control.setting('tm.user') or keys.tmdb_key
        self.user = self.tmdb_user
        self.trakt_user = control.setting('trakt.user').strip()
        self.imdb_user = control.setting('imdb.user').replace('ur', '')

        ####cm##
        # headers
        #
        self.fanart_tv_headers = {'api-key': keys.fanart_key}
        if not self.fanart_tv_user == '':
            self.fanart_tv_headers.update({'client-key': self.fanart_tv_user})

        self.items_per_page = str(control.setting('items.per.page')) or '20'
        self.trailer_source = control.setting('trailer.source') or '2'
        self.country = control.setting('official.country') or 'US'
        self.lang = control.apiLanguage()['tmdb'] or 'en'

        self.search_link = f'{self.trakt_link}/search/show?limit=20&page=1&query=%s'
        self.tvmaze_info_link = 'https://api.tvmaze.com/shows/%s'
        self.fanart_tv_art_link = 'http://webservice.fanart.tv/v3/tv/%s'
        self.fanart_tv_level_link = 'http://webservice.fanart.tv/v3/level'

        self.tmdb_link = 'https://api.themoviedb.org/3'
        self.tmdb_img_link = 'https://image.tmdb.org/t/p/%s%s'
        self.tmdb_img_prelink = 'https://image.tmdb.org/t/p/{}{}'

        ####cm##
        #trakt
        #
        self.trending_link = f'{self.trakt_link}/shows/trending?limit=40&page=1'
        self.traktlists_link = f'{self.trakt_link}/users/me/lists'
        self.traktlikedlists_link = f'{self.trakt_link}/users/likes/lists?limit=1000000'
        self.traktlist_link = f'{self.trakt_link}/users/%s/lists/%s/items'
        self.traktcollection_link = f'{self.trakt_link}/users/me/collection/shows'
        self.traktwatchlist_link = f'{self.trakt_link}/users/me/watchlist/shows'
        self.traktfeatured_link = f'{self.trakt_link}/recommendations/shows?limit=40'
        self.related_link = f'{self.trakt_link}/shows/%s/related'

        ####cm##
        # tmdb status tvshow
        # ['Returning Series', 'Planned', 'In Production', 'Ended', 'Canceled', 'Pilot']
        #
        self.person_link = f'{self.tmdb_link}/search/person?api_key={self.tmdb_user}&query=%s&include_adult=false&language=en-US&page=1'
        self.persons_link = f'{self.tmdb_link}/person/%s?api_key={self.tmdb_user}&?language=en-US'
        self.personlist_link = f'{self.tmdb_link}/trending/person/day?api_key={self.tmdb_user}&language=en-US'
        self.person_show_link = f'{self.tmdb_link}/person/%s/tv_credits?api_key={self.tmdb_user}&language=en-US'
        self.premiere_link = f'{self.tmdb_link}/discover/tv?api_key={self.tmdb_user}&include_adult=false&first_air_date.gte=date[60]&include_null_first_air_dates=false&language=en-US&sort_by=popularity.desc&with_origin_country=US|UK|AU&with_original_language=en&page=1'
        self.airing_link = f'{self.tmdb_link}/discover/tv?api_key={self.tmdb_user}&language=en-US&with_origin_country=US|UK|AU&with_original_language=en&sort_by=popularity.desc&air_date.lte=date[0]&air_date.gte=date[1]&page=1'
        self.popular_link = f'{self.tmdb_link}/discover/tv?api_key={self.tmdb_user}&include_adult=false&include_null_first_air_dates=false&sort_by=popularity.desc&vote_count.gte=1000&with_origin_country=US|UK|AU&air_date.gte=date[1]&language=en-US&with_original_language=en&page=1'
        self.genre_link = f'{self.tmdb_link}/discover/tv?api_key={self.tmdb_user}&include_adult=false&include_null_first_air_dates=false&language=en-US&sort_by=popularity.desc&with_origin_country=US|UK|AU&with_original_language=en&with_genres=%s&page=1'
        self.rating_link = f'{self.tmdb_link}/discover/tv?api_key={self.tmdb_user}&include_adult=false&include_null_first_air_dates=false&language=en-US&with_origin_country=US|UK|AU&with_original_language=en&sort_by=vote_average.desc&vote_count.gte=200&page=1'
        self.views_link = f'{self.tmdb_link}/discover/tv?api_key={self.tmdb_user}&include_adult=false&include_null_first_air_dates=false&language=en-US&with_origin_country=US|UK|AU&with_original_language=en&sort_by=vote_count.desc&vote_count.gte=1500&page=1'
        self.language_link = f'{self.tmdb_link}/discover/tv?api_key={self.tmdb_user}&include_adult=false&include_video=false&sort_by=popularity.desc&with_original_language=%s&page=1'
        self.active_link = f'{self.tmdb_link}/discover/tv?api_key={self.tmdb_user}&include_adult=false&include_null_first_air_dates=false&language=en-US&sort_by=popularity.desc&with_origin_country=US|UK|AU&with_original_language=en&with_status=0|2&page=1'
        self.tmdb_api_link = f'{self.tmdb_link}/tv/%s?api_key={self.tmdb_user}&language={self.lang}&append_to_response=aggregate_credits,content_ratings,external_ids'
        self.tmdb_networks_link = f'{self.tmdb_link}/discover/tv?api_key={self.tmdb_user}&sort_by=first_air_date.desc&with_networks=%s&page=1'
        self.tmdb_networks_link_no_unaired = f'{self.tmdb_link}/discover/tv?api_key={self.tmdb_user}&first_air_date.lte={self.today_date}&sort_by=first_air_date.desc&with_networks=%s&page=1'
        self.tmdb_search_tvshow_link = f'{self.tmdb_link}/search/tv?api_key={self.tmdb_user}&language=en-US&query=%s&page=1'
        #self.search_link = f'{self.tmdb_link}/search/tv?api_key={self.tmdb_user}&language=en-US&query=%s&page=1'
        self.related_link = f'{self.tmdb_link}/tv/%s/similar?api_key={self.tmdb_user}&page=1'
        self.certification_link = f'{self.tmdb_link}/discover/tv?api_key={self.tmdb_user}&certification=%s&certification_country=US&language=en-US&sort_by=first_air_date.desc&append_to_response=aggregate_credits,content_ratings,external_ids&page=1'
        self.tmdb_info_tvshow_link = f'{self.tmdb_link}/tv/%s?api_key={self.tmdb_user}&language={self.lang}&append_to_response=images'
        self.tmdb_by_imdb = f'{self.tmdb_link}/find/%s?api_key={self.tmdb_user}&external_source=imdb_id'
        self.tmdb_tv_top_rated_link = f'{self.tmdb_link}/tv/top_rated?api_key={self.tmdb_user}&language={self.lang}&sort_by=popularity.desc&page=1'
        self.tmdb_tv_popular_tv_link = f'{self.tmdb_link}/tv/popular?api_key={self.tmdb_user}&language={self.lang}&page=1'
        self.tmdb_tv_on_the_air_link = f'{self.tmdb_link}/tv/on_the_air?api_key={self.tmdb_user}&language={self.lang}&page=1'
        self.tmdb_tv_airing_today_link = f'{self.tmdb_link}/tv/airing_today?api_key={self.tmdb_user}&language={self.lang}&page=1'
        self.tmdb_tv_trending_day_link = f'{self.tmdb_link}/trending/tv/day?api_key={self.tmdb_user}'
        self.tmdb_tv_trending_week_link = f'{self.tmdb_link}/trending/tv/week?api_key={self.tmdb_user}'
        self.tmdb_tv_discover_year_link = f'{self.tmdb_link}/discover/tv?api_key={self.tmdb_user}&language=%s&sort_by=popularity.desc&first_air_date_year={self.year}&include_null_first_air_dates=false&with_original_language=en&append_to_response=aggregate_credits,content_ratings,external_ids&page=1'

    def __del__(self):
        self.session.close()

    def get(self, url, tid=0, idx=True, create_directory=True):
        try:


            if 'trakt' in url and '/search' in url:
                pass
            else:
                if url.startswith('http'):
                    pass
                else:
                    url = getattr(self, f'{url}_link')
            c.log(f"[CM Debug @ 172 in tvshows.py] url = {url}")

            ####cm#
            # Making it possible to use date[xx] in url's where xx is a str(int)
            for i in re.findall(r'date\[(\d+)\]', url):
                url = url.replace(f'date[{i}]', (self.datetime - datetime.timedelta(days=int(i))).strftime('%Y-%m-%d'))

            if(self.showunaired) == 'false' and url == self.tmdb_networks_link:
                url = self.tmdb_networks_link_no_unaired

            u = urlparse(url).netloc.lower()
            if not u:
                raise Exception()

            if u in self.trakt_link and '/collection/' in url:
                    self.list = cache.get(self.collection_list, 0)
                    c.log(f"[CM Debug @ 197 in tvshows.py] self.list = {self.list}")
                    self.list = sorted(self.list, key=lambda k: utils.title_key(k['title']))

            if u in self.trakt_link and '/users/' in url:
                try:
                    c.log(f"[CM Debug @ 211 in tvshows.py] url = {url} and tid = {tid} and idx = {idx} and create_directory = {create_directory}")
                    if '/users/me/' not in url:
                        raise Exception()
                    if trakt.getActivity() > cache.timeout(self.trakt_list, url, self.trakt_user):
                        raise Exception()
                    #self.list = cache.get(self.trakt_list, 720, url, self.trakt_user)
                    self.list = cache.get(self.trakt_list, 0, url, self.trakt_user)
                except Exception:
                    #self.list = cache.get(self.trakt_list, 1, url, self.trakt_user)
                    self.list = cache.get(self.trakt_list, 0, url, self.trakt_user)



            elif u in self.trakt_link:
                #self.list = cache.get(self.trakt_list, 24, url, self.trakt_user)
                self.list = cache.get(self.trakt_list, 4, url, self.trakt_user)

            #elif u in self.imdb_link and ('/user/' in url or '/list/' in url):
            #    self.list = cache.get(self.imdb_list, 1, url)
            #    if idx is True:
            #        self.worker()

            #elif u in self.imdb_link: #checked
            #    self.list = cache.get(self.imdb_list, 24, url)
            #    if idx is True:
            #        self.worker()

            elif u in self.tvmaze_link:
                self.list = cache.get(self.tvmaze_list, 168, url)
                if idx is True:
                    self.worker()

            elif u in self.tmdb_link and 'tv_credits' in url:
                self.list = cache.get(self.tmdb_cast_list, 24, url)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)

            #elif u in self.tmdb_link and self.search_link in url:
            elif u in self.tmdb_link and '/search/' in url:
                c.log(f"[CM Debug @ 238 in tvshows.py] searching with url = {url}")
                #self.list = cache.get(self.tmdb_list, 1, url)
                self.list = self.tmdb_list(url)
                c.log(f"[CM Debug @ 242 in tvshows.py] list = {self.list}")

            elif u in self.tmdb_networks_link and 'with_networks' in url and 'first_air_date.lte' not in url:
                self.list = cache.get(self.tmdb_list, 24, url, tid)

            elif u in self.tmdb_networks_link_no_unaired and 'with_networks' in url and 'first_air_date.lte' in url:
                self.list = cache.get(self.tmdb_list, 24, url, tid)

            elif u in self.tmdb_link:
                #self.list = cache.get(self.tmdb_list, 24, url)
                #self.list = cache.get(self.tmdb_list, 0, url)
                self.list = self.tmdb_list(url)

            if idx is True:
                self.worker()
            if idx is True and create_directory is True:
                self.tvshowDirectory(self.list)
            return self.list
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 249 in tvshows.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 249 in tvshows.py]Exception raised. Error = {e}')
            pass
        #except Exception as e:
            #c.log(f'[CM Debug @ 269 in tvshows.py]Exception raised. Error = {e}')



#TC 2/01/19 started
    def search(self):
        """Executes a search operation for TV shows."""

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()

        navigator.navigator.addDirectoryItem(32603, 'tvSearchnew', 'search.png', 'DefaultTVShows.png')

        try:
            sql = "SELECT count(*) as aantal FROM sqlite_master WHERE type='table' AND name='tvshow'"
            dbcur.execute(sql)
            dbcon.commit()
            if dbcur.fetchone()[0] == 0:
                sql = 'CREATE TABLE tvshow (id INTEGER PRIMARY KEY AUTOINCREMENT, term TEXT)'
            dbcur.execute(sql)
        except OperationalError as e:
            c.log(f"[CM Debug @ 422 in movies.py] OperationalError in movies.search, {e}", 1)

        dbcur.execute("SELECT * FROM tvshow ORDER BY id DESC")

        search_terms = []
        cm = []
        delete_option = False
        rows = dbcur.fetchall()
        for _id, term in rows:
            if term not in search_terms:
                delete_option = True
                cm = ((32070, f'tvDeleteTerm&id={_id}'))
                navigator.navigator.addDirectoryItem(
                    term,
                    f'tvSearchterm&name={term}',
                    'search.png',
                    'DefaultTVShows.png',
                    context=cm
                )
                search_terms.append(term)

        dbcur.close()

        if delete_option:
            navigator.navigator.addDirectoryItem(32605, 'clearCacheSearch', 'tools.png', 'DefaultAddonProgram.png')

        navigator.navigator.endDirectory()

    def create_db_connection(self):
        """Creates and returns a database connection to the search database."""
        db_connection = database.connect(control.searchFile)
        db_cursor = db_connection.cursor()
        return db_connection, db_cursor

    def close_db_connection(self, db_connection, db_cursor):
        """Closes the given database connection and cursor."""
        db_cursor.close()
        db_connection.close()

    def search_new(self):
        """Search for a TV show."""
        control.idle()

        keyboard_header = control.lang(32010)
        keyboard = control.keyboard('', keyboard_header)
        keyboard.doModal()
        search_query = keyboard.getText() if keyboard.isConfirmed() else None

        if search_query is None:
            return

        search_query = search_query.lower()
        clean_search_query = utils.title_key(search_query)

        db_connection, db_cursor = self.create_db_connection()
        db_cursor.execute("DELETE FROM tvshow WHERE term = ?", (search_query,))
        db_cursor.execute("INSERT INTO tvshow VALUES (?,?)", (None, search_query))
        db_connection.commit()
        self.close_db_connection(db_connection, db_cursor)

        url = self.search_link % quote_plus(clean_search_query)
        self.get(url)

    def search_term(self, query):
        control.idle()
        query = query.lower()
        cleaned_query = utils.title_key(query)

        db_connection, db_cursor = self.create_db_connection()
        db_cursor.execute("DELETE FROM tvshow WHERE term = ?", (query,))
        db_cursor.execute("INSERT INTO tvshow VALUES (?, ?)", (None, query))
        db_connection.commit()
        self.close_db_connection(db_connection, db_cursor)

        search_url = self.search_link % quote_plus(cleaned_query)
        self.get(search_url)

    def delete_search_term(self, search_term_id):
        """
        Deletes a search term from the database.

        This method takes the ID of a search term as an argument, deletes the
        corresponding record from the database, and refreshes the Kodi UI.

        :param search_term_id: The ID of the search term to delete.
        :type search_term_id: int
        """
        try:
            db_connection, db_cursor = self.create_db_connection()
            db_cursor.execute("DELETE FROM tvshow WHERE ID = ?", (search_term_id,))
            db_connection.commit()
            self.close_db_connection(db_connection, db_cursor)
            control.refresh()
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            c.log(f'[Error in delete_search_term] Traceback: {error_traceback}')
            c.log(f'[Error in delete_search_term] Exception: {e}')

    def person(self):
        """
        Prompts the user for a person's name using a keyboard input dialog,
        formats the input into a URL, and retrieves information about the person.

        This method uses a control interface to display a keyboard for user input.
        If a valid query is provided, it constructs a URL with the person's name
        and calls the `persons` method to fetch the person's details.

        Logs any errors encountered during URL formatting or data retrieval.

        Exceptions:
            Logs any exceptions that occur during user input, URL formatting,
            or person data retrieval.
        """
        try:
            control.idle()

            prompt_text = control.lang(32010)
            keyboard = control.keyboard('', prompt_text)
            keyboard.doModal()
            query = keyboard.getText() if keyboard.isConfirmed() else None

            if not query:
                return

            try:
                person_url = self.person_link % quote(query)
                self.persons(person_url)
            except Exception as e:
                c.log(f'Error formatting URL or calling persons: {e}')
                return

        except Exception as e:
            c.log(f'Error in person method: {e}')
            return

    #####cm#
    # Completely redone for compatibility with tmdb
    # source reference/genre-tv-list
    def genres(self):
        genre_list = [
            {"id": 10759, "name": "Action & Adventure"},
            {"id": 16, "name": "Animation"},
            {"id": 35, "name": "Comedy"},
            {"id": 80, "name": "Crime"},
            {"id": 99, "name": "Documentary"},
            {"id": 18, "name": "Drama"},
            {"id": 10751, "name": "Family"},
            {"id": 10762, "name": "Kids"},
            {"id": 9648, "name": "Mystery"},
            {"id": 10763, "name": "News"},
            {"id": 10764, "name": "Reality"},
            {"id": 10765, "name": "Sci-Fi & Fantasy"},
            {"id": 10766, "name": "Soap"},
            {"id": 10767, "name": "Talk"},
            {"id": 10768, "name": "War & Politics"},
            {"id": 37, "name": "Western"}
        ]

        for genre in genre_list:
            self.list.append({
                'name': cleangenre.lang(genre['name'], self.lang),
                'url': self.genre_link % genre['id'],
                'image': 'genres.png',
                'action': 'tvshows'
            })

        self.addDirectory(self.list)
        return self.list

    def networks(self):
        try:
            network_data = [
                (129, "A&E", f'{self.logo_link}/ptSTdU4GPNJ1M8UVEOtA0KgtuNk.png'),
                (2, "ABC", f'{self.logo_link}/an88sKsFz0KX5CQngAM95WkncX4.png'),
                (1024, "Amazon", f'{self.logo_link}/uK6yuqMkUvKhCgVJjg5JWDUoabA.png'),
                (174, "AMC", f'{self.logo_link}/alqLicR1ZMHMaZGP3xRQxn9sq7p.png'),
                (91, "Animal Planet", f'{self.logo_link}/xQ25rzpv83d74V1zpOzSHbYlwJq.png'),
                (173, "AT-X", f'{self.logo_link}/fERjndErEpveJmQZccJbJDi93rj.png'),
                (493, "BBC America", f'{self.logo_link}/8Js4sUaxjE3RSxJcOCDjfXvhZqz.png'),
                (4, "BBC One", f'{self.logo_link}/uJjcCg3O4DMEjM0xtno9OWFciRP.png'),
                (332, "BBC Two", f'{self.logo_link}/7HVPn1p2w1nC5oRKBehXVHpss7e.png'),
                (3, "BBC Three", f'{self.logo_link}/s22fRhj8xFPbiexrJwiAOcDEIrS.png'),
                (100, "BBC Four", f'{self.logo_link}/AgsOSxGvfxIonhPgrfkWCmsOKfA.png'),
                (24, "BET", f'{self.logo_link}/gaouRlJrfZlEA5EPHhO5qqZ1Fgu.png'),
                (74, "Bravo", f'{self.logo_link}/wX5HsfS47u6UUCSpYXqaQ1x2qdu.png'),
                (56, "Cartoon Network", f'{self.logo_link}/c5OC6oVCg6QP4eqzW6XIq17CQjI.png'),
                (201, "CBC", f'{self.logo_link}/qNooLje0YQh1y3y9LUM2Y5QCtiF.png'),
                (16, "CBS", f'{self.logo_link}/wju8KhOUsR5y4bH9p3Jc50hhaLO.png'),
                (26, "Channel 4", f'{self.logo_link}/zCUWm0Xb6AnjUbxzjL5OkzmHhd7.png'),
                (99, "Channel 5", f'{self.logo_link}/bMuKs6xuhI0GHSsq4WWd9FsntUN.png'),
                (47, "Comedy Central", f'{self.logo_link}/6ooPjtXufjsoskdJqj6pxuvHEno.png'),
                (2548, "CBC", f'{self.logo_link}/qe2RYSTCxbPh3jCaM1tk9E4uJZ6.png'),
                (403, "CTV", f'{self.logo_link}/volHUxY1MHjSPI4ju7j36EdhR2m.png'),
                (928, "Crackle", f'{self.logo_link}/bR8S6Fjv3VGtEKyKF5lvvRJ5xfw.png'),
                (71, "The CW", f'{self.logo_link}/ge9hzeaU7nMtQ4PjkFlc68dGAJ9.png'),
                (1049, "CW seed", f'{self.logo_link}/wwo3PZyBpHL3Wz8eg4cr3kqVZQY.png'),
                (64, "Discovery", f'{self.logo_link}/8qkdZlbrTSVfkJ73DjOBrwYtMSC.png'),
                (4883, "discovery+", f'{self.logo_link}/iKvdFk5lpbvs4g0vd6yVUcV36i3.png'),
                (244, "Discovery ID", f'{self.logo_link}/yfkdPLHjsed7vwUNuh20eMuDiDO.png'),
                (2739, "Disney+", f'{self.logo_link}/PQxvkeK8cTtD7vjataBsNpjbJ5.png'),
                (54, "Disney Channel", f'{self.logo_link}/gvhBea9OGqChmGKHa5CntbmsDBp.png'),
                (44, "Disney XD", f'{self.logo_link}/nKM9EnV7jTpt3MKRbhBusJ03lAY.png'),
                (2087, "Discovery Channel", f'{self.logo_link}/8qkdZlbrTSVfkJ73DjOBrwYtMSC.png'),
                (76, "E! Entertainment", f'{self.logo_link}/ptpx2Ag52sYJG6LiX9zBlnKsQOS.png'),
                (136, "E4", f'{self.logo_link}/fJPM9Rj12us4HF03N3qvakz7WuZ.png'),
                (19, "FOX", f'{self.logo_link}/1DSpHrWyOORkL9N2QHX7Adt31mQ.png'),
                (1267, "Freeform", f'{self.logo_link}/jk2Z7WH6JnHSZrxouYh4sireM3a.png'),
                (88, "FX", f'{self.logo_link}/aexGjtcs42DgRtZh7zOxayiry4J.png'),
                (384, "Hallmark Channel", f'{self.logo_link}/9JTL7HcaiVxq7M6eu5m7giFqaxR.png'),
                (65, "History", f'{self.logo_link}/9fGgdJz17aBX7dOyfHJtsozB7bf.png'),
                (49, "HBO", f'{self.logo_link}/hizvY65SpyF3BPY2qsBZMgUOxjs.png'),
                (3186, "HBO Max", f'{self.logo_link}/nmU0UMDJB3dRRQSTUqawzF2Od1a.png'),
                (210, "HGTV", f'{self.logo_link}/tzTtKdQ7vC2FkBvJDUErOhBPdKJ.png'),
                (453, "Hulu", f'{self.logo_link}/pqUTCleNUiTLAVlelGxUgWn1ELh.png'),
                (9, "ITV", f'{self.logo_link}/j3KAlTmxGDCHQZqs1A2hagzjYqu.png'),
                (34, "Lifetime", f'{self.logo_link}/kU18GafTybg4uMhkj3wvsGBgn8s.png'),
                (33, "MTV USA", f'{self.logo_link}/w4qtv7xBkSVsbOQdSzjUjlyOuSr.png'),
                (488, "MTV UK", f'{self.logo_link}/w4qtv7xBkSVsbOQdSzjUjlyOuSr.png'),
                (43, "National Geographic", f'{self.logo_link}/q9rPBG1rHbUjII1Qn98VG2v7cFa.png'),
                (6, "NBC", f'{self.logo_link}/cm111bsDVlYaC1foL0itvEI4yLG.png'),
                (213, "Netflix", f'{self.logo_link}/wwemzKWzjKYJFfCeiB57q3r4Bcm.png'),
                (13, "Nickelodeon", f'{self.logo_link}/aYkLXz4dxHgOrFNH7Jv7Cpy56Ms.png'),
                (14, "PBS", f'{self.logo_link}/hp2Fs7AIdsMlEjiDUC1V8Ows2jM.png'),
                (67, "Showtime", f'{self.logo_link}/Allse9kbjiP6ExaQrnSpIhkurEi.png'),
                (1755, "Sky History", f'{self.logo_link}/mzLlbqnnLiDIzriohlvfSbWlEfR.png'),
                (1431, "Sky One", f'{self.logo_link}/dVBHOr0nYCx9GSNesTVb1TT52Xj.png'),
                (318, "Starz", f'{self.logo_link}/GMDGZk9iDG4WDijY3VgUgJeyus.png'),
                (270, "SundanceTV", f'{self.logo_link}/xhTdszjVRy1tABMix2dffBcdDJ1.png'),
                (77, "Syfy", f'{self.logo_link}/iYfrkobwDhTOFJ4AXYPSLIEeaAT.png'),
                (68, "TBS", f'{self.logo_link}/9PYsQf3YbDUJo1rg3pgtaiOrb6s.png'),
                (84, "TLC", f'{self.logo_link}/6GRfZSrYh9D6C88n9kWlyrySB2l.png'),
                (41, "TNT", f'{self.logo_link}/6ISsKwa2XUhSC6oBtHZjYf6xFqv.png'),
                (209, "Travel Channel", f'{self.logo_link}/8SwN81R7P5vD5mhtOE0taw5mji4.png'),
                (364, "truTV", f'{self.logo_link}/c48pVcWAEYhEFXrWFsYxx343mjx.png'),
                (30, "USA Network", f'{self.logo_link}/g1e0H0Ka97IG5SyInMXdJkHGKiH.png'),
                (158, "VH1", f'{self.logo_link}/w9oUxxUiXTC1O1MzJSvsMjQbgft.png'),
                (202, "WGN America", f'{self.logo_link}/kCNFRiqVRMgNWKSWu0LzAIpy9um.png'),
                (247, "YouTube", f'{self.logo_link}/9Ga8A5QegQmiSVHp4hyusfMfpVk.png'),
                (1436, "YouTube Premium", f'{self.logo_link}/3p05CgodUb9gPayuliuhawNj1Wo.png'),
            ]

            #for network_id, name, logo in network_data:
            #    c.log(f"[CM Debug @ 534 in tvshows.py] network_id = {network_id} and name = {name} and logo = {logo}")
            #    self.list.append({
            #        'name': name,
            #        'url': self.tmdb_networks_link % network_id,
            #        'image': logo,
            #        'action': 'tvshows'
            #    })

            self.list = [
                {
                    'name': name,
                    'url': self.tmdb_networks_link % network_id,
                    'image': logo,
                    'action': 'tvshows'
                }
                for network_id, name, logo in network_data
            ]

            c.log(f"[CM Debug @ 552 in tvshows.py] list = self.list = {repr(self.list)}")

            self.addDirectory(self.list)
            #return self.list
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            c.log(f'[Error in networks] Traceback: {error_traceback}')
            c.log(f'[Error in networks] Exception: {e}')

    def languages(self):
        languages = [
            ('Arabic', 'ar'),
            ('Bosnian', 'bs'),
            ('Bulgarian', 'bg'),
            ('Chinese', 'zh'),
            ('Croatian', 'hr'),
            ('Dutch', 'nl'),
            ('English', 'en'),
            ('Finnish', 'fi'),
            ('French', 'fr'),
            ('German', 'de'),
            ('Greek', 'el'),
            ('Hebrew', 'he'),
            ('Hindi', 'hi'),
            ('Hungarian', 'hu'),
            ('Icelandic', 'is'),
            ('Italian', 'it'),
            ('Japanese', 'ja'),
            ('Korean', 'ko'),
            ('Norwegian', 'no'),
            ('Persian', 'fa'),
            ('Polish', 'pl'),
            ('Portuguese', 'pt'),
            ('Punjabi', 'pa'),
            ('Romanian', 'ro'),
            ('Russian', 'ru'),
            ('Serbian', 'sr'),
            ('Spanish', 'es'),
            ('Swedish', 'sv'),
            ('Turkish', 'tr'),
            ('Ukrainian', 'uk')
        ]


        for i in languages:
            self.list.append({'name': str(i[0]), 'url': self.language_link % i[1], 'image': 'international2.png', 'action': 'tvshows'})
        self.addDirectory(self.list)
        return self.list

    def certifications(self):
        certificates = [
            ('TV-Y', 'All Children', 'tv_y.png'),
            ('TV-G', 'General Audiences', 'tv_g.png'),
            ('TV-PG', 'Parental Guidance', 'tv_pg.png'),
            ('TV-14', 'Parents Strongly Cautioned', 'tv_14.png'),
            ('TV-MA', 'Mature Audiences', 'tv_ma.png'),
            ]


        self.list = [
                {
                    'name': name,
                    'url': self.certification_link % code,
                    'image': icon,
                    'action': 'tvshows'
                }
                for code, name, icon in certificates
            ]


        #for i in certificates:
            #self.list.append({'name': str(i), 'url': self.certification_link % str(i), 'image': 'certificates.png', 'action': 'tvshows'})
        self.addDirectory(self.list)
        return self.list

    def persons(self, url):
        c.log(f'[CM DEBUG @ 542 in tvshows.py] url = {url}')
        if url is None:
            #self.list = cache.get(self.tmdb_person_list, 24, self.personlist_link)
            self.tmdb_person_list(self.personlist_link)

        else:
            #self.list = cache.get(self.tmdb_person_list, 1, url)
            self.tmdb_person_list (url)

        #for i in range(len(self.list)):
            #self.list[i].update({'action': 'tvshows'})
        for item in self.list:
            item.update({'action': 'tvshows'})
        self.addDirectory(self.list)
        return self.list

    def userlists(self):
        try:
            userlists = []
            if trakt.get_trakt_credentials_info() is False:
                raise Exception()
            activity = trakt.getActivity()
        except Exception:
            pass

        try:
            if trakt.get_trakt_credentials_info() is False:
                raise Exception()
            try:
                if activity > cache.timeout(self.trakt_user_list, self.traktlists_link, self.trakt_user):
                    raise Exception()
                userlists += cache.get(self.trakt_user_list, 720, self.traktlists_link, self.trakt_user)
            except Exception:
                userlists += cache.get(self.trakt_user_list, 0, self.traktlists_link, self.trakt_user)
        except Exception:
            pass
        try:
            self.list = []
            if self.imdb_user == '':
                raise Exception()
            userlists += cache.get(self.imdb_user_list, 0, self.imdblists_link)
        except Exception:
            pass
        try:
            self.list = []
            if trakt.get_trakt_credentials_info() is False:
                raise Exception()
            try:
                if activity > cache.timeout(self.trakt_user_list, self.traktlikedlists_link, self.trakt_user): raise Exception()
                userlists += cache.get(self.trakt_user_list, 720, self.traktlikedlists_link, self.trakt_user)
            except Exception:
                userlists += cache.get(self.trakt_user_list, 0, self.traktlikedlists_link, self.trakt_user)
        except Exception:
            pass

        self.list = userlists

        #for i in range(len(self.list)):
            #self.list[i].update({'image': 'userlists.png', 'action': 'tvshows'})

        for item in self.list:
            item.update({'image': 'userlists.png', 'action': 'tvshows'})

        self.addDirectory(self.list)
        return self.list

    def trakt_list(self, url, user):
        try:
            dupes = []

            q = dict(parse_qsl(urlsplit(url).query))
            q['extended'] = 'full'
            q = (urlencode(q)).replace('%2C', ',')
            #u = url.replace('?' + urlparse(url).query, '') + '?' + q
            u = url.replace(f'?{urlparse(url).query}', '') + '?' + q
            result = trakt.getTraktAsJson(u)

            items = []
            for i in result:
                try:
                    items.append(i['show'])
                except Exception:
                    pass
            if not items:
                items = result
        except Exception:
            return

        #c.log(f"[CM Debug @ 619 in tvshows.py] items = {items}")

        try:
            q = dict(parse_qsl(urlsplit(url).query))
            if int(q['limit']) != len(items):
                raise Exception()
            #q.update({'page': str(int(q['page']) + 1)})
            q['page'] = str(int(q['page']) + 1)
            q = (urlencode(q)).replace('%2C', ',')
            #_next = url.replace('?' + urlparse(url).query, '') + '?' + q
            _next = url.replace(f'?{urlparse(url).query}', '') + '?' + q
            _next = str(_next)
        except Exception:
            _next = ''

        if c.is_widget_listing():
            c.log("[CM Debug @ 682 in tvshows.py]The listing call is from a widget.", 1)
        else:
            c.log("[CM Debug @ 684 in tvshows.py]The listing call is from a normal screen.", 1)


        def add_to_list(item):
            title = item.get('title', '')
            if title != '':
                title = re.sub(r'\s(|[(])(UK|US|AU|\d{4})(|[)])$', '', title)
                title = client.replaceHTMLCodes(title)

            #year = item['year']
            year = item.get('year', '0')
            if year == '0':
                year = re.sub('[^0-9]', '', str(year))

            #imdb = item['ids']['imdb'] or '0'
            ids = item.get('ids', {})
            if ids:
                imdb = ids.get('imdb', '0')
                if imdb != '0':
                    imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))
                tmdb = ids.get('tmdb', '0')
                tvdb = ids.get('tvdb', '0')
                tmdb = str(tmdb)
                tvdb = str(tvdb)
            else:
                imdb = tmdb = tvdb = '0', '0', '0'

            if tmdb not in dupes:
                dupes.append(tmdb)

            premiered = item.get('first_aired', '0')

            #try:
                #premiered = item['first_aired']
            #except Exception:
                #premiered = '0'

            if premiered != '0':
                premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(premiered)[0]



            #studio = item['network'] or '0'
            studio = item.get('network', '0')


            #genre = item['genres'] or '0'
            genre = item.get('genres', '0')

            if genre != '0':
                genre = [i.title() for i in genre]
                genre = ' / '.join(genre)

            #duration = str(item['runtime']) or '0'
            duration = str(item.get('runtime', '0'))

            #rating = str(item['rating']) or '0'
            rating = str(item.get('rating', '0'))
            if rating == '0.0':
                rating = '0'

            #votes = str(item['votes']) or '0'
            votes = str(item.get('votes', '0'))


            if votes != '0':
                votes = str(format(int(votes), ',d'))

            #mpaa = item['certification'] or '0'
            mpaa = item.get('certification', '0')
            plot = item['overview'] or 'The Crew - No plot available'
            plot = client.replaceHTMLCodes(plot)

            country = item.get('country').upper() or '0'

            status = item.get('status', '0')
            trailer = item.get('trailer', '0')

            poster = fanart = '0'
            seasons = episodes = '0'


            if tmdb != '0':
                url = self.tmdb_info_tvshow_link % tmdb
                result = self.session.get(url, timeout=10).json()
                #episodes = result['number_of_episodes']
                episodes = result.get('number_of_episodes', '0')
                #seasons = result['number_of_seasons']
                seasons = result.get('number_of_seasons', '0')
                try:
                    poster = self.tmdb_img_prelink.format('w500', result['poster_path'])
                    fanart = self.tmdb_img_prelink.format('w1280', result['backdrop_path'])
                except Exception:
                    poster = '0'
                    fanart = '0'



            #self.list.append({'title': title, 'originaltitle': title, 'poster': poster,
            #                    'fanart': fanart, 'year': year, 'premiered': premiered,
            #                    'studio': studio, 'genre': genre, 'duration': duration,
            #                    'rating': rating, 'votes': votes, 'mpaa': mpaa, 'plot': plot,
            #                    'country': country, 'status': status, 'imdb': imdb, 'tvdb': tvdb,
            #                    'seasons': seasons, 'episodes': episodes,
            #                    'tmdb': tmdb, 'trailer': trailer, 'next': _next})

            return ({'title': title, 'originaltitle': title, 'poster': poster,
                    'fanart': fanart, 'year': year, 'premiered': premiered,
                    'studio': studio, 'genre': genre, 'duration': duration,
                    'rating': rating, 'votes': votes, 'mpaa': mpaa, 'plot': plot,
                    'country': country, 'status': status, 'imdb': imdb, 'tvdb': tvdb,
                    'seasons': seasons, 'episodes': episodes,
                    'tmdb': tmdb, 'trailer': trailer, 'next': _next})





        try:
            max_nr = len(items)

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_nr) as executor:
                futures = {executor.submit(add_to_list, item): item for item in items}
                for future in concurrent.futures.as_completed(futures):
                    item = futures[future]
                    try:
                        result = future.result()
                        self.list.append(result)
                    except Exception as exc:
                        c.log(f"Error processing item {item}: {exc}")
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 876 in tvshows.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 876 in tvshows.py]Exception raised. Error = {e}')
            pass


        #self.list = results


        #for item in items:
            #try:

                #threads = workers.Thread(add_to_list(item)).start()
                #threads.join()


            #except Exception as e:
                #import traceback
                #failure = traceback.format_exc()
                #c.log(f'[CM Debug @ 717 in tvshows.py]Traceback:: {failure}')
                #c.log(f'[CM Debug @ 717 in tvshows.py]Exception raised. Error = {e}')
                #pass

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
                url = str(url)

                self.list.append({'name': name, 'url': url, 'context': url})
            except Exception:
                pass

        self.list = sorted(self.list, key=lambda k: utils.title_key(k['name']))
        return self.list




    def collection_list(self):
        # collection = trakt.get_collection('tvshows')
        if not self.list:
            self.list = []


        collection = trakt.get_collection('tvshows') or []
        c.log(f"[CM Debug @ 1048 in tvshows.py] collection = {collection}")
        if len(collection) == 0:
            trakt.get_trakt_collection('movies')
            collection = trakt.get_collection('movies') or []
        if len(collection) == 0:
            return
        c.log(f"[CM Debug @ 927 in tvshows.py] collection = {collection}")


        for item in collection:
            try:

                c.log(f"[CM Debug @ 1059 in tvshows.py] item = {item}")
                tmdb = str(item['tmdb'])

                imdb = item['imdb']
                _trakt = str(item['trakt'])
                slug = item['slug']
                title = item['Title']
                year = str(item['Year'])

                self.list.append({
                                'title': title, 'year': year, 'imdb': imdb, 'tmdb': tmdb,
                                'trakt': _trakt, 'slug': slug
                                })
            except Exception as e:
                c.log(f"Exception raised in collection_list() with e = {e}")

        return self.list





    ####cm#
    # new def for tmdb lists
    def list_tmdb_list(self, url, tid=0):
        try:
            if not tid == 0: url = url % tid

            result = self.session.get(url, timeout=15).json()
            items = result['items']
        except Exception:
            return
        try:
            page = int(result['page'])
            total = int(result['total_pages'])
            if page >= total:
                raise Exception()
            if 'page=' not in url:
                raise Exception()
            _next = '%s&page=%s' % (url.split('&page=', 1)[0], page+1)
        except Exception:
            _next = ''

        for item in items:
            try:
                tmdb = str(item['id'])
                title = item['title']

                originaltitle = item['original_title']
                if not originaltitle: originaltitle = title

                try: rating = str(item['vote_average'])
                except Exception: rating = ''
                if not rating: rating = '0'

                try: votes = str(item['vote_count'])
                except Exception: votes = ''
                if not votes: votes = '0'

                try: premiered = item['release_date']
                except Exception: premiered = ''
                if not premiered: premiered = '0'

                try: year = re.findall(r'(\d{4})', premiered)[0]
                except Exception: year = ''
                if not year: year = '0'

                if premiered == '0':
                    pass
                elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    if self.showunaired != 'true':
                        raise Exception()

                try: plot = item['overview']
                except Exception:  plot = ''
                if not plot: plot = '0'

                try:  poster_path = item['poster_path']
                except Exception: poster_path = ''
                if poster_path:
                    poster = self.tmdb_img_prelink.format('w500', poster_path)
                else:
                    poster = '0'

                backdrop_path = item['backdrop_path'] if 'backdrop_path' in item else ''
                if backdrop_path:
                    fanart = self.tmdb_img_prelink.format('w1280', 'backdrop_path')
                else:
                    fanart = ''

                self.list.append({'title': title, 'originaltitle': originaltitle,
                                    'premiered': premiered, 'year': year, 'rating': rating,
                                    'votes': votes, 'plot': plot, 'imdb': '0', 'tmdb': tmdb,
                                    'tvdb': '0', 'fanart': fanart, 'poster': poster, 'next': _next
                                })
            except Exception:
                pass

        return self.list

    def tmdb_cast_list(self, url):
        try:
            result = self.session.get(url, timeout=15).json()
            items = result['cast']
        except Exception:
            return

        try:
            page = int(result['page'])
            total = int(result['total_pages'])
            if page >= total:
                raise Exception()
            if 'page=' not in url:
                raise Exception()
            # _next = '%s&page=%s' % (url.split('&page=', 1)[0], page+1)
            _next = f"{url.split('&page=', 1)[0]}&page={page+1}"
        except Exception:
            _next = ''

        for item in items:

            try:
                tmdb = str(item['id'])
                title = item['name']
                originaltitle = item.get('original_name', '') or title

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
                    premiered = item['first_air_date']
                except Exception:
                    premiered = ''
                if not premiered :
                    premiered = '0'

                unaired = ''
                if not premiered or premiered == '0':
                    pass
                elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    unaired = 'true'
                    if self.showunaired != 'true':
                        raise Exception('unaired is False')

                try:
                    year = re.findall('(\d{4})', premiered)[0]
                except Exception:
                    year = ''
                if not year :
                    year = '0'

                try:
                    plot = item['overview']
                except Exception:
                    plot = ''
                if not plot:
                    plot = '0'

                try:
                    poster_path = item['poster_path']
                except Exception:
                    poster_path = ''
                if poster_path:
                    poster = self.tmdb_img_link % (c.tmdb_postersize, poster_path)
                else:
                    poster = '0'

                backdrop_path = item['backdrop_path'] if 'backdrop_path' in item else ''
                if backdrop_path:
                    fanart = self.tmdb_img_link % (c.tmdb_fanartsize, 'backdrop_path')

                self.list.append({'title': title, 'originaltitle': originaltitle,
                                'premiered': premiered, 'year': year, 'rating': rating,
                                'votes': votes, 'plot': plot, 'imdb': '0', 'tmdb': tmdb,
                                'tvdb': '0', 'poster': poster, 'fanart': fanart, 'next': _next,
                                'unaired': unaired
                                })
            except Exception as e:
                c.log(f'[CM DEBUG @ 1082 in tvshows.py] Exception raised: e = {e}')
                pass

        return self.list

    def tvmaze_list(self, url):
        try:
            result = client.request(url)
            result = client.parseDom(result, 'section', attrs={'id': 'this-seasons-shows'})

            items = client.parseDom(result, 'div', attrs={'class': 'content auto cell'})
            items = [client.parseDom(i, 'a', ret='href') for i in items]
            items = [i[0] for i in items if len(i) > 0]
            items = [re.findall('/(\d+)/', i) for i in items]
            items = [i[0] for i in items if len(i) > 0]

            #items = items[:50]

            _next = ''
            last = []
            nextp = []
            page = int(str(url.split('&page=', 1)[1]))
            _next = '%s&page=%s' % (url.split('&page=', 1)[0], page+1)
            last = client.parseDom(result, 'li', attrs = {'class': 'last disabled'})
            nextp = client.parseDom(result, 'li', attrs = {'class': 'next'})
            if last != [] or nextp == []:
                _next = ''
        except Exception:
            return

        def items_list(i):
            try:
                url = self.tvmaze_info_link % i

                item = self.session.get(url, timeout=16).json()

                #item = client.request(url)
                #item = json.loads(item)

                title = item['name']
                title = re.sub(r'\s(|[(])(UK|US|AU|\d{4})(|[)])$', '', title)
                title = client.replaceHTMLCodes(title)
                title = str(title)
                premiered = item['premiered']
                try:
                    premiered = re.findall(r'(\d{4}-\d{2}-\d{2})', premiered)[0]
                except Exception:
                    premiered = '0'
                premiered = c.ensure_str(premiered)

                year = item['premiered']
                try:
                    year = re.findall('(\d{4})', year)[0]
                except Exception:
                    year = '0'
                year = str(year)

                #if int(year) > int(self.datetime.strftime('%Y')): raise Exception()

                imdb = item['externals']['imdb']
                if imdb is None or imdb == '':
                    imdb = '0'
                else:
                    imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))
                imdb = str(imdb)

                tvdb = item['externals']['thetvdb']
                if tvdb is None or tvdb == '':
                    tvdb = '0'
                else:
                    tvdb = re.sub('[^0-9]', '', str(tvdb))
                tvdb = str(tvdb)

                try:
                    poster = item['image']['original']
                except Exception:
                    poster = '0'
                if not poster:
                    poster = '0'
                poster = str(poster)

                try:
                    studio = item['network']['name']
                except Exception:
                    studio = '0'
                if studio is None:
                    studio = '0'
                studio = c.ensure_str(studio)

                try:
                    genre = item['genres']
                except Exception:
                    genre = '0'
                genre = [i.title() for i in genre]
                if genre == []:
                    genre = '0'
                genre = ' / '.join(genre)
                genre = str(genre)

                try:
                    duration = item['runtime']
                except Exception:
                    duration = '0'
                if duration is None:
                    duration = '0'
                duration = str(duration)

                try:
                    rating = item['rating']['average']
                except Exception:
                    rating = '0'
                if rating is None or rating == '0.0':
                    rating = '0'
                rating = str(rating)

                try:
                    plot = item['summary']
                except Exception:
                    plot = '0'
                if plot is None:
                    plot = '0'
                plot = re.sub('<.+?>|</.+?>|\n', '', plot)
                plot = client.replaceHTMLCodes(plot)
                plot = str(plot)

                try:
                    content = item['type'].lower()
                except Exception:
                    content = '0'
                if content is None or content == '':
                    content = '0'
                content = str(content)

                self.list.append({
                    'title': title, 'originaltitle': title, 'year': year, 'premiered': premiered,
                    'studio': studio, 'genre': genre, 'duration': duration, 'rating': rating,
                    'plot': plot, 'imdb': imdb, 'tvdb': tvdb, 'tmdb': '0', 'poster': poster,
                    'content': content, 'next': _next
                    })
            except Exception:
                pass

        try:
            threads = []
            for i in items:
                threads.append(workers.Thread(items_list, i))
            #[i.start() for i in threads]
            #[i.join() for i in threads]

            for i in threads:
                i.start()
            for i in threads:
                i.join()

            self.list = sorted(self.list, key=lambda k: k['title'].lower())


            #filter = [i for i in self.list if i['content'] == 'scripted']
            #filter += [i for i in self.list if not i['content'] == 'scripted']
            #self.list = filter

            return self.list
        except Exception:
            return

    def tmdb_list(self, url, tid=0):
        try:
            #c.log(f"[CM Debug @ 1051 in tvshows.py] inside tmdb_list,url = {url}")
            if tid != 0:
                url = url % tid

            for i in re.findall(r'date\[(\d+)\]', url):
                #url = url.replace('date[%s]' % i, (self.datetime - datetime.timedelta(days=int(i))).strftime('%Y-%m-%d'))
                url = url.replace(
                    f'date[{i}]',
                    (self.datetime - datetime.timedelta(days=int(i))).strftime(
                        '%Y-%m-%d'
                    ),
                )
            c.log(f"[CM Debug @ 1240 in tvshows.py] url = {url}")

            result = self.session.get(url, timeout=16).json()
            items = result['results']
        except Exception:
            return

        try:
            page = int(result['page'])
            total = int(result['total_pages'])
            if page >= total or 'page=' not in url:
                raise Exception() # sourcery skip: raise-specific-error
            #_next = '%s&page=%s' % (url.split('&page=', 1)[0], page+1)
            _next = f"{(url.split('&page=', 1)[0])}&page={(page+1)}"
            #c.log(f"[CM Debug @ 1075 in tvshows.py] next = {_next}")
        except Exception:
            _next = ''


            c.log(f"[CM Debug @ 1287 in tvshows.py] items = {items}")

        def add_to_list(item):
            try:
                #c.log(f"\n\n---------------------------------------------------------------------\n\n[CM Debug @ 1260 in tvshows.py] url = {url} of type {type(url)}")
                #c.log(f"[CM Debug @ 1261 in tvshows.py] item = {item} of type {type(item)}\n\n------------------------------------------------------\n\n")
                if '/search/' in url or 'episodes_number' not in item:
                    #cm we need to get extended result like seasons and episodes
                    #first, lets get tmdb
                    tmdb = str(item['id'])
                    r_extended = self.session.get(self.tmdb_info_tvshow_link % tmdb, timeout=16).json()


                    #c.log(f"[CM Debug @ 1154 in tvshows.py] r_extended = {r_extended}")
                    seasons = r_extended['number_of_seasons']
                    episodes = r_extended['number_of_episodes']

                #c.log(f"[CM Debug @ 1093 in tvshows.py]item = {item}")
                tmdb = str(item['id'])
                title = item['name']
                originaltitle = item['original_name'] if 'original_name' in item and item['original_name'] else item['name'] or '0'
                rating = str(item['vote_average']) or '0'
                votes = str(item['vote_count']) or '0'
                premiered = item['first_air_date'] or '0'

                unaired = ''
                if not premiered or premiered == '0':
                    pass
                elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    unaired = 'true'
                    if self.showunaired != 'true':
                        raise Exception('unaired is False')

                try:
                    year = re.findall(r'(\d{4})', premiered)[0]
                except Exception:
                    year = ''
                if not year :
                    year = '0'

                plot = item['overview'] or '0'
                poster_path = item['poster_path'] or ''

                if poster_path:
                    poster = self.tmdb_img_link % (c.tmdb_postersize, poster_path)
                else:
                    poster = '0'

                backdrop_path = item['backdrop_path'] if 'backdrop_path' in item else ''
                if backdrop_path:
                    if not backdrop_path.startswith('/'):
                        backdrop_path = f'/{backdrop_path}'
                    fanart = self.tmdb_img_link % (c.tmdb_fanartsize, backdrop_path)
                else:
                    fanart = '0'

                #self.list.append({
                #    'title': title, 'originaltitle': originaltitle, 'premiered': premiered,
                #    'year': year, 'rating': rating, 'votes': votes, 'plot': plot,
                #    'imdb': '0', 'tmdb': tmdb, 'tvdb': '0', 'poster': poster,
                #    'seasons':  seasons, 'episodes': episodes,
                #    'unaired': unaired, 'fanart': fanart, 'next': _next
                #    })
                return ({
                    'title': title, 'originaltitle': originaltitle, 'premiered': premiered,
                    'year': year, 'rating': rating, 'votes': votes, 'plot': plot,
                    'imdb': '0', 'tmdb': tmdb, 'tvdb': '0', 'poster': poster,
                    'seasons':  seasons, 'episodes': episodes,
                    'unaired': unaired, 'fanart': fanart, 'next': _next
                    })
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 1319 in tvshows.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 1319 in tvshows.py]Exception raised. Error = {e}')
                pass
            #except Exception as e:
                #c.log(f'[CM DEBUG @ 1320 in tvshows.py] Exception raised: e = {e}')
                #pass

        try:

            max_nr = len(items)

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_nr) as executor:
                futures = {executor.submit(add_to_list, item): item for item in items}

                for future in concurrent.futures.as_completed(futures):
                    item = futures[future]
                    try:
                        result = future.result()
                        self.list.append(result)
                    except Exception as exc:
                        c.log(f"Error processing item {item}: {exc}")
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1396 in tvshows.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1397 in tvshows.py]Exception raised. Error = {e}')
            pass


        #for item in items:
            #try:

                #thread = workers.Thread(add_item(item)).start()
                #thread.join()
            #except Exception as e:
                #c.log(f'[CM DEBUG @ 1316 in tvshows.py] Exception raised: e = {e}')
                #pass

        return self.list

    def worker(self):
        self.meta = []
        total = len(self.list)

        if total == 0:
            control.infoDialog('List returned no relevant results', icon='INFO', sound=False)
            return

        for i in range(total):
            self.list[i].update({'metacache': False})

        self.list = metacache.fetch(self.list, self.lang, self.user)

        # cm changed worker - 15-04-2025
        #for r in range(0, total, 40):
        #    threads = []
        #    for i in range(r, r+40):
        #        if i < total:
        #            threads.append(workers.Thread(self.super_info(i)))

        #[i.start() for i in threads]
        #[i.join() for i in threads]

        try:
            result = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=total) as executor:
                #futures = {executor.submit(self.super_info, i): item for item in items}
                futures = {executor.submit(self.super_info, i): i for i in range(0,total, 40)}

                c.log(f"[CM Debug @ 1435 in tvshows.py] futures = {futures}")



                #for future in concurrent.futures.as_completed(futures):
                #    i = futures[future]
                #    try:
                #        result = future.result()
                #        result.append(result)

                #    except Exception as exc:
                #        c.log(f"Error processing item {i}: {exc}")
                #    c.log(f"[CM Debug @ 1443 in tvshows.py] result = {result}")
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1396 in tvshows.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1397 in tvshows.py]Exception raised. Error = {e}')
            pass












        if self.meta:
            metacache.insert(self.meta)

    def super_info(self, i):
        try:
            item_data = self.list[i]
            if item_data.get('metacache'):
                return

            imdb = item_data.get('imdb', '0')
            tmdb = item_data.get('tmdb', '0')
            tvdb = item_data.get('tvdb', '0')
            list_title = item_data['title']

            if tmdb == '0' and imdb != '0':
                try:
                    url = self.tmdb_by_imdb % imdb
                    result = self.session.get(url, timeout=10).json()
                    tmdb = str(result['tv_results'][0].get('id', '0'))
                except Exception:
                    pass

            if tmdb == '0':
                try:
                    search_url = self.search_link % quote(list_title) + '&first_air_date_year=' + item_data['year']
                    result = client.request(search_url)
                    results = json.loads(result)['results']
                    show = next((r for r in results if cleantitle.get(r.get('name')) == cleantitle.get(list_title)), {})
                    tmdb = str(show.get('id', '0'))
                except Exception:
                    pass

            if tmdb == '0':
                raise Exception()

            url = self.tmdb_api_link % tmdb
            url = url if self.lang == 'en' else url + ',translations'
            item = self.session.get(url, timeout=10).json()

            if not item:
                raise Exception()

            if imdb == '0':
                imdb = item['external_ids'].get('imdb_id', '0')

            if tvdb == '0':
                tvdb = str(item['external_ids'].get('tvdb_id', '0'))

            original_language = item.get('original_language', '')
            translations = item.get('translations', {}).get('translations', [])
            en_trans_item = next((x['data'] for x in translations if x['iso_639_1'] == 'en'), {})

            name = item.get('name', '')
            original_name = item.get('original_name', '')
            en_trans_name = en_trans_item.get('name', '') if self.lang != 'en' else None

            title = label = name if self.lang == 'en' else en_trans_name or original_name
            if original_language != self.lang:
                label = en_trans_name or name

            title = title or list_title
            label = label or list_title

            plot = item.get('overview', item_data.get('plot', ''))
            tagline = item.get('tagline', '0')

            if self.lang != 'en':
                en_plot = en_trans_item.get('overview', '')
                plot = plot if plot != '0' else en_plot

                en_tagline = en_trans_item.get('tagline', '')
                tagline = tagline if tagline != '0' else en_tagline

            premiered = item.get('first_air_date', '0')
            year_match = re.search(r'(\d{4})', premiered)
            year = year_match.group(1) if year_match else '0'

            status = item.get('status', '0')
            studio = item['networks'][0].get('name', '0')

            genres = [d['name'] for d in item.get('genres', [])] or ['0']
            genre = ' / '.join(genres)

            countries = [c['name'] for c in item.get('production_countries', [])] or ['0']
            country = ' / '.join(countries)

            crew = item.get('crew', [])
            directors = [d['name'] for d in crew if d['job'] == 'Director'] or ['0']
            director = ' / '.join(directors)

            writers = [d['name'] for d in crew if d['job'] == 'Writer'] or ['0']
            writer = ' / '.join(writers)


            duration = '46'

            #duration = str(item.get('episode_run_time', ['0'])[0]) if 'episode_run_time' in item and item['episode_run_time'] != [] else '0'

            ratings = item.get('content_ratings', {}).get('results', [])
            mpaa = next((d['rating'] for d in ratings if d['iso_3166_1'] == 'US'), '0')

            plot = item.get('overview', item_data.get('plot', control.lang(32623)))
            plot = client.replaceHTMLCodes(plot)

            tagline = client.replaceHTMLCodes(tagline) if tagline != '0' else '0'

            if self.lang != 'en':
                en_title = en_trans_item.get('name', '')
                if en_title and original_language != 'en':
                    title = label = en_title

                en_plot = en_trans_item.get('overview', '')
                plot = plot if plot != '0' else client.replaceHTMLCodes(en_plot)

                en_tagline = en_trans_item.get('tagline', '')
                tagline = tagline if tagline != '0' else client.replaceHTMLCodes(en_tagline)

            cast = item.get('aggregate_credits', {}).get('cast', [])[:30]
            castwiththumb = [
                {'name': person['name'], 'role': person['roles'][0]['character'], 'thumbnail': self.tmdb_img_link % (c.tmdb_profilesize, person['profile_path']) if person.get('profile_path') else ''}
                for person in cast
            ] or '0'

            poster1 = item_data.get('poster', '0')
            poster_path = item.get('poster_path')
            poster2 = self.tmdb_img_link % (c.tmdb_postersize, poster_path) if poster_path else None

            fanart_path = item.get('backdrop_path')
            fanart1 = self.tmdb_img_link % (c.tmdb_fanartsize, fanart_path) if fanart_path else '0'

            poster3 = fanart2 = None
            banner = clearlogo = clearart = landscape = '0'
            if self.hq_artwork == 'true' and tvdb != '0':
                temp_art = fanart_tv.get_fanart_tv_art(tvdb=tvdb)
                poster3 = temp_art.get('poster', '0')
                fanart2 = temp_art.get('fanart', '0')
                banner = temp_art.get('banner', '0')
                landscape = temp_art.get('landscape', '0')
                clearlogo = temp_art.get('clearlogo', '0')
                clearart = temp_art.get('clearart', '0')

            poster = poster3 or poster1 or poster2
            fanart = fanart2 or fanart1

            item = {
                'title': title, 'originaltitle': title, 'label': label, 'year': year,
                'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'poster': poster, 'fanart': fanart,
                'banner': banner, 'clearlogo': clearlogo, 'clearart': clearart,
                'landscape': landscape, 'premiered': premiered, 'studio': studio,
                'genre': genre, 'duration': duration, 'mpaa': mpaa, 'writer': writer,
                'director': director, 'country': country,
                'castwiththumb': castwiththumb, 'plot': plot, 'status': status, 'tagline': tagline
            }

            item = {k: v for k, v in item.items() if v != '0'}

            self.list[i].update(item)
            meta = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'lang': self.lang, 'user': self.user, 'item': item}
            self.meta.append(meta)

        except Exception as e:
            import traceback
            c.log(f'[CM Error] Traceback: {traceback.format_exc()}')
            c.log(f'[CM Error] Exception: {e}')

    def super_info_original(self, i):
        try:
            if self.list[i]['metacache'] is True:
                return

            imdb = self.list[i]['imdb'] if 'imdb' in self.list[i] else '0'
            tmdb = self.list[i]['tmdb'] if 'tmdb' in self.list[i] else '0'
            tvdb = self.list[i]['tvdb'] if 'tvdb' in self.list[i] else '0'

            c.log(f"[CM Debug @ 1412 in tvshows.py] item = {self.list[i]}")

            list_title = self.list[i]['title']

            #trying to fetch a missing tmdb id
            if tmdb == '0' and imdb != '0':
                try:
                    url = self.tmdb_by_imdb % imdb
                    result = self.session.get(url, timeout=10).json()

                    tv_results = result['tv_results'][0]
                    tmdb = str(tv_results['id']) or '0'
                except Exception:
                    pass

            if tmdb == '0':
                try:
                    url = self.search_link % (quote(self.list[i]['title'])) + '&first_air_date_year=' + self.list[i]['year']
                    result = client.request(url)
                    result = json.loads(result)
                    results = result['results']
                    show = [r for r in results if cleantitle.get(r.get('name'))\
                        == cleantitle.get(list_title)][0]# and re.findall('(\d{4})', r.get('first_air_date'))[0] == self.list[i]['year']][0]
                    tmdb = str(show.get('id')) or '0'

                except Exception:
                    pass

            if tmdb == '0':
                raise Exception()


            en_url = self.tmdb_api_link % (tmdb)
            foreign_url = en_url + ',translations'

            url = en_url if self.lang == 'en' else foreign_url
            r = self.session.get(url, timeout=10)
            r.raise_for_status()
            r.encoding = 'utf-8'
            item = r.json()

            if item is None:
                raise Exception()

            if imdb == '0' and 'imdb_id' in item['external_ids']:
                imdb = item['external_ids']['imdb_id'] or '0'

            if tvdb == '0' and 'tvdb_id' in item['external_ids']:
                tvdb = str(item['external_ids']['tvdb_id']) or '0'

            original_language = item.get('original_language', '')

            if self.lang == 'en':
                en_trans_item = None
            else:
                try:
                    translations = item['translations']['translations']
                    en_trans_item = [x['data'] for x in translations if x['iso_639_1'] == 'en'][0]
                except Exception:
                    en_trans_item = {}

            name = item.get('name', '')
            original_name = item.get('original_name', '')
            #en_trans_name = en_trans_item.get('name', '') if not self.lang == 'en' else None
            en_trans_name = None if self.lang == 'en' else en_trans_item.get('name', '')

            if self.lang == 'en':
                title = label = name
            else:
                title = en_trans_name or original_name
                if original_language == self.lang:
                    label = name
                else:
                    label = en_trans_name or name
            if not title:
                title = list_title
            if not label:
                label = list_title

            plot = item['overview'] or self.list[i]['plot'] or ''
            tagline = item.get('tagline', '') or '0'

            if not self.lang == 'en':
                if plot == '0':
                    en_plot = en_trans_item.get('overview') or ''
                    if en_plot:
                        plot = en_plot

                if tagline == '0':
                    en_tagline = en_trans_item.get('tagline') or ''
                    if en_tagline:
                        tagline = en_tagline

            premiered = item['first_air_date'] or '0'

            try:
                year = re.findall(r'(\d{4})', premiered)[0]
            except Exception:
                year = ''
            if not year :
                year = '0'

            status = item['status'] or '0'
            studio = item['networks'][0]['name'] or '0'

            genres = item['genres']
            if genres:
                genres = [d['name'] for d in genres]
                genre = ' / '.join(genres)
            else:
                genre = '0'

            countries = item['production_countries'] or []
            if countries:
                countries = [c['name'] for c in countries]
                country = ' / '.join(countries)
            else:
                country = '0'

            directors = item.get('crew', [])
            if directors:
                directors = [d['name'] for d in directors if d['job'] == 'Director']
                director = ' / '.join(directors)
            else:
                director = '0'

            writers = item.get('crew', [])
            if writers:
                writers = [d['name'] for d in writers if d['job'] == 'Writer']
                writer = ' / '.join(writers)
            else:
                writer = '0'

            duration = str(item['episode_run_time'][0]) or '0'

            m = item['content_ratings']['results']
            if m:
                mpaa = [d['rating'] for d in m if d['iso_3166_1'] == 'US'][0]
            else:
                mpaa = '0'

            try:
                status = item['status']
            except Exception:
                status = ''
            if not status:
                status = '0'

            plot = item['overview'] if 'overview' in item and item['overview'] != ''\
                else self.list[i]['plot']
            if not plot:
                plot = 'The Crew - No Plot Available'
            plot = client.replaceHTMLCodes(str(plot))

            tagline = item['tagline'] or '0'
            if tagline != '0':
                tagline = client.replaceHTMLCodes(str(tagline))

            if not self.lang == 'en':
                try:
                    translations = item.get('translations', {})
                    translations = translations.get('translations', [])
                    trans_item = [x['data'] for x in translations if x.get('iso_639_1') == 'en'][0]

                    en_title = trans_item.get('name', '')
                    if en_title and not original_language == 'en':
                        title = label = str(en_title)

                    if plot == '0':
                        en_plot = trans_item.get('overview', '')
                        if en_plot:
                            plot = client.replaceHTMLCodes(str(en_plot))

                    if tagline == '0':
                        en_tagline = trans_item.get('tagline', '')
                        if en_tagline:
                            tagline = client.replaceHTMLCodes(str(en_tagline))
                except Exception:
                    pass

            castwiththumb = []
            try:
                cast = item['aggregate_credits']['cast'][:30]
                for person in cast:
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

            poster1 = self.list[i].get('poster', '0') or '0'

            poster_path = item.get('poster_path')
            if poster_path:
                poster2 = self.tmdb_img_link % (c.tmdb_postersize, poster_path)
                poster2 = str(poster2)
            else:
                poster2 = None

            fanart_path = item.get('backdrop_path')
            if fanart_path:
                fanart1 = self.tmdb_img_link % (c.tmdb_fanartsize, fanart_path)
                fanart1 = str(fanart1)
            else:
                fanart1 = '0'

            poster3 = fanart2 = None
            banner = clearlogo = clearart = landscape = '0'
            if self.hq_artwork == 'true' and not tvdb == '0':
                temp_art = fanart_tv.get_fanart_tv_art(tvdb=tvdb)
                poster3 = temp_art.get('poster', '0')
                fanart2 = temp_art.get('fanart', '0')
                banner = temp_art.get('banner', '0')
                landscape = temp_art.get('landscape', '0')
                clearlogo = temp_art.get('clearlogo', '0')
                clearart = temp_art.get('clearart', '0')


            poster = poster3 or poster1 or poster2
            fanart = fanart2 or fanart1

            item = {
                    'title': title, 'originaltitle': title, 'label': label, 'year': year,
                    'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'poster': poster, 'fanart': fanart,
                    'banner': banner, 'clearlogo': clearlogo, 'clearart': clearart,
                    'landscape': landscape, 'premiered': premiered, 'studio': studio,
                    'genre': genre, 'duration': duration, 'mpaa': mpaa, 'writer': writer,
                    'director': director, 'country': country,
                    'castwiththumb': castwiththumb, 'plot': plot, 'status': status, 'tagline': tagline
                    }

            item = dict((k,v) for k, v in item.items() if not v == '0')

            self.list[i].update(item)

            meta = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'lang': self.lang, 'user': self.user, 'item': item}
            self.meta.append(meta)
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1494 in tvshows.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1494 in tvshows.py]Exception raised. Error = {e}')
            pass
        #except Exception as e:
            #c.log(f"Inside tvshows - superinfo - Exception raised: error = {e}")

    def tvshowDirectory(self, items):
        if items is None or len(items) == 0:
            control.idle()
            control.infoDialog(c.lang(32500), sound=False, icon='INFO')
            return


        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])

        traktIndicatorInfo = trakt.getTraktIndicatorsInfo()
        addon_poster, addon_banner = c.addon_poster(), c.addon_banner()
        addon_fanart, setting_fanart = c.addon_fanart(), control.setting('fanart')
        addon_clearlogo, addon_clearart = c.addon_clearlogo(), c.addon_clearart()
        addon_discart = c.addon_discart()

        traktCredentials = trakt.get_trakt_credentials_info()
        indicators = playcount.get_tvshow_indicators(refresh=True) if action == 'tvshows' else playcount.get_tvshow_indicators()
        flatten = control.setting('flatten.tvshows') or 'false'

        #cm - menus
        findSimilar = c.lang(32100)
        playRandom = c.lang(32535)
        queueMenu = c.lang(32065)
        watchedMenu = c.lang(32068) if traktIndicatorInfo is True else c.lang(32066)
        unwatchedMenu = c.lang(32069) if traktIndicatorInfo is True else c.lang(32067)
        traktManagerMenu = c.lang(32515)
        addToLibrary = c.lang(32551)
        infoMenu = c.lang(32101)
        nextMenu = c.lang(32053)
        playtrailermenu = c.lang(32381)

        for i in items:
            try:
                #cm - for some reason trakt returns movies too sometimes so check for seasons key
                if 'seasons' not in i:
                    continue

                label = i['label'] if 'label' in i and i['label'] != '0' else i['title']
                status = i.get('status', '')
                try:
                    premiered = i['premiered']
                    if (premiered == '0' and status in ['Upcoming', 'In Production', 'Planned']) or (int(re.sub('[^0-9]', '', premiered)) > int(re.sub('[^0-9]', '', str(self.today_date)))):

                        #changed by cm -  27-4-2023
                        colorlist = [32589, 32590, 32591, 32592, 32593, 32594, 32595, 32596, 32597, 32598]
                        colornr = colorlist[int(control.setting('unaired.identify'))]
                        unairedcolor = re.sub(r"\][\w\s]*\[", "][I]%s[/I][", control.lang(int(colornr)))
                        label = unairedcolor % label

                        if unairedcolor == '':
                            unairedcolor = '[COLOR red][I]%s[/I][/COLOR]'
                except Exception:
                    pass

                poster = i['poster'] if 'poster' in i and i['poster'] != '0' else addon_poster
                fanart = i['fanart'] if 'fanart' in i and i['fanart'] != '0' else addon_fanart
                clearlogo = i['clearlogo'] if 'clearlogo' in i and i['clearlogo'] != '0' else addon_clearlogo
                clearart = i['clearart'] if 'clearart' in i and i['clearart'] != '0' else addon_clearart
                discart = i['discart'] if 'discart' in i and i['discart'] != '0' else addon_discart
                banner1 = i.get('banner', '')
                banner = banner1 or fanart or addon_banner
                if 'landscape' in i and i['landscape'] != '0':
                    landscape = i['landscape']
                else:
                    landscape = fanart

                systitle = quote_plus(i['title'])

                meta = {
                    'poster': poster,
                    'fanart': fanart,
                    'banner': banner,
                    'clearlogo': clearlogo,
                    'clearart': clearart,
                    'discart': discart,
                    'landscape': landscape
                    }

                sysmeta = quote_plus(json.dumps(meta))

                imdb = i.get('imdb')
                tmdb = i.get('tmdb')
                year = i.get('year')

                # meta = dict((k,v) for k, v in i.items() if not v == '0')
                # build meta by filtering out '0' values and merging extra keys in one step
                meta = {
                    **{k: v for k, v in i.items() if v != '0'},
                    'code': tmdb,
                    'imdbnumber': imdb,
                    'mediatype': 'tvshow',
                    'tvshowtitle': i.get('title'),
                    'tmdb_id': str(tmdb),
                    'imdb_id': imdb,
                    'dev': 'Classy'
                }

                trailer = c.ensure_str(i['trailer']) if 'trailer' in i and i['trailer'] != '' else '0'

                trailer_url = quote(trailer) if trailer != '0' else '0'
                search_name = systitle

                if trailer_url == '0':
                    meta['trailer'] = f'{sysaddon}?action=trailer&name={search_name}&imdb={imdb}&tmdb={tmdb}&mediatype=tvshow&meta={sysmeta}'
                else:
                    meta['trailer'] = f'{sysaddon}?action=trailer&name={search_name}&url={trailer_url}&imdb={imdb}&tmdb={tmdb}&mediatype=tvshow&meta={sysmeta}'

                if 'duration' not in meta or meta['duration'] == '0':
                    meta['duration'] = '45'

                try:
                    #meta.update({'duration': str(int(meta['duration']) * 60)})
                    meta['duration'] = str(int(meta['duration']) * 60)
                    #c.log(f"[CM Debug @ 1613 in tvshows.py] durationm = {meta['duration']}")

                except Exception:
                    pass
                try:
                    #meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
                    meta['genre'] = cleangenre.lang(meta['genre'], self.lang)
                except Exception:
                    pass

                if 'castwiththumb' in i and i['castwiththumb'] != '0':
                    meta.pop('cast', '0')

                try:
                    overlay = int(playcount.getTVShowOverlay(indicators, tmdb))
                    if overlay == 7:
                        meta.update({'playcount': 1, 'overlay': 7})
                    else:
                        meta.update({'playcount': 0, 'overlay': 6})
                except Exception:
                    pass

                related_url = quote_plus(self.related_link % tmdb)
                cm = [
                    (
                        playtrailermenu,
                        f'RunPlugin({sysaddon}?action=trailer&name={systitle}&imdb={imdb}&tmdb={tmdb}&mediatype=tvshow&meta={sysmeta})',
                    ),
                    (
                        findSimilar,
                        f'Container.Update({sysaddon}?action=tvshows&url={related_url})',
                    ),
                    (
                        playRandom,
                        f'RunPlugin({sysaddon}?action=random&rtype=season&tvshowtitle={systitle}&imdb={imdb}&tmdb={tmdb})',
                    ),
                    (
                        queueMenu,
                        f'RunPlugin({sysaddon}?action=queueItem)',
                    ),
                ]
                # TODO: fix watched/unwatched
                if overlay == 6:
                    cm.append((watchedMenu, f'RunPlugin({sysaddon}?action=tvPlaycount&name={systitle}&imdb{imdb}&tmdb={tmdb}&query=7)'))
                else:
                    cm.append((unwatchedMenu, f'RunPlugin({sysaddon}?action=tvPlaycount&name={systitle}&imdb={imdb}&tmdb={tmdb}&query=6)'))
                if traktCredentials is True:
                    cm.append((traktManagerMenu, f'RunPlugin({sysaddon}?action=traktManager&name={systitle}&tmdb={tmdb}&content=tvshow)'))
                cm.append((addToLibrary, f'RunPlugin({sysaddon}?action=tvshowToLibrary&tvshowtitle={systitle}&year={year}&imdb={imdb}&tmdb={tmdb})'))

                art ={
                    'icon': poster,
                    'thumb': landscape or fanart,
                    'poster': poster,
                    'tvshow.poster': poster,
                    'season.poster': poster,
                    'banner': banner,
                    'landscape': landscape
                    }

                art['fanart'] = fanart if setting_fanart == 'true' else c.addon_fanart()
                if 'clearlogo' in i and i['clearlogo'] != '0':
                    art['clearlogo'] = i['clearlogo']
                if 'clearart' in i and i['clearart'] != '0':
                    art['clearart'] = i['clearart']

                meta['art'] = art

                try:
                    item = control.item(label=label, offscreen=True)
                except Exception:
                    item = control.item(label=label)


                item.setArt(art)

                #c.log(f"[CM Debug @ 1837 in tvshows.py] tmdb = {tmdb}")
                index = c.search_tmdb_index_in_indicators(tmdb, indicators) or 0

                if index == -1:
                    #tmdb not in indicators so
                    watched_episodes = 0
                else:
                    watched_episodes = c.count_wachted_items_in_indicators(index, indicators)



                if index in [None, 0, -1]:
                    watched_episodes = 0
                else:
                    watched_episodes = c.count_wachted_items_in_indicators(index, indicators) or 0

                if 'episodes' not in i or i['episodes'] is None:
                    total_episodes = c.count_total_items_in_indicators(index, indicators) or 0
                else:
                    total_episodes = i['episodes'] or 0

                # Ensure numeric ints to avoid type errors from None or unexpected types
                try:
                    total_episodes = int(total_episodes)
                except Exception:
                    total_episodes = 0
                try:
                    watched_episodes = int(watched_episodes)
                except Exception:
                    watched_episodes = 0

                total_episodes = max(total_episodes, 0)
                # Compute unwatched safely and clamp to non-negative
                unwatched_episodes = total_episodes - watched_episodes
                unwatched_episodes = max(unwatched_episodes, 0)
                if unwatched_episodes == 0:
                    watched_episodes = total_episodes

                item.setProperties({'WatchedEpisodes': watched_episodes, 'UnWatchedEpisodes': unwatched_episodes})
                item.setProperties({'TotalSeasons': i['seasons'], 'TotalEpisodes': total_episodes})

                genre = i.get('genre') or '0'

                genres = c.string_split_to_list(genre) if genre != '0' else []
                studio = i.get('studio') or '0'

                studios = c.string_split_to_list(studio) if studio != '0' else []
                country = i.get('country') or '0'

                if country != '0':
                    countries = c.string_split_to_list(country)
                    countries = [x.upper() for x in countries]
                else:
                    countries = []


                info_tag = ListItemInfoTag(item, 'video')
                infolabels = control.tagdataClean(meta)

                infolabels.update({'genre': genres, 'studio': studios, 'country': countries})

                info_tag.set_info(infolabels)
                unique_ids = {'imdb': imdb, 'tmdb': str(tmdb)}
                info_tag.set_unique_ids(unique_ids)

                if 'cast' in meta:
                    cast = meta.get('cast')
                    info_tag.set_cast(cast)
                elif 'castwiththumb' in meta:
                    cast = meta.get('castwiththumb')
                    info_tag.set_cast(meta.get('castwiththumb'))
                else:
                    info_tag.set_cast([])

                item.addContextMenuItems(cm)

                if flatten == 'true':
                    url = f"{sysaddon}?action=episodes&tvshowtitle={systitle}&year={year}&imdb={imdb}&tmdb={tmdb}&fanart={fanart}&duration={i['duration']}&meta={sysmeta}"
                    #url = f'{sysaddon}?action=episodes&tvshowtitle={systitle}&year={year}&imdb={imdb}&tmdb={tmdb}&fanart={fanart}&duration={meta["duration"]}&meta={sysmeta}'
                else:
                    #url = '%s?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&meta=%s' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)
                    url = f'{sysaddon}?action=seasons&tvshowtitle={systitle}&year={year}&imdb={imdb}&tmdb={tmdb}&meta={sysmeta}'

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)

            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 1709 in tvshows.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 1709 in tvshows.py]Exception raised. Error = {e}')




        try:
            url = items[0]['next']
            if url not in ['0', '', None, 'None']:
                icon = control.addonNext()
                q_url = quote_plus(url)
                url = f'{sysaddon}?action=tvshowPage&url={q_url}'

                try:
                    item = control.item(label=nextMenu, offscreen=True)
                except Exception:
                    item = control.item(label=nextMenu)

                item.setArt({
                    'icon': icon,
                    'thumb': icon,
                    'poster': icon,
                    'banner': icon,
                    'fanart': addon_fanart
                    })

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
        except Exception as e:
            c.log(f"Exception in tvshows.adddirectory() #2: error = {e}")


        control.content(syshandle, 'tvshows')
        control.directory(syshandle, cacheToDisc=True)

    def addDirectory(self, items, queue=False):
        if items is None or len(items) == 0:
            control.idle()
            c.log(f"[CM Debug @ 2053 in tvshows.py] aantal items = {len(items)}")
            # sys.exit()
            return

        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])
        addon_fanart, art_path = c.addon_fanart(), c.get_art_path()


        queueMenu = control.lang(32065)
        playRandom = control.lang(32535)
        addToLibrary = control.lang(32551)

        c.log(f"[CM Debug @ 2068 in tvshows.py] items = {items}")
        #{
        # 'name': 'A&E',
        # 'url': 'https://api.themoviedb.org/3/discover/tv?api_key=0049795edb57568b95240bc9e61a9dfc&sort_by=first_air_date.desc&with_networks=129&page=1',
        # 'image': 'https://image.tmdb.org/t/p/original/ptSTdU4GPNJ1M8UVEOtA0KgtuNk.png',
        # 'action': 'tvshows'
        # }
        for i in items:
            try:
                name = i['name']
                plot = i.get('plot') or '[CR]'

                if i['image'].startswith('http'):
                    thumb = i['image']
                elif art_path is not None:
                    thumb = os.path.join(art_path, i['image'])
                else:
                    thumb = c.addon_thumb()

                #url = '%s?action=%s' % (sysaddon, i['action'])
                url = f'{sysaddon}?action={i["action"]}'

                try:
                    #url += '&url=%s' % quote_plus(i['url'])
                    url += f'&url={quote_plus(i["url"])}'
                except Exception:
                    pass

                cm = []
                if 'context' in i:
                    cm.append((playRandom, f'RunPlugin({sysaddon}?action=random&rtype=show&url={quote_plus(i["context"])})'))

                if queue is True:
                    cm.append((queueMenu, f'RunPlugin({sysaddon}?action=queueItem)'))

                if 'context' in i:
                    cm.append((addToLibrary, f'RunPlugin({sysaddon}?action=tvshowsToLibrary&url={quote_plus(i["context"])})'))

                try:
                    item = control.item(label=name, offscreen=True)
                except Exception:
                    item = control.item(label=name)

                item.setArt({'icon': thumb, 'thumb': thumb, 'poster': thumb, 'fanart': addon_fanart})
                item.setInfo(type='video', infoLabels={'plot': plot})

                item.addContextMenuItems(cm)

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 2116 in tvshows.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 2116 in tvshows.py]Exception raised. Error = {e}')
                pass
            #except Exception:

                #pass

        control.content(syshandle, 'tvshows')
        control.directory(syshandle, cacheToDisc=True)
