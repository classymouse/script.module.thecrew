# -*- coding: utf-8 -*-
'''
***********************************************************
*
* @file artwork.py
* @package script.module.thecrew
*
* Created on 2024-06-11.
* Copyright 2024 by The Crew. All rights reserved.
*
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''
import os
import xbmcvfs
import xbmcaddon
import requests
from .database import CMDatabase as db
from .crewruntime import c

import time

from datetime import datetime, timedelta


########
# paths

dataPath = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
artworkPath = os.path.join(dataPath, 'artwork.db')
artworkFile = 'artwork.db'
#artwork_path = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.thecrew/artwork.db')

########
# sql
sql_table_artwork = "CREATE TABLE artwork (id INTEGER PRIMARY KEY AUTOINCREMENT,imdb TEXT, tmdb TEXT, tvdb TEXT, trakt TEXT, slug TEXT, title TEXT, year INTEGER, season INTEGER, episode INTEGER, poster TEXT, fanart TEXT, season_poster TEXT, tvshow_poster TEXT, thumb TEXT, banner TEXT, clearart TEXT, clearlogo TEXT, added INTEGER)"
#sql_table_exists = f"SELECT name FROM sqlite_master WHERE type='table' AND name={table_name}"

class artwork():
    def __init__(self, *args, **kwargs):
        self.dbFile = artworkFile
        self.db = db(db_file = self.dbFile)
        self.timeout = 720 # timeout in hrs
        self._check_databases
        #c.log(f'[CM DEBUG in artwork.py @ 47]initialized, db file = {self.dbFile}')

    def __delete__(self):
        self.db.close()


    def get(self, key, table='artwork', timeout=720): # timeout in hrs
        try:
            sql = f'SELECT * FROM {table} WHERE imdb={key} or tmdb={key} or tvdb={key} or trakt={key} or slug={key}'
            row = self.db.fetch_one(sql)
            if row:
                if self._is_valid(timeout, row):
                    #c.log(f'[CM DEBUG in artwork.py @ 58] is_valid = {self._is_valid(timeout, row)}')
                    return row
            else:
                return None
        except Exception as e:

                import traceback
                failure = traceback.format_exc()
                if 'no such table' in failure:

                    c.log(f'[CM Debug @ 58 in artwork.py]Traceback:: {failure}')
                    c.log(f'[CM Debug @ 58 in artwork.py]Exception raised. Error = {e}')
                    self._check_databases()
                    pass
                else:
                    c.log(f'[CM Debug @ 58 in artwork.py]Traceback:: {failure}')
                    c.log(f'[CM Debug @ 58 in artwork.py]Exception raised. Error = {e}')
                    pass

    def insert(self, imdb, tmdb, tvdb, trakt, slug, title, year, season, episode, poster, fanart, season_poster, tvshow_poster, thumb, banner, clearart, clearlogo):
        try:
            if not self._table_exists('artwork'):
                self.db.execute(sql_table_artwork)
                self.db.commit()

            added = time.mktime(datetime.now().timetuple())
            self.db.insert('artwork', dict(imdb=imdb, tmdb=tmdb, tvdb=tvdb, trakt=trakt, slug=slug, title=title, year=year, season=season, episode=episode, poster=poster, fanart=fanart, season_poster=season_poster, tvshow_poster=tvshow_poster, thumb=thumb, banner=banner, clearart=clearart, clearlogo=clearlogo, added=added))
            self.db.commit()
        except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 66 in artwork.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 66 in artwork.py]Exception raised. Error = {e}')
                pass


    def _check_databases(self):
        try:
            #c.log(f'[CM DEBUG in artwork.py @ 70] after db.connect(), file = {self.dbFile}')
            chk = self._table_exists('artwork')
            #c.log(f'[CM DEBUG in artwork.py @ 72] _check_databases, file = {sql_table_artwork}')


            if not chk:
                self.db.execute(sql_table_artwork)
                self.db.commit()
                self._check_databases()
            #else:
                #c.log(f'[CM DEBUG in artwork.py @ 80] _check_databases, file = {sql_table_artwork}')
        except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 82 in artwork.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 83 in artwork.py]Exception raised. Error = {e}')
                pass

    def _table_exists(self, table_name) -> bool:
        try:

            sql_table_exists = f'SELECT name FROM sqlite_master WHERE type="table" AND name="{table_name}"'
            #c.log(f'[CM DEBUG in artwork.py @ 67] sql_table_exists={sql_table_exists}')
            chk = self.db.fetch_one(sql_table_exists)
            if not chk:
                #c.log(f'[CM DEBUG in artwork.py @ 70] table chk = {chk}')
                return False
            return True
        except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 97 in artwork.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 97 in artwork.py]Exception raised. Error = {e}')
                pass

    def _is_valid(self, timeout, row):
        unixstamp = int(time.mktime(datetime.now().timetuple()))
        #c.log(f'[CM DEBUG in artwork.py @ 134] timeout = {timeout}, unixstamp = {unixstamp}, row["added"] = {row["added"]}')
        #c.log(f'[CM DEBUG in artwork.py @ 135] links = {(unixstamp - row["added"])} en rechts dus > {(timeout * 3600)}')
        return ((unixstamp - row['added']) < (timeout * 3600))







#art = artwork()