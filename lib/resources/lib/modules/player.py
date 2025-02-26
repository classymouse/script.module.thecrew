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

import base64
import codecs
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
        self.ids = {}
        self.offset = 0
        self.getbookmark = False



        xbmc.Player.__init__(self)

    def run(self, title, year, season, episode, imdb, tmdb, url, meta):#: -> Any
        try:
            control.sleep(200)

            self.totalTime = 0
            self.currentTime = 0

            self.content = 'movie' if season is None or episode is None else 'episode'
            self.getbookmark = True if self.content in ['movie','episode'] else False

            self.title = title
            self.year = year

            self.name = quote_plus(title) + quote_plus(f' ({year})') if self.content == 'movie'\
                else quote_plus(title) + quote_plus(f' S{int(season):02d}E{int(episode):02d}')
            self.name = unquote_plus(self.name)

            self.season = f'{int(season):01d}' if self.content == 'episode' else None
            self.episode = f'{int(episode):01d}' if self.content == 'episode' else None

            self.DBID = None
            self.imdb = imdb if imdb is not None else '0'
            self.tmdb = tmdb if tmdb is not None else '0'
            #self.ids = {'imdb': self.imdb, 'tmdb': self.tmdb}
            #self.ids = dict((k,v) for k, v in six.iteritems(self.ids) if not v == '0')
            self.ids = dict((k,v) for k, v in self.ids.items() if not v == '0')
            self.duration = int(meta.get('duration', 0))
            c.log(f"[CM Debug @ 96 in player.py] duration = {self.duration} with title = {self.title}")

            c.log(f"[CM Debug @ 93 in player.py] self.content = {self.content}")

            self.offset = bookmarks.get(self.content, imdb=self.imdb, tmdb=self.tmdb)
            #beware, new offset is in percentage of total playing time
            #offset = float((self.duration * self.offset) / 100)
            offset = (self.duration/100) * self.offset
            self.offset = offset

            c.log(f"[CM Debug @ 106 in player.py] offset = {self.offset} with title = {self.title}")

            poster, thumb, fanart, clearlogo, clearart, discart, meta = self.getMeta(meta)

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

    def getMeta(self, meta):

        try:
            poster = meta.get('poster')
            thumb = meta.get('thumb') or poster
            fanart = meta.get('fanart')
            clearlogo = meta.get('clearlogo', '')
            clearart = meta.get('clearart', '')
            discart = meta.get('discart', '')

            return poster, thumb, fanart, clearlogo, clearart, discart, meta
        except:
            pass

        try:
            if not self.content == 'movie':
                raise Exception()

            meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "year", "genre", "studio", "country", "runtime", "rating", "votes", "mpaa", "director", "writer", "plot", "plotoutline", "tagline", "thumbnail", "file"]}, "id": 1}' % (self.year, str(int(self.year)+1), str(int(self.year)-1)))
            meta = c.ensure_text(meta, errors='ignore')
            meta = json.loads(meta)['result']['movies']

            t = cleantitle.get(self.title)
            meta = [i for i in meta if self.year == str(i['year']) and (t == cleantitle.get(i['title']) or t == cleantitle.get(i['originaltitle']))][0]

            for k, v in meta.items():
                #if type(v) == list:
                if isinstance(v, list):
                    try:
                        meta[k] = str(' / '.join([c.ensure_text(i) for i in v]))
                    except:
                        meta[k] = ''
                else:
                    try:
                        meta[k] = str(c.ensure_text(v))
                    except:
                        meta[k] = str(v)

            if 'plugin' not in control.infoLabel('Container.PluginName'):
                self.DBID = meta['movieid']

            poster = thumb = meta['thumbnail']

            return poster, thumb, '', '', '', '', meta
        except:
            pass

        try:
            if not self.content == 'episode':
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
                if type(v) == list:
                    try:
                        meta[k] = str(' / '.join([c.ensure_text(i) for i in v]))
                    except:
                        meta[k] = ''
                else:
                    try:
                        meta[k] = str(c.ensure_text(v))
                    except:
                        meta[k] = str(v)

            if not 'plugin' in control.infoLabel('Container.PluginName'):
                self.DBID = meta['episodeid']

            thumb = meta['thumbnail']

            return poster, thumb, '', '', '', '', meta
        except:
            pass

        poster, thumb, fanart, clearlogo, clearart, discart, meta = '', '', '', '', '', '', {'title': self.name}
        return poster, thumb, fanart, clearlogo, clearart, discart, meta



#TC 2/01/19 started
    def keepPlaybackAlive_old(self):
        pname = f"{control.addonInfo('id')}.player.overlay"
        control.window.clearProperty(pname)
        pname2 = f"{control.addonInfo('id')}.player.playtime"
        control.window.clearProperty(pname)

        if self.content == 'movie':
            #overlay = playcount.getMovieOverlay(playcount.getMovieIndicators(), self.imdb)
            overlay = playcount.get_movie_overlay(playcount.getMovieIndicators(), self.imdb)

        elif self.content == 'episode':
            #overlay = playcount.getEpisodeOverlay(playcount.getTVShowIndicators(), self.imdb, self.tmdb, self.season, self.episode)
            overlay = playcount.get_episode_overlay(playcount.getTVShowIndicators(), self.imdb, self.tmdb, self.season, self.episode)

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
                except:
                    pass
                xbmc.sleep(2000)

        elif self.content == 'movie':
            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()

                    watcher = self.currentTime / self.totalTime >= .92
                    _property = control.window.getProperty(pname)

                    if watcher is True and not _property == '7':
                        control.window.setProperty(pname, '7')
                        playcount.markMovieDuringPlayback(self.imdb, '7')

                    elif watcher is False and not _property == '6':
                        control.window.setProperty(pname, '6')
                        playcount.markMovieDuringPlayback(self.imdb, '6')
                except:
                    pass
                xbmc.sleep(2000)

        elif self.content == 'episode':
            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()

                    watcher = self.currentTime / self.totalTime >= .92
                    _property = control.window.getProperty(pname)

                    if watcher is True and not _property == '7':
                        control.window.setProperty(pname, '7')
                        playcount.markEpisodeDuringPlayback(self.imdb, self.tmdb, self.season, self.episode, '7')

                    elif watcher is False and not _property == '6':
                        control.window.setProperty(pname, '6')
                        playcount.markEpisodeDuringPlayback(self.imdb, self.tmdb, self.season, self.episode, '6')
                except:
                    pass
                xbmc.sleep(2000)

        control.window.clearProperty(pname)


#cm 19-02-2025
#overlay isn't used anymore and is calculated by kodi based on percentage of video watched
#so i need to completely rewrite the keepPlaybackAlive function
#i will keep the same logic as before but without the overlay
#i will also remove the playcount.py file and move the functions to the player.py file
#i will also remove the playcount module from the imports
#i will also remove the playcount.markMovieDuringPlayback and playcount.markEpisodeDuringPlayback functions
#i will also remove the playcount.getMovieOverlay and playcount.getEpisodeOverlay functions
#i will also remove the playcount.getMovieIndicators and playcount.getTVShowIndicators functions
#i will also remove the playcount.getMovieOverlay and playcount.getEpisodeOverlay functions
    def keepPlaybackAlive(self):
        pname = f"{control.addonInfo('id')}.player.overlay"
        control.window.clearProperty(pname)

        if self.content == 'movie':
            #overlay = playcount.getMovieOverlay(playcount.getMovieIndicators(), self.imdb)
            overlay = playcount.get_movie_overlay(playcount.getMovieIndicators(), self.imdb)

        elif self.content == 'episode':
            #overlay = playcount.getEpisodeOverlay(playcount.getTVShowIndicators(), self.imdb, self.tmdb, self.season, self.episode)
            overlay = playcount.get_episode_overlay(playcount.getTVShowIndicators(), self.imdb, self.tmdb, self.season, self.episode)

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
                except:
                    pass
                xbmc.sleep(2000)

        elif self.content == 'movie':
            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()

                    watcher = self.currentTime / self.totalTime >= .92
                    _property = control.window.getProperty(pname)

                    if watcher is True and not _property == '7':
                        control.window.setProperty(pname, '7')
                        playcount.markMovieDuringPlayback(self.imdb, '7')

                    elif watcher is False and not _property == '6':
                        control.window.setProperty(pname, '6')
                        playcount.markMovieDuringPlayback(self.imdb, '6')
                except:
                    pass
                xbmc.sleep(2000)

        elif self.content == 'episode':
            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()

                    watcher = self.currentTime / self.totalTime >= .92
                    _property = control.window.getProperty(pname)

                    if watcher is True and not _property == '7':
                        control.window.setProperty(pname, '7')
                        playcount.markEpisodeDuringPlayback(self.imdb, self.tmdb, self.season, self.episode, '7')

                    elif watcher is False and not _property == '6':
                        control.window.setProperty(pname, '6')
                        playcount.markEpisodeDuringPlayback(self.imdb, self.tmdb, self.season, self.episode, '6')
                except:
                    pass
                xbmc.sleep(2000)

        control.window.clearProperty(pname)







    #! f-string on rpc impossible for now on py < 3.11 because of nesting-level
    def libForPlayback(self):
        try:
            if self.DBID is None:
                raise Exception()

            if self.content == 'movie':
                rpc = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : %s, "playcount" : 1 }, "id": 1 }' % str(self.DBID)
            elif self.content == 'episode':
                rpc = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid" : %s, "playcount" : 1 }, "id": 1 }' % str(self.DBID)
            else:
                rpc = ''

            if rpc:
                control.jsonrpc(rpc)
                control.refresh()
        except:
            pass

    def idleForPlayback(self):
        for _ in range(400):
            if control.condVisibility('Window.IsActive(busydialog)') == 1 or\
                control.condVisibility('Window.IsActive(busydialognocancel)') == 1:
                control.idle()
            else:
                break
            control.sleep(100)

    def onAVStarted(self) -> None:
        #control.execute('Dialog.Close(all,true)')
        #if self.getbookmark is True and self.offset != '0':
        #    self.seekTime(float(self.offset))
        #    c.log(f"[CM Debug @ 429 in player.py] onPlayBackStarted for title = {self.title} with seektime = {self.offset}")
        if control.setting('bookmarks') == 'true' and int(self.offset) > 0 and self.isPlayingVideo():
            if control.setting('bookmarks.auto') == 'true':
                self.seekTime(float(self.offset))
            else:
                self.pause()

                minutes, seconds = divmod(float(self.offset), 60)
                hours, minutes = divmod(minutes, 60)
                label = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                label = control.lang2(12022).format(label)
                if control.setting('bookmarks') == 'true' and trakt.getTraktCredentialsInfo() is True:
                    yes = control.yesnoDialog(label + '[CR]  (Trakt scrobble)', heading=control.lang2(13404))
                else:
                    yes = control.yesnoDialog(label, heading=control.lang2(13404))
                if yes:
                    self.seekTime(float(self.offset))
                control.sleep(1000)
                self.pause()


            #subtitles().get(self.name, self.imdb, self.season, self.episode)
            self.idleForPlayback()


    def onPlayBackPaused(self):
        if self.getbookmark is True:
            bookmarks.reset(self.currentTime, self.totalTime, self.name, self.year)


    def onPlayBackStopped(self):
        if self.getbookmark is True:
            bookmarks.reset(self.currentTime, self.totalTime, self.name, self.year)

    def onPlayBackEnded(self):
        self.onPlayBackStopped()




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
                if control.setting('bookmarks') == 'true' and trakt.getTraktCredentialsInfo() is True:
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

        if (trakt.getTraktCredentialsInfo() is True and control.setting('trakt.scrobble') == 'true'):
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
                except:
                    langs.append(langDict[control.setting('subtitles.lang.1')])
            except:
                pass
            try:
                try:
                    langs = langs + langDict[control.setting('subtitles.lang.2')].split(',')
                except:
                    langs.append(langDict[control.setting('subtitles.lang.2')])
            except:
                pass


            try:
                subLang = xbmc.Player().getSubtitles()
            except:
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
                except:
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
            except:
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
                    except:
                        pass

            file = control.openFile(subtitle, 'w')
            file.write(content)
            file.close()

            control.sleep(1000)
            xbmc.Player().setSubtitles(subtitle)
        except:
            pass
