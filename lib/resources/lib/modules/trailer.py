# -*- coding: utf-8 -*-
# pylint: disable=W0703
'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file trailer.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

import sys
import json
#import re
import requests # type: ignore

from . import client
from . import control
from . import utils
from . import cache
from . import keys
from .crewruntime import c


class trailers:
    '''
    Represents a trailer with associated metadata.
    '''
    def __init__(self):
        try:

            #https://www.imdb.com/_json/video/tt15571732
            c.log("[CM Debug @ 32 in trailer.py] inside trailers")

            self.session = requests.Session()

            self.imdb_baselink = 'https://www.imdb.com/_json/video/{}'
            self.tmdb_base = 'https://api.themoviedb.org/3'
            self.tmdb_user = control.setting('tm.personal_user') or control.setting('tm.user')
            self.tmdb_lang = control.apiLanguage()['tmdb']
            if not self.tmdb_user:
                self.tmdb_user = keys.tmdb_key
            self.tmdb_baselink = ''
            self.tmdb_url = f'{self.tmdb_base}/%s/%s/videos?api_key={self.tmdb_user}' \
                                        f'&language=en-US'
            self.show_url = f'{self.tmdb_base}/tv/%s/videos?api_key={self.tmdb_user}' \
                                        f'&include_video_language={self.tmdb_lang}'
            self.base_link = 'https://www.youtube.com'
            self.base_link2 = 'https://youtube.com'
            self.base_link3 = 'https://youtu.be'
            self.yt_url = 'https://www.youtube.com/watch?v='
            self.yt_plugin_url = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s'
            self.name = ''
            self.url = ''
            self.meta = ''
            self.tmdb = ''
            self.imdb = ''
            self.season = ''
            self.episode = ''
            self.windowedtrailer = 0
            self.mediatype = ''
            self.poster = ''
            self.fanart = ''
            self.banner = ''
            self.clearlogo = ''
            self.clearart = ''

            self.is_youtube_link = True if 'youtu' in self.url else False
            #self.key = control.addon('plugin.video.youtube').getSetting('youtube.api.key') or keys.yt_key
            self.key = control.addon('plugin.video.youtube').getSetting('youtube.api.key') or ""


            self.search_link = f'https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=10&q=%s&key={self.key}'
            self.youtube_watch = 'https://www.youtube.com/watch?v=%s'
            self.yt_plugin_url = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s'
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 67 in trailer.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 67 in trailer.py]Exception raised. Error = {e}')




    def __del__(self):
        self.session.close()

    def get(self, name, url, imdb, tmdb, windowedtrailer, mediatype, meta):
        try:
            self.name = name
            self.url = url
            self.imdb = imdb
            self.tmdb = tmdb
            self.mediatype = mediatype
            self.windowedtrailer = windowedtrailer
            #self.meta = json.dumps(meta) if not meta == None else meta
            #self.meta = meta if meta is None else json.dumps(meta)
            self.meta = meta if meta is None else json.loads(meta)

            self.poster = self.meta.get('poster', '') or control.addonPoster()
            self.fanart = self.meta.get('fanart', '') or control.addonFanart()
            self.banner = self.meta.get('banner') or control.addonBanner()
            self.clearlogo = self.meta.get('clearlogo') or control.addonClearlogo()
            self.clearart = self.meta.get('clearart') or control.addonClearart()

            #1. do we have an url?
            # play url
            #3if self.is_youtube_link is True:
            #    result = {}
            #    result['video'] = self.url
            #    result['title'] = self.name
            #    result['plot'] = ''
            #    result['icon'] = self.poster
            #    c.log(f"[CM Debug @ 117 in trailer.py] result = {result}")
            #    self.play(result)
            #    return

            #2. start with tmdb
            #First try tmdb
            result = self.getSources(mode='tmdb')


            if not result:
                #2. next, continue with imdb
                result = self.getSources(mode='imdb')

            #if not result in ['canceled', 'empty'] and result != '':
            if result not in ['canceled', 'empty', '']:
                c.log(f"[cm debug @ 117 in trailer.py]url = {result}") # cm - named tuple
                self.play(result)
            elif result == 'empty':
                control.infoDialog('No trailers available.')
            elif result == 'canceled':
                control.infoDialog('User cancelled trailers')
            else:
                control.infoDialog('Unexpected result in trailers')
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 128 in trailer.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 129 in trailer.py]Exception raised. Error = {e}')


    def play(self, result):
        try:
            #if not self.imdb or self.imdb == '0':
            #    raise Exception('self.imdb and self.tmdb !== 0')

            c.log(f"[CM Debug @ 140 in trailer.py] result = {repr(result)}")

            url = result['video']
            title = result['title']
            plot = result['plot']
            icon = result['video']
            poster = self.poster
            fanart = self.fanart

            item = control.item(label=title, path=url)
            item.setArt({'icon': poster, 'thumb': fanart, 'poster': poster, 'fanart': fanart})
            item.setInfo(type='video', infoLabels={'title': title, 'plot': plot})
            item.setProperty('IsPlayable', 'true')
            control.resolve(handle=int(sys.argv[1]), succeeded=True, listitem=item)

            if self.windowedtrailer == 1:
                control.sleep(1000)
                while control.player.isPlayingVideo():
                    control.sleep(1000)
                control.execute('Dialog.Close(%s, true)' % control.getCurrentDialogId)


        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 163 in trailer.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 164 in trailer.py]Exception raised. Error = {e}')



    def getSources(self, mode):
        try:
            if mode == 'imdb':
                #result = cache.get(client.request, 0, self.imdb_baselink.format(self.imdb))
                result = cache.get(client.request, 0, self.imdb_baselink.format(self.imdb))
                c.log(f"[CM Debug @ 165 in trailer.py] result={result}")
                if not result:
                    return
                items = utils.json_loads_as_str(result)

                list_items = items['playlists'][self.imdb]['listItems']
                video_metadata = items['videoMetadata']
                trailer_list = []
                for item in list_items:
                    try:
                        metadata = video_metadata[item['videoId']]
                        c.log(f"[CM Debug @ 193 in trailer.py] metadata = {repr(metadata)}")
                        title = metadata['title']
                        icon = metadata['smallSlate']['url2x']
                        #canoniculUrl = metadata['canonicalUrl']
                        plot = item.get('description') or title
                        related_to = metadata.get('primaryConst') or self.imdb

                        #if (not related_to == self.imdb) and (not self.name.lower() in ' '.join((title, plot)).lower()):
                        if (
                            related_to != self.imdb
                            and self.name.lower()
                            not in ' '.join((title, plot)).lower()
                        ):
                            continue

                        #trailer_url = [i['videoUrl'] for i in metadata['encodings'] if i['definition'] in ['1080', '720', '480p', '360p', 'SD']]
                        if trailer_url := [
                            i['videoUrl']
                            for i in metadata['encodings']
                            if i['definition']
                            in ['1080', '720', '480p', '360p', 'SD']
                        ]:
                            trailer_list.append({
                                'title': title,
                                'icon': icon,
                                'plot': plot,
                                'video': trailer_url[0]
                            })
                        if not trailer_url:
                            continue

                        trailer_list.append({
                            'title': title,
                            'icon': icon,
                            'plot': plot,
                            'video': trailer_url[0]
                        })

                    except Exception:
                        pass
            elif mode == 'tmdb':
                #if self.mediatype == 'tv':
                #url = self.tmdb_url % ('tv', self.tmdb)
                if self.mediatype in ['tvshow','episode']:
                    self.mediatype = 'tv'
                url = self.tmdb_url % (self.mediatype, self.tmdb)
                c.log(f"[CM Debug @ 216 in trailer.py] ---> url = {url}")
                result = self.session.get(url, timeout=15).json()

                listItems = result['results']
                trailer_list = []

                for item in listItems:
                    try:
                        title = item['name']
                        if item['site'] == 'YouTube':
                            trailer_url = self.yt_plugin_url % str(item['key'])
                        else:
                            trailer_url = ''
                        icon = control.addonThumb()
                        plot = title

                        if trailer_url == '':
                            continue

                        trailer_list.append({
                            'title': title,
                            'icon': icon,
                            'poster': self.poster,
                            'plot': plot,
                            'video': trailer_url
                            })
                    except Exception:
                        pass

            if not trailer_list:
                return 'empty'

            try:
                trailers = []
                for t in trailer_list:
                    li = control.item(label=t['title'])
                    #li.setArt({'icon': t['icon'], 'thumb': t['icon'], 'poster': t['icon']})
                    li.setArt({'icon': t['icon'], 'thumb': t['icon'], 'poster': self.poster})
                    trailers.append(li)

                if len(trailers) == 1:
                    return trailer_list[0]

                if len(trailers) == 0:
                    return 'empty'

                select = control.selectDialog(trailers, control.lang(90220) % str(mode), useDetails=True)

                if select < 0:
                    return 'canceled'
                return trailer_list[select]

            except Exception:
                pass
        except Exception:
            pass
