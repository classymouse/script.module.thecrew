# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file player.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''


from argparse import Action
import base64
import codecs
import contextlib
import gzip
import json
import os
import re
import sys
#import time

import xbmc

import six
#from six.moves import xmlrpc_client

import xmlrpc.client



from urllib.parse import quote_plus, unquote_plus


from . import bookmarks
from . import control
from . import cleantitle
from . import playcount
from . import trakt#
#from . import log_utils
from .crewruntime import c


class player(xbmc.Player):
    def __init__ (self):
        self.totalTime = 0
        self.currentTime = 0
        self.duration = 0
        self.content = ''
        self.name = ''
        self.title = ''
        self.year = ''
        self.season = None
        self.episode = None
        self.DBID = None
        self.imdb = None
        self.tmdb = None
        self.tvdb = None
        self.ids = {}
        self.offset = 0
        self.getbookmark = False
        self.resume_point = 0



        xbmc.Player.__init__(self)

    def run(self, title, year, season, episode, imdb, tmdb, url, meta):#: -> Any
        try:
            control.sleep(200)
            c.log(f"[CM Debug @ 72 in player.py] inside player.run with title = {title}, year = {year}, season = {season}, episode = {episode}, imdb = {imdb}, tmdb = {tmdb}")

            self.totalTime = 0
            self.currentTime = 0
            self.content = 'movie' if season is None or episode is None else 'episode'
            #self.getbookmark = True if self.content in ['movie','episode'] else False
            self.getbookmark = True

            self.title = title
            self.year = year
            # TODO: Fix this, library, needs jsonrpc call
            self.DBID = None

            if self.content == 'movie':
                self.name = quote_plus(title) + quote_plus(f' ({year})')
            else:
                self.name = quote_plus(title) + quote_plus(f' S{int(season):02d}E{int(episode):02d}')
            self.name = unquote_plus(self.name)

            self.season = f'{int(season):01d}' if self.content == 'episode' else None
            self.episode = f'{int(episode):01d}' if self.content == 'episode' else None

            self.imdb = meta['imdb_id'] if imdb is None and 'imdb_id' in meta else imdb
            self.tmdb = meta['tmdb_id'] if tmdb is None and 'tmdb_id' in meta else tmdb
            self.tvdb = meta['tvdb_id'] if 'tvdb_id' in meta else None

            self.ids = {'imdb': self.imdb, 'tmdb': self.tmdb, 'tvdb': self.tvdb}
            self.ids = dict((k,v) for k, v in self.ids.items() if not v == '0')

            self.duration = int(meta.get('duration', 0))

            if 'resume_point' in meta:
                self.resume_point = meta['resume_point']  # in %
            elif 'offset' in meta:
                self.offset = meta['offset'] # in seconds
            else:
                self.offset = bookmarks.get(self.content, imdb=self.imdb, tmdb=self.tmdb)

            if self.resume_point:
                self.offset: float = (float(self.resume_point)/100) * float(self.duration)
            else:
                self.offset = float((self.duration/100) * float(self.offset))

            poster, thumb, fanart, clearlogo, clearart, discart, meta = self.getMetaArt(meta)

            item = control.item(path=url)
            if self.content == 'movie':
                item.setArt({
                    'icon': thumb, 'thumb': thumb, 'poster': poster, 'fanart': fanart,
                    'clearlogo': clearlogo, 'clearart': clearart, 'discart': discart
                    })
            else:
                item.setArt({
                    'icon': thumb, 'thumb': thumb, 'tvshow.poster': poster,
                    'season.poster': poster, 'fanart': fanart, 'clearlogo': clearlogo,
                    'clearart': clearart
                    })

            item.setInfo(type='video', infoLabels = control.metadataClean(meta))

            if 'plugin' in control.infoLabel('Container.PluginName'):
                control.player.play(url, item)

            control.resolve(int(sys.argv[1]), True, item)
            control.window.setProperty('script.trakt.ids', json.dumps(self.ids))

            self.keepPlaybackAlive()

            control.window.clearProperty('script.trakt.ids')
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 133 in player.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 133 in player.py]Exception raised. Error = {e}')
            return
        #except Exception as e:
            #c.log(f'player_fail, error = {e}')
            #return

    def getMetaArt(self, meta):

        try:
            poster = meta.get('poster')
            thumb = meta.get('thumb') or poster
            fanart = meta.get('fanart')
            clearlogo = meta.get('clearlogo', '')
            clearart = meta.get('clearart', '')
            discart = meta.get('discart', '')

            return poster, thumb, fanart, clearlogo, clearart, discart, meta
        except Exception:
            pass


    def getMeta(self, meta):

        try:
            poster = meta.get('poster')
            thumb = meta.get('thumb') or poster
            fanart = meta.get('fanart')
            clearlogo = meta.get('clearlogo', '')
            clearart = meta.get('clearart', '')
            discart = meta.get('discart', '')

            #return poster, thumb, fanart, clearlogo, clearart, discart, meta
        except Exception:
            pass

        try:
            if not self.content == 'movie':
                raise Exception()

            meta = control.jsonrpc(
                '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "year", "genre", "studio", "country", "runtime", "rating", "votes", "mpaa", "director", "writer", "plot", "plotoutline", "tagline", "thumbnail", "file"]}, "id": 1}' % (self.year, str(int(self.year)+1), str(int(self.year)-1))
                )
            meta = c.ensure_text(meta, errors='ignore')
            meta = json.loads(meta)['result']['movies']

            t = cleantitle.get(self.title)
            meta = [i for i in meta if self.year == str(i['year']) and (t == cleantitle.get(i['title']) or t == cleantitle.get(i['originaltitle']))][0]

            for k, v in meta.items():
                #if type(v) == list:
                if isinstance(v, list):
                    try:
                        meta[k] = str(' / '.join([c.ensure_text(i) for i in v]))
                    except Exception:
                        meta[k] = ''
                else:
                    try:
                        meta[k] = str(c.ensure_text(v))
                    except Exception:
                        meta[k] = str(v)

            if 'plugin' not in control.infoLabel('Container.PluginName'):
                self.DBID = meta['movieid']

            poster = thumb = meta['thumbnail']

            return poster, thumb, '', '', '', '', meta
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 217 in player.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 217 in player.py]Exception raised. Error = {e}')
            pass
        # except Exception as e:
        #     c.log(f"[CM Debug @ 218 in player.py] exception in getMeta for movie: {e}", 1)


        try:
            if self.content != 'episode':
                raise Exception()

            meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "year", "thumbnail", "file"]}, "id": 1}' % (self.year, str(int(self.year)+1), str(int(self.year)-1)))
            meta = c.ensure_text(meta, errors='ignore')
            meta = json.loads(meta)['result']['tvshows']

            t = cleantitle.get(self.title)
            meta = [i for i in meta if self.year == str(i['year']) and t == cleantitle.get(i['title'])][0]

            tvshowid = meta['tvshowid']
            poster = meta['thumbnail']

            meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params":{ "tvshowid": %d, "filter":{"and": [{"field": "season", "operator": "is", "value": "%s"}, {"field": "episode", "operator": "is", "value": "%s"}]}, "properties": ["title", "season", "episode", "showtitle", "firstaired", "runtime", "rating", "director", "writer", "plot", "thumbnail", "file"]}, "id": 1}' % (tvshowid, self.season, self.episode))
            meta = c.ensure_text(meta, errors='ignore')
            meta = json.loads(meta)['result']['episodes'][0]

            for k, v in six.iteritems(meta):
                if isinstance(v, list):
                    try:
                        meta[k] = str(' / '.join([c.ensure_text(i) for i in v]))
                    except Exception:
                        meta[k] = ''
                else:
                    try:
                        meta[k] = str(c.ensure_text(v))
                    except Exception:
                        meta[k] = str(v)

            if 'plugin' not in control.infoLabel('Container.PluginName'):
                self.DBID = meta['episodeid']

            thumb = meta['thumbnail']

            return poster, thumb, '', '', '', '', meta
        except Exception:
            pass

        poster, thumb, fanart, clearlogo, clearart, discart, meta = '', '', '', '', '', '', {'title': self.name}
        return poster, thumb, fanart, clearlogo, clearart, discart, meta



#TC 2/01/19 started
    def keepPlaybackAlive_old(self):
        pname = f"{control.addonInfo('id')}.player.overlay"
        control.window.clearProperty(pname)


        if self.content == 'movie':
            #overlay = playcount.getMovieOverlay(playcount.getMovieIndicators(), self.imdb)
            overlay = playcount.get_movie_overlay(playcount.get_movie_indicators(), self.imdb)

        elif self.content == 'episode':
            #overlay = playcount.getEpisodeOverlay(playcount.getTVShowIndicators(), self.imdb, self.tmdb, self.season, self.episode)
            overlay = playcount.get_episode_overlay(playcount.get_tvshow_indicators(), self.imdb, self.tmdb, self.season, self.episode)

        else:
            overlay = '6'

        for __ in range(240):
            if self.isPlayingVideo():
                break
            xbmc.sleep(1000)

        if overlay == '7':
            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()
                except Exception:
                    pass
                xbmc.sleep(2000)

        elif self.content == 'movie':
            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()

                    watcher = self.currentTime / self.totalTime >= .92
                    _property = control.window.getProperty(pname)

                    if watcher and _property != '7':
                        control.window.setProperty(pname, '7')
                        playcount.markMovieDuringPlayback(self.imdb, '7')

                    elif not watcher and not _property == '6':
                        control.window.setProperty(pname, '6')
                        playcount.markMovieDuringPlayback(self.imdb, '6')
                except Exception:
                    pass
                xbmc.sleep(2000)

        elif self.content == 'episode':
            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()

                    watcher = self.currentTime / self.totalTime >= .92
                    _property = control.window.getProperty(pname)

                    if watcher and not _property == '7':
                        control.window.setProperty(pname, '7')
                        playcount.markEpisodeDuringPlayback(self.imdb, self.tmdb, self.season, self.episode, '7')

                    elif not watcher and not _property == '6':
                        control.window.setProperty(pname, '6')
                        playcount.markEpisodeDuringPlayback(self.imdb, self.tmdb, self.season, self.episode, '6')
                except Exception:
                    pass
                xbmc.sleep(2000)

        control.window.clearProperty(pname)


#cm 19-02-2025
#overlay isn't used anymore and is calculated by kodi based on percentage of video watched

    def keepPlaybackAlive(self):
        pname = f"{control.addonInfo('id')}.player.overlay"
        control.window.clearProperty(pname)


        if self.content == 'movie':
            #overlay = playcount.getMovieOverlay(playcount.getMovieIndicators(), self.imdb)
            overlay = playcount.get_movie_overlay(playcount.get_movie_indicators(), self.imdb)

        elif self.content == 'episode':
            #overlay = playcount.getEpisodeOverlay(playcount.getTVShowIndicators(), self.imdb, self.tmdb, self.season, self.episode)
            overlay = playcount.get_episode_overlay(playcount.get_tvshow_indicators(), self.imdb, self.tmdb, self.season, self.episode)

        else:
            overlay = '6'

        for __ in range(240):
            if self.isPlayingVideo():
                break
            xbmc.sleep(1000)

        if overlay == '7':
            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()
                except Exception:
                    pass
                xbmc.sleep(2000)

        elif self.content == 'movie':
            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()

                    watcher = self.currentTime / self.totalTime >= .92
                    c.log(f"[CM Debug @ 356 in player.py] watcher: {watcher}")
                    _property = control.window.getProperty(pname)

                    if watcher and _property != '7':
                        control.window.setProperty(pname, '7')
                        playcount.markMovieDuringPlayback(self.imdb, '7')

                    elif not watcher and _property != '6':
                        control.window.setProperty(pname, '6')
                        playcount.markMovieDuringPlayback(self.imdb, '6')
                except Exception:
                    pass
                xbmc.sleep(2000)

        elif self.content == 'episode':
            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()

                    watcher = self.currentTime / self.totalTime >= .92
                    c.log(f"[CM Debug @ 412 in player.py] episode watcher: {watcher}")
                    _property = control.window.getProperty(pname)

                    if watcher and _property != '7':
                        control.window.setProperty(pname, '7')
                        playcount.markEpisodeDuringPlayback(self.imdb, self.tmdb, self.season, self.episode, '7')

                    elif not watcher and _property != '6':
                        control.window.setProperty(pname, '6')
                        playcount.markEpisodeDuringPlayback(self.imdb, self.tmdb, self.season, self.episode, '6')
                except Exception:
                    pass
                xbmc.sleep(2000)

        control.window.clearProperty(pname)


    def do_rpc(self, method, params):
        """
        Construct a JSON-RPC request string.
        - method: String, e.g., "VideoLibrary.SetMovieDetails"
        - params: Dict, e.g., {"movieid": 123, "playcount": 1}
        Returns the formatted JSON string or None on error.
        """
        try:
            # Serialize params to JSON string
            params_json = json.dumps(params)
            return '{"jsonrpc": "2.0", "method": "%s", "params": %s, "id": 1}' % (
                method,
                params_json,
            )
        except Exception as e:
            c.log(f"[CM Debug @ do_rpc] Failed to construct RPC: {e}")
            return None




    #! f-string on rpc impossible for now on py < 3.11 because of nesting-level
    def libForPlayback(self):
        with contextlib.suppress(Exception):
            if not self.DBID:
                return

            if self.content == 'movie':
                self.do_rpc('VideoLibrary.SetMovieDetails', {"movieid" : int(self.DBID), "playcount" : 1})
            elif self.content == 'episode':
                self.do_rpc('VideoLibrary.SetEpisodeDetails', {"episodeid" : int(self.DBID), "playcount" : 1})
            else:
                rpc = ''

            if rpc:
                control.jsonrpc(rpc)
                control.refresh()

    def idleForPlayback(self):
        for _ in range(400):
            if control.condVisibility('Window.IsActive(busydialog)') == 1 or\
                control.condVisibility('Window.IsActive(busydialognocancel)') == 1:
                control.idle()
            else:
                break
            control.sleep(100)

    def onAVStarted(self) -> None:
        try:
            control.execute('Dialog.Close(all,true)')
            if control.setting('bookmarks') == 'true' and int(self.offset) > 0 and self.isPlayingVideo():
                if control.setting('bookmarks.auto') == 'true':
                    self.seekTime(float(self.offset))
                else:
                    self.pause()
                    minutes, seconds = divmod(float(self.offset), 60)
                    hours, minutes = divmod(minutes, 60)
                    label = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
                    label = c.lang(32350) % label
                    if control.setting('bookmarks') == 'true' and trakt.get_trakt_credentials_info() is True:
                        yes = control.yesnoDialog(label + '[CR][I]Trakt sync is enabled [scrobble][/I] ', heading=c.lang(32344)) #RESUME
                    else:
                        yes = control.yesnoDialog(label, heading=c.lang(32344)) #RESUME
                    if yes:
                        self.seekTime(float(self.offset))
                    if not yes:
                        self.seekTime(0.0)
                    control.sleep(1000)
                    self.pause()


                #subtitles().get(self.name, self.imdb, self.season, self.episode)
                self.idleForPlayback()
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 458 in player.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 458 in player.py]Exception raised. Error = {e}')
            pass

    def update_time(self, action='pause') -> None:
        if self.totalTime == 0 or self.currentTime == 0:
            control.sleep(2000)
            return

        if self.getbookmark is True:
            c.log(f"[CM Debug @ 501 in player.py] reset bookmarks with action = {action}. self.currentTime = {self.currentTime}, self.totalTime = {self.totalTime}, self.content = {self.content}, self.imdb = {self.imdb}, self.season = {self.season}, self.episode = {self.episode}")
            bookmarks.reset(self.currentTime, self.totalTime, self.content, self.imdb, self.season, self.episode)

        if trakt.get_trakt_credentials_info() is True and control.setting('trakt.scrobble') == 'true' and action is not None:
            c.log(f"[CM Debug @ 506 in player.py] scrobbling to trakt: {action} with self.currentTime = {self.currentTime}, self.totalTime = {self.totalTime}, self.content = {self.content}, self.imdb = {self.imdb}, self.season = {self.season}, self.episode = {self.episode}")
            bookmarks.set_scrobble(self.currentTime, self.totalTime, self.content, self.imdb, self.season, self.episode, action)

        if float(self.currentTime / self.totalTime) >= 0.92:
            self.libForPlayback()

        control.refresh()



    def onPlayBackResumed(self):
        c.log(f"[CM Debug @ 506 in player.py] onPlayBackResumed with self.currentTime = {self.currentTime}, self.totalTime = {self.totalTime}")
        self.update_time('start')

    def onPlayBackPaused(self):
        c.log(f"[CM Debug @ 510 in player.py] onPlayBackPaused with self.currentTime = {self.currentTime}, self.totalTime = {self.totalTime}")
        self.update_time('pause')

    def onPlayBackStopped(self):
        c.log(f"[CM Debug @ 514 in player.py] onPlayBackStopped with self.currentTime = {self.currentTime}, self.totalTime = {self.totalTime}")
        self.update_time('stop')

    def onPlayBackEnded(self):
        c.log(f"[CM Debug @ 518 in player.py] onPlayBackEnded with self.currentTime = {self.currentTime}, self.totalTime = {self.totalTime}")
        self.update_time('stop')

    def onPlayBackSeek(self, time, seekOffset):
        c.log(f"[CM Debug @ 522 in player.py] onPlayBackSeek with time = {time}, seekOffset = {seekOffset}")
        secs_time = float(time/60)
        secs_seekOffset = float(seekOffset/60)
        c.log(f"[CM Debug @ 525 in player.py] time = {secs_time}, seekOffset = {secs_seekOffset}")





    def onPlayBackStarted2(self):

        if control.setting('bookmarks') == 'true'and self.isPlayingVideo():# and int(self.offset) > 120
            if control.setting('bookmarks.auto') == 'true':
                c.log(f"[CM Debug @ 354 in player.py] seeking time {float(self.offset)}")
                self.seekTime(float(self.offset))
            else:
                self.pause()
                minutes, seconds = divmod(float(self.offset), 60)
                hours, minutes = divmod(minutes, 60)
                label = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                label = control.lang2(12022).format(label)
                if control.setting('bookmarks') == 'true' and trakt.get_trakt_credentials_info() is True:
                    yes = control.yesnoDialog(label + '[CR]  (Trakt scrobble)', heading=control.lang2(13404))
                else:
                    yes = control.yesnoDialog(label, heading=control.lang2(13404))
                if yes:
                    self.seekTime(float(self.offset))
                control.sleep(1000)
                self.pause()


            subtitles().get(self.name, self.imdb, self.season, self.episode)
            self.idleForPlayback()
        else:
            #self.onAVStarted()
            pass

    def onPlayBackStopped2(self):
        if self.totalTime == 0 or self.currentTime == 0:
            control.sleep(2000)
            return

        bookmarks.reset(self.currentTime, self.totalTime, self.content, self.imdb, self.season, self.episode)

        if (trakt.get_trakt_credentials_info() is True and control.setting('trakt.scrobble') == 'true'):
            bookmarks.set_scrobble(self.currentTime, self.totalTime, self.content, self.imdb, self.season, self.episode)

        if float(self.currentTime / self.totalTime) >= 0.92:
            self.libForPlayback()

            control.refresh()


    def onPlayBackEnded2(self):
        self.onPlayBackStopped()


class subtitles:
    def get(self, name, imdb, season, episode):
        try:
            if not control.setting('subtitles') == 'true':
                raise Exception()

            OSuser = control.setting('OSuser') or ''
            OSpass = control.setting('OSpass') or ''

            langDict = {
                'Afrikaans': 'afr', 'Albanian': 'alb', 'Arabic': 'ara', 'Armenian': 'arm', 'Basque': 'baq',
                'Bengali': 'ben', 'Bosnian': 'bos', 'Breton': 'bre', 'Bulgarian': 'bul', 'Burmese': 'bur',
                'Catalan': 'cat', 'Chinese': 'chi', 'Croatian': 'hrv', 'Czech': 'cze', 'Danish': 'dan', 'Dutch': 'dut',
                'English': 'eng', 'Esperanto': 'epo', 'Estonian': 'est', 'Finnish': 'fin', 'French': 'fre',
                'Galician': 'glg', 'Georgian': 'geo', 'German': 'ger', 'Greek': 'ell', 'Hebrew': 'heb', 'Hindi': 'hin',
                'Hungarian': 'hun', 'Icelandic': 'ice', 'Indonesian': 'ind', 'Italian': 'ita', 'Japanese': 'jpn',
                'Kazakh': 'kaz', 'Khmer': 'khm', 'Korean': 'kor', 'Latvian': 'lav', 'Lithuanian': 'lit',
                'Luxembourgish': 'ltz', 'Macedonian': 'mac', 'Malay': 'may', 'Malayalam': 'mal', 'Manipuri': 'mni',
                'Mongolian': 'mon', 'Montenegrin': 'mne', 'Norwegian': 'nor', 'Occitan': 'oci', 'Persian': 'per',
                'Polish': 'pol', 'Portuguese': 'por,pob', 'Portuguese(Brazil)': 'pob,por', 'Romanian': 'rum',
                'Russian': 'rus', 'Serbian': 'scc', 'Sinhalese': 'sin', 'Slovak': 'slo', 'Slovenian': 'slv',
                'Spanish': 'spa', 'Swahili': 'swa', 'Swedish': 'swe', 'Syriac': 'syr', 'Tagalog': 'tgl', 'Tamil': 'tam',
                'Telugu': 'tel', 'Thai': 'tha', 'Turkish': 'tur', 'Ukrainian': 'ukr', 'Urdu': 'urd'}

            codePageDict = {'ara': 'cp1256', 'ar': 'cp1256', 'ell': 'cp1253', 'el': 'cp1253', 'heb': 'cp1255',
                            'he': 'cp1255', 'tur': 'cp1254', 'tr': 'cp1254', 'rus': 'cp1251', 'ru': 'cp1251'}

            quality = ['bluray', 'hdrip', 'brrip', 'bdrip', 'dvdrip', 'webrip', 'hdtv']

            langs = []
            try:
                try:
                    langs = langDict[control.setting('subtitles.lang.1')].split(',')
                except Exception:
                    langs.append(langDict[control.setting('subtitles.lang.1')])
            except Exception:
                pass
            try:
                try:
                    langs = langs + langDict[control.setting('subtitles.lang.2')].split(',')
                except Exception:
                    langs.append(langDict[control.setting('subtitles.lang.2')])
            except Exception:
                pass


            try:
                subLang = xbmc.Player().getSubtitles()
            except Exception:
                subLang = ''
            if subLang == langs[0]:
                raise Exception()

            server = xmlrpc.client.Server('https://api.opensubtitles.org/xml-rpc', verbose=0)
            token = server.LogIn(OSuser, OSpass, 'en', 'XBMC_Subtitles_v5.2.14')['token']

            sublanguageid = ','.join(langs)
            imdbid = re.sub('[^0-9]', '', imdb)

            if not (season is None or episode is None):
                result = server.SearchSubtitles(token, [{'sublanguageid': sublanguageid, 'imdbid': imdbid, 'season': season, 'episode': episode}])['data']
                fmt = ['hdtv']
            else:
                result = server.SearchSubtitles(token, [{'sublanguageid': sublanguageid, 'imdbid': imdbid}])['data']
                try:
                    vidPath = xbmc.Player().getPlayingFile()
                except Exception:
                    vidPath = ''
                fmt = re.split(r'\.|\(|\)|\[|\]|\s|\-', vidPath)
                fmt = [i.lower() for i in fmt]
                fmt = [i for i in fmt if i in quality]

            filter = []
            result = [i for i in result if i['SubSumCD'] == '1']

            for lang in langs:
                filter += [i for i in result if i['SubLanguageID'] == lang and any(x in i['MovieReleaseName'].lower() for x in fmt)]
                filter += [i for i in result if i['SubLanguageID'] == lang and any(x in i['MovieReleaseName'].lower() for x in quality)]
                filter += [i for i in result if i['SubLanguageID'] == lang]

            try:
                lang = xbmc.convertLanguage(filter[0]['SubLanguageID'], xbmc.ISO_639_1)
            except Exception:
                lang = filter[0]['SubLanguageID']

            content = [filter[0]['IDSubtitleFile'], ]
            content = server.DownloadSubtitles(token, content)
            content = base64.b64decode(content['data'][0]['data'])
            content = gzip.GzipFile(fileobj=six.BytesIO(content)).read()

            subtitle = control.transPath('special://temp/')
            subtitle = os.path.join(subtitle, f'TemporarySubs.{lang}.srt')

            if control.setting('subtitles.utf') == 'true':
                codepage = codePageDict.get(lang, '')
                if codepage and not filter[0].get('SubEncoding', '').lower() == 'utf-8':
                    try:
                        content_encoded = codecs.decode(content, codepage)
                        content = codecs.encode(content_encoded, 'utf-8')
                    except Exception:
                        pass

            file = control.openFile(subtitle, 'w')
            file.write(content)
            file.close()

            control.sleep(1000)
            xbmc.Player().setSubtitles(subtitle)
        except Exception:
            pass
