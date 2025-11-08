# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file cache.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

from __future__ import absolute_import

import hashlib
import re
import time
import os

import six

from sqlite3 import dbapi2 as db, OperationalError
from resources.lib.modules import control
from resources.lib.modules import utils
from resources.lib.modules.crewruntime import c

cache_table = 'cache'

def get(function_, duration, *args, **table):

    try:

        response = None

        f = repr(function_)
        f = re.sub('.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', f)

        a = hashlib.md5()
        for i in args:
            a.update(six.ensure_binary(i))
        a = six.ensure_str(a.hexdigest())

    except:
        pass

    try:
        table = table['table']
    except:
        table = 'rel_list'

    try:

        control.makeFile(control.dataPath)
        dbcon = db.connect(control.cacheFile)
        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM {} WHERE func = '{}' AND args = '{}'".format(table, f, a))
        match = dbcur.fetchone()

        response = eval(match[2].encode('utf-8'))

        t1 = int(match[3])
        t2 = int(time.time())
        update = (abs(t2 - t1) / 3600) >= int(duration)
        if not update:
            return response

    except:
        pass

    try:
        r = function_(*args)
        if (r is None or r == []) and not response == None:
            return response
        elif r is None or r == []:
            return r

    except:
        return

    try:

        r = repr(r)
        t = int(time.time())
        dbcur.execute("CREATE TABLE IF NOT EXISTS {} (""func TEXT, ""args TEXT, ""response TEXT, ""added TEXT, ""UNIQUE(func, args)"")".format(table))
        dbcur.execute("DELETE FROM {} WHERE func = '{}' AND args = '{}'".format(table, f, a))
        dbcur.execute("INSERT INTO %s (func, args, response, added) Values (?,?,?,?)" % table, (f, a, r, t))
        dbcon.commit()


    except Exception as e:
        #import traceback
        #failure = traceback.format_exc()
        #c.log('[CM Debug @ 100 in cache.py]Traceback:: ' + str(failure))
        #c.log(f'[CM Debug @ 105 in cache.py]Exception raised. Error = {e}')
        pass

    try:
        return eval(r.encode('utf-8'))
    except Exception as e:
        c.log('cache.get error 2:  error =' + str(e))
        pass




def timeout(function_, *args):
    try:
        key = _hash_function(function_, args)
        result = cache_get(key)
        return int(result['date']) if result else 0
    except:
        return 0

def cache_get(key):
    # type: (str, str) -> dict or None
    try:
        cursor = _get_connection_cursor()
        cursor.execute("SELECT * FROM %s WHERE key = ?" % cache_table, [key])
        return cursor.fetchone()
    except OperationalError:
        return None

def cache_insert(key, value):
    # type: (str, str) -> None
    cursor = _get_connection_cursor()
    now = int(time.time())
    cursor.execute("CREATE TABLE IF NOT EXISTS %s (key TEXT, value TEXT, date INTEGER, UNIQUE(key))" % cache_table)
    update_result = cursor.execute("UPDATE %s SET value=?,date=? WHERE key=?" % cache_table, (value, now, key))

    if update_result.rowcount == 0:
        cursor.execute("INSERT INTO %s Values (?, ?, ?)" % cache_table, (key, value, now))

    cursor.connection.commit()



def clear_caches(cache_types=None):
    """
    General function to clear specified cache types.
    - cache_types: List of strings (e.g., ['main', 'meta', 'providers', 'debrid', 'search']) or None for all.
    - Maintains ability to call individual functions separately.
    - Uses improved exception handling for robustness.
    """
    if cache_types is None:
        cache_types = ['main', 'meta', 'providers', 'debrid', 'search']

    cache_functions = {
        'main': _clear_main_cache,
        'meta': _clear_meta_cache,
        'providers': _clear_providers_cache,
        'debrid': _clear_debrid_cache,
        'search': _clear_search_cache
    }

    for cache_type in cache_types:
        if cache_type in cache_functions:
            try:
                cache_functions[cache_type]()
                c.log(f"[CM Debug @ clear_caches] Successfully cleared {cache_type} cache")
            except Exception as e:
                c.log(f"[CM Debug @ clear_caches] Failed to clear {cache_type} cache: {e}")
        else:
            c.log(f"[CM Debug @ clear_caches] Unknown cache type: {cache_type}")

def _clear_main_cache():
    """Clear main cache tables (cache_table, rel_list, rel_lib)."""
    try:
        cursor = _get_connection_cursor()
        for t in [cache_table, 'rel_list', 'rel_lib']:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {t}")
                cursor.execute("VACUUM")
                cursor.connection.commit()
            except OperationalError as e:
                c.log(f"[CM Debug @ _clear_main_cache] SQLite error clearing table '{t}': {e}")
            except Exception as e:
                c.log(f"[CM Debug @ _clear_main_cache] Unexpected error clearing table '{t}': {e}")
    except Exception as e:
        c.log(f"[CM Debug @ _clear_main_cache] Failed to initialize cursor: {e}")

def _clear_meta_cache():
    """Clear meta cache tables (meta)."""
    try:
        cursor = _get_connection_cursor_meta()
        for t in ['meta']:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {t}")
                cursor.execute("VACUUM")
                cursor.connection.commit()
            except OperationalError as e:
                c.log(f"[CM Debug @ _clear_meta_cache] SQLite error clearing table '{t}': {e}")
            except Exception as e:
                c.log(f"[CM Debug @ _clear_meta_cache] Unexpected error clearing table '{t}': {e}")
    except Exception as e:
        c.log(f"[CM Debug @ _clear_meta_cache] Failed to initialize cursor: {e}")

def _clear_providers_cache():
    """Clear providers cache tables (rel_src, rel_url)."""
    try:
        cursor = _get_connection_cursor_providers()
        for t in ['rel_src', 'rel_url']:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {t}")
                cursor.execute("VACUUM")
                cursor.connection.commit()
            except OperationalError as e:
                c.log(f"[CM Debug @ _clear_providers_cache] SQLite error clearing table '{t}': {e}")
            except Exception as e:
                c.log(f"[CM Debug @ _clear_providers_cache] Unexpected error clearing table '{t}': {e}")
    except Exception as e:
        c.log(f"[CM Debug @ _clear_providers_cache] Failed to initialize cursor: {e}")

def _clear_debrid_cache():
    """Clear debrid cache tables (debrid_data)."""
    try:
        cursor = _get_connection_cursor_debrid()
        for t in ['debrid_data']:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {t}")
                cursor.execute("VACUUM")
                cursor.connection.commit()
            except OperationalError as e:
                c.log(f"[CM Debug @ _clear_debrid_cache] SQLite error clearing table '{t}': {e}")
            except Exception as e:
                c.log(f"[CM Debug @ _clear_debrid_cache] Unexpected error clearing table '{t}': {e}")
    except Exception as e:
        c.log(f"[CM Debug @ _clear_debrid_cache] Failed to initialize cursor: {e}")

def _clear_search_cache():
    """Clear search cache tables (tvshow, movies)."""
    try:
        cursor = _get_connection_cursor_search()
        for t in ['tvshow', 'movies']:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {t}")
                cursor.execute("VACUUM")
                cursor.connection.commit()
            except OperationalError as e:
                c.log(f"[CM Debug @ _clear_search_cache] SQLite error clearing table '{t}': {e}")
            except Exception as e:
                c.log(f"[CM Debug @ _clear_search_cache] Unexpected error clearing table '{t}': {e}")
    except Exception as e:
        c.log(f"[CM Debug @ _clear_search_cache] Failed to initialize cursor: {e}")

# Keep individual functions for backward compatibility and separate calls
def cache_clear():
    _clear_main_cache()

def cache_clear_meta():
    _clear_meta_cache()

def cache_clear_providers():
    _clear_providers_cache()

def cache_clear_debrid():
    _clear_debrid_cache()

def cache_clear_search():
    _clear_search_cache()

# Update cache_clear_all to use the new general function
def cache_clear_all():
    clear_caches()  # Clears all by default

def cache_clear_all_old():
    cache_clear()
    cache_clear_meta()
    cache_clear_providers()
    cache_clear_debrid()

def _get_connection_cursor():
    conn = _get_connection()
    return conn.cursor()

def _get_connection():
    control.makeFile(control.dataPath)
    conn = db.connect(control.cacheFile)
    conn.row_factory = _dict_factory
    return conn

def _get_connection_cursor_meta():
    conn = _get_connection_meta()
    return conn.cursor()

def _get_connection_meta():
    control.makeFile(control.dataPath)
    conn = db.connect(control.metacacheFile)
    conn.row_factory = _dict_factory
    return conn

def _get_connection_cursor_providers():
    conn = _get_connection_providers()
    return conn.cursor()

def _get_connection_providers():
    control.makeFile(control.dataPath)
    conn = db.connect(control.providercacheFile)
    conn.row_factory = _dict_factory
    return conn

def _get_connection_cursor_debrid():
    conn = _get_connection_debrid()
    return conn.cursor()

def _get_connection_debrid():
    control.makeFile(control.dataPath)
    conn = db.connect(control.dbFile)
    conn.row_factory = _dict_factory
    return conn

def _get_connection_cursor_search():
    conn = _get_connection_search()
    return conn.cursor()

def _get_connection_search():
    control.makeFile(control.dataPath)
    conn = db.connect(control.searchFile)
    conn.row_factory = _dict_factory
    return conn

def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def _hash_function(function_instance, *args):
    return _get_function_name(function_instance) + _generate_md5(args)


def _get_function_name(function_instance):
    return re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', repr(function_instance))


def _generate_md5(*args):
    md5_hash = hashlib.md5()
    args = utils.traverse(args)
    [md5_hash.update(six.ensure_binary(arg, errors='replace')) for arg in args]
    return str(md5_hash.hexdigest())


def _is_cache_valid(cached_time, cache_timeout):
    now = int(time.time())
    diff = now - cached_time
    return (cache_timeout * 3600) > diff


def cache_version_check():
    if _find_cache_version():
        control.infoDialog(control.lang(32057), sound=True, icon='INFO') # Keep calm and expect us!


def _find_cache_version():
    version_file = os.path.join(control.dataPath, 'cache.v')
    try:
        with open(version_file, 'r', encoding="utf8") as fh:
            old_version = fh.read()
    except:
        old_version = '0'

    try:
        cur_version = control.addon('script.module.thecrew').getAddonInfo('version')
        if old_version != cur_version:
            with open(version_file, 'w', encoding="utf8") as fh:
                fh.write(cur_version)
            return True
        return False
    except:
        return False