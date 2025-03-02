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
#from bs4 import BeautifulSoup

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

        self.imdb_link = 'https://www.imdb.com'
        self.trakt_link = 'https://api.trakt.tv'
        self.tmdb_link = 'https://api.themoviedb.org/3/'

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
        self.persons_link = (f'{self.tmdb_link}person/%s?api_key={self.tmdb_user}&?language=en-US')
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

        self.tmdb_api_link = f'{self.tmdb_link}movie/%s?api_key={self.tmdb_user}&language={self.lang}&append_to_response=aggregate_credits,content_ratings,external_ids'
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

    def get(self, url, tid=0, idx=True, create_directory=True):
        try:
            if url.startswith('https://'):
                #check if i can show a listing
            else:
                url = getattr(self, f"{url}_link", None)


            for days_offset in re.findall(r'date\[(\d+)\]', url):
                replacement_date = (self.datetime - datetime.timedelta(days=int(days_offset))).strftime('%Y-%m-%d')
                url = url.replace(f'date[{days_offset}]', replacement_date)

            parsed_url_netloc = urlparse(url).netloc.lower()

            if self.trakt_link in url and url == self.onDeck_link:
                self.on_deck_list = cache.get(self.trakt_list, 720, url, self.trakt_user)
                self.list = []
                self.list = cache.get(self.trakt_list, 0, url, self.trakt_user)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)
                self.list = self.list[::-1]
            elif 'collection' in url:
                self.list = self.collection_list()
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)
            elif 'movieProgress' in url:
                self.list = cache.get(self.movie_progress_list, 0)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)


            elif parsed_url_netloc in self.trakt_link and '/users/' in url:
                try:
                    if url != self.trakthistory_link and '/users/me/' in url:
                        if trakt.getActivity() > cache.timeout(self.trakt_list, url, self.trakt_user):
                            raise Exception()
                        self.list = cache.get(self.trakt_list, 720, url, self.trakt_user)
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
                self.movieDirectory(self.list)
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
        navigator.navigator().addDirectoryItem(32603,
                                            'movieSearchnew', 'search.png', 'DefaultMovies.png')

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()

        try:
            dbcur.executescript(
                "CREATE TABLE IF NOT EXISTS movies (ID Integer PRIMARY KEY AUTOINCREMENT, term TEXT);"
                )
        except Exception:
            pass

        dbcur.execute("SELECT * FROM movies ORDER BY ID DESC")
        lst = []
        cm = []

        for _id, term in dbcur.fetchall():
            if term not in str(lst):
                cm.append((32070, f'movieDeleteTerm&id={_id})'))
                navigator.navigator().addDirectoryItem(term,
                                    f'movieSearchterm&name={term}', 'search.png',
                                    'DefaultTVShows.png', context=cm)
                lst += [(term)]
        dbcur.close()

        if len(lst) > 0:
            navigator.navigator().addDirectoryItem(32605,
                                        'clearCacheSearch', 'tools.png', 'DefaultAddonProgram.png')

        navigator.navigator().endDirectory()

    def search_new(self):
        control.idle()

        t = control.lang(32010)
        k = control.keyboard('', t)
        k.doModal()
        q = k.getText() if k.isConfirmed() else None

        if not q:
            return

        q = q.lower()

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        dbcur.execute("DELETE FROM movies WHERE term = ?", (q,))
        dbcur.execute("INSERT INTO movies VALUES (?,?)", (None, q))
        dbcon.commit()
        dbcur.close()
        url = self.search_link % quote_plus(q)

        self.get(url)

    def search_term(self, name):
        url = self.search_link % quote_plus(name)
        self.get(url)


    def delete_search_term(self, search_term_id):
        """
        Deletes a search term from the database.

        This method takes the ID of a search term as an argument, deletes the
        corresponding record from the database, and refreshes the Kodi UI.

        :param search_term_id: The ID of the search term to delete.
        :type search_term_id: int
        """
        try:
            dbcon = database.connect(control.searchFile)
            dbcur = dbcon.cursor()
            dbcur.execute("DELETE FROM movies WHERE ID = ?", (search_term_id,))
            dbcur.execute("SELECT * FROM movies ORDER BY ID DESC")
            for _id, term in dbcur.fetchall():
                c.log(f"[CM Debug @ 389 in movies.py] id = {_id}, term = {term}")

            dbcon.commit()
            dbcur.close()
            control.refresh()
        except database.Error as e:
            c.log(f'Exception raised. Error = {e}')

        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 352 in movies.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 352 in movies.py]Exception raised. Error = {e}')
            pass


    def person(self):
        try:
            t = control.lang(32010)
            k = control.keyboard('', t)
            k.doModal()
            q = k.getText() if k.isConfirmed() else None

            if (q is None or q == ''):
                return

            url = self.person_link % quote_plus(q)
            self.persons(url)
        except Exception:
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

    def persons(self, url):
        if url is None:
            #self.list = cache.get(self.tmdb_person_list, 24, self.personlist_link)
            self.tmdb_person_list(self.personlist_link)
        else:
            self.list = cache.get(self.tmdb_person_list, 1, url)

        #for i in range(0, len(self.list)):
            #self.list[i].update({'action': 'movies'})

        for item in self.list:
            item.update({'action': 'movies'})
        self.addDirectory(self.list)
        return self.list

    def userlists(self):
        try:
            userlists = []
            if trakt.getTraktCredentialsInfo() is False:
                raise Exception()
            activity = trakt.getActivity()
        except Exception:
            pass

        try:
            if trakt.getTraktCredentialsInfo() is False:
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
            if trakt.getTraktCredentialsInfo() is False:
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

    def trakt_list(self, url, user):
        try:
            q = dict(parse_qsl(urlsplit(url).query))
            q.update({'extended': 'full'})
            q = (urlencode(q)).replace('%2C', ',')
            u = url.replace('?' + urlparse(url).query, '') + '?' + q

            result = trakt.getTraktAsJson(u)

            items = []

            for i in result:
                if 'movie' in i:
                    items.append(i['movie'])

            if len(items) == 0:
                items = result
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 582 in movies.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 582 in movies.py]Exception raised. Error = {e}')
            return
        #except Exception as e:
        #    c.log(f'Exception in movies.trakt_list 0. Error = {e}')
        #    return

        try:
            query = dict(parse_qsl(urlsplit(url).query))
            if not int(query['limit']) == len(items):
                raise Exception()

            query['page'] = str(int(query['page']) + 1)
            next_page_url = url.replace('?' + urlparse(url).query, '') + '?' + urlencode(query)
        except Exception:
            next_page_url = ''

        for item in items:
            try:
                title = item.get('title')
                title = client.replaceHTMLCodes(title)

                year = item.get('year', '0')
                year = re.sub(r'[^0-9]', '', str(year))

                if int(year) > int((self.datetime).strftime('%Y')):
                #   raise Exception()
                    break

                imdb = item.get('ids', {}).get('imdb')
                if not imdb:
                    imdb = '0'
                else:
                    imdb = 'tt' + re.sub(r'[^0-9]', '', str(imdb))

                tmdb = item.get('ids', {}).get('tmdb')
                if not tmdb:
                    tmdb = '0'
                else:
                    tmdb = str(tmdb)

                release_date = item.get('released')
                if release_date:
                    try:
                        premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(release_date)[0]
                    except Exception:
                        premiered = '0'
                else:
                    premiered = '0'

                genres = item.get('genres', [])
                if genres:
                    genres = ' / '.join([g.title() for g in genres])
                else:
                    genres = '0'

                duration = item.get('runtime')
                if duration:
                    duration = str(duration)
                else:
                    duration = '0'

                rating = item.get('rating')
                if rating and not rating == '0.0':
                    rating = str(rating)
                else:
                    rating = '0'

                try:
                    num_votes = int(item['votes'])
                    votes = f'{num_votes:,}'
                except (KeyError, ValueError, TypeError):
                    votes = '0'

                if int(year) > int((self.datetime).strftime('%Y')):
                    raise ValueError()

                mpaa = item.get('certification', '0')
                overview = item.get('overview', '0')
                if not overview:
                    overview = c.lang(32623)
                overview = client.replaceHTMLCodes(overview)

                country_code = item.get('country_code')
                if not country_code:
                    country_code = '0'
                else:
                    country_code = country_code.upper()

                tagline = item.get('tagline', '0') or '0'
                if tagline != '0':
                    tagline = client.replaceHTMLCodes(tagline)

                paused_at = item.get('paused_at', '0') or '0'
                paused_at = re.sub('[^0-9]+', '', paused_at)

                self.list.append({
                    'title': title, 'originaltitle': title, 'year': year, 'premiered': premiered,
                    'genre': genres, 'duration': duration, 'rating': rating, 'votes': votes,
                    'mpaa': mpaa, 'plot': overview, 'tagline': tagline, 'imdb': imdb, 'tmdb': tmdb,
                    'country': country_code, 'tvdb': '0', 'poster': '0', 'next': next_page_url,
                    'paused_at': paused_at
                    })
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log('[CM Debug @ 776 in movies.py]Traceback:: ' + str(failure))
                c.log('[CM Debug @ 777 in movies.py]Exception raised. Error = ' + str(e))

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
                url = url.encode('utf-8')

                self.list.append({'name': name, 'url': url, 'context': url})
            except Exception:
                pass

        self.list = sorted(self.list, key=lambda k: utils.title_key(k['name']))
        return self.list

    ####cm#
    # new def for tmdb lists
    def list_tmdb_list(self, url, tid=0):
        try:
            if tid != 0:
                url = url % tid

            result = self.session.get(url, timeout=15).json()
            items = result.get('items')
        except Exception:
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
                if premiered != '0':
                    if int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
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
        collection = trakt.get_collection('movies')

        for item in collection:
            try:
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
                pass

        return self.list

    def movie_progress_list(self):
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
                originaltitle = item['original_title']
                if not originaltitle:
                    originaltitle = title

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
                    premiered = item['release_date']
                except Exception:
                    premiered = ''
                if not premiered:
                    premiered = '0'

                try:
                    year = re.findall(r'(\d{4})', premiered)[0]
                except Exception:
                    year = ''
                if not year:
                    year = '0'

                if not premiered or premiered == '0':
                    pass
                elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    if self.showunaired != 'true':
                        raise Exception()

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
                    poster = self.tmdb_img_link.format(c.tmdb_postersize, poster_path)
                else:
                    poster = '0'

                backdrop_path = item['backdrop_path'] if 'backdrop_path' in item else ''
                if backdrop_path:
                    fanart = self.tmdb_img_link.format(c.tmdb_fanartsize, 'backdrop_path')
                else:
                    fanart = ''

                self.list.append({'title': title, 'originaltitle': originaltitle,
                                    'premiered': premiered, 'year': year, 'rating': rating,
                                    'votes': votes, 'plot': plot, 'imdb': '0', 'tmdb': tmdb,
                                    'tvdb': '0', 'fanart': fanart, 'poster': poster})
            except Exception as e:
                c.log(f'Exception raised: error = {e}')


        return self.list

    def trakt_collection(self, collection_type='movies'):
        collection = trakt.get_collection(collection_type)

        for item in collection:
            c.log(f"[CM Debug @ 972 in movies.py] item = {item}")

    def tmdb_list(self, url, tid=0):
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
                fanart = self.tmdb_img_link % (c.tmdb_fanartsize, backdrop_path) if backdrop_path else ''
                self.list.append({
                    'title': title,
                    'originaltitle': original_title,
                    'premiered': release_date,
                    'year': year,
                    'rating': rating,
                    'votes': votes,
                    'plot': plot,
                    'imdb': '0',
                    'tmdb': movie_id,
                    'tvdb': '0',
                    'fanart': fanart,
                    'poster': poster,
                    'unaired': unaired,
                    'next': next_page_url
                })

            except Exception:
                continue

        return self.list

    ####cm#
    # New def to hande tmdb persons listings
    def tmdb_person_list(self, url):
        try:
            result = self.session.get(url, timeout=15).json()
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
                self.list.append({'name': name, 'url': url, 'image': image, 'poster': image})
            except Exception:
                pass

        return self.list

    def worker(self, level=0):


        self.meta = []
        total = len(self.list)

        if total == 0:
            control.infoDialog('List returned no relevant results', icon='INFO', sound=False)
            return

        for i in range(total):
            self.list[i].update({'metacache': False})

        self.list = metacache.fetch(self.list, self.lang, self.user)

        # cm changed worker - 2024-05-14
        for r in range(0, total, 40): #cm increment 40 but why?
            threads = []
            for i in range(r, r+40):
                if i < total:
                    if level == 1:
                        threads.append(workers.Thread(self.no_info(i)))
                    else:
                        threads.append(workers.Thread(self.super_info(i)))

            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

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
                    imdb = result['imdb_id'] if 'imdb_id' in result and result['imdb_id'].startswith('tt') else '0'
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
                try:
                    imdb = item['external_ids']['imdb_id']
                    if not imdb:
                        imdb = '0'
                except Exception:
                    imdb = '0'

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

            name = item.get('title', '')
            original_title = item.get('original_title', '')
            en_trans_name = en_trans_item.get(
                'title', '') if not self.lang == 'en' else None

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
                plot = lst['plot'] if 'plot' in lst else 'The Crew - No Plot Available'

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
                _year = re.findall('(\d{4})', premiered)[0]
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
                country = item['production_countries']
                country = [c['name'] for c in country]
                country = ' / '.join(country)
            except Exception:
                country = ''
            if not country:
                country = '0'

            try:
                duration = str(item['runtime'])
            except Exception:
                duration = ''
            if not duration:
                duration = '0'

            rating = item['vote_average'] if 'vote_average' in item else '0'
            votes = item['votese'] if 'votes' in item else '0'

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

            try:
                crew = item['credits']['crew']
                director = ', '.join([d['name'] for d in [x for x in crew if x['job'] == 'Director']])
                writer = ', '.join([w['name'] for w in [y for y in crew if y['job'] in ['Writer', 'Screenplay', 'Author', 'Novel']]])
            except Exception:
                director = writer = '0'

            poster1 = lst['poster'] if 'poster' in lst else ''

            poster_path = item.get('poster_path')
            if poster_path:
                poster2 = self.tmdb_img_link % (c.tmdb_postersize, poster_path)
            else:
                poster2 = ''

            backdrop_path = item.get('backdrop_path')
            if backdrop_path:
                fanart1 = self.tmdb_img_link.format(c.tmdb_fanartsize, backdrop_path)
            else:
                fanart1 = '0'

            poster3 = fanart2 = ''
            banner = clearlogo = clearart = landscape = discart = '0'

            if imdb not in ['0', None]:
                tempart = fanart_tv.get_fanart_tv_art(imdb=imdb, tvdb='0', mediatype='movie')
                poster3 = tempart.get('poster', '0')
                fanart2 = tempart.get('fanart', '0')
                banner = tempart.get('banner', '0')
                clearlogo = tempart.get('clearlogo', '0')
                clearart = tempart.get('clearart', '0')
                landscape = tempart.get('landscape', '0')
                discart = tempart.get('discart', '0')

            poster = poster3 or poster2 or poster1
            fanart = fanart2 or fanart1

            item = {'title': title, 'originaltitle': title, 'year': year, 'imdb': imdb,
                    'tmdb': tmdb, 'status': status, 'studio': studio, 'poster': poster,
                    'banner': banner, 'fanart': fanart, 'fanart2': fanart2, 'landscape': landscape,
                    'discart': discart,'clearlogo': clearlogo, 'clearart': clearart,
                    'premiered': premiered, 'genre': genre,
                    'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa,
                    'director': director, 'writer': writer, 'castwiththumb': castwiththumb,
                    'plot': plot, 'tagline': tagline}

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
            pass

        #except Exception:
        #   pass

    def movieDirectory(self, items):
        if items is None or len(items) == 0:
            control.idle()
            sys.exit()

        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])
        addon_poster, addon_banner = c.addon_poster(), c.addon_banner()
        addon_fanart, setting_fanart = c.addon_fanart(), c.get_setting('fanart')
        addon_clearlogo, addon_clearart = c.addon_clearlogo(), c.addon_clearart()
        addonDiscart = c.addon_discart()

        traktCredentials = trakt.getTraktCredentialsInfo()

        isPlayable = 'true' if 'plugin' not in control.infoLabel( 'Container.PluginName') else 'false'
        indicators = playcount.get_movie_indicators(refresh=True) if action == 'movies' else playcount.get_movie_indicators()

        findSimilar = c.lang(32100)
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
                #label = '%s (%s)' % (i['title'], i['year'])
                #label = f"{i['title']} ({i['year']})"
                imdb = i['imdb']
                tmdb = i['tmdb']
                title = i['originaltitle']
                year = i['year']
                label = i['label'] if 'label' in i and i['label'] != '0' else title
                label = f"{label} ({year})"
                status = i['status'] if 'status' in i else '0'

                meta = dict((k, v) for k, v in i.items() if not v == '0')

                # cm - resume_point -warning: percentage, float!
                resume_point = int(i['resume_point']) if 'resume_point' in i else 0

                offset = 0.0

                if not resume_point:
                    #offset = float(bookmarks.get('movie', imdb, '', '', True))
                    resume_point= float(bookmarks.get('movie', imdb=imdb, tmdb=tmdb))

                offset = float(int(meta['duration']) * (resume_point / 100)) #= float(int(7200) * (4.39013/100)) = 315.0 with playing time = 7200 secs om 4.3 % of the movie
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
                    if (premiered == '0' and status in ['Upcoming', 'In Production', 'Planned']) or\
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

                        # changed by cm -  17-5-2023
                        #colorlist = [32589, 32590, 32591, 32592, 32593, 32594, 32595, 32596, 32597, 32598]
                        #colornr = colorlist[int(control.setting('unaired.identify'))]
                        #unairedcolor = re.sub(r"\][\w\s]*\[", "][I]%s[/I][", control.lang(int(colornr)))
                        #label = unairedcolor % label

                        #if unairedcolor == '':
                            #unairedcolor = '[COLOR red][I]%s[/I][/COLOR]'
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

                poster = i['poster'] if 'poster' in i and not i['poster'] == '0' else addon_poster
                fanart = i['fanart'] if 'fanart' in i and not i['fanart'] == '0' else addon_fanart
                banner = i['banner'] if 'banner' in i and not i['banner'] == '0' else addon_banner
                landscape = i['landscape'] if 'landscape' in i and not i['landscape'] == '0' else fanart
                clearlogo = i['clearlogo'] if 'clearlogo' in i and not i['clearlogo'] == '0' else addon_clearlogo
                clearart = i['clearart'] if 'clearart' in i and not i['clearart'] == '0' else addon_clearart
                discart = i['discart'] if 'discart' in i and not i['discart'] == '0' else addonDiscart

                poster = [i[x] for x in ['poster3', 'poster', 'poster2'] if i.get(x, '0') != '0']
                poster = poster[0] if poster else addon_poster
                meta.update({'poster': poster})

                sysmeta = quote_plus(json.dumps(meta))

                if systrailer == '0':
                    meta['trailer'] = f'{sysaddon}?action=trailer&name={systitle}&imdb={imdb}&tmdb={tmdb}&mediatype=movie&meta={sysmeta}'
                else:
                    meta['trailer'] = f'{sysaddon}?action=trailer&name={systitle}&url={systrailer}&imdb={imdb}&tmdb={tmdb}&mediatype=movie&meta={sysmeta}'
                #c.log(f"[CM Debug @ 1671 in movies.py] systime = {self.systime}")
                url = '%s?action=play&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s&t=%s' % (sysaddon, systitle, year, imdb, tmdb, sysmeta, self.systime)
                #url = f'{sysaddon}action=play&title={systitle}&year={year}&imdb={imdb}&tmdb={tmdb}&meta={sysmeta}&t={self.systime}'
                sysurl = quote_plus(url)

                cm = []
                cm.append((findSimilar, f"Container.Update({sysaddon}?action=movies&url={quote_plus(self.related_link % tmdb)})"))
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
                    cm.append((traktManagerMenu, 'RunPlugin(%s?action=traktManager&name=%s&imdb=%s&content=movie)' % (sysaddon, syslabel, imdb)))
                cm.append((playbackMenu, 'RunPlugin(%s?action=alterSources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))
                cm.append((addToLibrary, 'RunPlugin(%s?action=movieToLibrary&name=%s&title=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, syslabel, systitle, year, imdb, tmdb)))

                try:
                    item = control.item(label=label, offscreen=True)
                except Exception:
                    item = control.item(label=label)

                art = {}
                art.update({'icon': poster, 'thumb': poster, 'poster': poster})

                if setting_fanart == 'true':
                    art.update({'fanart': fanart})
                art.update({'banner': banner})
                art.update({'clearlogo': clearlogo})
                art.update({'clearart': clearart})
                art.update({'landscape': landscape})
                art.update({'discart': discart})

                item.setArt(art)
                item.addContextMenuItems(cm)
                item.setProperty('IsPlayable', isPlayable)

                castwiththumb = i.get('castwiththumb')

                if castwiththumb and not castwiththumb == '0':
                    item.setCast(castwiththumb)


                c.log(f"[CM Debug @ 11477 in movies.py] offset 2: {offset} for {title}")

                item.setProperty('imdb_id', imdb)
                item.setProperty('tmdb_id', tmdb)
                item.setInfo(type='Video', infoLabels=control.metadataClean(meta))

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

                c.log(f"[CM Debug @ 1508 in movies.py] offset = meta['resume_point'] = {meta['offset']} with duration = {meta['duration']}")

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
                raise Exception()

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
        except Exception:
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

        control.content(syshandle, 'addons')
        control.directory(syshandle, cacheToDisc=True)
