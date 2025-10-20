# -*- coding: utf-8 -*-
'''
 ***********************************************************
 * The Crew Add-on
 *
 * @file movies.py
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
#import base64
#import traceback
import json

from urllib.parse import quote_plus, parse_qsl, urlparse, urlsplit, urlencode
import sqlite3 as database

from sqlite3 import OperationalError
#from bs4 import BeautifulSoup

import concurrent.futures

import requests

from ..modules import trakt
from ..modules import keys
from ..modules import bookmarks
from ..modules import fanart as fanart_tv
from ..modules import cleangenre
#from ..modules import cleantitle
from ..modules import control
from ..modules import client
from ..modules import cache
from ..modules import metacache
from ..modules import playcount
from ..modules import workers
from ..modules import views
from ..modules import utils
from ..modules.listitem import ListItemInfoTag
#from ..modules import log_utils
from . import navigator
from ..modules.crewruntime import c

parameters = dict(parse_qsl(sys.argv[2].replace('?', ''))) if len(sys.argv) > 1 else {}
action = parameters.get('action')

class movies:
    def __init__(self):

        self.count = int(control.setting('page.item.limit'))
        self.list = self.on_deck_list=[]
        self.session = requests.Session()
        self.showunaired = control.setting('showunaired') or 'true'

        self.imdb_link:str = 'https://www.imdb.com'
        self.trakt_link: str = 'https://api.trakt.tv'
        self.tmdb_link:str = 'https://api.themoviedb.org/3/'

        #####
        # dates
        self.datetime = datetime.datetime.now()
        self.systime = (self.datetime).strftime('%Y%m%d%H%M%S%f')
        self.year_date = (self.datetime - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        self.month_date = (self.datetime - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        self.today_date = (self.datetime).strftime('%Y-%m-%d')
        self.year = self.datetime.strftime('%Y')
        self.country = control.setting('official.country') or 'US'

        #####
        # users
        self.trakt_user = control.setting('trakt.user').strip()
        self.imdb_user = control.setting('imdb.user').replace('ur', '')
        self.fanart_tv_user = control.setting('fanart.tv.user')

        self.tmdb_user = control.setting('tm.personal_user') or control.setting('tm.user')
        if not self.tmdb_user:
            self.tmdb_user = keys.tmdb_key

        self.user = self.tmdb_user

        #####
        # Settings
        self.lang = control.apiLanguage()['trakt']

        #####cm#
        # define links
        self.search_link = f'{self.trakt_link}/search/movie?limit=20&page=1&query='
        self.fanart_tv_art_link = 'https://webservice.fanart.tv/v3/movies/%s'
        self.fanart_tv_level_link = 'https://webservice.fanart.tv/v3/level'
        self.tmdb_img_link = 'https://image.tmdb.org/t/p/%s%s'
        self.tm_art_link = (f'{self.tmdb_link}movie/%s/images?api_key={self.tmdb_user}&language=en-US&include_image_language=en{self.lang},null')
        self.tmdb_external_ids_by_tmdb = (f'{self.tmdb_link}movie/%s/external_ids?api_key={self.tmdb_user}&language=en-US')

        ######
        # imdb
        self.keyword_link = f'https://www.imdb.com/search/title?title_type=feature,tv_movie,documentary&num_votes=100,&keywords=%s&sort=moviemeter,asc&count={self.count}&start=1'
        self.oscarsnominees_link = f'https://www.imdb.com/search/title?title_type=feature,tv_movie&production_status=released&groups=oscar_best_picture_nominees&sort=year,desc&count={self.count}&start=1'
        self.certification_link = f'https://www.imdb.com/search/title?title_type=feature,tv_movie&num_votes=100,&production_status=released&certificates=%s&sort=moviemeter,asc&count={self.count}&start=1'

        ######
        # tmdb
        self.person_link = (f'{self.tmdb_link}search/person?api_key={self.tmdb_user}&query=%s&include_adult=false&language=en-US&page=1')
        self.person_search_link = (f'{self.tmdb_link}person/%s?api_key={self.tmdb_user}&?language=en-US')
        self.persons_link = f'{self.tmdb_link}person/popular?api_key={self.tmdb_user}&language=en-US&page=1'
        self.personlist_link = (f'{self.tmdb_link}trending/person/day?api_key={self.tmdb_user}&language=en-US')
        self.personmovies_link = (f'{self.tmdb_link}person/%s/movie_credits?api_key={self.tmdb_user}&language=en-US')

        self.oscars_link = (f'{self.tmdb_link}list/28?api_key={self.tmdb_user}&language=en-US&page=1' )
        self.xristmas_link = (f'{self.tmdb_link}list/8280352?api_key={self.tmdb_user}&language=en-US&page=1' )
        self.theaters_link = (f'{self.tmdb_link}discover/movie?api_key={self.tmdb_user}&now_playing?language=en-US&page=1&region=US|UK&sort_by=popularity.desc')
        self.year_link = (f'{self.tmdb_link}discover/movie?api_key={self.tmdb_user}&include_adult=false&include_video=false&language=en-US&region=US&sort_by=release_date.desc&year=%s&page=1')
        self.language_link = (f'{self.tmdb_link}discover/movie?api_key={self.tmdb_user}&include_adult=false&include_video=false&sort_by=popularity.desc&with_original_language=%s&page=1')
        self.year_link = (f'{self.tmdb_link}discover/movie?api_key={self.tmdb_user}&include_adult=false&include_video=false&language=en-US&release_date.lte={self.today_date}&region=US&sort_by=release_date.desc&year=%s&page=1')
        self.featured_link = (f'{self.tmdb_link}discover/movie?api_key={self.tmdb_user}&include_adult=false&include_video=false&language=en-US&page=1&sort_by=popularity.desc&with_release_type=1|2|3&release_date.gte=date[60]&release_date.lte=date[0]')
        self.popular_link = (f'{self.tmdb_link}discover/movie?api_key={self.tmdb_user}&include_adult=false&include_video=false&language=en-US&page=1&sort_by=popularity.desc&with_release_type=1|2|3&release_date.gte=date[60]&release_date.lte=date[0]')
        self.views_link = (f'{self.tmdb_link}discover/movie?api_key={self.tmdb_user}&include_adult=false&include_video=false&language=en-US&page=1&sort_by=popularity.desc&vote_average.gte=8&vote_average.lte=10&with_original_language=en')
        self.genre_link = (f'{self.tmdb_link}discover/movie?api_key={self.tmdb_user}&include_adult=false&include_video=false&language=en-US&sort_by=release_date.desc&release_date.lte=date[0]&with_genres=%s&page=1')

        self.tmdb_by_imdb = f'{self.tmdb_link}find/%s?api_key={self.tmdb_user}&external_source=imdb_id'
        self.tm_search_link = f'{self.tmdb_link}search/movie?api_key={self.tmdb_user}&language=en-US&query=%s&page=1'
        self.related_link = f'{self.tmdb_link}movie/%s/similar?api_key={self.tmdb_user}&page=1'
        self.tmdb_providers_link = f'{self.tmdb_link}discover/movie?api_key={self.tmdb_user}&sort_by=popularity.desc&with_watch_providers=%s&watch_region=%s&page=1'
        self.tmdb_art_link = f'{self.tmdb_link}movie/%s/images?api_key={self.tmdb_user}&language=en-US&include_image_language=en,%s,null'

        self.tmdb_api_link = f'{self.tmdb_link}movie/%s?api_key={self.tmdb_user}&language={self.lang}&append_to_response=credits,ratings,external_ids'
        self.tmdb_networks_link = f'{self.tmdb_link}discover/movie?api_key={self.tmdb_user}&with_networks=%s&language=en-US&release_date.lte={self.today_date}&sort_by=primary_release_date.desc&page=1'
        self.tmdb_networks_no_unaired_link = f'{self.tmdb_link}discover/movie?api_key={self.tmdb_user}&first_air_date.lte={self.today_date}&sort_by=first_air_date.desc&with_networks=%s&page=1'
        self.tmdb_search_movie_link = f'{self.tmdb_link}search/movie?api_key={self.tmdb_user}&language=en-US&query=%s&page=1'
        self.search_link = f'{self.tmdb_link}search/movie?api_key={self.tmdb_user}&language=en-US&query=%s&page=1'
        self.related_link = f'{self.tmdb_link}movie/%s/similar?api_key={self.tmdb_user}&language=en-US&page=1'
        self.tmdb_info_tvshow_link = f'{self.tmdb_link}movie/%s?api_key={self.tmdb_user}&language={self.lang}&append_to_response=images'
        self.tmdb_by_imdb = f'{self.tmdb_link}find/%s?api_key={self.tmdb_user}&external_source=imdb_id'

        self.tmdb_movie_top_rated_link = (f'{self.tmdb_link}movie/top_rated?api_key={self.tmdb_user}&language={self.lang}&sort_by=popularity.desc&page=1')
        self.tmdb_movie_popular_link = (f'{self.tmdb_link}movie/popular?api_key={self.tmdb_user}&language={self.lang}&page=1')
        self.tmdb_movie_trending_day_link = (f'{self.tmdb_link}trending/movie/day?api_key={self.tmdb_user}')
        self.tmdb_movie_trending_week_link = (f'{self.tmdb_link}trending/movie/week?api_key={self.tmdb_user}')
        self.tmdb_movie_discover_year_link = (f'{self.tmdb_link}discover/movie?api_key={self.tmdb_user}&language=%s&sort_by=popularity.desc&first_air_date_year={self.year}&include_null_first_air_dates=false&with_original_language=en&page=1')


        self.halloween_link = f'{self.tmdb_link}discover/movie?api_key={self.tmdb_user}&with_genres=27&language=en-US&sort_by=popularity.desc&page=1'
        self.halloween_fun_link = f'{self.trakt_link}/users/istoit/lists/halloween-fun-frights?sort=rank,asc/items'

        ###cm#
        # Trakt
        self.trending_link = f'{self.trakt_link}/movies/trending?limit={self.count}&page=1'
        self.traktlists_link = f'{self.trakt_link}/users/me/lists'
        self.traktlikedlists_link = f'{self.trakt_link}/users/likes/lists?limit=1000000'
        self.traktlist_link = f'{self.trakt_link}/users/%s/lists/%s/items'
        self.traktcollection_link = f'{self.trakt_link}/users/me/collection/movies'
        self.traktwatchlist_link = f'{self.trakt_link}/users/me/watchlist/movies'
        self.traktfeatured_link = f'{self.trakt_link}/recommendations/movies?limit={self.count}'
        self.trakthistory_link = f'{self.trakt_link}/users/me/history/movies?limit={self.count}&page=1'
        self.onDeck_link = f'{self.trakt_link}/sync/playback/movies?extended=full&limit={self.count}'

        self.movieProgress_link = f'{self.trakt_link}/sync/playback/movies?extended=full&limit={self.count}'
        self.collection_link = f'{self.trakt_link}/users/me/collection/movies?extended=full&limit={self.count}'

    def __del__(self):
        self.session.close()

    def get(self, url:str, tid=0, idx=True, create_directory=True):
        """
        Get a list of movies from the given url
        """
        try:
            # Check for an empty url
            if not url:
                c.log('No URL provided, returning empty list.')
                return []

            # If starts with https, i have a full link so i can use it directly
            # no need to add any suffixes or prefixes
            if url.startswith('http'):
                c.log(f'[CM DEBUG @ 176 in movies.py] url= {url}')
            else:
                url_link = getattr(self, f"{url}_link", None)
                if url_link is None:
                    c.log(f'Failed to find attribute {url}_link')
                    return []
                url = url_link

            # Replace dates with the current date minus the offset
            for days_offset in re.findall(r'date\[(\d+)\]', url):
                replacement_date = (self.datetime - datetime.timedelta(days=int(days_offset))).strftime('%Y-%m-%d')
                url = url.replace(f'date[{days_offset}]', replacement_date)

            # Get the netloc from the url
            parsed_url_netloc = urlparse(url).netloc.lower()#.decode('utf-8')
            c.log(f"[CM Debug @ 195 in movies.py] url = {parsed_url_netloc}")

            # If the url is a trakt link and onDeck is in the url
            assert self.trakt_link is not None
            if self.trakt_link in url and url == self.onDeck_link:
                # self.on_deck_list = cache.get(self.trakt_list, 720, url, self.trakt_user)


                self.list = cache.get(self.trakt_list, 0, url, self.trakt_user)
                c.log(f"[CM Debug @ 203 in movies.py] self.list length = {len(self.list)}")
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)

                # self.list = self.list[::-1]
            elif 'collection' in url:
                c.log(f"[CM Debug @ 211 in movies.py] url = {url}")
                self.list = self.collection_list()
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=False)
            elif 'movieProgress' in url:
                self.list = cache.get(self.movie_progress_list, 0)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)

            elif parsed_url_netloc in self.trakt_link and '/users/' in url:
                try:
                    if url == self.trakthistory_link:
                        raise Exception()
                    if trakt.getActivity() > cache.timeout(self.trakt_list, url, self.trakt_user):
                        raise Exception()
                    self.list = cache.get(self.trakt_list, 720, url, self.trakt_user)
                except Exception:
                    self.list = cache.get(self.trakt_list, 6, url, self.trakt_user)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)

            elif parsed_url_netloc in self.search_link and '/search/movie' in url:

                self.list = cache.get(self.tmdb_list, 1, url)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)

            elif parsed_url_netloc in self.trakt_link and '/sync/playback/' in url:
                self.list = self.trakt_list(url, self.trakt_user)
                self.list = sorted(self.list, key=lambda k: int(k['paused_at']), reverse=True)

            elif parsed_url_netloc in self.trakt_link:
                #self.list = cache.get(self.trakt_list, 24, url, self.trakt_user)
                self.list = self.trakt_list(url, self.trakt_user)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)

            elif parsed_url_netloc in self.tmdb_networks_link and int(tid) > 0:
                #self.list = cache.get(self.tmdb_list, 24, url, tid)
                self.list = self.tmdb_list(url, tid)

            elif parsed_url_netloc in self.tmdb_link and ('/user/' in url or '/list/' in url):
                self.list = cache.get(self.list_tmdb_list, 0, url)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)

            elif parsed_url_netloc in self.tmdb_link and '/movie_credits' in url:
                self.list = cache.get(self.tmdb_cast_list, 24, url)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)

            elif parsed_url_netloc in self.tmdb_link:
                # self.list = cache.get(self.tmdb_list, 24, url)
                self.list = self.tmdb_list(url)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)

            # If idx is True, call the worker
            if idx is True:
                self.worker()

            # If idx is True and create_directory is True, call the movieDirectory
            if idx is True and create_directory is True:
                self.movie_directory(self.list)
            # Return the list
            return self.list
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 262 in movies.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 262 in movies.py]Exception raised. Error = {e}')
            pass
        # except Exception as e:
        #     # Log the error
            c.log(f'Exception raised in movies.get(), error = {e}', 1)




    def getDisabled(self, url, tid=0, idx=True, create_directory=True):
        try:
            #check for an empty url
            if not url or url is None:
                c.log('[CM Debug @ 822 in movies.py] No URL provided, returning empty list.')
                return []

            if isinstance(url, bytes):
                url = url.decode('utf-8')

            if url.startswith('https://'):
                #if starts with https, i have a full link so i can use it directly
                # no need to add any suffixes or prefixes
                c.log(f"[CM DEBUG @ 174 in movies.py] Log url: {url}")
            else:
                url = getattr(self, f"{url}_link", None)


            for days_offset in re.findall(r'date\[(\d+)\]', url):
                replacement_date = (self.datetime - datetime.timedelta(days=int(days_offset))).strftime('%Y-%m-%d')
                url = url.replace(f'date[{days_offset}]', replacement_date)

            #parsed_url_netloc = urlparse(url).netloc.lower()
            parsed_url_netloc = urlparse(url).netloc.decode('utf-8').lower()

            if self.trakt_link in url and url == self.onDeck_link:
                self.on_deck_list = cache.get(self.trakt_list, 720, url, self.trakt_user)
                self.list = []
                self.list = cache.get(self.trakt_list, 0, url, self.trakt_user)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)
                self.list = self.list[::-1]
            elif 'collection' in url:
                self.list = self.collection_list()
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=False)
            elif 'movieProgress' in url:
                self.list = cache.get(self.movie_progress_list, 0)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)


            elif parsed_url_netloc in self.trakt_link and '/users/' in url:
                try:
                    if url != self.trakthistory_link and '/users/me/' in url:
                        if trakt.getActivity() > cache.timeout(self.trakt_list, url, self.trakt_user):
                            raise Exception()
                        self.list = cache.get(self.trakt_list, 720, url, self.trakt_user)
                        #self.list = self.trakt_list(url, self.trakt_user)
                    else:
                        raise Exception()
                except Exception:
                    self.list = cache.get(self.trakt_list, 6, url, self.trakt_user)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)

                #if '/users/me/' in url and '/collection/' in url:
                    #self.list = sorted(self.list, key=lambda k: utils.title_key(k['title']))

            elif parsed_url_netloc in self.search_link and '/search/movie' in url:

                self.list = cache.get(self.tmdb_list, 1, url)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)

            elif parsed_url_netloc in self.trakt_link and '/sync/playback/' in url:
                self.list = self.trakt_list(url, self.trakt_user)
                self.list = sorted(self.list, key=lambda k: int(k['paused_at']), reverse=True)

            elif parsed_url_netloc in self.trakt_link:
                self.list = cache.get(self.trakt_list, 24, url, self.trakt_user)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)

            #elif parsed_url_netloc in self.imdb_link and ('/user/' in url or '/list/' in url):
                #self.list = cache.get(self.imdb_list, 0, url)

            #elif parsed_url_netloc in self.imdb_link:
                #self.list = cache.get(self.imdb_list, 24, url)

            elif parsed_url_netloc in self.tmdb_networks_link and int(tid) > 0:
                #self.list = cache.get(self.tmdb_list, 24, url, tid)
                self.list = self.tmdb_list(url, tid)

            elif parsed_url_netloc in self.tmdb_link and ('/user/' in url or '/list/' in url):
                self.list = cache.get(self.list_tmdb_list, 0, url)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)

            elif parsed_url_netloc in self.tmdb_link and '/movie_credits' in url:
                self.list = cache.get(self.tmdb_cast_list, 24, url)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)

            elif parsed_url_netloc in self.tmdb_link:
                # self.list = cache.get(self.tmdb_list, 24, url)
                self.list = self.tmdb_list(url)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)

            if idx is True:
                self.worker()

            if idx is True and create_directory is True:
                self.movie_directory(self.list)
            return self.list
        except Exception as e: # pylint: disable=W0703
            import traceback
            failure = traceback.format_exc()
            c.log('[CM Debug @ 322 in movies.py]Traceback:: ' + str(failure))
            c.log('[CM Debug @ 323 in movies.py]Exception raised. Error = ' + str(e))
            c.log(f'Exception raised in movies.get(), error = {e}', 1)


    def widget(self):

        self.get(self.featured_link)

        # setting = control.setting('movie.widget')

        # if setting == '2':
        #     self.get(self.trending_link)
        # elif setting == '3':
        #     self.get(self.popular_link)
        # elif setting == '4':
        #     self.get(self.theaters_link)
        # elif setting == '5':
        #     self.get(self.added_link)
        # else:
        # self.get(self.featured_link)


    def search(self):
        """Executes a search operation for TV shows."""

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()

        navigator.navigator.addDirectoryItem(32603, 'movieSearchnew', 'search.png', 'DefaultMovies.png')

        try:
            sql = "SELECT count(*) as aantal FROM sqlite_master WHERE type='table' AND name='movies'"
            dbcur.execute(sql)
            dbcon.commit()
            if dbcur.fetchone()[0] == 0:
                # table does not exist
                sql = "CREATE TABLE movies (id INTEGER PRIMARY KEY AUTOINCREMENT, term TEXT)"
                dbcur.execute(sql)
            dbcon.commit()
        except OperationalError as e:
            c.log(f"[CM Debug @ 422 in movies.py] OperationalError in movies.search, {e}", 1)


        dbcur.execute("SELECT * FROM movies ORDER BY id DESC")
        dbcon.commit()
        cm = []

        search_terms = []
        context_menu_items = []
        rows = dbcur.fetchall()
        delete_option = False
        for _id, term in rows:
            if term not in search_terms:
                delete_option = True
                cm = ((32070, f'movieDeleteTerm&id={_id}'))

                navigator.navigator.addDirectoryItem(
                    f'{term}',
                    f'movieSearchterm&name={term}',
                    'search.png',
                    'DefaultTVShows.png',
                    context=cm,
                )
                search_terms.append(term)
        dbcur.close()

        if delete_option:
            navigator.navigator.addDirectoryItem(32605, 'clearCacheSearch', 'tools.png', 'DefaultAddonProgram.png')

        navigator.navigator.endDirectory()


    def search_new(self):
        """Search for a Movie."""
        control.idle()

        keyboard_header = control.lang(32010)
        keyboard = control.keyboard('', keyboard_header)
        keyboard.doModal()
        search_query = keyboard.getText() if keyboard.isConfirmed() else None

        if search_query is None:
            return

        search_query = search_query.lower()
        clean_search_query = utils.title_key(search_query)

        db_connection = database.connect(control.searchFile)
        db_cursor = db_connection.cursor()
        db_cursor.execute("DELETE FROM movies WHERE term = ?", (search_query,))
        db_cursor.execute("INSERT INTO movies VALUES (?,?)", (None, search_query))
        db_connection.commit()
        db_cursor.close()

        url = self.search_link % quote_plus(clean_search_query)
        self.get(url)



    def search_term(self, query):
        control.idle()
        query = query.lower()
        cleaned_query = utils.title_key(query)

        db_connection = database.connect(control.searchFile)
        db_cursor = db_connection.cursor()
        db_cursor.execute("DELETE FROM movies WHERE term = ?", (query,))
        db_cursor.execute("INSERT INTO movies VALUES (?, ?)", (None, query))
        db_connection.commit()
        db_cursor.close()

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
            db_connection = database.connect(control.searchFile)
            db_cursor = db_connection.cursor()
            db_cursor.execute("DELETE FROM movies WHERE ID = ?", (search_term_id,))
            db_connection.commit()
            db_cursor.close()
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

        Logs any errors encountered during user input, URL formatting,
        or person data retrieval.

        Exceptions:
            Logs any exceptions that occur during user input, URL formatting,
            or person data retrieval.
        """
        try:
            search_header = control.lang(32010)
            keyboard = control.keyboard('', search_header)
            keyboard.doModal()
            search_query = keyboard.getText() if keyboard.isConfirmed() else None

            if not search_query:
                return

            search_query = search_query.lower()
            clean_search_query = utils.title_key(search_query)
            # url = self.person_search_link % quote_plus(clean_search_query)
            url = self.person_link % quote_plus(clean_search_query)
            c.log(f"[CM Debug @ 427 in movies.py] url = {url}")
            self.persons(url)

        except Exception as e:
            c.log(f'Error in person method: {e}')
            return


# TC 2/01/19 started

    #####cm#
    # Completely redone for compatibility with tmdb
    #
    def genres(self):
        genres = [
            {"id": 28, "name": "Action"},
            {"id": 12, "name": "Adventure"},
            {"id": 16, "name": "Animation"},
            {"id": 35, "name": "Comedy"},
            {"id": 80, "name": "Crime"},
            {"id": 99, "name": "Documentary"},
            {"id": 18, "name": "Drama"},
            {"id": 10751, "name": "Family"},
            {"id": 14, "name": "Fantasy"},
            {"id": 36, "name": "History"},
            {"id": 27, "name": "Horror"},
            {"id": 10402, "name": "Music"},
            {"id": 9648, "name": "Mystery"},
            {"id": 10749, "name": "Romance"},
            {"id": 878, "name": "Science Fiction"},
            {"id": 10770, "name": "TV Movie"},
            {"id": 53, "name": "Thriller"},
            {"id": 10752, "name": "War"},
            {"id": 37, "name": "Western"}
        ]

        for i in genres:
            self.list.append(
                {
                    'name': cleangenre.lang(i['name'], self.lang),
                    'url': self.genre_link % i['id'],
                    'image': 'genres.png',
                    'action': 'movies'
                })

        self.addDirectory(self.list)
        return self.list

    def languages(self):
        language_data = [
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
            ('Macedonian', 'mk'),
            ('Norwegian', 'no'),
            ('Persian', 'fa'),
            ('Polish', 'pl'),
            ('Portuguese', 'pt'),
            ('Punjabi', 'pa'),
            ('Romanian', 'ro'),
            ('Russian', 'ru'),
            ('Serbian', 'sr'),
            ('Slovenian', 'sl'),
            ('Spanish', 'es'),
            ('Swedish', 'sv'),
            ('Turkish', 'tr'),
            ('Ukrainian', 'uk')
        ]

        for language_name, language_code in language_data:
            self.list.append({
                'name': language_name,
                'url': self.language_link % language_code,
                'image': 'international.png',
                'action': 'movies'
            })
        self.addDirectory(self.list)
        return self.list


    # @todo fix this
    def certifications(self):
        certificates = [
            '[COLOR dodgerblue][B]¤[/B][/COLOR] [B][COLOR white]G[/COLOR][/B] [COLOR dodgerblue][B]¤[/B][/COLOR]',
            '[COLOR dodgerblue][B]¤[/B][/COLOR] [B][COLOR white]PG[/COLOR][/B] [COLOR dodgerblue][B]¤[/B][/COLOR]',
            '[COLOR dodgerblue][B]¤[/B][/COLOR] [B][COLOR white]PG-13[/COLOR][/B] [COLOR dodgerblue][B]¤[/B][/COLOR]',
            '[COLOR dodgerblue][B]¤[/B][/COLOR] [B][COLOR white]R[/COLOR][/B] [COLOR dodgerblue][B]¤[/B][/COLOR]',
            '[COLOR dodgerblue][B]¤[/B][/COLOR] [B][COLOR white]NC-17[/COLOR][/B] [COLOR dodgerblue][B]¤[/B][/COLOR]'
        ]



        for i in certificates:
            self.list.append({
                'name': str(i),
                'url': self.certification_link % str(i).replace('-', '_').lower(),
                'image': 'certificates.png',
                'action': 'movies'})
        self.addDirectory(self.list)
        return self.list

    def years(self):
        year = self.datetime.strftime('%Y')

        for i in range(int(year)-0, 1900, -1):
            self.list.append({
                'name': str(i),
                'url': self.year_link % (str(i)),
                'image': 'years.png',
                'action': 'movies'
                })
        self.addDirectory(self.list)
        return self.list

    def persons(self, url) -> list:
        """
        Retrieve a list of persons (TMDB) and prepare them for directory display.

        - If url is None, use the default popular-persons endpoint (self.persons_link).
        - Ensures self.list is reset to avoid duplicates.
        - Validates tmdb_person_list return value and normalizes to a list.
        - Adds an 'action' key to each item only if missing/appropriate.
        - Returns a list (never None).
        """
        c.log(f"[CM Debug @ 682 in movies.py] persons() called with url = {url!r}")

        try:
            # Ensure we start from a clean list to avoid duplicates
            self.list = []

            # Choose the URL to fetch
            fetch_url = self.persons_link if not url else url

            # tmdb_person_list appends into self.list and returns it,
            # but wrap in try/except in case of unexpected errors.
            try:
                result = self.tmdb_person_list(fetch_url)
            except Exception as exc:
                c.log(f"[CM Debug @ 690 in movies.py] tmdb_person_list failed for {fetch_url}: {exc}")
                result = None

            # Normalize result to a list
            if result is None:
                c.log(f"[CM Debug @ 696 in movies.py] tmdb_person_list returned None for {fetch_url}")
                self.list = []
            elif isinstance(result, list):
                self.list = result
            else:
                # If result is a single dict, wrap it; if it's iterable, try to convert
                if isinstance(result, dict):
                    self.list = [result]
                else:
                    try:
                        self.list = list(result)
                    except Exception:
                        c.log(f"[CM Debug @ 706 in movies.py] Unexpected result type from tmdb_person_list: {type(result)}")
                        self.list = []

            # Ensure each item has an action and minimal fields expected by callers/UI
            for item in self.list:
                if isinstance(item, dict):
                    item.setdefault('action', 'movies')
                    item.setdefault('name', item.get('name', 'Unknown'))
                    # ensure image/thumb/poster keys exist to avoid later KeyError
                    item.setdefault('image', item.get('image', c.addon_poster()))
                    item.setdefault('poster', item.get('poster', item.get('image')))
                    item.setdefault('thumb', item.get('thumb', item.get('image')))
                else:
                    c.log(f"[CM Debug @ 722 in movies.py] Skipping non-dict item in person list: {repr(item)}")

            # Only call addDirectory if we have items
            if self.list:
                self.addDirectory(self.list)
                return self.list

            return []
        except Exception as e:  # keep top-level safety
            import traceback
            c.log(f"[CM Debug @ 734 in movies.py] persons() unexpected error: {traceback.format_exc()}")
            return []

    def userlists(self):
        try:
            userlists = []
            activity = 0
            if trakt.get_trakt_credentials_info():
                activity = trakt.getActivity()

            try:
                if not trakt.get_trakt_credentials_info():
                    raise Exception()
                try:
                    if activity > cache.timeout(self.trakt_user_list, self.traktlists_link, self.trakt_user):
                        raise Exception()
                    userlists += cache.get(self.trakt_user_list, 720, self.traktlists_link, self.trakt_user)
                except Exception:
                    c.log(f"[CM Debug @ 713 in movies.py] Fetching user lists without timeout, link = {self.traktlists_link}, user = {self.trakt_user}")
                    userlists += cache.get(self.trakt_user_list, 0, self.traktlists_link, self.trakt_user)
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 714 in movies.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 714 in movies.py]Exception raised. Error = {e}')
                # pass
            # except Exception as e:
            #     c.log(f'[CM Debug @ 740 in movies.py]Exception raised. Error = {e}')
            #     pass
            # try:
            #     self.list = []
            #     if self.imdb_user == '':
            #         raise Exception()
            #     userlists += cache.get(self.imdb_user_list, 0, self.imdblists_link)
            # except Exception:
            #     pass
            try:
                self.list = []
                if trakt.get_trakt_credentials_info() is False:
                    raise Exception()
                try:
                    if activity > cache.timeout(self.trakt_user_list, self.traktlikedlists_link, self.trakt_user):
                        raise Exception()
                    userlists += cache.get(self.trakt_user_list, 720, self.traktlikedlists_link, self.trakt_user)
                except Exception:
                    userlists += cache.get(self.trakt_user_list, 0, self.traktlikedlists_link, self.trakt_user)
            except Exception:
                pass

            self.list = userlists
            for i in range(len(self.list)):
                self.list[i].update({'image': 'userlists.png', 'action': 'movies'})
            self.addDirectory(self.list, queue=True)
            return self.list
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 744 in movies.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 744 in movies.py]Exception raised. Error = {e}')
            pass

    def trakt_list(self, url, user):
        try:
            #because we are also handling user_lists, we need to check if the url is a trakt list
            #a user list will always have a user in the url
            if '/lists/' in url:
                # list url = https://trakt.tv/lists/5308818
                if url.startswith('https://'):
                    #strip the first part until the next / and keep the rest after that
                    u = url.split('/', 3)[3]
                    c.log(f"[CM Debug @ 754 in movies.py] u = {u}")
            else:
                q = dict(parse_qsl(urlsplit(url).query))
                q.update({'extended': 'full'})
                q = (urlencode(q)).replace('%2C', ',')
                u = url.replace('?' + urlparse(url).query, '') + '?' + q

                c.log(f"[CM Debug @ 624 in movies.py] url = {url}")

            result = trakt.getTraktAsJson(u)
            # c.log(f"[CM Debug @ 762 in movies.py] result = {result}")

            if not result:
                c.log(f"[CM Debug @ 761 in movies.py] No results found for URL: {u}")
                c.infoDialog('No results found in Trakt List', 'Message from The Crew', sound=False)
            else:
                c.log(f"[CM Debug @ 764 in movies.py] Found {len(result)} results for URL: {u}")

            items = []


            if result:
                items.extend(i for i in result if 'movie' in i)

            # c.log(f"[CM Debug @ 767 in movies.py] items = {items}")

            if not items:
                items = result
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 779 in movies.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 780 in movies.py]Exception raised. Error = {e}')
            return


        c.log(f"[CM Debug @ 788 in movies.py] len items = {len(items)}")

        try:
            if 'page' in url:
                query = dict(parse_qsl(urlsplit(url).query))
                if int(query['limit']) != len(items or []):
                    next_page_url = ''
                else:
                    query['page'] = str(int(query['page']) + 1)
                    next_page_url = url.replace('?' + urlparse(url).query, '') + '?' + urlencode(query)
            else:
                next_page_url = ''


        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 798 in movies.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 798 in movies.py]Exception raised. Error = {e}')


        c.log(f"[CM Debug @ 798 in movies.py] next_page_url = {next_page_url}")

        def add_item(item):
            c.log('[CM Debug @ 777 in movies.py]Adding item to list (start)')
            progress = item.get('progress', 0)

            item = item.get('movie') if 'movie' in item else item
            title = item.get('title')
            title = client.replaceHTMLCodes(title)

            year = item.get('year', '0')
            year = re.sub(r'[^0-9]', '', str(year))

            if int(year) > int((self.datetime).strftime('%Y')):
                raise Exception()
                #break

            imdb = item.get('ids', {}).get('imdb', '')
            imdb = 'tt' + re.sub(r'[^0-9]', '', str(imdb)) if imdb else '0'
            tmdb = str(item.get('ids', {}).get('tmdb', '0'))


            release_date = item.get('released', '')
            if release_date:
                try:
                    premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(release_date)[0]
                except Exception:
                    premiered = '0'
            else:
                premiered = '0'

            genres = item.get('genres', [])
            genres = ' / '.join([g.title() for g in genres]) if genres else '0'
            duration = item.get('runtime', '90')
            if duration:
                duration = str(duration)

            rating = item.get('rating', '0.0')
            if rating and rating != '0.0':
                rating = str(rating)

            try:
                num_votes = int(item['votes'])
                votes = f'{num_votes:,}'
            except (KeyError, ValueError, TypeError):
                votes = '0'

            if int(year) > int((self.datetime).strftime('%Y')):
                raise ValueError()

            mpaa = item.get('certification', '0')
            overview = item.get('overview', c.lang(32623))
            overview = client.replaceHTMLCodes(overview)

            country_code = item.get('country_code', '0')
            if country_code != '0':
                country_code = country_code.upper()

            tagline = item.get('tagline', '0')
            if tagline != '0':
                tagline = client.replaceHTMLCodes(tagline)

            paused_at = item.get('paused_at', '0') or '0'
            paused_at = re.sub('[^0-9]+', '', paused_at)

            return({
                'title': title, 'originaltitle': title, 'year': year, 'progress': progress, 'premiered': premiered,
                'genre': genres, 'duration': duration, 'rating': rating, 'votes': votes,
                'mpaa': mpaa, 'plot': overview, 'tagline': tagline, 'imdb': imdb, 'tmdb': tmdb,
                'country': country_code, 'tvdb': '0', 'poster': '0', 'next': next_page_url,
                'paused_at': paused_at
                })




        if not items:
            c.log(f'[CM Debug @ 870 in movies.py]ERROR :: trakt_list in movies. url = {url}. No items found')
            return

        try:
            result = []
            aantal = len(items)
            c.log(f"[CM Debug @ 874 in movies.py] aantal = {aantal}")

            with concurrent.futures.ThreadPoolExecutor(max_workers=c.get_max_threads(aantal, 50)) as executor:
                futures = {executor.submit(add_item, item): item for item in items}

                for future in concurrent.futures.as_completed(futures):
                    i = futures[future]
                    try:
                        response = future.result()
                        c.log(f"[CM Debug @ 886 in movies.py] response = {response}")
                        self.list.append(response)
                    except Exception as exc:
                        c.log(f"Error processing item {i}: {exc}")
                    c.log(f"[CM Debug @ 750 in movies.py] result = {result}")
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 755 in movies.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 756 in movies.py]Exception raised. Error = {e}')

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


    ####cm#
    # new def for tmdb lists
    def list_tmdb_list(self, url, tid=0):
        """
        Retrieves and processes a list of movies from a TMDB list URL.

        This function fetches a list of movies from the provided TMDB URL, processes each movie to extract relevant
        information such as title, original title, rating, votes, release date, and more, and appends the processed
        data to the `self.list` attribute. It handles pagination by constructing a URL for the next page of results.

        Args:
            url (str): The TMDB API URL to fetch the list of movies.
            tid (int, optional): The TMDB list ID to be embedded in the URL if not zero. Defaults to 0.

        Returns:
            list: A list of dictionaries, each containing information about a movie.
        """

        try:
            if tid != 0:
                url = url % tid

            result = self.session.get(url, timeout=15).json()
            items = result.get('items')
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 823 in movies.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 823 in movies.py]Exception raised. Error = {e}')
            return

        try:
            page = int(result['page'])
            total = int(result['total_pages'])
            if page >= total or 'page=' not in url:
                raise Exception()
            _next = '%s&page=%s' % (url.split('&page=', 1)[0], page+1)
        except Exception:
            _next = ''

        for item in items:
            try:
                tmdb = str(item['id'])
                title = item['title']

                originaltitle = item['original_title'] if item['original_title'] and 'original_title' in item else title
                rating = str(item['vote_average']) or '0'
                votes = str(item['vote_count']) or '0'
                premiered = item['release_date'] or '0'
                year = re.findall(r'(\d{4})', premiered)[0] or '0'
                unaired = 'false'
                if premiered != '0' and int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    unaired = 'true'
                    if self.showunaired != 'true':
                        raise ValueError()

                plot = c.lang(32084) if'overview' not in item and not item['overview'] else item['overview']
                #plot = c.lang(32084)

                poster_path = item['poster_path'] if 'poster_path' in item else ''
                if poster_path:
                    poster = self.tmdb_img_link.format(c.tmdb_postersize, poster_path)

                backdrop_path = item['backdrop_path'] if 'backdrop_path' in item else ''
                if backdrop_path:
                    fanart = self.tmdb_img_link.format(c.tmdb_fanartsize, 'backdrop_path')

                self.list.append({
                                'title': title, 'originaltitle': originaltitle, 'unaired': unaired,
                                'premiered': premiered, 'year': year, 'rating': rating,
                                'votes': votes, 'plot': plot, 'imdb': '0', 'tmdb': tmdb,
                                'tvdb': '0', 'fanart': fanart, 'poster': poster, 'next': _next
                                })

            except Exception:
                pass
        return self.list

    def collection_list(self):
        # collection = trakt.get_collection('movies')
        collection = trakt.get_collection('movies') or []
        c.log(f"[CM Debug @ 1048 in movies.py] collection = {collection}")
        if len(collection) == 0:
            trakt.get_trakt_collection('movies')
            collection = trakt.get_collection('movies') or []
        if len(collection) == 0:
            return

        c.log(f"[CM Debug @ 1046 in movies.py] collection = {collection}")

        for item in collection:
            try:
                c.log(f"[CM Debug @ 1059 in movies.py] item = {item}")
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

    def movie_progress_list(self)-> list:
        """Return a list of dictionaries containing information about the user's
        movie progress on trakt.tv."""

        try:
            progress = trakt.get_trakt_progress('movie')

            for item in progress:
                tmdb = str(item['tmdb'])
                tvdb = str(item['tvdb'])
                imdb = item['imdb']
                trakt_id = str(item['trakt'])
                title = item['title']
                season = item['season']
                episode = item['episode']
                resume_point = item['resume_point']
                c.log(f"[CM Debug @ 817 in movies.py] resume_point = {resume_point} with title = {title}")
                year = item['year']


                self.list.append({
                                'title': title, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb,
                                'trakt': trakt_id, 'season': season, 'episode': episode,
                                'resume_point': resume_point, 'year': year

                                })
        except Exception as e:
            c.log(f"Exception raised in movie_progress_list() with e = {e}")
            #pass
        return self.list

    def tmdb_cast_list(self, url):
        try:
            result = self.session.get(url, timeout=15).json()
            items = result['cast']
        except Exception:
            return

        for item in items:

            try:
                tmdb = str(item['id'])
                title = item['title']
                originaltitle = item['original_title'] if 'original_title' in item else title


                rating = str(item.get('vote_average', '0'))

                vote_count = str(item.get('vote_count', '0'))


                premiered = item.get('release_date', '0')

                year = item.get('release_year', '0')

                if premiered is None or premiered == '0':
                    premiered = ''
                else:
                    premiered = premiered.split('-')[0]

                if premiered > self.today_date[:4]:
                    if self.showunaired != 'true':
                        raise Exception()

                plot = item.get('overview', '')

                poster_path = item.get('poster_path', '')
                if poster_path:
                    poster = self.tmdb_img_link.format(c.tmdb_postersize, poster_path)
                else:
                    poster = '0'

                backdrop_path = item.get('backdrop_path', '')
                if backdrop_path:
                    fanart = self.tmdb_img_link.format(c.tmdb_fanartsize, backdrop_path)
                else:
                    fanart = ''

                self.list.append({'title': title, 'originaltitle': originaltitle,
                                    'premiered': premiered, 'year': year, 'rating': rating,
                                    'votes': vote_count, 'plot': plot, 'imdb': '0', 'tmdb': tmdb,
                                    'tvdb': '0', 'fanart': fanart, 'poster': poster})
            except Exception as e:
                c.log(f'Exception raised: error = {e}')


        return self.list

    def trakt_collection(self, collection_type='movies'):
        collection = trakt.get_collection(collection_type)

        for item in collection:
            c.log(f"[CM Debug @ 972 in movies.py] item = {item}")

    def tmdb_list(self, url, tid=0):
        """Retrieves and processes a list of movies from a TMDB list URL."""
        try:
            if int(tid) > 0:
                url = url % tid

            response = self.session.get(url, timeout=15).json()
            items = response.get('results', [])
        except Exception as e:
            return

        try:
            page = int(response.get('page', 0))
            total_pages = int(response.get('total_pages', 0))

            if page >= total_pages or 'page=' not in url:
                raise ValueError("Invalid page or URL format")
            next_page_url = f"{url.split('&page=', 1)[0]}&page={page + 1}"

        except Exception:
            next_page_url = ''
        for item in items:

            try:
                movie_id = str(item.get('id', '0'))
                title = item.get('title', '')
                original_title = item.get('original_title', title)
                rating = str(item.get('vote_average', '0'))
                votes = str(item.get('vote_count', '0'))
                release_date = item.get('release_date', '0')
                year_match = re.findall(r'(\d{4})', release_date)
                year = year_match[0] if year_match else '0'
                unaired = 'false'
                if release_date != '0' and int(re.sub(r'\D', '', release_date)) > int(re.sub(r'\D', '', self.today_date)):
                    unaired = 'true'
                    if self.showunaired != 'true':
                        continue
                plot = item.get('overview', c.lang(32084))
                poster_path = item.get('poster_path', '')
                poster = self.tmdb_img_link % (c.tmdb_postersize, poster_path) if poster_path else '0'
                backdrop_path = item.get('backdrop_path', '')
                fanart = self.tmdb_img_link % (c.tmdb_fanartsize, backdrop_path) if backdrop_path else '0'

                self.list.append({
                    'title': title, 'originaltitle': original_title,
                    'premiered': release_date, 'year': year, 'rating': rating, 'votes': votes,
                    'plot': plot, 'imdb': '0', 'tmdb': movie_id, 'tvdb': '0', 'fanart': fanart,
                    'poster': poster, 'unaired': unaired, 'next': next_page_url
                })

            except Exception:
                continue

        return self.list

    ####cm#
    # New def to hande tmdb persons listings
    def tmdb_person_list(self, url):
        try:
            result = self.session.get(url, timeout=15).json()

            c.log(f"[CM Debug @ 1224 in movies.py] result = {result}")
            items = result['results']
        except Exception:
            pass

        for item in items:
            try:
                name = item['name']
                _id = item['id']
                profile_img = item['profile_path'] if 'profile_path' in item else ''
                if profile_img:
                    image = self.tmdb_img_link % (c.tmdb_profilesize, profile_img)
                else:
                    image = c.addon_poster
                url = self.personmovies_link % _id
                self.list.append({'name': name, 'url': url, 'image': image, 'poster': image, 'thumb': image})
            except Exception:
                pass

        return self.list

    def worker(self, level=0):


        self.meta = []
        total = len(self.list)
        c.log(f"[CM Debug @ 1239 in movies.py] list has {total} items")

        if total == 0:
            control.infoDialog('List returned no relevant results', icon='INFO', sound=False)
            return

        for i in range(total):
            self.list[i].update({'metacache': False})

        self.list = metacache.fetch(self.list, self.lang, self.user)

        try:
            result = []
            #cm - changed worker 21-04-2025
            with concurrent.futures.ThreadPoolExecutor(max_workers=total) as executor:
                c.log(f"[CM Debug @ 1255 in movies.py] working inside executor with level = {level}")
                if level == 1:
                    futures = {executor.submit(self.no_info, i): i for i in range(total)}
                else:
                    futures = {executor.submit(self.super_info, i): i for i in range(total)}

                c.log(f"[CM Debug @ 1435 in movies.py] futures = {futures}")


                # for future in concurrent.futures.as_completed(futures):
                #     i = futures[future]

                #     c.log(f"[CM Debug @ 1265 in movies.py] i = {i} completed")
                #     try:
                #         resp = future.result()

                #         result.append(resp)
                #         if len(result) == total:
                #             c.log(f"[CM Debug @ 1073 in movies.py] completed = {result}")

                #     except Exception as exc:
                #         c.log(f"Error processing item {i}: {exc}")
                #     c.log(f"[CM Debug @ 1272 in movies.py] result = {result}")
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1396 in movies.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1397 in movies.py]Exception raised. Error = {e}')
            pass


        # cm changed worker - 2024-05-14
        #for r in range(0, total, 40): #cm increment 40 but why?
        #    threads = []
        #    for i in range(r, r+40):
        #        if i < total:
        #            if level == 1:
        #                threads.append(workers.Thread(self.no_info(i)))
        #            else:
        #                threads.append(workers.Thread(self.super_info(i)))
        #    [i.start() for i in threads]
        #    [i.join() for i in threads]
            #for thread in threads:
            #    thread.start()
            #for thread in threads:
            #    thread.join()

        if self.meta:
            metacache.insert(self.meta)
    def no_info(self, i) -> None:
        return

    def super_info(self, i) -> None:
        '''
        Filling missing pieces
        '''
        try:
            if self.list[i]['metacache'] is True:
                return



            lst = self.list[i]
            imdb = lst['imdb'] if 'imdb' in lst else '0'
            tmdb = lst['tmdb'] if 'tmdb' in lst else '0'
            list_title = lst['title']

            if imdb == '0' and tmdb != '0':
                #cm - get external id's from tmdb
                try:
                    url = self.tmdb_external_ids_by_tmdb % tmdb
                    result = self.session.get(url, timeout=15).json()
                    imdb = result['imdb_id'] if 'imdb_id' in result else '0'
                except Exception:
                    imdb = '0'


            if tmdb == '0' and imdb != '0':
                try:
                    url = self.tmdb_by_imdb % imdb
                    result = self.session.get(url, timeout=15).json()
                    movie_result = result['movie_results'][0]
                    tmdb = movie_result['id']
                    if not tmdb:
                        tmdb = '0'
                    else:
                        tmdb = str(tmdb)
                except Exception:
                    pass

            _id = tmdb if not tmdb == '0' else imdb
            if _id in ['0', None]:
                raise Exception()


            en_url = self.tmdb_api_link % _id
            trans_url = en_url + ',translations'
            url = en_url if self.lang == 'en' else trans_url

            item = self.session.get(url, timeout=15).json()

            if imdb == '0':
                imdb =  item.get('external_ids').get('imdb_id') if 'external_ids' in item and 'imdb_id' in item.get('external_ids') and item.get('external_ids').get('imdb_id').startswith('tt') else '0'

            mpaa = item.get('mpaa', '0')

            original_language = item.get('original_language', '')

            if self.lang == 'en':
                en_trans_item = None
            else:
                try:
                    translations = item['translations']['translations']
                    en_trans_item = [x['data'] for x in translations if x['iso_639_1'] == 'en'][0]
                except Exception:
                    en_trans_item = {}

            en_trans_item = {}

            name = item.get('title', '')
            original_title = item.get('original_title', '')
            en_trans_name = en_trans_item.get('title', '') if en_trans_item is not None and not self.lang == 'en' else None

            if self.lang == 'en':
                title = label = name
            else:
                title = en_trans_name or original_title
                if original_language == self.lang:
                    label = name
                else:
                    label = en_trans_name or name
            if not title:
                title = list_title
            if not label:
                label = list_title

            plot = item.get('overview')

            if not plot:
                plot = lst['plot'] if 'plot' in lst else c.lang(32623)

            tagline = item.get('tagline') or '0'

            if not self.lang == 'en':
                if plot == '0':
                    en_plot = en_trans_item.get('overview', '')
                    if en_plot:
                        plot = en_plot

                if tagline == '0':
                    en_tagline = en_trans_item.get('tagline', '')
                    if en_tagline:
                        tagline = en_tagline

            premiered = item.get('release_date') or '0'

            try:
                _year = re.findall(r'(\d{4})', premiered)[0]
            except Exception:
                _year = ''
            if not _year:
                _year = '0'
            year = lst['year'] if not lst['year'] == '0' else _year

            status = item.get('status') or '0'

            try:
                studio = item['production_companies'][0]['name']
            except Exception:
                studio = ''
            if not studio:
                studio = '0'

            try:
                genre = item['genres']
                genre = [d['name'] for d in genre]
                genre = ' / '.join(genre)
            except Exception:
                genre = ''
            if not genre:
                genre = '0'

            try:
                countries = item.get('production_countries')
                country = [c['name'] for c in countries]
                country = ' / '.join(country)
            except Exception:
                country = ''
            if not country:
                country = '0'


            duration = str(item.get('runtime', "90"))


            rating = item.get('vote_average', '0')
            votes = item.get('vote_count', '0') #votes ?

            castwiththumb = []
            try:
                cast = item['credits']['cast'][:30]
                cast = item.get('credits').get('cast', '0')
                for person in cast:
                    _icon = person['profile_path']
                    icon = self.tmdb_img_link % (c.tmdb_profilesize, _icon) if _icon else ''
                    castwiththumb.append(
                        {
                            'name': person['name'],
                            'role': person['character'],
                            'thumbnail': icon
                            })
            except Exception as e:
                c.log(f"[CM Debug @ 1183 in movies.py] error = {e}")


            if not castwiththumb:
                castwiththumb = '0'


            crew = item['credits']['crew'] if 'credits' in item  and 'crew' in item['credits'] else []
            director = writer = '0', '0'

            if crew:
                try:
                    director = ', '.join([d['name'] for d in [x for x in crew if x['job'] == 'Director']])
                except:
                    director = '0'

                try:
                    writer = ', '.join([w['name'] for w in [y for y in crew if y['job'] in ['Writer', 'Screenplay', 'Author', 'Novel']]])
                except:
                    writer = '0'

            lst_poster = lst['poster'] if 'poster' in lst else ''

            poster_path = item.get('poster_path', '')
            if poster_path:
                tmdb_poster = self.tmdb_img_link % (c.tmdb_postersize, poster_path)
            else:
                tmdb_poster = "0"


            backdrop_path = item.get('backdrop_path', '')#backdrop_path

            if backdrop_path:
                tmdb_fanart = self.tmdb_img_link % (c.tmdb_fanartsize, backdrop_path)
            else:
                tmdb_fanart = '0'

            fanart_poster = fanart_fanart = ''
            banner = clearlogo = clearart = landscape = discart = '0'

            if imdb not in ['0', None]:
                tempart = fanart_tv.get_fanart_tv_art(imdb=imdb, tvdb='0', mediatype='movie')
                fanart_poster = tempart.get('poster', '0')
                fanart_fanart = tempart.get('fanart', '0')
                banner = tempart.get('banner', '0')
                clearlogo = tempart.get('clearlogo', '0')
                clearart = tempart.get('clearart', '0')
                landscape = tempart.get('landscape', '0')
                discart = tempart.get('discart', '0')

            poster = tmdb_poster or fanart_poster or lst_poster
            fanart = tmdb_fanart or fanart_fanart

            item = {
                'title': title, 'originaltitle': title, 'year': year, 'imdb': imdb,
                'tmdb': tmdb, 'status': status, 'studio': studio, 'poster': poster,
                'banner': banner, 'fanart': fanart, 'fanart2': fanart_fanart, 'landscape': landscape,
                'discart': discart,'clearlogo': clearlogo, 'clearart': clearart,
                'premiered': premiered, 'genre': genre,
                'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa,
                'director': director, 'writer': writer, 'castwiththumb': castwiththumb,
                'plot': plot, 'tagline': tagline
                }

            item = dict((k, v) for k, v in item.items() if not v == '0')
            lst.update(item)

            meta = {
                'imdb': imdb, 'tmdb': tmdb, 'tvdb': '0', 'lang': self.lang,
                'user': self.user, 'item': item}
            self.meta.append(meta)
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1534 in movies.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1534 in movies.py]Exception raised. Error = {e}')



    def movie_directory(self, items):
        '''create the directory'''
        if items is None or len(items) == 0:
            control.idle()
            sys.exit()

        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])
        addon_poster, addon_banner = c.addon_poster(), c.addon_banner()
        addon_fanart, setting_fanart = c.addon_fanart(), c.get_setting('fanart')
        addon_clearlogo, addon_clearart = c.addon_clearlogo(), c.addon_clearart()
        addon_discart = c.addon_discart()

        traktCredentials = trakt.get_trakt_credentials_info()

        isPlayable = 'true' if 'plugin' not in control.infoLabel( 'Container.PluginName') else 'false'
        indicators = playcount.get_movie_indicators(refresh=True) if action == 'movies' else playcount.get_movie_indicators()

        findSimilar = c.lang(32100)
        playtrailer = c.lang(32062)
        playbackMenu = control.lang(32063) if control.setting('hosts.mode') == '2' else control.lang(32064)
        watchedMenu = control.lang(32068) if traktCredentials else control.lang(32066)
        unwatchedMenu = control.lang(32069) if traktCredentials else control.lang(32067)
        queueMenu = control.lang(32065)
        traktManagerMenu = control.lang(32515)
        nextMenu = control.lang(32053)
        addToLibrary = control.lang(32551)
        infoMenu = control.lang(32101)

        for i in items:

            try:
                imdb = i['imdb']
                tmdb = i['tmdb']
                title = i['originaltitle']
                year = i['year']
                label = i['label'] if 'label' in i and i['label'] != '0' else title
                label = f"{label} ({year})"
                status = i['status'] if 'status' in i else '0'

                meta = dict((k, v) for k, v in i.items() if not v == '0')

                # cm - resume_point -warning: percentage, float!
                resume_point = float(meta['resume_point']) if 'resume_point' in meta else 0
                offset = 0.0

                if not resume_point:
                    #offset = float(bookmarks.get('movie', imdb, '', '', True))
                    resume_point= float(bookmarks.get('movie', imdb=imdb, tmdb=tmdb))

                if 'duration' in meta and meta['duration'] != '0':
                    offset = float(int(meta['duration']) * (resume_point / 100)) #= float(int(7200) * (4.39013/100)) = 315.0 with playing time = 7200 secs om 4.3 % of the movie
                elif 'duration' in i and i['duration'] != '0':
                    offset = float(int(i['duration']) * (resume_point / 100)) #= float(int(7200) * (4.39013/100)) = 315.0 with playing time = 7200 secs om 4.3 % of the movie
                else:
                    offset = 0.0

                meta.update({'offset': offset})
                meta.update({'resume_point': resume_point})

                if resume_point:
                    #resume_point = percentage_played so remaining = 100 - percentage_played
                    percentage_played = resume_point
                    remaining = float(100 - resume_point) #percentage
                    remaining_minutes = float(remaining/100 * float(meta['duration']))
                    label += f' [COLOR gold]({int(remaining_minutes)} min. remaining)[/COLOR] '
                    #label += f' [COLOR gold]({int(resume_point)}%)[/COLOR] '
                try:
                    premiered = i['premiered']
                    if (premiered == '0' and status in ['Upcoming', 'In Production', 'Planned']) or \
                            (int(re.sub('[^0-9]', '', premiered)) > int(re.sub('[^0-9]', '', str(self.today_date)))):

                        # changed by cm -  17-5-2023
                        # changed by cm -  27-12-2024
                        color_ids = [32589, 32590, 32591, 32592, 32593, 32594, 32595, 32596, 32597, 32598]
                        selected_color_id = color_ids[int(control.setting('unaired.identify'))]
                        color_template = control.lang(selected_color_id)
                        formatted_label = re.sub(r"\][\w\s]*\[", "][I]%s[/I][", color_template) % label

                        if not formatted_label.strip():
                            formatted_label = f'[COLOR red][I]{label}[/I][/COLOR]'

                        label = formatted_label
                except Exception:
                    pass

                syslabel = quote_plus(f"{title} ({year})")
                if resume_point:
                    syslabel = quote_plus(f"{title} ({year}) [{resume_point}%]")
                systitle = quote_plus(title)
                systrailer = quote_plus(i['trailer']) if 'trailer' in i else '0'

                meta.update({'code': imdb, 'imdbnumber': imdb})
                meta.update({'tmdb_id': tmdb})
                meta.update({'imdb_id': imdb})
                meta.update({'mediatype': 'movie'})

                if 'duration' not in i or i['duration'] == '0':
                    meta.update({'duration': '90'})

                meta.update({'duration': str(int(meta['duration']) * 60)})
                #meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})

                poster = i['poster'] if 'poster' in i and i['poster'] != '0' else addon_poster
                fanart = i['fanart'] if 'fanart' in i and i['fanart'] != '0' else addon_fanart
                banner = i['banner'] if 'banner' in i and i['banner'] != '0' else addon_banner
                landscape = i['landscape'] if 'landscape' in i and i['landscape'] != '0' else fanart
                clearlogo = i['clearlogo'] if 'clearlogo' in i and i['clearlogo'] != '0' else addon_clearlogo
                clearart = i['clearart'] if 'clearart' in i and i['clearart'] != '0' else addon_clearart
                discart = i['discart'] if 'discart' in i and i['discart'] != '0' else addon_discart

                poster = [i[x] for x in ['poster3', 'poster', 'poster2'] if i.get(x, '0') != '0']
                poster = poster[0] if poster else addon_poster

                meta['poster'] = poster

                sysmeta = quote_plus(json.dumps(meta))

                if systrailer == '0':
                    meta['trailer'] = f'{sysaddon}?action=trailer&name={systitle}&imdb={imdb}&tmdb={tmdb}&mediatype=movie&meta={sysmeta}'
                else:
                    meta['trailer'] = f'{sysaddon}?action=trailer&name={systitle}&url={systrailer}&imdb={imdb}&tmdb={tmdb}&mediatype=movie&meta={sysmeta}'
                #c.log(f"[CM Debug @ 1671 in movies.py] systime = {self.systime}")
                url = f'{sysaddon}?action=play&title={systitle}&year={year}&imdb={imdb}&tmdb={tmdb}&meta={sysmeta}&t={self.systime}'
                #url = f'{sysaddon}action=play&title={systitle}&year={year}&imdb={imdb}&tmdb={tmdb}&meta={sysmeta}&t={self.systime}'
                sysurl = quote_plus(url)

                cm = [
                    (
                        findSimilar,
                        f"Container.Update({sysaddon}?action=movies&url={quote_plus(self.related_link % tmdb)})",
                    )
                ]
                cm.append((queueMenu, f'RunPlugin({sysaddon}?action=queueItem)'))

                try:
                    overlay = int(playcount.get_movie_overlay(indicators, imdb))
                    #c.log(f"[CM Debug @ 1721 in movies.py] overlay = {overlay}")
                    if overlay == 7:
                        cm.append((unwatchedMenu, 'RunPlugin(%s?action=moviePlaycount&imdb=%s&query=6)' % (sysaddon, imdb)))
                        meta.update({'playcount': 1, 'overlay': 7})
                    else:
                        cm.append((watchedMenu, 'RunPlugin(%s?action=moviePlaycount&imdb=%s&query=7)' % (sysaddon, imdb)))
                        meta.update({'playcount': 0, 'overlay': 6})
                except Exception:
                    pass

                if traktCredentials is True:
                #     cm.append((traktManagerMenu, 'RunPlugin(%s?action=traktManager&name=%s&imdb=%s&content=movie)' % (sysaddon, syslabel, imdb)))
                # cm.append((playbackMenu, 'RunPlugin(%s?action=alterSources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))
                # cm.append((addToLibrary, 'RunPlugin(%s?action=movieToLibrary&name=%s&title=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, syslabel, systitle, year, imdb, tmdb)))
                    cm.append((traktManagerMenu, f'RunPlugin({sysaddon}?action=traktManager&name={syslabel}&imdb={imdb}&content=movie)'))
                cm.append((playbackMenu, f'RunPlugin({sysaddon}?action=alterSources&url={sysurl}&meta={sysmeta})'))
                cm.append((addToLibrary, f'RunPlugin({sysaddon}?action=movieToLibrary&name={syslabel}&title={systitle}&year={year}&imdb={imdb}&tmdb={tmdb})'))

                try:
                    item = control.item(label=label, offscreen=True)
                except Exception:
                    item = control.item(label=label)

                art = {}
                art.update({
                    'icon': poster,
                    'thumb': poster,
                    'poster': poster,
                    **({'fanart': fanart} if setting_fanart == 'true' else {}),
                    'banner': banner,
                    'clearlogo': clearlogo,
                    'clearart': clearart,
                    'landscape': landscape,
                    'discart': discart
                })

                item.setArt(art)
                #item.addContextMenuItems(cm)
                item.setProperty('IsPlayable', isPlayable)

                item.setProperty('imdb_id', imdb)
                item.setProperty('tmdb_id', tmdb)
                #item.setInfo(type='Video', infoLabels=control.metadataClean(meta))

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
                info_tag.set_cast(meta.get('castwiththumb', []))

                if(offset > 0):
                    info_tag.set_resume_point(meta, 'offset', 'duration', False)

                stream_info = {'codec': 'h264'}
                info_tag.add_stream_info('video', stream_info)  # (stream_details)
                item.addContextMenuItems(cm)

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 1796 in movies.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 1796 in movies.py]Exception raised. Error = {e}')
                pass
                #except Exception as e:
                    #c.log(f"[CM Debug @ 1797 in movies.py] exception raised: error = {e}")
                    #pass

        try:
            url = items[0]['next']
            if url == '':
                raise ValueError('No next page URL found')

            icon = control.addonNext()
            url = '%s?action=moviePage&url=%s' % (sysaddon, quote_plus(url))

            try:
                item = control.item(label=nextMenu, offscreen=True)
            except Exception:
                item = control.item(label=nextMenu)

            item.setArt({
                'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon, 'fanart': addon_fanart
                })

            control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
        except (Exception, ValueError):
            pass

        control.content(syshandle, 'movies')
        control.directory(syshandle, cacheToDisc=True)
        views.set_view('movies', {'skin.estuary': 55, 'skin.confluence': 500})

    def addDirectory(self, items, queue=False):
        if items is None or len(items) == 0:
            control.idle()
            sys.exit()

        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])
        addonFanart, addonThumb, artPath = control.addonFanart(), control.addonThumb(), control.artPath()
        queueMenu = control.lang(32065)
        playRandom = control.lang(32535)
        addToLibrary = control.lang(32551)

        for i in items:
            try:
                name = i['name']

                plot = i.get('plot') or '[CR]'
                if i['image'].startswith('http'):
                    thumb = i['image']
                elif not artPath is None:
                    thumb = os.path.join(artPath, i['image'])
                else:
                    thumb = addonThumb

                url = '%s?action=%s' % (sysaddon, i['action'])
                try:
                    url += '&url=%s' % quote_plus(i['url'])
                except Exception:
                    pass

                cm = []

                cm.append((playRandom, 'RunPlugin(%s?action=random&rtype=movie&url=%s)' % (sysaddon, quote_plus(i['url']))))

                if queue is True:
                    cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                try:
                    cm.append((addToLibrary, 'RunPlugin(%s?action=moviesToLibrary&url=%s)' % (sysaddon, quote_plus(i['context']))))
                except Exception:
                    pass

                try:
                    item = control.item(label=name, offscreen=True)
                except Exception:
                    item = control.item(label=name)

                item.setArt({'icon': thumb, 'thumb': thumb, 'poster': thumb, 'fanart': addonFanart})
                item.setInfo(type='video', infoLabels={'plot': plot})

                item.addContextMenuItems(cm)

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
            except Exception:
                c.log('mov_addDir', 1)
                pass

        control.content(syshandle, 'movies')
        control.directory(syshandle, cacheToDisc=True)
