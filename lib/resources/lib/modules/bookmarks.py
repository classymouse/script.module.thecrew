# -*- coding: utf-8 -*-

'''
********************************************************cm*
* Classy Add-on
*
* @file bookmarks.py
* @package plugin.video.classy
*
* @copyright (c) 2025, Classy Mouse
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''

import sqlite3 as database

from . import control
from . import trakt
from .crewruntime import c



def get_episode_progress_old(trakt_info, imdb, season, episode):
    """
    Return the seek position in seconds for an episode of a show.

    :param list trakt_info: The full list of trakt progress info for the user
    :param str imdb: The IMDB ID of the show
    :param int season: The season number of the episode
    :param int episode: The episode number of the episode
    :return: The seek position in seconds for the episode
    :rtype: float
    """
    for i in trakt_info:
        if imdb == i['show']['ids']['imdb']:
            if int(season) == i['episode']['season'] and int(episode) == i['episode']['number']:
                seekable = 1 < i['progress'] < 92
                if seekable:
                    return float(i['progress'] / 100) * int(i['episode']['runtime']) * 60
    return 0

def get_movie_progress_old(trakt_info, imdb):
    """
    Return the seek position in seconds for a movie.

    :param list trakt_info: The full list of trakt progress info for the user
    :param str imdb: The IMDB ID of the movie
    :return: The seek position in seconds for the movie
    :rtype: float
    """
    for i in trakt_info:
        if imdb == i['movie']['ids']['imdb']:
            seekable = 1 < i['progress'] < 92
            if seekable:
                return (float(i['progress'] / 100) * int(i['movie']['runtime']) * 60)
    return 0

def get_progress_bookmark(imdb = 0, tmdb = 0, traktid = 0, tvdb = 0, mediatype = '', season = 0, episode = 0):
    try:
        #check if table progress exists
        if not trakt.table_exists('progress'):
            c.log(f"[CM Debug @ 63 in bookmarks.py]table does not exist {trakt.table_exists('progress')}")
            trakt.create_table('trakt_progress')

        sql_base = "SELECT * from progress WHERE "
        if mediatype != '':
            sql_base += f"media_type = '{mediatype}' and "

        tmdb = int(tmdb)
        traktid = int(traktid)
        tvdb = int(tvdb)

        sql_add = []
        sql_season = []
        if season != 0 and episode != 0:
            if imdb != 0:
                sql_add.append(f"showimdb = '{imdb}'")
            if tmdb != 0:
                sql_add.append(f"showtmdb = {tmdb}")
            if traktid != 0:
                sql_add.append(f"showtrakt = {traktid}")
            if tvdb != 0:
                sql_add.append(f"showtvdb = {tvdb}")
        else:
            if imdb != 0:
                sql_add.append(f"imdb = '{imdb}'")
            if tmdb != 0:
                sql_add.append(f"tmdb = {tmdb}")
            if traktid != 0:
                sql_add.append(f"trakt = {traktid}")
            if tvdb != 0:
                sql_add.append(f"tvdb = {tvdb}")


        sql = sql_base + ' or '.join(sql_add)

        sql_add = []

        if season != 0:
            sql_season.append(f"season = {season}")
        if episode != 0:
            sql_season.append(f"episode = {episode}")

        if len(sql_season) > 0:
            sql_select = sql + ' and ' + ' and '.join(sql_season)
        else:
            sql_select = sql

        if mediatype == 'movie':
            sql_select += " ORDER BY year DESC"
        elif mediatype == 'episode':
            sql_select += " ORDER BY tvshowtitle, season, episode ASC"
        else:
            sql_select += " ORDER BY tvshowtitle ASC"

        c.log(f"[CM Debug @ 109 in bookmarks.py] sql_select = {sql_select}")

        control.makeFile(control.dataPath)
        dbcon = trakt.get_connection(control.traktsyncFile, return_as_dict=True)
        dbcur = trakt.get_connection_cursor(dbcon)
        result = None
        if dbcur is not None:
            dbcur.execute(sql_select)
            result = dbcur.fetchone()
        if dbcon is not None:
            dbcon.commit()
        if result:
            return result['resume_point']
        else:
            return 0
    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 113 in bookmarks.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 113 in bookmarks.py]Exception raised. Error = {e}')
        return 0

def get_episode_progress(imdb, tmdb=0, traktid=0, tvdb=0, season=0, episode=0):
    return get_progress_bookmark(imdb=imdb, tmdb=tmdb, traktid=traktid, tvdb=tvdb, mediatype='episode', season=season, episode=episode)

def get_movie_progress(imdb, tmdb=0, traktid=0, tvdb=0, season=0, episode=0):
    return get_progress_bookmark(imdb=imdb, tmdb=tmdb, traktid=traktid, tvdb=tvdb, mediatype='movie', season=season, episode=episode)

def get_local_bookmark(imdb, media_type,season, episode):
    """
    Return the seek position in seconds for a given movie or episode.

    :param str imdb: The IMDB ID of the movie or show
    :param str media_type: The type of the media, either 'movie' or 'episode'
    :param int season: The season number of the episode
    :param int episode: The episode number of the episode
    :return: The seek position in seconds for the media
    :rtype: float
    """
    try:
        sql_select = f"SELECT * FROM bookmarks WHERE imdb = '{imdb}'"
        if media_type == 'episode':
            sql_select += f" AND season = '{season}' AND episode = '{episode}'"

        control.makeFile(control.dataPath)
        dbcon = database.connect(control.bookmarksFile)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS bookmarks (""timeInSeconds TEXT, ""type TEXT, ""imdb TEXT, ""season TEXT, ""episode TEXT, ""playcount INTEGER, ""overlay INTEGER, ""UNIQUE(imdb, season, episode)"");")
        dbcur.execute(sql_select)
        match = dbcur.fetchone()
        dbcon.commit()
        if match:
            offset = match[0]
            return float(offset)
        else:
            return 0
    except BaseException:
        return 0

def get(media_type, imdb, tmdb=0, traktid=0, tvdb=0, season=0, episode=0, local=False):
    """
    Return the seek position in seconds for a movie or episode.

    :param str media_type: The type of the media, either 'movie' or 'episode'
    :param str imdb: The IMDB ID of the movie or show
    :param int season: The season number for TV shows
    :param int episode: The episode number for TV shows
    :param bool local: Whether to use local bookmarks or trakt
    :return: The seek position in seconds for the media
    :rtype: float
    """
    if control.setting('bookmarks') == 'true' and trakt.get_trakt_credentials_info() and not local:
        try:
            if media_type == 'episode':
                #trakt_info = trakt.getTraktAsJson('https://api.trakt.tv/sync/playback/episodes?extended=full')
                #c.log(f"[CM Debug @ 134 in bookmarks.py] trakt_info = {trakt_info}")
                #return get_episode_progress(trakt_info, imdb, season, episode)
                return get_episode_progress(imdb=imdb, tmdb=tmdb, traktid=traktid, tvdb=tvdb, season=season, episode=episode)

            #trakt_info = trakt.getTraktAsJson('https://api.trakt.tv/sync/playback/movies?extended=full')
            #return get_movie_progress(trakt_info, imdb)
            return get_movie_progress(imdb=imdb, tmdb=tmdb, traktid=traktid, tvdb=tvdb)
        except Exception:
            return 0
    else:
        try:
            return get_local_bookmark(imdb, media_type,season, episode)
        except Exception:
            c.log('Exception in bookmarks.get()')
            return 0

def reset(current_time, total_time, media_type, imdb, season='', episode=''):
    """
    Reset a bookmark, marking the media as watched or unwatched.

    :param int current_time: The current time in seconds
    :param int total_time: The total time of the media in seconds
    :param str media_type: The type of media, either 'movie' or 'episode'
    :param str imdb: The IMDB ID of the movie or show
    :param int season: The season number for TV shows
    :param int episode: The episode number for TV shows
    """
    try:
        _playcount = 0
        overlay = 6
        time_in_seconds = str(current_time)
        ok = int(current_time) > 0 and (current_time / total_time) < .92
        watched = (current_time / total_time) >= .92
        resume_point = float(float(current_time) / float(total_time))

        sql_select = f"SELECT * FROM bookmarks WHERE imdb = '{imdb}'"
        if media_type == 'episode':
            sql_select += f" AND season = '{season}' AND episode = '{episode}'"

        sql_update = f"UPDATE bookmarks SET timeInSeconds = '{time_in_seconds}' WHERE imdb = '{imdb}'"
        if media_type == 'episode':
            sql_update += f" AND season = '{season}' AND episode = '{episode}'"

        if media_type == 'movie':
            sql_update_watched = f"UPDATE bookmarks SET timeInSeconds = '0', playcount = ?, overlay = ? WHERE imdb = '{imdb}'"
            sql_update_progress = f"UPDATE bookmarks SET resume_point = '{resume_point}' WHERE imdb = '{imdb}'"
        elif media_type == 'episode':
            sql_update_watched = f"UPDATE bookmarks SET timeInSeconds = '0', playcount = ?, overlay = ? WHERE imdb = '{imdb}' AND season = '{season}' AND episode = '{episode}'"

        if media_type == 'movie':
            sql_insert = f"INSERT INTO bookmarks Values ('{time_in_seconds}', '{media_type}', '{imdb}', '', '', '{_playcount}', '{overlay}')"
        elif media_type == 'episode':
            sql_insert = f"INSERT INTO bookmarks Values ('{time_in_seconds}', '{media_type}', '{imdb}', '{season}', '{episode}', '{_playcount}', '{overlay}')"

        if media_type == 'movie':
            sql_insert_watched = f"INSERT INTO bookmarks Values ('{time_in_seconds}', '{media_type}', '{imdb}', '', '', '?', '?')"
        elif media_type == 'episode':
            sql_insert_watched = f"INSERT INTO bookmarks Values ('{time_in_seconds}', '{media_type}', '{imdb}', '{season}', '{episode}', ?, ?)"

        control.makeFile(control.dataPath)
        dbcon = database.connect(control.bookmarksFile)
        dbcur = dbcon.cursor()

        sql = '''
                CREATE TABLE IF NOT EXISTS bookmarks (
                timeInSeconds TEXT,
                type TEXT,
                imdb TEXT,
                season TEXT,
                episode TEXT,
                playcount INTEGER,
                overlay INTEGER,
                UNIQUE(imdb, season, episode)
                )
        '''

        dbcur.execute(sql)
        #dbcur.execute("CREATE TABLE IF NOT EXISTS bookmarks (""timeInSeconds TEXT,
        # ""type TEXT, ""imdb TEXT,
        # ""season TEXT, ""episode TEXT, ""playcount INTEGER, ""overlay INTEGER,
        # ""UNIQUE(imdb, season, episode)"");")
        dbcur.execute(sql_select)
        match = dbcur.fetchone()
        #match = ('3148.21', 'movie', 'tt16366836', '', '', 1, 7)
        if match:
            if ok:
                dbcur.execute(sql_update)
            elif watched:
                _playcount = match[5] + 1
                overlay = 7
                dbcur.execute(sql_update_watched, (_playcount, overlay))

                dbcur.execute(sql_update_progress)
        else:
            if ok:
                dbcur.execute(sql_insert)
            elif watched:
                _playcount = 1
                overlay = 7
                dbcur.execute(sql_insert_watched, (_playcount, overlay))
        dbcon.commit()
    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 274 in bookmarks.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 274 in bookmarks.py]Exception raised. Error = {e}')
        pass
    #except Exception:
    #    c.log('Exception in bookmarks.reset()')

def set_scrobble2(current_time: int, total_time: int, content: str, imdb: str = '', season: str = '', episode: str = '', action: str = 'pause') -> None:
    """
    Update the scrobble status for a movie or TV episode on Trakt.
    """
    try:
        progress = current_time / total_time * 100 if current_time != 0 and total_time != 0 else 0
        if 0 < progress < 92:
            if content == 'movie':
                trakt.scrobbleMovie(imdb, progress, action)
            else:
                trakt.scrobbleEpisode(imdb, season, episode, progress, action)
        elif progress >= 92:
            if content == 'movie':
                trakt.scrobbleMovie(imdb, progress, 'stop')
            else:
                trakt.scrobbleEpisode(imdb, str(season), str(episode), progress, 'stop')
            control.infoDialog('Trakt: Scrobbled')
    except Exception as e:
        control.infoDialog('Scrobble Failed')
        c.log(f'Exception raised in bookmarks.set_scrobble() Scrobble failed with error: {e}')




def set_scrobble(current_time, total_time, content, imdb='', season='', episode='', action='pause'):
    """
    Update the scrobble status for a movie or TV episode on Trakt.
    This function sends the current playback status to Trakt, allowing it to
    track the user's progress in watching movies or TV shows.
    """
    try:
        percent = current_time / total_time * 100 if current_time != 0 and total_time != 0 else 0
        if 0 < percent < 92:# and current_time > 120
            if content == 'movie':
                trakt.scrobbleMovie(imdb, percent, action)
            else:
                trakt.scrobbleEpisode(imdb, season, episode, percent, action)

            if control.setting('trakt.scrobble.notify') == 'true':
                control.sleep(1000)
                control.infoDialog(f'Trakt: Scrobble, action = {action}')
            elif c.devmode:
                control.sleep(1000)
                control.infoDialog(f'[Devmode] Trakt: Scrobble, action = {action}')
        elif percent >= 92:
            if content == 'movie':
                trakt.scrobbleMovie(imdb, percent, 'stop')
            else:
                trakt.scrobbleEpisode(imdb, str(season), str(episode), percent, 'stop')
            if control.setting('trakt.scrobble.notify') == 'true':
                control.sleep(1000)
                control.infoDialog('Trakt: Scrobbled')
            elif c.devmode:
                control.sleep(1000)
                control.infoDialog('Devmode - Trakt: Scrobbled')
    except Exception as e:
        control.infoDialog('Scrobble Failed')
        c.log(f'Exception raised in bookmarks.set_scrobble() Scrobble failed with error: {e}')


def get_indicators():
    """
    Return a list of media items that have been marked as watched.

    This function queries the bookmarks database and returns a list of IMDB IDs
    of media items that have been marked as watched. The list is empty if no
    media items have been marked as watched.

    :return: A list of IMDB IDs of media items marked as watched
    :rtype: list
    """
    control.makeFile(control.dataPath)
    dbcon = database.connect(control.bookmarksFile)
    dbcur = dbcon.cursor()
    dbcur.execute("SELECT * FROM bookmarks WHERE overlay = 7")
    match = dbcur.fetchall()
    dbcon.commit()
    if match:
        return [i[2] for i in match]
    else:
        return []

#! This def is going to be deprecated
def get_watched(media_type, imdb, season, episode):
    """
    Return the watched status of a media item.

    :param media_type: The type of the media, either 'movie' or 'episode'
    :param imdb: The IMDB ID of the media
    :param season: The season number of the episode
    :param episode: The episode number of the episode
    :return: The watched status of the media, either 6 (unwatched) or 7 (watched)
    :rtype: int
    """
    sql_select = f"SELECT * FROM bookmarks WHERE imdb = '{imdb}' AND overlay = 7"
    if media_type == 'episode':
        sql_select += f" AND season = '{season}' AND episode = '{episode}'"
    control.makeFile(control.dataPath)
    dbcon = database.connect(control.bookmarksFile)
    dbcur = dbcon.cursor()
    dbcur.execute(sql_select)
    match = dbcur.fetchone()
    dbcon.commit()
    if match:
        return 7
    else:
        return 6

def update_watched(media_type, new_value, imdb, season, episode):
    """
    Update the watched status of a media item in the bookmarks database.

    :param media_type: The type of the media, either 'movie' or 'episode'
    :param new_value: The new overlay value indicating the watched status
    :param imdb: The IMDB ID of the media
    :param season: The season number for TV shows (if applicable)
    :param episode: The episode number for TV shows (if applicable)
    """
    sql_update = f"UPDATE bookmarks SET overlay = {new_value} WHERE imdb = '{imdb}'"
    if media_type == 'episode':
        sql_update += f" AND season = '{season}' AND episode = '{episode}'"
    dbcon = database.connect(control.bookmarksFile)
    dbcur = dbcon.cursor()
    dbcur.execute(sql_update)
    dbcon.commit()

def delete_record(media_type, imdb, season, episode):
    """
    Delete a record from the bookmarks database.

    :param media_type: The type of the media, either 'movie' or 'episode'
    :param imdb: The IMDB ID of the media
    :param season: The season number for TV shows (if applicable)
    :param episode: The episode number for TV shows (if applicable)
    """
    sql_delete = f"DELETE FROM bookmarks WHERE imdb = '{imdb}'"
    if media_type == 'episode':
        sql_delete += f" AND season = '{season}' AND episode = '{episode}'"
    dbcon = database.connect(control.bookmarksFile)
    dbcur = dbcon.cursor()
    dbcur.execute(sql_delete)
    dbcon.commit()


# TODO def sync_with_trakt(): Needs checking
def sync_with_trakt():
    trakt.sync_bookmarks()
