# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * Genesis Add-on
 * Copyright (C) 2015 lambda
 *
 * - Mofidied by The Crew
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

from . import control
from . import trakt
from .crewruntime import c



def get_episode_progress(trakt_info, imdb, season, episode):
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

def get_movie_progress(trakt_info, imdb):
    """
    Return the seek position in seconds for a movie.

    :param list trakt_info: The full list of trakt progress info for the user
    :param str imdb: The IMDB ID of the movie
    :return: The seek position in seconds for the movie
    :rtype: float
    """
    for i in trakt_info:
        c.log(f"[CM Debug @ 55 in bookmarks.py] trakt_info = {trakt_info}")
        if imdb == i['movie']['ids']['imdb']:
            seekable = 1 < i['progress'] < 92
            if seekable:
                return (float(i['progress'] / 100) * int(i['movie']['runtime']) * 60)
    return 0

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


def get(media_type, imdb, season, episode, local=False):
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
    if control.setting('rersume.source') == '1' and trakt.getTraktCredentialsInfo() and not local:
        try:
            if media_type == 'episode':
                trakt_info = trakt.getTraktAsJson('https://api.trakt.tv/sync/playback/episodes?extended=full')
                c.log(f"[CM Debug @ 110 in bookmarks.py] trakt_info = {trakt_info}")
                return get_episode_progress(trakt_info, imdb, season, episode)
            else:
                trakt_info = trakt.getTraktAsJson('https://api.trakt.tv/sync/playback/movies?extended=full')
                return get_movie_progress(trakt_info, imdb)
        except BaseException:
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
        ok = int(current_time) > 120 and (current_time / total_time) < .92
        watched = (current_time / total_time) >= .92

        sql_select = f"SELECT * FROM bookmarks WHERE imdb = '{imdb}'"
        if media_type == 'episode':
            sql_select += f" AND season = '{season}' AND episode = '{episode}'"

        sql_update = f"UPDATE bookmarks SET timeInSeconds = '{time_in_seconds}' WHERE imdb = '{imdb}'"
        if media_type == 'episode':
            sql_update += f" AND season = '{season}' AND episode = '{episode}'"

        if media_type == 'movie':
            sql_update_watched = f"UPDATE bookmarks SET timeInSeconds = '0', playcount = %s, overlay = %s WHERE imdb = '{imdb}'"
        elif media_type == 'episode':
            sql_update_watched = f"UPDATE bookmarks SET timeInSeconds = '0', playcount = %s, overlay = %s WHERE imdb = '{imdb}' AND season = '{season}' AND episode = '{episode}'"

        if media_type == 'movie':
            sql_insert = f"INSERT INTO bookmarks Values ('{time_in_seconds}', '{media_type}', '{imdb}', '', '', '{_playcount}', '{overlay}')"
        elif media_type == 'episode':
            sql_insert = f"INSERT INTO bookmarks Values ('{time_in_seconds}', '{media_type}', '{imdb}', '{season}', '{episode}', '{_playcount}', '{overlay}')"

        if media_type == 'movie':
            sql_insert_watched = f"INSERT INTO bookmarks Values ('{time_in_seconds}', '{media_type}', '{imdb}', '', '', '%s', '%s')"
        elif media_type == 'episode':
            sql_insert_watched = f"INSERT INTO bookmarks Values ('{time_in_seconds}', '{media_type}', '{imdb}', '{season}', '{episode}', '%s', '%s')"

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
        if match:
            if ok:
                dbcur.execute(sql_update)
            elif watched:
                _playcount = match[5] + 1
                overlay = 7
                dbcur.execute(sql_update_watched % (_playcount, overlay))
        else:
            if ok:
                dbcur.execute(sql_insert)
            elif watched:
                _playcount = 1
                overlay = 7
                dbcur.execute(sql_insert_watched % (_playcount, overlay))
        dbcon.commit()
    except Exception:
        c.log('Exception in bookmarks.reset()')



def set_scrobble(current_time, total_time, content, imdb='', season='', episode=''):
    """
    Update the scrobble status for a movie or TV episode on Trakt.

    This function calculates the percentage of content watched based on the
    current playback time and total duration. It then sends a 'pause' or 'stop'
    scrobble action to Trakt depending on the percentage watched and notifies
    the user if notifications are enabled.

    :param current_time: The current playback time in seconds.
    :param total_time: The total duration of the content in seconds.
    :param content: The type of content being scrobbled ('movie' or 'episode').
    :param imdb: The IMDb ID of the content. Default is an empty string.
    :param season: The season number for TV episodes. Default is an empty string.
    :param episode: The episode number for TV episodes. Default is an empty string.
    """
    try:
        c.log(f"[CM Debug @ 230 in bookmarks.py] inside set_scrobble with current_time = {current_time}, total_time = {total_time}, content = {content}, imdb = {imdb}, season = {season}, episode = {episode}")
        percent = current_time / total_time * 100 if current_time != 0 and total_time != 0 else 0
        if 2 < percent < 92 and current_time > 120:
            trakt.scrobbleMovie(imdb, percent, 'pause') if content == 'movie' else trakt.scrobbleEpisode(imdb, season, episode, percent, 'pause')
            if content == 'movie':
                c.log(f"[CM Debug @ 235 in bookmarks.py] imdb = {imdb} | percent = {percent}, paused on {current_time}/{total_time}")
                trakt.scrobbleMovie(imdb, percent, 'pause')

                c.log(f"[CM Debug @ 237 in bookmarks.py] after scrobbleMovie: imdb = {imdb} | percent = {percent}, paused on {current_time}/{total_time}")
            else:
                trakt.scrobbleEpisode(imdb, season, episode, percent, 'pause')

            if control.setting('trakt.scrobble.notify') == 'true':
                control.sleep(1000)
                control.infoDialog('Trakt: Scrobble Paused')
        elif percent >= 92:
            #trakt.scrobbleMovie(imdb, percent, 'stop') if content == 'movie' else trakt.scrobbleEpisode(imdb, season, episode, percent, 'stop')
            if content == 'movie':
                trakt.scrobbleMovie(imdb, percent, 'stop')
            else:
                trakt.scrobbleEpisode(imdb, season, episode, percent, 'stop')
            if control.setting('trakt.scrobble.notify') == 'true':
                control.sleep(1000)
                control.infoDialog('Trakt: Scrobbled')
    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 252 in bookmarks.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 252 in bookmarks.py]Exception raised. Error = {e}')
        pass
    #except BaseException:
        #control.infoDialog('Scrobble Failed')



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


def sync_with_trakt():
    trakt.sync_bookmarks()