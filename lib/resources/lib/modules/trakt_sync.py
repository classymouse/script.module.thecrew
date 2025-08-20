# -*- coding: utf-8 -*-
'''
***********************************************************
*
* @file trakt_sync.py
* @package script.module.thecrew
*
* Created on 2024-05-30.
* Copyright 2024 by The Crew. All rights reserved.
*
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''

import json

from resources.lib.modules import keys
from . import trakt
from .database import CMDatabase as db
from .crewruntime import c


activities_dict = {
    "all": "TEXT",
    "movies":
    {
        "watched_at": "TEXT",
        "collected_at": "TEXT",
        "rated_at": "TEXT",
        "watchlisted_at": "TEXT",
        "favorited_at": "TEXT",
        "recommendations_at": "TEXT",
        "commented_at": "TEXT",
        "paused_at": "TEXT",
        "hidden_at": "TEXT"
    },
    "episodes":
    {
        "watched_at": "TEXT",
        "collected_at": "TEXT",
        "rated_at": "TEXT",
        "watchlisted_at": "TEXT",
        "commented_at": "TEXT",
        "paused_at": "TEXT"
    },
    "shows":
    {
        "rated_at": "TEXT",
        "watchlisted_at": "TEXT",
        "favorited_at": "TEXT",
        "recommendations_at": "TEXT",
        "commented_at": "TEXT",
        "hidden_at": "TEXT"
    },
    "seasons":
    {
        "rated_at": "TEXT",
        "watchlisted_at": "TEXT",
        "commented_at": "TEXT",
        "hidden_at": "TEXT"
    },

    "comments":
    {
        "liked_at": "TEXT",
        "blocked_at": "TEXT"
    },
    "lists":
    {
        "liked_at": "TEXT",
        "updated_at": "TEXT",
        "commented_at": "TEXT"
    },
    "watchlist":
    {
        "updated_at": "TEXT"
    },
    "favorites":
    {
        "updated_at": "TEXT"
    },
    "recommendations":
    {
        "updated_at": "TEXT"
    },
    "collaborations":
    {
        "updated_at": "TEXT"
    },
    "account":
    {
        "settings_at": "TEXT",
        "followed_at": "TEXT",
        "following_at": "TEXT",
        "pending_at": "TEXT",
        "requested_at": "TEXT"
    },
    "saved_filters":
    {
        "updated_at": "TEXT"
    },
    "notes":
    {
        "updated_at": "TEXT"
    }
}


class TraktSync:
    """
    Class for synchronizing with Trakt.
    """

    def __init__(self, **kwargs) -> None:
        """
        Initialize TraktSync class.

        Args:
            **kwargs: Keyword arguments to store in the instance.
        """
        self.datapath = kwargs.get('datapath', c.datapath)
        self.db_file = kwargs.get('db_file') if 'db_file' in kwargs else 'trakt_sync.db'
        self.db = db(db_file=self.db_file)
        self.get_trakt = kwargs.get('get_trakt', trakt.get_trakt_as_json)

    def __del__(self) -> None:
        """
        Close the database connection.
        """
        self.db.close()

    def get_activities(self) -> dict:

        response_json = self.get_trakt("sync/last_activities")

        for item in response_json:
            value = json.loads(json.dumps(response_json[item]))

            #c.log(f'[CM DEBUG in trakt_sync.py @ 137] type item = {type(item)} and type value = {type(value)}')
            #c.log(f'[CM DEBUG in trakt_sync.py @ 140] value = {value}')
            if not self._table_exists(item):
            #create table so loop over the response and insert into db
                #c.log(f'[CM DEBUG in trakt_sync.py @ 165] item = {item}')
                #create table
                if item == 'all':
                    sql = f'CREATE TABLE IF NOT EXISTS "{item}" ("{item}" TEXT)'
                else:
                    sql = f'CREATE TABLE IF NOT EXISTS "{item}" ({",".join([f"{key} TEXT" for key in list(response_json[item])])})'
                #c.log(f'[CM DEBUG in trakt_sync.py @ 171] sql = {sql}')
                self.db.execute(sql)
                self.db.commit()
                keys = []
                values = []
                if item == 'all':
                    temp.append(f"'{item}' = '{response_json[item]}'")
                else:
                    for key in list(response_json[item]):
                        #c.log(f'[CM DEBUG in trakt_sync.py @ 157] key = {key}')
                        value = response_json[item][key]
                        #c.log(f'[CM DEBUG in trakt_sync.py @ 159] value = {value}')
                        temp.append(f"'{key}' = '{value}'")
                keys = ", ".join(keys)
                values = ", ".join(values)
                sql = f"INSERT INTO '{item}' {keys} VALUES {values}"

                #c.log(f'[CM DEBUG in trakt_sync.py @ 172] sql = {sql}')
            else:
                #c.log(f'[CM DEBUG in trakt_sync.py @ 154] type value = {type(value)}')

                if item == 'all':
                    temp.append(f"'{item}' = '{response_json[item]}'")
                else:
                    for key in list(response_json[item]):
                        #c.log(f'[CM DEBUG in trakt_sync.py @ 157] key = {key}')
                        value = response_json[item][key]
                        #c.log(f'[CM DEBUG in trakt_sync.py @ 159] value = {value}')

                        temp.append(f"'{key}' = '{value}'")
                temp = ", ".join(temp)
                sql = f"REPLACE INTO '{item}' set {temp}"

                c.log(f'[CM DEBUG in trakt_sync.py @ 165] sql = {sql}')
                #self.db.execute(sql, tuple(response_json[item].values()))
                #self.db.commit()

        return response_json


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
