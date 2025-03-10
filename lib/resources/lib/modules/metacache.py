# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2015 lambda

    -Mofidied by The Crew
    -Copyright (C) 2019 The Crew


    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
# pylint: disable=W0703
# pylint: disable=W0719
#
import time
import sqlite3 as database


import six

from . import control
from .crewruntime import c


def fetch(items, lang='en', user=''):
    try:
        t2 = int(time.time())
        dbcon = database.connect(control.metacacheFile)
        dbcur = dbcon.cursor()
    except:
        return items

    for item in items:
        try:

            sql = f"""SELECT *
                        FROM meta
                        WHERE (
                                    imdb = '{item['imdb']}'
                                    and lang = '{lang}'
                                    and user = '{user}'
                                    and not imdb = '0'
                                )
                                or
                                (
                                    tmdb = '{item['tmdb']}'
                                    and lang = '{lang}'
                                    and user = '{user}'
                                    and not tmdb = '0'
                                )
                    """
            dbcur.execute(sql)
            #dbcur.execute("SELECT * FROM meta WHERE (imdb = '%s' and lang = '%s' and user = '%s' and not imdb = '0') or\
            #                                        (tmdb = '%s' and lang = '%s' and user = '%s' and not tmdb = '0')" % \
            #                                        (item['imdb'], lang, user, item['tmdb'], lang, user))
            match = dbcur.fetchone()

            t1 = int(match[6])
            update = (abs(t2 - t1) / 3600) >= 720
            if update is True:
                raise Exception()

            item_data = eval(c.ensure_str(match[5]))
            item_data = dict((k,v) for k, v in item_data.items() if not v == '0')

            item.update(item_data)
            item.update({'metacache': True})
        except Exception as e:
            pass

    return items


def insert(meta):
    try:
        control.makeFile(control.dataPath)
        dbcon = database.connect(control.metacacheFile)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS meta (""imdb TEXT, ""tmdb TEXT, ""tvdb TEXT, ""lang TEXT, ""user TEXT, ""item TEXT, ""time TEXT, ""UNIQUE(imdb, tmdb, tvdb, user, lang)"");")
        t = int(time.time())
        for m in meta:
            try:
                if "user" not in m:
                    m["user"] = ''
                if "lang" not in m:
                    m["lang"] = 'en'
                i = repr(m['item'])
                try:
                    dbcur.execute("DELETE * FROM meta WHERE (imdb = '%s' and lang = '%s' and user = '%s' and not imdb = '0') or \
                                                            (tvdb = '%s' and lang = '%s' and user = '%s' and not tvdb = '0' or \
                                                            (tmdb = '%s' and lang = '%s' and user = '%s' and not tmdb = '0'))" % \
                                                            (m['imdb'], m['lang'], m['user'], m['tvdb'], m['lang'], m['user'], m['tmdb'], m['lang'], m['user']))
                except:
                    pass
                dbcur.execute("INSERT OR REPLACE INTO meta Values (?, ?, ?, ?, ?, ?, ?)", (m['imdb'], m['tmdb'], m['tvdb'], m['lang'], m['user'], i, t))
            except:
                pass

        dbcon.commit()
    except:
        return


# def local(items, link, poster, fanart):
    # try:
        # dbcon = database.connect(control.metaFile())
        # dbcur = dbcon.cursor()
        # args = [i['imdb'] for i in items]
        # dbcur.execute('SELECT * FROM mv WHERE imdb IN (%s)'  % ', '.join(list(map(lambda arg:  "'%s'" % arg, args))))
        # data = dbcur.fetchall()
    # except:
        # return items

    # for i in range(0, len(items)):
        # try:
            # item = items[i]

            # match = [x for x in data if x[1] == item['imdb']][0]

            # try:
                # if poster in item and not item[poster] == '0': raise Exception()
                # if match[2] == '0': raise Exception()
                # items[i].update({poster: link % ('300', '/%s.jpg' % match[2])})
            # except:
                # pass
            # try:
                # if fanart in item and not item[fanart] == '0': raise Exception()
                # if match[3] == '0': raise Exception()
                # items[i].update({fanart: link % ('1280', '/%s.jpg' % match[3])})
            # except:
                # pass
        # except:
            # pass

    #return items