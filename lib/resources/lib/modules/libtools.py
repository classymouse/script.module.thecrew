# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 * @file bookmarks.py
 * @package script.module.thecrew
 *
 * @copyright 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''


import sqlite3 as database

import datetime
import json
import os
import re
import sys

from urllib.parse import parse_qsl, quote_plus
from ftplib import FTP

from . import control
from . import cleantitle
from . import sources
from .crewruntime import c

from ..indexers import movies
from ..indexers import tvshows


class lib_tools:
    @staticmethod
    def create_folder(folder):
        try:
            folder = control.legalFilename(folder)
            control.makeFile(folder)

            try:
                if 'ftp://' not in folder:
                    raise Exception()


                ftparg = re.compile(r'ftp://(.+?):(.+?)@(.+?):?(\d+)?/(.+/?)').findall(folder)
                ftp = FTP(ftparg[0][2], ftparg[0][0], ftparg[0][1])
                try:
                    ftp.cwd(ftparg[0][4])
                except Exception:
                    ftp.mkd(ftparg[0][4])
                ftp.quit()
            except Exception:
                pass
        except Exception:
            pass

    @staticmethod
    def write_file(path, content):
        try:
            path = control.legalFilename(path)
            #if not isinstance(content, six.string_types):
            #cm - version py3 fix: six.string_types == str
            if not isinstance(content, str):
                content = str(content)

            file = control.openFile(path, 'w')
            file.write(str(content))
            file.close()
        except Exception as e:
            pass

    @staticmethod
    def nfo_url(media_string, ids):
        if 'imdb' in ids:
            return f'https://www.imdb.com/title/{str(ids["imdb"])}'
        elif 'tmdb' in ids:
            return f'https://www.themoviedb.org/{media_string}/{str(ids["tmdb"])}' % (media_string, str(ids['tmdb']))
        elif 'tvdb' in ids:
            return f'https://thetvdb.com/?tab=series&id={str(ids["tvdb"])}'
        else:
            return ''

    @staticmethod
    def check_sources(title, year, imdb, tmdb=None, season=None, episode=None, tvshowtitle=None, premiered=None):
        try:
            src = sources.sources().getSources(title, year, imdb, tmdb, season, episode, tvshowtitle, premiered)
            return src and len(src) > 5
        except Exception:
            return False

    @staticmethod
    def legal_filename(filename):
        try:
            filename = filename.strip()
            filename = re.sub(r'(?!%s)[^\w\-_\.]', '.', filename)
            filename = re.sub(r'\.+', '.', filename)
            filename = re.sub(re.compile(r'(CON|PRN|AUX|NUL|COM\d|LPT\d)\.', re.I), '\\1_', filename)
            control.legalFilename(filename)
            return filename
        except Exception:
            return filename

    @staticmethod
    def make_path(base_path, title, year='', season=''):
        """
        This function generates a file path for a TV show. It takes a base path, title, year,
        and season as input, and returns a path in the format base_path/title (year)/Season season.
        The title is sanitized to replace special characters with underscores.

        Args:
            base_path (_type_): _description_
            title (_type_): _description_
            year (str, optional): _description_. Defaults to ''.
            season (str, optional): _description_. Defaults to ''.

        Returns:
            _type_: _description_
        """
        show_folder = re.sub(r'[^\w\-_\. ]', '_', title)
        show_folder = f'{show_folder} ({year})' if year else show_folder
        path = os.path.join(base_path, show_folder)
        if season:
            path = os.path.join(path, f'Season {season}')
        return path

#TC 2/01/19 started
class libmovies:
    def __init__(self):
        self.library_folder = os.path.join(control.transPath(control.setting('library.movie')), '')

        self.check_setting = control.setting('library.check_movie') or 'false'
        self.library_setting = control.setting('library.update') or 'true'
        self.dupe_setting = control.setting('library.check') or 'true'
        self.silentDialog = False
        self.infoDialog = False


    def add(self, name, title, year, imdb, _range=False):
        if not control.condVisibility('Window.IsVisible(infodialog)')\
                and not control.condVisibility('Player.HasVideo')\
                and self.silentDialog is False:
            control.infoDialog(control.lang(32552), time=10000000)
            self.infoDialog = True

        try:
            if self.dupe_setting != 'true':
                raise Exception()


            lib = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["imdbnumber", "originaltitle", "year"]}, "id": 1}' % (year, str(int(year)+1), str(int(year)-1)))
            lib = c.ensure_text(lib, errors='ignore')
            lib = json.loads(lib)['result']['movies']
            lib = [i for i in lib if str(i['imdbnumber']) in imdb or (str(i['title']) == title and str(i['year']) == year)][0]
        except Exception as e:
            lib = []

        files_added = 0

        try:
            if lib != []:
                raise Exception()

            if self.check_setting == 'true':
                src = lib_tools.check_sources(title, year, imdb, None, None, None, None, None)
                if not src:
                    raise Exception()

            self.strmFile({'name': name, 'title': title, 'year': year, 'imdb': imdb})
            files_added += 1
        except Exception as e:
            pass

        if _range is True:
            return

        if self.infoDialog is True:
            control.infoDialog(control.lang(32554), time=1)

        if self.library_setting == 'true' and not\
            control.condVisibility('Library.IsScanningVideo') and\
            files_added > 0:
            control.execute('UpdateLibrary(video)')
    def add_movie(self, name: str, title: str, year: int, imdb_id: str, add_range: bool = False) -> None:
        """
        Adds a movie to the user's library.

        Args:
            name (str): The name of the movie.
            title (str): The title of the movie.
            year (int): The year of the movie.
            imdb_id (str): The IMDB ID of the movie.
            add_range (bool, optional): Whether to add a range of years or not. Defaults to False.
        """
        # Show a dialog if the user is not watching a video and the silent dialog setting is off
        if not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo') and not self.silentDialog:
            control.infoDialog(control.lang(32552), time=10000000)
            self.infoDialog = True

        try:
            # Check if the movie is already in the user's library
            if self.dupe_setting != 'true':
                raise Exception

            lib = control.jsonrpc(
                '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["imdbnumber", "originaltitle", "year"]}, "id": 1}' % (year, str(int(year)+1), str(int(year)-1))
            )
            lib = c.ensure_text(lib, errors='ignore')
            lib = json.loads(lib)['result']['movies']
            lib = [i for i in lib if str(i['imdbnumber']) == imdb_id or (str(i['title']) == title and str(i['year']) == year)][0]
        except Exception:
            lib = []

        files_added = 0

        try:
            # Add the movie to the user's library
            if lib != []:
                raise Exception

            if self.check_setting == 'true':
                src = lib_tools.check_sources(title, year, imdb_id, None, None, None, None, None)
                if not src:
                    raise Exception

            self.strmFile({'name': name, 'title': title, 'year': year, 'imdb': imdb_id})
            files_added += 1
        except Exception:
            pass

        if add_range is True:
            return

        # Hide the dialog if it was shown
        if self.infoDialog is True:
            control.infoDialog(control.lang(32554), time=1)

        # Update the user's library if the library setting is on and the library is not already being updated
        if self.library_setting == 'true' and not control.condVisibility('Library.IsScanningVideo') and files_added > 0:
            control.execute('UpdateLibrary(video)')




    def add_backup(self, name, title, year, imdb, _range=False):
        if not control.condVisibility('Window.IsVisible(infodialog)')\
                and not control.condVisibility('Player.HasVideo')\
                and self.silentDialog is False:
            control.infoDialog(control.lang(32552), time=10000000)
            self.infoDialog = True

        try:
            if self.dupe_setting != 'true':
                raise Exception()


            lib = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["imdbnumber", "originaltitle", "year"]}, "id": 1}' % (year, str(int(year)+1), str(int(year)-1)))
            lib = c.ensure_text(lib, errors='ignore')
            lib = json.loads(lib)['result']['movies']
            lib = [i for i in lib if str(i['imdbnumber']) in imdb or (str(i['title']) == title and str(i['year']) == year)][0]
        except Exception as e:
            lib = []

        files_added = 0

        try:
            if lib != []:
                raise Exception()

            if self.check_setting == 'true':
                src = lib_tools.check_sources(title, year, imdb, None, None, None, None, None)
                if not src:
                    raise Exception()

            self.strmFile({'name': name, 'title': title, 'year': year, 'imdb': imdb})
            files_added += 1
        except Exception as e:
            pass

        if _range is True:
            return

        if self.infoDialog is True:
            control.infoDialog(control.lang(32554), time=1)

        if self.library_setting == 'true' and not control.condVisibility('Library.IsScanningVideo') and files_added > 0:
            control.execute('UpdateLibrary(video)')






    def silent(self, url):
        control.idle()

        if not control.condVisibility('Window.IsVisible(infodialog)') and\
            not control.condVisibility('Player.HasVideo'):
            control.infoDialog(control.lang(32552), time=10000000)
            self.infoDialog = True
            self.silentDialog = True

        items = movies.movies().get(url, idx=False) or []

        for i in items:
            try:
                if control.monitor.abortRequested():
                    return sys.exit()
                title = i['title']
                year = i['year']
                self.add(f'{title} ({year})', title, year, i['imdb'], _range=True)
            except Exception:
                pass

        if self.infoDialog is True:
            self.silentDialog = False
            control.infoDialog("Trakt Movies Sync Complete", time=1)

    def range(self, url):
        control.idle()

        yes = control.yesnoDialog(control.lang(32056))
        if not yes:
            return

        if not control.condVisibility('Window.IsVisible(infodialog)') and\
            not control.condVisibility('Player.HasVideo'):
            control.infoDialog(control.lang(32552), time=10000000)
            self.infoDialog = True

        items = movies.movies().get(url, idx=False)
        if items is None:
            items = []

        for i in items:
            try:
                #if control.monitor.abortRequested(): return sys.exit()
                self.add(f"{i['title']} ({i['year']})", i['title'], i['year'], i['imdb'], _range=True)
            except Exception:
                pass

        if self.infoDialog is True:
            control.infoDialog(control.lang(32554), time=1)

        if self.library_setting == 'true' and not control.condVisibility('Library.IsScanningVideo'):
            control.execute('UpdateLibrary(video)')


    def strmFile(self, i):
        try:
            name, title, year, imdb = i['name'], i['title'], i['year'], i['imdb']

            sysname, systitle = quote_plus(name), quote_plus(title)

            try:
                transtitle = title.translate(None, r'\/:*?"<>|')
            except Exception:
                transtitle = title.translate(str.maketrans('', '', r'\/:*?"<>|'))
            transtitle = cleantitle.normalize(transtitle)

            content = '%s?action=play&name=%s&title=%s&year=%s&imdb=%s' % (sys.argv[0], sysname, systitle, year, imdb)

            folder = lib_tools.make_path(self.library_folder, transtitle, year)

            lib_tools.create_folder(folder)
            lib_tools.write_file(os.path.join(folder, lib_tools.legal_filename(transtitle) + '.' + year + '.strm'), content)
            lib_tools.write_file(os.path.join(folder, lib_tools.legal_filename(transtitle) + '.' + year + '.nfo'), lib_tools.nfo_url('movie', i))
        except Exception:
            pass


class libtvshows:
    def __init__(self):
        self.library_folder = os.path.join(control.transPath(control.setting('library.tv')),'')

        #self.version = control.version()
        self.version = c.pluginversion

        self.check_setting = control.setting('library.check_episode') or 'false'
        self.include_unknown = control.setting('library.include_unknown') or 'true'
        self.library_setting = control.setting('library.update') or 'true'
        self.dupe_setting = control.setting('library.check') or 'true'

        self.datetime = datetime.datetime.now()
        if control.setting('library.importdelay') != 'true':
            self.date = self.datetime.strftime('%Y%m%d')
        else:
            self.date = (self.datetime - datetime.timedelta(hours=24)).strftime('%Y%m%d')
        self.silentDialog = False
        self.infoDialog = False
        self.block = False


    def add(self, tvshowtitle, year, imdb, tmdb, _range=False):
        try:
            if not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo')\
                    and self.silentDialog is False:
                #control.infoDialog(control.lang(32552), time=10000000) # Adding to library...
                control.infoDialog(control.lang(32552), time=100) # Adding to library...
                self.infoDialog = True


            c.log(f"[CM Debug @ 289 in libtools.py] tvshowtitle = {tvshowtitle}|year = {year}|imdb = {imdb}|tmdb = {tmdb}")
            from resources.lib.indexers import episodes
            seasons = episodes.Seasons().get(tvshowtitle, year, imdb, tmdb, meta=None, idx=False)
            seasons = [i['season'] for i in seasons]
            c.log(f'[CM Debug @ 293 in libtools.py] seasons ={repr(seasons)}')
            for s in seasons:
                items = episodes.episodes().get(tvshowtitle, year, imdb, tmdb, meta=None, season=s, idx=False)

                try:
                    items = [{
                        'title': i['title'],
                        'year': i['year'],
                        'imdb': i['imdb'],
                        'tvdb': i['tvdb'],
                        'tmdb': i['tmdb'],
                        'season': i['season'],
                        'episode': i['episode'],
                        'tvshowtitle': i['tvshowtitle'],
                        'premiered': i['premiered']
                        } for i in items]
                except Exception:
                    items = []

                try:
                    if not self.dupe_setting == 'true':
                        raise Exception()
                    if items == []:
                        raise Exception('items is empty')

                    _id = [items[0]['imdb'], items[0]['tmdb']]

                    lib = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties" : ["imdbnumber", "title", "year"]}, "id": 1}')
                    lib = c.ensure_text(lib, errors='ignore')
                    lib = json.loads(lib)['result']['tvshows']
                    c.log(f"[CM Debug @ 320 in libtools.py] lib = {lib}")
                    lib = [str(i['title']) for i in lib if str(i['imdbnumber']) in _id or (str(i['title']) == items[0]['tvshowtitle'] and str(i['year']) == items[0]['year'])]

                    lib = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"filter":{"and": [{"field": "tvshow", "operator": "is", "value": "%s"}]}, "properties": ["season", "episode"]}, "id": 1}' % lib)
                    lib = c.ensure_text(lib, errors='ignore')
                    lib = json.loads(lib)['result']['episodes']
                    c.log(f"[CM Debug @ 326 in libtools.py] lib = {lib}")
                    lib = ['S%02dE%02d' % (int(i['season']), int(i['episode'])) for i in lib]

                    items = [i for i in items if 'S%02dE%02d' % (int(i['season']), int(i['episode'])) not in lib]

                except Exception as e:
                    c.log(f"[CM Debug @ 444 in libtools.py] Exception in libtools.libtvshows.add(). Error = {e}")


                files_added = 0

                for i in items:
                    try:
                        if control.monitor.abortRequested():
                            return sys.exit()

                        if self.check_setting == 'true':
                            if i['episode'] == '1':
                                self.block = True
                                src = lib_tools.check_sources(i['title'], i['year'], i['imdb'], i['tmdb'], i['season'], i['episode'], i['tvshowtitle'], i['premiered'])
                                if src:
                                    self.block = False
                            if self.block is True:
                                raise Exception()

                        premiered = i.get('premiered', '0')
                        if (premiered != '0' and int(re.sub('[^0-9]', '', str(premiered))) > int(self.date)) or (premiered == '0' and not self.include_unknown):
                            continue

                        self.strmFile(i)
                        files_added += 1
                    except Exception:
                        pass

            # cm - because running silent has range true, no lib update.
            # Lib is never control-executed even without the bool-checks, need to find out why
            if _range is True:
                return

            if self.infoDialog is True:
                control.infoDialog(control.lang(32554), time=1) # Process Complete

            if self.library_setting == 'true' and not control.condVisibility('Library.IsScanningVideo') and files_added > 0:
                control.execute('UpdateLibrary(video)')

        except Exception:
            pass

    def silent(self, url):
        control.idle()

        if not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
            control.infoDialog(control.lang(32608), time=10000000)
            self.infoDialog = True
            self.silentDialog = True


        items = tvshows.tvshows().get(url, idx=False)

        if items is None:
            items = []

        for i in items:
            try:
                if control.monitor.abortRequested():
                    return sys.exit()
                self.add(i['title'], i['year'], i['imdb'], i['tmdb'], _range=True)
            except Exception:
                pass

        if self.infoDialog is True:
            self.silentDialog = False
            control.infoDialog("Trakt TV Show Sync Complete", time=1)

    def range(self, url):
        control.idle()

        yes = control.yesnoDialog(control.lang(32056))
        if not yes:
            return

        if not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
            control.infoDialog(control.lang(32552), time=10000000)
            self.infoDialog = True


        items = tvshows.tvshows().get(url, idx=False)
        if items is None:
            items = []

        for i in items:
            try:
                #if control.monitor.abortRequested(): return sys.exit()
                self.add(i['title'], i['year'], i['imdb'], i['tmdb'], _range=True)
            except Exception:
                pass

        if self.infoDialog is True:
            control.infoDialog(control.lang(32554), time=1)

        if self.library_setting == 'true' and not control.condVisibility('Library.IsScanningVideo'):
            control.execute('UpdateLibrary(video)')

    def strmFile(self, i):
        try:
            title, year, imdb, tmdb, season, episode, tvshowtitle, premiered = i['title'], i['year'], i['imdb'], i['tmdb'], i['season'], i['episode'], i['tvshowtitle'], i['premiered']

            _episodetitle = quote_plus(cleantitle.normalize(title))
            _tvshowtitle, _premiered = quote_plus(cleantitle.normalize(tvshowtitle)), quote_plus(premiered)

            try:
                transtitle = tvshowtitle.translate(None, r'\/:*?"<>|')
            except Exception:
                transtitle = tvshowtitle.translate(str.maketrans('', '', r'\/:*?"<>|'))
            _transtitle = cleantitle.normalize(transtitle)

            #cm - 2.0.6 changed from play1
            content = '%s?action=play&title=%s&year=%s&imdb=%s&tmdb=%s&season=%s&episode=%s&tvshowtitle=%s&date=%s' % (sys.argv[0], _episodetitle, year, imdb, tmdb, season, episode, _tvshowtitle, _premiered)

            folder = lib_tools.make_path(self.library_folder, _transtitle, year)
            if not os.path.isfile(os.path.join(folder, 'tvshow.nfo')):
                lib_tools.create_folder(folder)
                lib_tools.write_file(os.path.join(folder, 'tvshow.nfo'), lib_tools.nfo_url('tv', i))

            folder = lib_tools.make_path(self.library_folder, _transtitle, year, season)
            lib_tools.create_folder(folder)
            lib_tools.write_file(os.path.join(folder, lib_tools.legal_filename('%s S%02dE%02d' % (_transtitle, int(season), int(episode))) + '.strm'), content)
        except Exception:
            pass


class libepisodes:
    def __init__(self):
        self.library_folder = os.path.join(control.transPath(control.setting('library.tv')),'')

        self.library_setting = control.setting('library.update') or 'true'
        self.include_unknown = control.setting('library.include_unknown') or 'true'
        self.property = '%s_service_property' % control.addonInfo('name').lower()

        self.datetime = datetime.datetime.utcnow()
        if control.setting('library.importdelay') != 'true':
            self.date = self.datetime.strftime('%Y%m%d')
        else:
            self.date = (self.datetime - datetime.timedelta(hours=24)).strftime('%Y%m%d')

        self.infoDialog = False


    def update(self, query=None, info='true'):
        if query is not None:
            control.idle()

        try:
            items = []
            season, episode = [], []
            show = [os.path.join(self.library_folder, i) for i in control.listDir(self.library_folder)[0]]
            for s in show:
                try:
                    season += [os.path.join(s, i) for i in control.listDir(s)[0]]
                except FileNotFoundError:
                    pass
            for s in season:
                try:
                    episode.append([os.path.join(s, i) for i in control.listDir(s)[1] if i.endswith('.strm')][-1])
                except:
                    pass

            for file in episode:
                try:
                    file = control.openFile(file)
                    read = file.read()
                    read = c.ensure_str(read)
                    file.close()

                    if not read.startswith(sys.argv[0]):
                        raise Exception()

                    params = dict(parse_qsl(read.replace('?','')))

                    try:
                        tvshowtitle = params['tvshowtitle']
                    except Exception:
                        tvshowtitle = None
                    try:
                        tvshowtitle = params['show']
                    except Exception:
                        pass
                    if tvshowtitle is None or tvshowtitle == '':
                        raise Exception()

                    year, imdb, tmdb = params['year'], params['imdb'], params.get('tmdb', '0')

                    imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))

                    items.append({
                        'tvshowtitle': tvshowtitle, 'year': year, 'imdb': imdb, 'tmdb': tmdb
                        })
                except Exception:
                    c.log('lib_ep_upd0', 1)
                    pass

            items = [i for x, i in enumerate(items) if i not in items[x + 1:]]
            if len(items) == 0:
                raise Exception()
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 640 in libtools.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 640 in libtools.py]Exception raised. Error = {e}')
            pass
        #except Exception:
        #    c.log('lib_ep_upd1', 1)
        #    return

        try:
            lib = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties" : ["imdbnumber", "title", "year"]}, "id": 1}')
            lib = c.ensure_text(lib, errors='ignore')
            lib = json.loads(lib)['result']['tvshows']
        except Exception:
            return

        if info == 'true' and not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
            control.infoDialog(control.lang(32553), time=10000000)
            self.infoDialog = True

        try:
            control.makeFile(control.dataPath)
            dbcon = database.connect(control.libcacheFile)
            dbcur = dbcon.cursor()
            dbcur.execute("CREATE TABLE IF NOT EXISTS tvshows (""id TEXT, ""items TEXT, ""UNIQUE(id)"");")
        except Exception:
            return

        try:
            from resources.lib.indexers import episodes
        except Exception:
            return

        files_added = 0

        # __init__ doesn't get called from services so self.date never gets updated and new episodes are not added to the library
        self.datetime = datetime.datetime.utcnow()
        if control.setting('library.importdelay') != 'true':
            self.date = self.datetime.strftime('%Y%m%d')
        else:
            self.date = (self.datetime - datetime.timedelta(hours=24)).strftime('%Y%m%d')

        for item in items:
            it = None

            if control.monitor.abortRequested():
                return sys.exit()

            try:
                dbcur.execute(f"SELECT * FROM tvshows WHERE id = \'{item['imdb']}\'")
                fetch = dbcur.fetchone()
                it = eval(c.ensure_str(fetch[1]))
            except Exception:
                pass

            try:
                if it is not None:
                    raise Exception()

                seasons = episodes.Seasons().get(item['tvshowtitle'], item['year'], item['imdb'], item['tmdb'], meta=None, idx=False)
                season = [i['season'] for i in seasons]
                for s in season:
                    #c.log('lib_seasons: ' + str(s))
                    it = episodes.episodes().get(item['tvshowtitle'], item['year'], item['imdb'], item['tmdb'], meta=None, season=s, idx=False)
                    #c.log('lib_it: ' + str(it))

                    status = seasons[0]['status'].lower()

                    it = [{'title': i['title'], 'year': i['year'], 'imdb': i['imdb'], 'tmdb': i['tmdb'], 'season': i['season'], 'episode': i['episode'], 'tvshowtitle': i['tvshowtitle'], 'premiered': i['premiered']} for i in it]

                if status in ['continuing', 'returning series']: # cm - 'Returning Series', 'Planned', 'In Production', 'Ended', 'Canceled', 'Pilot'
                    raise Exception()
                dbcur.execute("INSERT INTO tvshows Values (?, ?)", (item['imdb'], repr(it)))
                dbcon.commit()
            except Exception:
                pass

            try:
                id = [item['imdb'], item['tmdb']]

                ep = [c.ensure_str(x['title']) for x in lib if str(x['imdbnumber']) in id or (c.ensure_str(x['title']) == item['tvshowtitle'] and str(x['year']) == item['year'])][0]
                ep = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"filter":{"and": [{"field": "tvshow", "operator": "is", "value": "%s"}]}, "properties": ["season", "episode"]}, "id": 1}' % ep)

                ep = json.loads(ep).get('result', {}).get('episodes', {})
                ep = [{'season': int(i['season']), 'episode': int(i['episode'])} for i in ep]
                ep = sorted(ep, key=lambda x: (x['season'], x['episode']))[-1]

                num = [x for x,y in enumerate(it) if str(y['season']) == str(ep['season']) and str(y['episode']) == str(ep['episode'])][-1]
                it = [y for x,y in enumerate(it) if x > num]
                if len(it) == 0:
                    continue
            except Exception as e:
                continue

            for i in it:
                try:
                    if control.monitor.abortRequested():
                        return sys.exit()

                    premiered = i.get('premiered', '0')
                    if (premiered != '0' and int(re.sub('[^0-9]', '', str(premiered))) > int(self.date)) or (premiered == '0' and not self.include_unknown):
                        continue

                    libtvshows().strmFile(i)
                    files_added += 1
                except Exception as e:
                    pass

        if self.infoDialog is True:
            control.infoDialog(control.lang(32554), time=1)

        if self.library_setting == 'true' and not control.condVisibility('Library.IsScanningVideo') and files_added > 0:
            control.execute('UpdateLibrary(video)')


    def service(self):
        try:
            lib_tools.create_folder(os.path.join(control.transPath(control.setting('library.movie')), ''))
            lib_tools.create_folder(os.path.join(control.transPath(control.setting('library.tv')), ''))
        except Exception:
            pass

        try:
            control.makeFile(control.dataPath)
            dbcon = database.connect(control.libcacheFile)
            dbcur = dbcon.cursor()
            dbcur.execute("CREATE TABLE IF NOT EXISTS service (""setting TEXT, ""value TEXT, ""UNIQUE(setting)"");")
            dbcur.execute("SELECT * FROM service WHERE setting = 'last_run'")
            fetch = dbcur.fetchone()
            if fetch is None:
                serviceProperty = "1970-01-01 23:59:00.000000"
                dbcur.execute("INSERT INTO service Values (?, ?)", ('last_run', serviceProperty))
                dbcon.commit()
            else:
                serviceProperty = str(fetch[1])
            dbcon.close()
        except Exception:
            try:
                return dbcon.close()
            except Exception:
                return

        try:

            control.window.setProperty(self.property, serviceProperty)
        except Exception: return

        while not control.monitor.abortRequested():
            try:
                serviceProperty = control.window.getProperty(self.property)

                t1 = datetime.timedelta(hours=6)
                t2 = datetime.datetime.strptime(serviceProperty, '%Y-%m-%d %H:%M:%S.%f')
                t3 = datetime.datetime.now()

                check = abs(t3 - t2) > t1
                if check is False:
                    raise Exception()

                if (control.player.isPlaying() or control.condVisibility('Library.IsScanningVideo')):
                    raise Exception()

                serviceProperty = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

                control.window.setProperty(self.property, serviceProperty)

                try:
                    dbcon = database.connect(control.libcacheFile)
                    dbcur = dbcon.cursor()
                    dbcur.execute("CREATE TABLE IF NOT EXISTS service (""setting TEXT, ""value TEXT, ""UNIQUE(setting)"");")
                    #dbcur.execute("DELETE FROM service WHERE setting = 'last_run'")
                    dbcur.execute("REPLACE INTO service Values (?, ?)", ('last_run', serviceProperty))
                    dbcon.commit()
                    dbcon.close()
                except Exception:
                    try:
                        dbcon.close()
                    except Exception:
                        pass

                if not control.setting('library.service.update') == 'true':
                    raise Exception()
                info = control.setting('library.service.notification') or 'true'
                self.update(info=info)
            except Exception:
                pass

            control.sleep(10000)
