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

import re
import sys
import json
#import re
import requests

from . import client
from . import control
from . import utils
from . import cache
from . import keys
from .crewruntime import c
from .listitem import ListItemInfoTag


class Trailers:
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

            self.is_youtube_link = 'youtu' in self.url
            #self.key = control.addon('plugin.video.youtube').getSetting('youtube.api.key') or keys.yt_key
            self.key = control.addon('plugin.video.youtube').getSetting('youtube.api.key') or ""


            self.search_link = f'https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=10&q=%s&key={self.key}'
            self.youtube_watch = 'https://www.youtube.com/watch?v=%s'
            self.yt_plugin_url1 = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s'
            self.yt_plugin_url = 'plugin://plugin.video.youtube/play/?video_id=%s'
            self.yt_plugin_url2 = "https://www.youtube.com/embed/%s?autohide=0&iv_load_policy=3&modestbranding=0&rel=0&mute=0&autoplay=0&enablejsapi=1&origin=https://www.bubblegum.com&widgetid=1"
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
            self.meta = meta if meta is None else json.loads(meta)
            self.poster = self.meta.get('poster', '') or control.addonPoster()
            self.fanart = self.meta.get('fanart', '') or control.addonFanart()
            self.banner = self.meta.get('banner') or control.addonBanner()
            self.clearlogo = self.meta.get('clearlogo') or control.addonClearlogo()
            self.clearart = self.meta.get('clearart') or control.addonClearart()

            result = self.get_sources(mode='tmdb') or self.get_sources(mode='imdb')

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
            c.log(f"[CM Debug @ 160 in trailer.py] url = {url}")

            if 'youtube' in url and 'video_id' in url:
                #split the url on 'video_id=' and take the last part
                video_id = url.split('video_id=')[-1]
                c.log(f"[CM Debug @ 163 in trailer.py]found the culprit! splitting on video_id: {video_id}")
                url = self.yt_plugin_url % video_id
                c.log(f"[CM Debug @ 167 in trailer.py] new url = {url}")


            c.log(f"[CM Debug @ 168 in trailer.py] url = {url}")
            #if 'youtube' in url:
                #url = self.get_youtube_link(url)
            title = result['title']
            plot = result['plot']
            #icon = result['video']
            poster = self.poster
            fanart = self.fanart

            item = control.item(label=title, path=url)
            item.setProperty('IsPlayable', 'true')

            infolabels={'title': title, 'plot': plot}

            info_tag = ListItemInfoTag(item, 'video')
            imdb = self.imdb
            tmdb = self.tmdb
            c.log(f"[CM Debug @ 182 in trailer.py] tmdb = {tmdb}")

            info_tag.set_info(infolabels)
            unique_ids = {'imdb': imdb, 'tmdb': str(tmdb)}
            info_tag.set_unique_ids(unique_ids)

            item.setArt({'icon': poster, 'thumb': fanart, 'poster': poster, 'fanart': fanart})
            #item.setInfo()

            control.resolve(handle=int(sys.argv[1]), succeeded=True, listitem=item)

            if self.windowedtrailer == 1:
                control.sleep(1000)
                while control.player.isPlayingVideo():
                    control.sleep(1000)
                control.execute(f'Dialog.Close({control.getCurrentDialogId}, true)')


        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 199 in trailer.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 200 in trailer.py]Exception raised. Error = {e}')



    def get_sources(self, mode):
        """
        Retrieves trailer sources from IMDB or TMDb.

        Args:
            mode (str): The source to retrieve the trailer from. Options are 'imdb' and 'tmdb'.

        Returns:
            dict: A dictionary containing the trailer url and other metadata.
        """
        try:
            if mode == 'imdb':
                #result = cache.get(client.request, 0, self.imdb_baselink.format(self.imdb))
                result = cache.get(client.request, 0, self.imdb_baselink.format(self.imdb))
                c.log(f"[CM Debug @ 165 in trailer.py] result={result}")
                if not result:
                    return
                items = utils.json_loads_as_str(result)

                # Safely access 'playlists' and the imdb entry to avoid indexing non-mappings
                playlists = items.get('playlists') if isinstance(items, dict) else None
                if not isinstance(playlists, dict):
                    c.log(f"[CM Debug @ 165 in trailer.py] Invalid or missing 'playlists' in response: {repr(playlists)}")
                    return

                # Try both direct and stringified imdb keys
                imdb_entry = playlists.get(self.imdb) or playlists.get(str(self.imdb))
                if not isinstance(imdb_entry, dict):
                    c.log(f"[CM Debug @ 165 in trailer.py] Missing playlist for imdb id {self.imdb}")
                    return

                # Some payloads may use 'listItems' or 'items'
                list_items = imdb_entry.get('listItems') or imdb_entry.get('items') or []
                video_metadata = items.get('videoMetadata', {})
                trailer_list = []

                for item in list_items:
                    try:
                        # Safely retrieve metadata and ensure it's a mapping before using string keys
                        if isinstance(video_metadata, dict):
                            metadata = video_metadata.get(item.get('videoId')) if isinstance(item, dict) else None
                        else:
                            metadata = None
                        c.log(f"[CM Debug @ 193 in trailer.py] metadata = {repr(metadata)}")
                        if not isinstance(metadata, dict):
                            continue

                        title = metadata.get('title', '')
                        # smallSlate may be missing or not a dict, guard accordingly
                        small_slate = metadata.get('smallSlate') or {}
                        icon = ''
                        if isinstance(small_slate, dict):
                            icon = small_slate.get('url2x') or small_slate.get('url') or ''

                        #canoniculUrl = metadata.get('canonicalUrl')
                        plot = item.get('description') or title if isinstance(item, dict) else title
                        related_to = metadata.get('primaryConst') or self.imdb

                        #if (not related_to == self.imdb) and (not self.name.lower() in ' '.join((title, plot)).lower()):
                        if (
                            related_to != self.imdb
                            and self.name.lower()
                            not in ' '.join((title, plot)).lower()
                        ):
                            continue

                        # Build trailer_url safely from encodings (ensure enc is a dict before using string keys)
                        trailer_url = []
                        for enc in metadata.get('encodings', []) or []:
                            try:
                                if isinstance(enc, dict) and enc.get('definition') in ['1080', '720', '480p', '360p', 'SD']:
                                    video = enc.get('videoUrl') or enc.get('videoURL') or enc.get('video') or ''
                                    if video:
                                        trailer_url.append(video)
                            except Exception:
                                # skip malformed encoding entries
                                continue

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
                if self.mediatype in ['tvshow','episode']:
                    self.mediatype = 'tv'
                url = self.tmdb_url % (self.mediatype, self.tmdb)
                result = self.session.get(url, timeout=15).json()

                list_items = result['results']
                trailer_list = []

                for item in list_items:
                    try:
                        title = item['name']
                        if item['site'].lower() == 'youtube':
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
                return self.select_item(trailer_list, mode)
                        # return self.select_item(trailer_list, mode)
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 324 in trailer.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 324 in trailer.py]Exception raised. Error = {e}')

        except Exception as e:
            c.log(f"[CM Debug @ 305 in trailer.py] exception: {e}")




    def select_item(self, trailer_list, mode):
        trailers = []
        for t in trailer_list:
            li = control.item(label=t['title'])
            # li.setProperty('IsPlayable', 'true')
            li.setArt({'icon': t['icon'], 'thumb': t['icon'], 'poster': self.poster})
            trailers.append(li)
            # trailers.sort(reverse=True)

        if len(trailers) == 1:
            return trailer_list[0]

        if not trailers:
            return 'empty'

        select = control.selectDialog(trailers, control.lang(90220) % str(mode), useDetails=True)

        return 'canceled' if select < 0 else trailer_list[select]
