# -*- coding: utf-8 -*-
'''
***********************************************************
*
* @file database.py
* @package script.module.thecrew
*
* Created on 2024-06-09.
* Copyright 2024 by The Crew. All rights reserved.
*
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''

from sqlite3 import dbapi2 as db, OperationalError
import os
import traceback

import xbmcvfs
import xbmcgui
import xbmcaddon

from .crewruntime import c

dataPath = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))


class CMDatabase():
    '''CMDatabase class'''
    def __init__(self, **kwargs) -> None:
        self.con = None
        self.cur = None
        self.db_file = kwargs.get('db_file', None)
        self.table = kwargs.get('table') or None
        self._get_connection()
        self._set_settings()

    def __del__(self) -> None:
        '''Close shop.'''

        if self.cur:
            self.cur.close()


        if self.con:
            self.con.close()


    def _get_connection(self) -> None:
        try:
            if self.db_file:
                xbmcvfs.mkdir(dataPath)
                self.con = db.connect(os.path.join(dataPath, self.db_file), timeout=60, isolation_level=None)
                #self.con.row_factory = db.Row
                self.con.row_factory = self._dict_factory
                self.cur = self.con.cursor()
                return

            return
        except Exception as e:
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 72 in database.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 72 in database.py]Exception raised. Error = {e}')
            c.log(f'[CM DEBUG in database.py @ 77] datapath = {dataPath}, datafile = {self.db_file}')
            pass


    def _dict_factory(self, cursor, row) -> dict:
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d


    def _set_settings(self) -> None:
        try:
            self.execute('PRAGMA synchronous = OFF')
            self.execute('PRAGMA journal_mode = OFF')
            self.commit()
        except Exception as e:

            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 98 in database.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 99 in database.py]Exception raised. Error = {e}')


    def set_table(self, table) -> None:
        self.table = table

    def execute(self, query, params=None) -> None:
        if params:
            self.cur.execute(query, params)
        else:
            self.cur.execute(query)

    def commit(self) -> None:
        self.con.commit()

    def close(self) -> None:
        self.con.close()
        self.cur.close()

    def fetch_all(self, query, params=None) -> list:
        self.execute(query, params)
        return self.cur.fetchall()

    def fetch_one(self, query, params=None) -> dict:
        self.execute(query, params)
        return self.cur.fetchone()

    def fetch_column(self, query, column_name, params=None) -> list:
        self.execute(query, params)
        return [row[column_name] for row in self.cur.fetchall()]

    def create_table(self, table_name, columns) -> None:
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
        self.execute(query)

    def insert(self, table_name, values) -> None:
        columns = ', '.join(values.keys())
        placeholders = ', '.join('?' * len(values))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        self.execute(query, list(values.values()))

    def insert_many(self, table_name, values) -> None:
        columns = ', '.join(values[0].keys())
        placeholders = ', '.join('?' * len(values[0]))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        self.execute(query, [row.values() for row in values])

    def replace(self, table_name, values) -> None:
        columns = ', '.join(values.keys())
        placeholders = ', '.join('?' * len(values))
        query = f"REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})"
        #c.log(f'[CM DEBUG in database.py @ 82] query = {query}, values = {values}')
        self.execute(query, list(values.values()))

    def update(self, table_name, where, values) -> None:
        set_clause = ', '.join([f'{col}=?' for col in values.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where}"
        self.execute(query, list(values.values()))

    def delete(self, table_name, where) -> None:
        query = f"DELETE FROM {table_name} WHERE {where}"
        self.execute(query)
