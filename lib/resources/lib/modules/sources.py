# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 * @file sources.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023-2026, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''


import contextlib
import json
import datetime
import random
import re
import sys
import time
import traceback
import base64
import concurrent.futures as futures
from urllib.parse import quote_plus, parse_qsl
from functools import reduce

from . import trakt
from . import control
from . import cleantitle
from . import debrid
from . import keys
from . import workers
from . import source_utils
from . import log_utils
from . import crew_errors

from . import playcount
from .listitem import ListItemInfoTag
from .player import player
from .crewruntime import c


if c.is_orion_installed():
    from orion import *
    from .orion_api import oa
    ORION_INSTALLED = True
else:
    ORION_INSTALLED = False





import sqlite3 as database
import resolveurl
import xbmc

#import six
#from six.moves import reduce #zip,

class Sources:
    def __init__(self):
        self.getConstants()
        self.sources = []
        self.url = ''
        self.dev_mode = False
        if(control.setting('dev_pw') == c.ensure_text(base64.b64decode(b'dGhlY3Jldw=='))):
            self.dev_mode = True
        c.log(f"[CM Debug @ 70 in sources.py] devmode is {self.dev_mode}")
        if ORION_INSTALLED:
            self.Orion = Orion(keys.orion_key)
        else:
            self.Orion = None


    def play(self, title, year, imdb, tmdb, season, episode, tvshowtitle, premiered, meta, select='1'):
        """
        Play a video based on the provided metadata.

        :param title: The title of the video
        :param year: The release year of the video
        :param imdb_id: The IMDb ID of the video
        :param tmdb_id: The TMDb ID of the video
        :param season: The season number of the video (if applicable)
        :param episode: The episode number of the video (if applicable)
        :param tvshowtitle: The title of the TV show (if applicable)
        :param premiered: The premiere date of the video (if applicable)
        :param meta: A JSON string containing metadata about the video
        :param select: A string indicating whether to select sources automatically (1) or show a dialog (0)
        """
        try:
            url = None

            metadata = json.loads(meta) if meta else {}
            media_type = metadata.get('mediatype') or ''

            if media_type != 'movie' and tvshowtitle:
                title = tvshowtitle or title

            returned_sources = self.getSources(title, year, imdb, tmdb, season, episode, tvshowtitle, premiered)
            select = select or c.get_setting('hosts.mode')
            c.log(f"[CM Debug @ 1191 in sources.py] select = {select} and is of type {type(select)}")

            if returned_sources:
                if select == '1' and 'plugin' in control.infoLabel('Container.PluginName'):
                    control.window.clearProperty(self.itemProperty)
                    control.window.setProperty(self.itemProperty, json.dumps(returned_sources))

                    control.window.clearProperty(self.metaProperty)
                    control.window.setProperty(self.metaProperty, meta)

                    control.sleep(200)
                    base_url = sys.argv[0]
                    title_param = quote_plus(title)
                    control.execute(f"Container.Update({base_url}?action=addItem&title={title_param})")

                if select == '0' or select == '1':
                    url = self.sourcesDialog(returned_sources)
                else:
                    url = self.sourcesDirect(returned_sources)

            if not url or url == 'close://':
                self.url = url
                return self.errorForSources()

            player().run(title, year, season, episode, imdb, tmdb, url, metadata)
        except Exception:
            pass







    def addItem(self, title):

        addon_poster, addon_banner = c.addon_poster(), c.addon_banner()
        addon_fanart = c.addon_fanart()
        setting_fanart = control.setting('fanart')
        addon_clearlogo, addon_clearart = c.addon_clearlogo(), c.addon_clearart()
        addon_thumb, addon_discart = c.addon_thumb(), c.addon_discart()

        indicators = playcount.get_movie_indicators(refresh=True)

        c.log(f"[CM Debug @ 124 in sources.py] inside addItem function, addon_poster = {addon_poster}")

        control.playlist.clear()

        items = control.window.getProperty(self.itemProperty)
        items = json.loads(items)

        if items is None or len(items) == 0:
            control.idle()
            sys.exit()

        meta = control.window.getProperty(self.metaProperty)
        meta = json.loads(meta)
        poster = meta['poster']
        c.log(f"[CM Debug @ 140 in sources.py] poster = {poster}")
        #c.log(f"[CM Debug @ 139 in sources.py] meta = {meta}")
        #meta = sourcesDirMeta(meta)

        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])

        downloads = (
            control.setting('downloads') == 'true'
            and control.setting('movie.download.path') != ''
            and control.setting('tv.download.path') != ''
        )

        systitle = sysname = quote_plus(title)

        if 'tvshowtitle' in meta and 'season' in meta and 'episode' in meta:
            sysname += quote_plus(' S%02dE%02d' % (int(meta['season']), int(meta['episode'])))
        elif 'year' in meta:
            sysname += quote_plus(f" ({meta['year']})")

        poster = meta['poster'] if 'poster' in meta else addon_poster
        fanart = meta.get('fanart2') if 'fanart2' in meta else addon_fanart
        thumb = meta['thumb'] if 'thumb' in meta else addon_thumb
        banner = meta['banner'] if 'banner' in meta else addon_banner
        clearlogo = meta['clearlogo'] if 'clearlogo' in meta else addon_clearlogo
        clearart = meta['clearart'] if 'clearart' in meta else addon_clearart
        discart = meta['discart'] if 'discart' in meta else addon_discart

        if not setting_fanart == 'true':
            fanart = addon_fanart
            poster = addon_poster
            banner = addon_banner
            thumb = addon_thumb
            clearlogo = addon_clearlogo
            clearart = addon_clearart
            discart = addon_discart

        #meta = control.tagdataClean(meta)
        sysimage = quote_plus(str(poster))
        download_menu = control.lang(32403)

        for item in items:
            try:
                label = str(item['label'])
                if control.setting('sourcelist.multiline') == 'true':
                    label = str(item['multiline_label'])

                syssource = quote_plus(json.dumps([item]))

                sysurl = f'{sysaddon}?action=playItem&title={systitle}&source={syssource}'

                cm = []

                if downloads:
                    cm.append((download_menu, f'RunPlugin({sysaddon}?action=download&name={sysname}&image={sysimage}&source={syssource})'))

                cm.append(('CM Test', f'RunPlugin({sysaddon}?action=classytest&title={systitle}&source={syssource})'))
                item_list = control.item(label=label)


                meta['studio'] = c.string_split_to_list(meta['studio']) if 'studio' in meta else []
                meta['genre'] = c.string_split_to_list(meta['genre']) if 'genre' in meta else []
                meta['director'] = c.string_split_to_list(meta['director']) if 'director' in meta else []
                meta['writer'] = c.string_split_to_list(meta['writer']) if 'writer' in meta else []

                info_tag = ListItemInfoTag(item_list, 'video')
                infolabels = control.tagdataClean(meta)
                info_tag.set_info(infolabels)

                item_list.setArt({
                    'icon': poster, 'thumb': thumb, 'poster': poster, 'banner': banner,
                    'fanart': fanart, 'landscape': fanart, 'clearlogo': clearlogo,
                    'clearart': clearart, 'discart': discart
                    })

                video_streaminfo = {'codec': 'h264'}
                info_tag.add_stream_info('video', video_streaminfo)

                item_list.addContextMenuItems(cm)
                #item_list.setInfo(type='Video', infoLabels=meta)

                control.addItem(handle=syshandle, url=sysurl, listitem=item_list, isFolder=False)
            except Exception as e:
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 233 in sources.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 233 in sources.py]Exception raised. Error = {e}')
                pass
            #except Exception as e:
                #c.log(f"[CM Debug @ 234 in sources.py] Exception raised. Error = {e}")
                #pass

        control.content(syshandle, 'files')
        control.directory(syshandle, cacheToDisc=True)

    #TC 2/01/19 started
    def playItem(self, title, source):
        try:
            meta = control.window.getProperty(self.metaProperty)
            meta = json.loads(meta)

            year = meta['year'] if 'year' in meta else None
            season = meta['season'] if 'season' in meta else None
            episode = meta['episode'] if 'episode' in meta else None

            imdb = meta['imdb'] if 'imdb' in meta else None
            tvdb = meta['tvdb'] if 'tvdb' in meta else None
            tmdb = meta['tmdb'] if 'tmdb' in meta else None

            _next = []
            prev = []
            total = []

            for i in range(1, 1000):
                try:
                    u = control.infoLabel(f'ListItem({i}).FolderPath')
                    if u in total:
                        raise Exception()
                    total.append(u)
                    u = dict(parse_qsl(u.replace('?', '')))
                    u = json.loads(u['source'])[0]
                    _next.append(u)
                    #c.log(f"[CM Debug @ 257 in sources.py] u  = {u} and _next = {_next}")
                except Exception:
                    break
            for i in range(-1000,0)[::-1]:
                try:
                    u = control.infoLabel(f'ListItem({i}).FolderPath')
                    if u in total:
                        raise Exception()
                    total.append(u)
                    u = dict(parse_qsl(u.replace('?', '')))
                    u = json.loads(u['source'])[0]
                    prev.append(u)
                except Exception:
                    break

            items = json.loads(source)
            items = [i for i in items+_next+prev][:40]

            header = control.addonInfo('name')
            header2 = header.upper()

            progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
            progressDialog.create(header, '')
            progressDialog.update(0)

            block = None

            for i, item in enumerate(items):
                try:
                    try:
                        if progressDialog.iscanceled():
                            break
                        progressDialog.update(
                            int((100 / float(len(items))) * i),
                            str(items['label'])+'\n'+ str(' ')
                            )
                    except Exception:
                        progressDialog.update(
                            int((100 / float(len(items))) * i),
                            str(header2)+'\n'+ str(item['label'])
                            )

                    if item['source'] == block:
                        raise Exception('block')

                    w = workers.Thread(self.sourcesResolve, item)
                    w.start()

                    offset = 60 * 2 if item.get('source') in self.hostcapDict else 0

                    m = ''

                    for x in range(3600):
                        try:
                            if control.monitor.abortRequested():
                                return sys.exit()
                            if progressDialog.iscanceled():
                                return progressDialog.close()
                        except Exception:
                            pass

                        k = control.condVisibility('Window.IsActive(virtualkeyboard)')
                        if k:
                            m += '1'
                            m = m[-1]
                        if (w.is_alive() is False or x > 30 + offset) and not k:
                            break
                        k = control.condVisibility('Window.IsActive(yesnoDialog)')
                        if k:
                            m += '1'
                            m = m[-1]
                        if (w.is_alive() is False or x > 30 + offset) and not k:
                            break
                        time.sleep(0.5)

                    for x in range(30):
                        try:
                            if control.monitor.abortRequested():
                                return sys.exit()
                            if progressDialog.iscanceled():
                                return progressDialog.close()
                        except Exception:
                            pass

                        if m == '':
                            break
                        if w.is_alive() is False:
                            break
                        time.sleep(0.5)

                    if w.is_alive() is True:
                        block = item['source']

                    if self.url is None:
                        raise Exception()

                    try:
                        progressDialog.close()
                    except Exception:
                        pass

                    control.sleep(200)
                    control.execute('Dialog.Close(virtualkeyboard)')
                    control.execute('Dialog.Close(yesnoDialog)')

                    player().run(title, year, season, episode, imdb, tmdb, self.url, meta)

                    return self.url
                except Exception as e:
                    pass

            try:
                progressDialog.close()
            except Exception:
                pass

            self.errorForSources()
        except Exception:
            pass

    def getSources(self, title, year, imdb, tmdb, season, episode, tvshowtitle, premiered, quality='HD', timeout=30):
        try:
            self.start = time.time()
            #string1 = control.lang(32404)
            #string2 = control.lang(32405)
            string3 = control.lang(32406)
            string4 = control.lang(32601)
            #string5 = control.lang(32602)
            string6 = control.lang(32606)
            string7 = control.lang(32607)

            progressDialog = control.progressDialog if c.get_setting('progress.dialog') == '0' else control.progressDialogBG

            progressDialog.create(control.addonInfo('name'), '')
            progressDialog.update(0)

            self.prepare_sources()
            sourceDict = self.sourceDict
            progressDialog.update(0, control.lang(32600))

            sourceDict, content = self.filter_source_dict(tvshowtitle, sourceDict)
            threads = []
            mainsourceDict, sourcelabelDict = self.get_movie_episode_sources(title, year, imdb, tmdb, season, episode, tvshowtitle, premiered, sourceDict, content, threads)

            timeout = int(control.setting('scrapers.timeout.1')) or 30
            quality = int(control.setting('hosts.quality')) or 0
            debrid_only = control.setting('debrid.only') or 'false'

            line1 = line2 = line3 = ""

            pre_emp =  control.setting('preemptive.termination')
            pre_emp_limit = int(control.setting('preemptive.limit'))

            source_4k = d_source_4k = 0
            source_1080 = d_source_1080 = 0
            source_720 = d_source_720 = 0
            source_sd = d_source_sd = 0

            debrid_list = debrid.debrid_resolvers
            debrid_status = debrid.status()

            total_format = '[COLOR %s][B]%s[/B][/COLOR]'
            pdiag_format = ' 4K: %s | 1080p: %s | 720p: %s | SD: %s | %s: %s'.split('|')

            for i in range(timeout):
                if str(pre_emp) == 'true':
                    quality_sources = {
                        0: source_4k + d_source_4k,
                        1: source_1080 + d_source_1080,
                        2: source_720 + d_source_720,
                        3: source_sd + d_source_sd
                    }
                    if (
                        quality in quality_sources
                        and quality_sources[quality] >= pre_emp_limit
                    ):
                        c.log(f"[CM Debug @ 1530 in sources.py] quality_sources = {quality_sources} | quality = {quality} | pre_emp_limit = {pre_emp_limit}, going to break", 1)
                        break


                if control.monitor.abortRequested():
                    sys.exit()

                if progressDialog.iscanceled():
                    break

                if len(self.sources) > 0:
                    debrid_4k_label, debrid_1080_label, debrid_720_label, debrid_total_label, source_4k_label, source_1080_label, source_720_label, source_sd_label, source_total_label = self.get_labels(debrid_list, debrid_status, total_format)

                    if (i / 2) < timeout:
                        try:
                            alive_threads = [thread for thread in threads if thread.is_alive()]
                            thread_names = [thread.getName() for thread in alive_threads]
                            # waiting_for = [sourcelabelDict[name] for name in thread_names if name in mainsourceDict]
                            info = [sourcelabelDict[name] for name in thread_names]

                            #c.log(f"[CM Debug @ 1474 in sources.py] alive_threads = {alive_threads} | thread_names = {thread_names} | waiting_for = {waiting_for} | info = {info}", 1)


                            if debrid_status:
                                if progressDialog == control.progressDialogBG:
                                    control.idle()

                                if quality == 0:
                                    line1 = '|'.join(pdiag_format) % (debrid_4k_label, debrid_1080_label, debrid_720_label, debrid_720_label, str(string4), debrid_total_label)
                                    line2 = '|'.join(pdiag_format) % (source_4k_label, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                elif quality in [1, 2]:
                                    line1 = '|'.join(pdiag_format[1:]) % (debrid_1080_label, debrid_720_label, debrid_720_label, str(string4), debrid_total_label)
                                    line2 = '|'.join(pdiag_format[1:]) % (source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                elif quality == 3:
                                    line1 = '|'.join(pdiag_format[2:]) % (debrid_720_label, debrid_720_label, str(string4), debrid_total_label)
                                    line2 = '|'.join(pdiag_format[2:]) % (source_720_label, source_sd_label, str(string4), source_total_label)
                                else:
                                    line1 = '|'.join(pdiag_format[3:]) % (debrid_720_label, str(string4), debrid_total_label)
                                    line2 = '|'.join(pdiag_format[3:]) % (source_sd_label, str(string4), source_total_label)
                                if c.devmode:
                                    between = time.time() - self.start
                                    between = f"{between:.2f}"
                                    line4 = f'[COLOR lawngreen]Devmode: {between} seconds[/COLOR]'
                                if len(info) > 6:
                                    line3 = string3 % (str(len(info)))
                                elif len(info) > 0:
                                    line3 = string3 % (', '.join(info))
                                else:
                                    break
                                percent = int(100 * float(i) / timeout)
                                if progressDialog == control.progressDialogBG:
                                    if c.devmode:
                                        progressDialog.update(max(1, percent), line1 + '\n' + line3 + '\n' + line4)
                                    else:
                                        progressDialog.update(max(1, percent), line1 + '\n' + line3)
                                elif c.devmode:
                                    progressDialog.update(max(1, percent), line1 + '\n' + line2 + '\n' + line3 + '\n' + line4)
                                else:
                                    progressDialog.update(max(1, percent), line1 + '\n' + line2 + '\n' + line3)
                            else:

                                if quality == 0:
                                    line1 = '|'.join(pdiag_format) % (source_4k_label, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                elif quality in [1, 2]:
                                    line1 = '|'.join(pdiag_format[1:]) % (source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                elif quality == 3:
                                    line1 = '|'.join(pdiag_format[2:]) % (source_720_label, source_sd_label, str(string4), source_total_label)
                                else:
                                    line1 = '|'.join(pdiag_format[3:]) % (source_sd_label, str(string4), source_total_label)

                                if len(info) > 6:
                                    line2 = string3 % (str(len(info)))
                                elif len(info) > 0:
                                    line2 = string3 % (', '.join(info))
                                else:
                                    break
                                percent = int(100 * float(i) / timeout)

                                progressDialog.update(max(1, percent), line1 + '\n' + line2)
                        except Exception as e:
                            c.log(f'Exception Raised in get_sources 1: {e}', 1)
                    else:
                        try:
                            waiting_sources = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() and x.getName() in mainsourceDict]
                            if (
                                i >= timeout
                                or not waiting_sources
                                or len(self.sources) >= 100 * len(info)
                            ):
                                break

                            line3 = f"{control.lang(32602)}: " + (', '.join(waiting_sources))
                            percent = int(100 * float(i) / (2 * timeout) + 0.5)
                            if progressDialog != control.progressDialogBG:
                                progressDialog.update(max(1, percent), line1 + '\n' + line2 + '\n' + line3)
                            else:
                                progressDialog.update(max(1, percent), line1 + '\n' + line3)
                        except Exception as e:
                            c.log(f'Exception Raised in get_sources 2: {e}', 1)

                time.sleep(0.1)

            try:
                progressDialog.close()
            except Exception as e:
                c.log(f"[CM Debug @ 1355 in sources.py] exception raised. Error = {e}")


            self.sourcesFilter()

            return self.sources

        except Exception as e:
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1362 in sources.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1362 in sources.py]Exception raised. Error = {e}')
            pass

    def get_labels(self, debrid_list, debrid_status, total_format):
        try:
            source_4k, source_1080, source_720, source_sd, total = self._get_source_counts()
            debrid_source_4k = debrid_source_1080 = debrid_source_720 = debrid_source_sd = debrid_total = 0
            if debrid_status:
                debrid_source_4k, debrid_source_1080, debrid_source_720, debrid_source_sd, debrid_total = self._get_debrid_source_counts(debrid_list)
            debrid_4k_label, debrid_1080_label, debrid_720_label, debrid_total_label = self._get_debrid_labels(
                debrid_source_4k, debrid_source_1080, debrid_source_720, debrid_source_sd, debrid_total, total_format
            )
            source_4k_label, source_1080_label, source_720_label, source_sd_label, source_total_label = self._get_source_labels(
                source_4k, source_1080, source_720, source_sd, total, total_format
            )
        except Exception as e:
            c.log(f"[CM Debug @ 1573 in sources.py] exception raised. Error = {e}")

        return (
            debrid_4k_label,
            debrid_1080_label,
            debrid_720_label,
            debrid_total_label,
            source_4k_label,
            source_1080_label,
            source_720_label,
            source_sd_label,
            source_total_label,
        )

    def _get_source_counts(self):
        sources_by_quality = {
            '4K': len([e for e in self.sources if e['quality'] == '4K' and not e['debridonly']]),
            '1080p': len([e for e in self.sources if e['quality'] in '1080p' and not e['debridonly']]),
            '720p': len([e for e in self.sources if e['quality'] in ['720p', 'HD'] and not e['debridonly']]),
            'SD': len([e for e in self.sources if e['quality'] == 'SD' and not e['debridonly']]),
        }
        source_4k = sources_by_quality.get('4K', 0)
        source_1080 = sources_by_quality.get('1080p', 0)
        source_720 = sources_by_quality.get('720p', 0)
        source_sd = sources_by_quality.get('SD', 0)
        total = source_4k + source_1080 + source_720 + source_sd
        return source_4k, source_1080, source_720, source_sd, total

    def _get_debrid_source_counts(self, debrid_list):
        debrid_source_counts = {
            '4K': len([s for s in self.sources if s['quality'] in ['4K', '4k'] and any(d.valid_url(s['url'], s['source']) for d in debrid_list)]),
            '1080p': len([s for s in self.sources if s['quality'] in ['1440p', '1080p'] and any(d.valid_url(s['url'], s['source']) for d in debrid_list)]),
            '720p': len([s for s in self.sources if s['quality'] in ['720p', 'HD'] and any(d.valid_url(s['url'], s['source']) for d in debrid_list)]),
            'SD': len([s for s in self.sources if s['quality'] == 'SD' and any(d.valid_url(s['url'], s['source']) for d in debrid_list)]),
        }
        debrid_source_4k = debrid_source_counts.get('4K', 0)
        debrid_source_1080 = debrid_source_counts.get('1080p', 0)
        debrid_source_720 = debrid_source_counts.get('720p', 0)
        debrid_source_sd = debrid_source_counts.get('SD', 0)
        debrid_total = debrid_source_4k + debrid_source_1080 + debrid_source_720 + debrid_source_sd
        return debrid_source_4k, debrid_source_1080, debrid_source_720, debrid_source_sd, debrid_total

    def _get_debrid_labels(self, debrid_source_4k, debrid_source_1080, debrid_source_720, debrid_source_sd, debrid_total, total_format):
        debrid_4k_label = total_format % ('red', debrid_source_4k) if debrid_source_4k == 0 else total_format % ('lime', debrid_source_4k)
        debrid_1080_label = total_format % ('red', debrid_source_1080) if debrid_source_1080 == 0 else total_format % ('lime', debrid_source_1080)
        debrid_720_label = total_format % ('red', debrid_source_720) if debrid_source_720 == 0 else total_format % ('lime', debrid_source_720)
        source_sd_label = total_format % ('red', debrid_source_sd) if debrid_source_sd == 0 else total_format % ('lime', debrid_source_sd)
        debrid_total_label = total_format % ('red', debrid_total) if debrid_total == 0 else total_format % ('lime', debrid_total)
        return debrid_4k_label, debrid_1080_label, debrid_720_label, debrid_total_label

    def _get_source_labels(self, source_4k, source_1080, source_720, source_sd, total, total_format):
        source_4k_label = total_format % ('red', source_4k) if source_4k == 0 else total_format % ('lime', source_4k)
        source_1080_label = total_format % ('red', source_1080) if source_1080 == 0 else total_format % ('lime', source_1080)
        source_720_label = total_format % ('red', source_720) if source_720 == 0 else total_format % ('lime', source_720)
        source_sd_label = total_format % ('red', source_sd) if source_sd == 0 else total_format % ('lime', source_sd)
        source_total_label = total_format % ('red', total) if total == 0 else total_format % ('lime', total)
        return source_4k_label, source_1080_label, source_720_label, source_sd_label, source_total_label



    def filter_source_dict(self, tvshowtitle, source_dict):
        # sourcery skip: assign-if-exp, extract-method, use-fstring-for-concatenation
        """
        Filter and sort the source dictionary based on content type, availability, language, settings, and priority.
        Returns the filtered source_dict and content type.
        """
        try:
            # Determine content type
            content = 'movie' if tvshowtitle is None else 'episode'

            # Step 1: Filter sources based on content availability (movie or tvshow attribute)
            if content == 'movie':
                filtered_sources = [(name, obj, getattr(obj, 'movie', None)) for name, obj in source_dict]
            else:
                filtered_sources = [(name, obj, getattr(obj, 'tvshow', None)) for name, obj in source_dict]

            # Remove sources where the content attribute is None
            filtered_sources = [(name, obj) for name, obj, attr in filtered_sources if attr is not None]

            # Step 2: Filter by language support
            language = self.getLanguage()
            filtered_sources = [(name, obj, obj.language) for name, obj in filtered_sources]
            filtered_sources = [(name, obj) for name, obj, lang in filtered_sources if any(supported_lang in lang for supported_lang in language)]

            # Step 3: Filter by provider settings (enable/disable individual providers)
            try:
                filtered_sources = [(name, obj, control.setting('provider.' + name)) for name, obj in filtered_sources]
            except Exception:
                # Default to 'true' if setting retrieval fails
                filtered_sources = [(name, obj, 'true') for name, obj in filtered_sources]
            filtered_sources = [(name, obj) for name, obj, enabled in filtered_sources if enabled != 'false']

            # Step 4: Add priority and sort
            filtered_sources = [(name, obj, obj.priority) for name, obj in filtered_sources]
            filtered_sources = sorted(filtered_sources, key=lambda item: item[2])  # Sort by priority (ascending)

            return filtered_sources, content
        except Exception as e:
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 667 in sources.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 667 in sources.py]Exception raised. Error = {e}')






    def get_movie_episode_sources(self, title, year, imdb, tmdb, season, episode, tvshowtitle, premiered, source_dict, content, threads):
        try:
            if content == 'movie':
                title = self.getTitle(title)
                localtitle = self.getLocalTitle(title, imdb, tmdb, content)
                aliases = self.getAliasTitles(imdb, localtitle, content)

                if not c.orion_disabled:
                    threads.append(workers.Thread(self.getOrionMovieSource, title, localtitle, aliases, year, imdb, tmdb))

                for i in source_dict:
                    threads.append(workers.Thread(self.get_movie_source, title, localtitle, aliases, year, imdb, i[0], i[1]))
            elif content == 'episode':
                tvshowtitle = self.getTitle(tvshowtitle)
                localtvshowtitle = self.getLocalTitle(tvshowtitle, imdb, tmdb, content)
                aliases = self.getAliasTitles(imdb, localtvshowtitle, content)

                if not c.orion_disabled and c.is_orion_installed():
                    threads.append(workers.Thread(self.get_orion_tvshow_source(title, tvshowtitle, aliases, year, imdb, tmdb, season, episode)))

                for i in source_dict:
                    threads.append(workers.Thread(self.getEpisodeSource, title, year, imdb, tmdb, season, episode, tvshowtitle, localtvshowtitle, aliases, premiered, i[0], i[1]))

            # Combine sourceDict (source_name, source_obj, priority) with threads into a list of tuples
            combined_sources = [(source_name, source_obj, priority, thread) for (source_name, source_obj, priority), thread in zip(source_dict, threads)]

            # Extract thread names, source names, and priorities for easier processing
            thread_info = [(thread.getName(), source_name, priority) for source_name, source_obj, priority, thread in combined_sources]

            # Get main source dict: thread names where priority is 0
            mainsource_dict = [thread_name for thread_name, source_name, priority in thread_info if priority == 0]

            # Get source label dict: {thread_name: source_name.upper()}
            sourcelabel_dict = {thread_name: source_name.upper() for thread_name, source_name, priority in thread_info}

            for i in threads:
                i.start()

            return mainsource_dict, sourcelabel_dict
        except Exception as e:
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1740 in sources.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1740 in sources.py]Exception raised. Error = {e}')


    #checked OH - 26-04-2021
    def prepare_sources(self):
        try:
            control.makeFile(control.dataPath)
            dbcon = database.connect(control.providercacheFile)
            dbcur = dbcon.cursor()
            sql_create_rel_url = """
                CREATE TABLE IF NOT EXISTS rel_url (
                    source TEXT,
                    imdb_id TEXT,
                    season TEXT,
                    episode TEXT,
                    rel_url TEXT,
                    UNIQUE(source, imdb_id, season, episode)
                    );
                """
            sql_create_rel_src = """
                CREATE TABLE IF NOT EXISTS rel_src (
                    source TEXT,
                    imdb_id TEXT,
                    season TEXT,
                    episode TEXT,
                    hosts TEXT,
                    added TEXT,
                    UNIQUE(source, imdb_id, season, episode)
                    );
                """
            dbcur.execute(sql_create_rel_url)
            dbcur.execute(sql_create_rel_src)
            dbcon.commit()

            dbcur.close()
            dbcon.close()
            #dbcur.execute("CREATE TABLE IF NOT EXISTS rel_url (""source TEXT, ""imdb_id TEXT, ""season TEXT, ""episode TEXT, ""rel_url TEXT, UNIQUE(source, imdb_id, season, episode));")
            #dbcur.execute("CREATE TABLE IF NOT EXISTS rel_src (""source TEXT, ""imdb_id TEXT, ""season TEXT, ""episode TEXT, ""hosts TEXT, ""added TEXT, UNIQUE(source, imdb_id, season, episode));")

        except Exception as e:
            c.log(f"[CM Debug @ 1413 in sources.py] Exception raised: {e}", 1)


    def get_movie_source(self, title, localtitle, aliases, year, imdb, source, call):
        try:
            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
        except Exception:
            pass



        #Fix to stop items passed with a 0 IMDB id pulling old unrelated sources from the database.
        # cm - changed 2025-03-12
        if imdb == '0':
            try:
                dbcur.execute(f"DELETE FROM rel_src WHERE source = '{source}' AND imdb_id = '{imdb}'")
                dbcur.execute(f"DELETE FROM rel_url WHERE source = '{source}' AND imdb_id = '{imdb}'")
                dbcon.commit()
            except Exception:
                pass
        #END

        try:
            sources = []
            dbcur.execute(f"SELECT * FROM rel_src WHERE source = '{source}' AND imdb_id = '{imdb}' AND season = '' AND episode = ''")
            match = dbcur.fetchone()
            t1 = int(re.sub('[^0-9]', '', str(match[5])))
            t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            update = abs(t2 - t1) > 3600
            if update is False:
                sources = json.loads(c.ensure_str(match[4]))
                c.log(f"[CM Debug @ 1445 in sources.py] sources = {repr(sources)}")
                return self.sources.extend(sources)
        except Exception:
            pass

        try:
            url = None
            dbcur.execute(f"SELECT * FROM rel_url WHERE source = '{source}' AND imdb_id = '{imdb}' AND season = '' AND episode = ''")
            url = dbcur.fetchone()
            url = json.loads(c.ensure_str(url[4]))
        except Exception:
            pass

        try:
            if url is None:
                url = call.movie(imdb, title, localtitle, aliases, year)
                # c.log(f"[CM Debug @ 873 in sources.py] call.movie() url = {url} with call = {call}")
            if url is None:
                raise Exception()
            dbcur.execute(f"DELETE FROM rel_url WHERE source = '{source}' AND imdb_id = '{imdb}' AND season = '' AND episode = ''")
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, '', '', repr(url)))
            dbcon.commit()
        except Exception:
            pass



        try:
            sources = []
            # c.log(f"[CM Debug @ 885 in sources.py] call = {call}")
            sources = call.sources(url, self.hostDict, self.hostprDict)

            if sources is None or sources == []:
                raise crew_errors.NoResultsError()

            sources = [
                json.loads(t)
                for t in {json.dumps(d, sort_keys=True) for d in sources}
            ]

            for i in sources:
                i.update({'provider': source})
            self.sources.extend(sources)

            dbcur.execute(f"DELETE FROM rel_src WHERE source = '{source}' AND imdb_id = '{imdb}' AND season = '' AND episode = ''")
            dbcur.execute("INSERT INTO rel_src Values (?, ?, ?, ?, ?, ?)", (source, imdb, '', '', repr(sources), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))

            dbcon.commit()
            dbcon.close()

        except ValueError as e:
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 911 in sources.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 912 in sources.py]ValueError raised. Error = {e}')
        except crew_errors.NoResultsError:
            c.log(f'[CM Debug @ 914 in sources.py]NoResultsError raised, source = {source}')
        except Exception as e:
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 918 in sources.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 919 in sources.py]Exception raised. Error = {e}')



    # !Orion, self.oa = OrionApi
    # TODO: check  for validity of user
    # TODO: check limit in get_movie. get_movie returns, without limit alle results for a movie.
    # TODO: so a user with a "free" or even a "modest" premium account would have his daily limit reached with
    # TODO: this (or 1) call.
    def getOrionMovieSource(self, title, localtitle, aliases, year, imdb, tmdb):

        dbcon = database.connect(self.sourceFile)
        dbcur = dbcon.cursor()

        try:
            dbcur.execute(f"SELECT * FROM rel_url WHERE source = 'Orion' AND imdb_id = '{imdb}'")
            row = dbcur.fetchone()
            hosts = json.loads(c.ensure_str(row[4]))
            t1 = int(re.sub('[^0-9]', '', str(row[5])))
            t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            update = abs(t2 - t1) > 3600
            if update is False:
                return self.sources.extend(hosts)
        except Exception:
            pass

        #we have no cached orion data of this movie
        try:
            if update or hosts is None:
                sources = []
                data = oa.get_movie(imdb, limit=250)
                sources = oa.do_orion_scrape(data, 'movie')
                if sources:
                    dbcur.execute(f"DELETE FROM rel_url WHERE source = 'Orion' AND imdb_id = '{imdb}'")
                    dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", ('Orion', imdb, '', '', repr(sources)))
                    dbcon.commit()
                    self.sources.extend(sources)
                    return sources
                return []
        except Exception as e:
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1546 in sources.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1547 in sources.py]Exception raised. Error = {e}')
            pass

    # !Orion, self.oa = OrionApi
    # TODO: check  for validity of user
    # TODO: check limit in get_movie. get_movie returns, without limit alle results for a movie.
    # TODO: so a user with a "free" or even a "modest" premium account would have his daily limit reached with
    # TODO: this (or 1) call.
    def get_orion_tvshow_source(self, title, localtitle, aliases, year, imdb, tmdb, season, episode):

        dbcon = database.connect(self.sourceFile)
        dbcur = dbcon.cursor()

        update = False
        hosts = None


        try:
            dbcur.execute(f"SELECT * FROM rel_url WHERE source = 'Orion' AND imdb_id = '{imdb}' AND season = '{season}' AND episode = '{episode}'")
            row = dbcur.fetchone()
            if not row:
                update = True
                raise Exception()
            hosts = json.loads(c.ensure_str(row[4]))
            t1 = int(re.sub('[^0-9]', '', str(row[5])))
            t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            update = abs(t2 - t1) > 3600
            if not update:
                return self.sources.extend(hosts)
        except Exception as e:
            self._extracted_from_get_orion_tvshow_source_23(
                traceback,
                '[CM Debug @ 1582 in sources.py]Traceback:: ',
                '[CM Debug @ 1583 in sources.py]Exception raised. Error = ',
                e,
            )

        #we have no cached orion data of this movie
        try:
            if update or hosts is None:
                sources = []
                data = oa.get_movie(imdb, limit=250)
                sources = oa.do_orion_scrape(data, 'episode')


                if sources:
                    c.log(f"[CM Debug @ 1596 in sources.py]sources = {repr(sources)}")
                    sql_delete = f"DELETE FROM rel_url WHERE source = 'Orion' AND imdb_id = '{imdb}' AND season = '{season}' AND episode = '{episode}'"
                    c.log(f"[CM Debug @ 1601 in sources.py] sql = {sql_delete}")
                    dbcur.execute(sql_delete)
                    dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", ('Orion', imdb, season, episode, repr(sources)))
                    dbcon.commit()
                return self.sources.extend(sources) if sources else []
        except Exception as e:
            self._extracted_from_get_orion_tvshow_source_23(
                traceback,
                '[CM Debug @ 1587 in sources.py]Traceback:: ',
                '[CM Debug @ 1588 in sources.py]Exception raised. Error = ',
                e,
            )

    # TODO Rename this here and in `get_orion_tvshow_source`
    def _extracted_from_get_orion_tvshow_source_23(self, traceback, arg1, arg2, e):
        failure = traceback.format_exc()
        c.log(f'{arg1}{failure}')
        c.log(f'{arg2}{e}')






    def getEpisodeSource(self, title, year, imdb, tmdb, season, episode, tvshowtitle, localtvshowtitle, aliases, premiered, source, call):
        try:
            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
        except Exception:
            pass

        try:
            sources = []
            dbcur.execute(f"SELECT * FROM rel_src WHERE source = '{source}' AND imdb_id = '{imdb}' AND season = '{season}' AND episode = '{episode}'")

            match = dbcur.fetchone()
            t1 = int(re.sub('[^0-9]', '', str(match[5])))
            t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            update = abs(t2 - t1) > 3600
            if not update:
                sources = json.loads(c.ensure_str(match[4]))
                return self.sources.extend(sources)
        except Exception:
            pass

        try:
            url = None
            query = f"SELECT * FROM rel_url WHERE source = '{source}' AND imdb_id = '{imdb}' AND season = '' AND episode = ''"
            dbcur.execute(query)
            url = dbcur.fetchone()
            url = json.loads(c.ensure_str(url[4]))
        except Exception:
            pass

        try:
            if url is None:
                url = call.tvshow(imdb, tmdb, tvshowtitle, localtvshowtitle, aliases, year)
            if url is None:
                raise Exception()
            dbcur.execute(
                f"DELETE FROM rel_url WHERE source = '{source}' AND imdb_id = '{imdb}' AND season = '' AND episode = ''")
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, '', '', repr(url)))
            dbcon.commit()
        except Exception:
            pass

        try:
            ep_url = None
            query = f"SELECT * FROM rel_url WHERE source = '{source}' AND imdb_id = '{imdb}' AND season = '{season}' AND episode = '{episode}'"
            dbcur.execute(query)
            ep_url = dbcur.fetchone()
            ep_url = json.loads(c.ensure_str(ep_url[4]))
        except Exception:
            pass

        try:
            if url is None:
                raise Exception()
            if ep_url is None:
                ep_url = call.episode(url, imdb, tmdb, title, premiered, season, episode)
            if ep_url is None:
                raise Exception()
            dbcur.execute(f"DELETE FROM rel_url WHERE source = '{source}' AND imdb_id = '{imdb}' AND season = '{season}' AND episode = '{episode}'")
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, season, episode, repr(ep_url)))
            dbcon.commit()
        except Exception:
            pass

        if c.is_orion_installed() and source == 'Orion':
            oa = OrionApi()
            try:
                # !Orion, self.oa = OrionApi
                # TODO: check  for validity of user
                # TODO: check limit in get_movie. get_movie returns, without limit alle results for a movie.
                # TODO: so a user with a "free" or even a "modest" premium account would have his daily limit reached with
                # TODO: this (or 1) call.
                sources = []
                data = oa.get_episode(imdb, tmdb, title, season, episode, limit=25)
                if sources := oa.do_orion_scrape(data, 'movie'):
                    self.sources.extend(sources)
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 1472 in sources.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 1473 in sources.py]Exception raised. Error = {e}')




        try:
            sources = []
            sources = call.sources(ep_url, self.hostDict, self.hostprDict)
            if sources is None or sources == []:
                raise Exception()
            sources = [json.loads(t) for t in set(json.dumps(d, sort_keys=True) for d in sources)]
            for i in sources: i.update({'provider': source})
            self.sources.extend(sources)
            dbcur.execute(f"DELETE FROM rel_src WHERE source = '{source}' AND imdb_id = '{imdb}' AND season = '{season}' AND episode = '{episode}'")
            dbcur.execute("INSERT INTO rel_src Values (?, ?, ?, ?, ?, ?)", (source, imdb, season, episode, repr(sources), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
            dbcon.commit()
        except Exception:
            pass

    def alter_sources(self, url, meta):
        with contextlib.suppress(Exception):
            url += '&select=1' if control.setting('hosts.mode') == '2' else '&select=2'
            c.log(f"[CM Debug @ 1131 in sources.py] Altered URL: {url}")
            control.execute(f'RunPlugin({url})')

    #cm - fixed
    def clearSources(self):
        try:
            control.idle()

            yes = control.yesnoDialog(control.lang(32076))
            if not yes:
                return

            control.makeFile(control.dataPath)
            dbcon = database.connect(control.providercacheFile)
            dbcur = dbcon.cursor()
            dbcur.execute("DROP TABLE IF EXISTS rel_src")
            dbcur.execute("DROP TABLE IF EXISTS rel_url")
            dbcur.execute("VACUUM")
            dbcon.commit()

            control.infoDialog(control.lang(32077), sound=True, icon='INFO')
        except Exception:
            pass

    def unique_sources(self, sources):
        """Yield unique sources from a list of sources based on URL.

        This function takes a list of sources and checks if the URL is unique.
        If the URL is unique, it yields the source. If the URL is not unique, it
        ignores the source.

        Args:
            sources (list): A list of sources.

        Yields:
            dict: A unique source.
        """
        unique_urls = set()
        for source in sources:
            url = source.get('url')
            if isinstance(url, str):
                if url.startswith('magnet:'):
                    url = url[:60]
                if url not in unique_urls:
                    unique_urls.add(url)
                    yield source  # Yield the unique source.

    def sourcesProcessTorrents2(self, torrent_sources):
        """Process torrent sources by checking for cached hashes.

        This function takes a list of torrent sources and checks if the torrent
        info hashes are cached in the local database. If so, it marks the source
        as a cached torrent, otherwise it marks it as an uncached torrent.

        Args:
            torrent_sources (list): A list of torrent sources.

        Returns:
            list: A list of processed torrent sources.
        """
        if not torrent_sources:
            return []

        debrid_services = ['Real-Debrid', 'AllDebrid', 'Premiumize.me', 'Torbox']
        valid_sources = [source for source in torrent_sources if source.get('debrid', '') in debrid_services]

        if not valid_sources:
            return torrent_sources

        try:
            from resources.lib.modules import debridcheck
            DBCheck = debridcheck.DebridCheck()

            # Get the list of info hashes from the sources
            info_hashes = []
            for source in valid_sources:
                try:
                    info_hash = re.findall(r'btih:(\w{40})', source.get('url', ''))[0].lower()
                    info_hashes.append(info_hash)
                    source['info_hash'] = info_hash
                except IndexError:
                    c.log('Invalid URL format: %s' % source.get('url', ''), 1)

            # Get the cached hashes for each debrid service
            cached_hashes = DBCheck.run(info_hashes)

            # Separate the sources into cached and uncached
            cached_sources = []
            uncached_sources = []
            for source in valid_sources:
                if source.get('info_hash') in cached_hashes:
                    source['source'] = 'cached torrent'
                    cached_sources.append(source)
                else:
                    source['source'] = 'uncached torrent'
                    uncached_sources.append(source)

            # Return the combined list of sources
            return cached_sources + uncached_sources
        except Exception as e:
            failure = traceback.format_exc()
            log_utils.log('Torrent check - Exception: %s' % failure, log_utils.LOGERROR)
            control.infoDialog('Error Processing Torrents')
            return torrent_sources


    def sourcesProcessTorrents(self, torrent_sources):#adjusted Fen code
        if len(torrent_sources) == 0:
            return
        for i in torrent_sources:
            if i.get('debrid', '') not in ['Real-Debrid', 'AllDebrid', 'Premiumize.me', 'Torbox']:
                return torrent_sources

        try:
            from resources.lib.modules import debridcheck
            #control.sleep(500)
            DBCheck = debridcheck.DebridCheck()
            hashList = []
            cachedTorrents = []
            uncachedTorrents = []
            #uncheckedTorrents = []
            for i in torrent_sources:
                try:
                    r = re.findall(r'btih:(\w{40})', str(i['url']))[0]
                    if r:
                        infoHash = r.lower()
                        i['info_hash'] = infoHash
                        hashList.append(infoHash)
                except Exception:
                    torrent_sources.remove(i)
            if len(torrent_sources) == 0:
                return torrent_sources
            torrent_sources = [i for i in torrent_sources if 'info_hash' in i]
            hashList = list(set(hashList))
            control.sleep(500)
            cachedRDHashes, cachedADHashes, cachedPMHashes, cachedTBHashes = DBCheck.run(hashList)

            #cached
            cachedRDSources = [dict(i.items()) for i in torrent_sources if (any(v in i.get('info_hash') for v in cachedRDHashes) and i.get('debrid', '') == 'Real-Debrid')]
            cachedTorrents.extend(cachedRDSources)
            cachedADSources = [dict(i.items()) for i in torrent_sources if (any(v in i.get('info_hash') for v in cachedADHashes) and i.get('debrid', '') == 'AllDebrid')]
            cachedTorrents.extend(cachedADSources)
            cachedPMSources = [dict(i.items()) for i in torrent_sources if (any(v in i.get('info_hash') for v in cachedPMHashes) and i.get('debrid', '') == 'Premiumize.me')]
            cachedTorrents.extend(cachedPMSources)
            cachedTBSources = [dict(i.items()) for i in torrent_sources if (any(v in i.get('info_hash') for v in cachedTBHashes) and i.get('debrid', '') == 'Torbox')]
            cachedTorrents.extend(cachedTBSources)
            for i in cachedTorrents:
                i.update({'source': 'cached torrent'})

            #uncached
            uncachedRDSources = [dict(i.items()) for i in torrent_sources if (not any(v in i.get('info_hash') for v in cachedRDHashes) and i.get('debrid', '') == 'Real-Debrid')]
            uncachedTorrents.extend(uncachedRDSources)
            uncachedADSources = [dict(i.items()) for i in torrent_sources if (not any(v in i.get('info_hash') for v in cachedADHashes) and i.get('debrid', '') == 'AllDebrid')]
            uncachedTorrents.extend(uncachedADSources)
            uncachedPMSources = [dict(i.items()) for i in torrent_sources if (not any(v in i.get('info_hash') for v in cachedPMHashes) and i.get('debrid', '') == 'Premiumize.me')]
            uncachedTorrents.extend(uncachedPMSources)
            uncachedTBSources = [dict(i.items()) for i in torrent_sources if (not any(v in i.get('info_hash') for v in cachedTBHashes) and i.get('debrid', '') == 'Torbox')]
            uncachedTorrents.extend(uncachedTBSources)
            for i in uncachedTorrents:
                i.update({'source': 'uncached torrent'})

            return cachedTorrents + uncachedTorrents
        except Exception:
            failure = traceback.format_exc()
            c.log('Torrent check - Exception: ' + str(failure))
            control.infoDialog('Error Processing Torrents')
            return


    def sourcesFilter_new(self):
        provider_sort_enabled = control.setting('hosts.sort.provider') == 'true'
        debrid_only_enabled = control.setting('debrid.only') == 'true'
        sort_the_crew_enabled = control.setting('torrent.sort.the.crew') == 'true'
        quality_setting = int(control.setting('hosts.quality'))
        captcha_enabled = control.setting('hosts.captcha') == 'true'
        show_cams_enabled = control.setting('hosts.screener') == 'true'
        remove_uncached_enabled = control.setting('remove.uncached') == 'true'

        hevc_keywords = ['hevc', 'h265', 'h.265', 'x265', 'x.265']
        hevc_keywords_lowercase = [x.lower() for x in hevc_keywords]

        if control.setting('HEVC') != 'true':
            self.sources = [src for src in self.sources if not any(keyword in src['url'].lower() for keyword in hevc_keywords_lowercase)]

        local_sources = [src for src in self.sources if src.get('local', False)]
        for src in local_sources:
            src['language'] = self._getPrimaryLang() or 'en'
        self.sources = [src for src in self.sources if src not in local_sources]

        # Filter out duplicate links
        if control.setting('remove.dups') == 'true':
            initial_count = len(self.sources)
            self.sources = list(self.unique_sources(self.sources))
            duplicates_removed = initial_count - len(self.sources)
            control.infoDialog(control.lang(32089).format(duplicates_removed), icon='main_classy.png', time=4000)

        torrent_sources = self.sourcesProcessTorrents([src for src in self.sources if 'magnet:' in src['url']])
        filtered_sources = []

        for debrid_resolver in debrid.debrid_resolvers:
            valid_hosters = {src['source'] for src in self.sources if debrid_resolver.valid_url('', src['source'])}

            if control.setting('check.torr.cache') == 'true':
                try:
                    for src in self.sources:
                        if 'magnet:' in src['url']:
                            src['debrid'] = debrid_resolver.name

                    torrent_sources = self.sourcesProcessTorrents([src for src in self.sources if 'magnet:' in src['url']])
                    cached_sources = [src for src in torrent_sources if src.get('source') == 'cached torrent']
                    filtered_sources.extend(cached_sources)
                    unchecked_sources = [src for src in torrent_sources if src.get('source').lower() == 'torrent']
                    filtered_sources.extend(unchecked_sources)

                    if not remove_uncached_enabled or not cached_sources:
                        uncached_sources = [src for src in torrent_sources if src.get('source') == 'uncached torrent']
                        filtered_sources.extend(uncached_sources)

                    filtered_sources.extend(
                        {**src, 'debrid': debrid_resolver.name}
                        for src in self.sources
                        if src['source'] in valid_hosters and 'magnet:' not in src['url']
                    )
                except Exception:
                    pass

            filtered_sources.extend(
                {**src, 'debrid': debrid_resolver.name}
                for src in self.sources
                if src['source'].lower() == 'torrent' or (src['source'] in valid_hosters and 'magnet:' not in src['url'])
            )
        if not debrid_only_enabled or not debrid.status():
            filtered_sources.extend(
                src for src in self.sources
                if src['source'].lower() not in self.hostprDict and not src.get('debridonly', True)
            )


        self.sources = filtered_sources

        for src in self.sources:
            if src['quality'].lower() == 'hd':
                src['quality'] = '720p'

        quality_levels = [
            ('4k', 0),
            ('1440p', 1),
            ('1080p', 2),
            ('720p', 3),
            ('sd', 4)
        ]

        for quality, level in quality_levels:
            if quality_setting <= level:
                filtered_sources.extend(
                    src for src in self.sources
                    if src['quality'].lower() == quality and (
                        'debrid' in src or
                        ('memberonly' in src if 'debrid' not in src else False))
                )

        if show_cams_enabled:
            filtered_sources.extend(
                src for src in self.sources
                if src['quality'].lower() in ['scr', 'cam']
            )

        self.sources = filtered_sources

        if not captcha_enabled:
            filtered_sources = [src for src in self.sources if src['source'].lower() in self.hostcapDict and 'debrid' not in src]
            self.sources = [src for src in self.sources if src not in filtered_sources]

        filtered_sources = [src for src in self.sources if src['source'].lower() in self.hostblockDict and 'debrid' not in src]
        self.sources = [src for src in self.sources if src not in filtered_sources]

        languages = {src['language'] for src in self.sources}
        multi_language = len(languages) > 1

        if multi_language:
            self.sources = [src for src in self.sources if src['language'] != 'en'] + [src for src in self.sources if src['language'] == 'en']

        max_sources = int(control.setting('returned.sources'))
        self.sources = self.sources[:max_sources]

        return self.sources

    def sourcesFilter(self):
        """
        Filter sources based on quality, provider, hoster, debrid, screener, etc.
        """
        provider = control.setting('hosts.sort.provider') or 'false'
        debrid_only = control.setting('debrid.only') or 'false'
        sortthecrew = control.setting('torrent.sort.the.crew') or 'false'
        quality = int(control.setting('hosts.quality')) or 0
        captcha = control.setting('hosts.captcha') or 'true'
        show_cams = control.setting('hosts.screener') or 'true'
        remove_uncached = control.setting('remove.uncached') or 'false'

        HEVC = control.setting('HEVC')

        #random.shuffle(self.sources)
        #self.sources = [i for i in self.sources if not i['source'].lower() in self.hostblockDict]

        #c.log(f"[CM Debug @ 1528 in sources.py] sources = {self.sources}")

        if sortthecrew == 'true':
            self.sources = sorted(self.sources, key=lambda k: k['source'], reverse=True)
            self.sources = sorted(
                self.sources,
                key=lambda k: (1 if "torrent" in k['source'] else 0, k['source']),
                reverse=True
            )

        if provider == 'true':
            self.sources = sorted(self.sources, key=lambda k: k['provider'])

        hevc_list = ['hevc', 'HEVC', 'h265', 'H265', 'h.265', 'H.265', 'x265', 'X265', 'x.265', 'X.265']

        if not HEVC == 'true':
            self.sources = [i for i in self.sources if not any(value in (i['url']).lower() for value in hevc_list)]# and not any(s in i.get('name').lower for s in hevc_list)

        local = [i for i in self.sources if 'local' in i and i['local'] is True]
        for i in local:
            i.update({'language': self._getPrimaryLang() or 'en'})
        self.sources = [i for i in self.sources if i not in local]

        #Filter-out duplicate links
        try:
            if control.setting('remove.dups') == 'true':
                stotal = len(self.sources)
                self.sources = list(self.unique_sources(self.sources))
                dupes = str(stotal - len(self.sources))
                control.infoDialog(control.lang(32089).format(dupes), icon='INFO')
            else:
                self.sources
        except Exception:
            import traceback
            failure = traceback.format_exc()
            c.log('DUP - Exception: ' + str(failure))
            control.infoDialog('Dupes filter failed', icon='INFO')
            self.sources
        #END


        #torrentSources = self.sourcesProcessTorrents([i for i in self.sources if 'magnet:' in i['url']])
        torrentSources = self.sourcesProcessTorrents([i for i in self.sources if 'magnet:' in i['url']])
        filter = []

        for d in debrid.debrid_resolvers:
            valid_hoster = set([i['source'] for i in self.sources])
            valid_hoster = [i for i in valid_hoster if d.valid_url('', i)]
            if control.setting('check.torr.cache') == 'true':
                try:
                    for i in self.sources:
                        if 'magnet:' in i['url']:
                            i.update({'debrid': d.name})

                    torrentSources = self.sourcesProcessTorrents([i for i in self.sources if 'magnet:' in i['url']])
                    cached = [i for i in torrentSources if i.get('source') == 'cached torrent']
                    filter += cached
                    unchecked = [i for i in torrentSources if i.get('source').lower() == 'torrent']
                    filter += unchecked
                    if remove_uncached == 'false' or len(cached) == 0:
                        uncached = [i for i in torrentSources if i.get('source') == 'uncached torrent']
                        filter += uncached
                    filter += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]
                except Exception:
                    filter += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i.get('source').lower() == 'torrent']
                    filter += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]
            else:
                filter += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i.get('source').lower() == 'torrent']
                filter += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]

        if debrid_only == 'false' or debrid.status() is False:
            filter += [i for i in self.sources if i['source'].lower() not in self.hostprDict and i['debridonly'] is False]

        self.sources = filter

        for i in range(len(self.sources)):
            if self.sources[i]['quality'] in ['hd', 'HD'] :
                self.sources[i].update({'quality': '720p'})

        quality_levels = [
            ('4k', 0),
            ('1440p', 1),
            ('1080p', 2),
            ('720p', 3),
            ('sd', 4)
        ]

        for quality, level in quality_levels:
            if quality_setting <= level:
                filtered_sources.extend(
                    src for src in self.sources
                    if src['quality'].lower() == quality and (
                        'debrid' in src or
                        ('memberonly' in src if 'debrid' not in src else False))
                )

        if show_cams_enabled:
            filtered_sources.extend(
                src for src in self.sources
                if src['quality'].lower() in ['scr', 'cam']
            )

        self.sources = filtered_sources

        if not captcha_enabled:
            filtered_sources = [src for src in self.sources if src['source'].lower() in self.hostcapDict and 'debrid' not in src]
            self.sources = [src for src in self.sources if src not in filtered_sources]

        filtered_sources = [src for src in self.sources if src['source'].lower() in self.hostblockDict and 'debrid' not in src]
        self.sources = [src for src in self.sources if src not in filtered_sources]

        languages = {src['language'] for src in self.sources}
        multi_language = len(languages) > 1

        if multi_language:
            self.sources = [src for src in self.sources if src['language'] != 'en'] + [src for src in self.sources if src['language'] == 'en']

        max_sources = int(control.setting('returned.sources'))
        self.sources = self.sources[:max_sources]

        return self.sources

    def sourcesFilter(self):
        """
        Filter sources based on quality, provider, hoster, debrid, screener, etc.
        """
        provider = control.setting('hosts.sort.provider') or 'false'
        debrid_only = control.setting('debrid.only') or 'false'
        sortthecrew = control.setting('torrent.sort.the.crew') or 'false'
        quality = int(control.setting('hosts.quality')) or 0
        captcha = control.setting('hosts.captcha') or 'true'
        show_cams = control.setting('hosts.screener') or 'true'
        remove_uncached = control.setting('remove.uncached') or 'false'

        HEVC = control.setting('HEVC')

        #random.shuffle(self.sources)
        #self.sources = [i for i in self.sources if not i['source'].lower() in self.hostblockDict]

        #c.log(f"[CM Debug @ 1528 in sources.py] sources = {self.sources}")

        if sortthecrew == 'true':
            self.sources = sorted(self.sources, key=lambda k: k['source'], reverse=True)
            self.sources = sorted(
                self.sources,
                key=lambda k: (1 if "torrent" in k['source'] else 0, k['source']),
                reverse=True
            )

        if provider == 'true':
            self.sources = sorted(self.sources, key=lambda k: k['provider'])

        hevc_list = ['hevc', 'HEVC', 'h265', 'H265', 'h.265', 'H.265', 'x265', 'X265', 'x.265', 'X.265']

        if not HEVC == 'true':
            self.sources = [i for i in self.sources if not any(value in (i['url']).lower() for value in hevc_list)]# and not any(s in i.get('name').lower for s in hevc_list)

        local = [i for i in self.sources if 'local' in i and i['local'] is True]
        for i in local:
            i.update({'language': self._getPrimaryLang() or 'en'})
        self.sources = [i for i in self.sources if i not in local]

        #Filter-out duplicate links
        try:
            if control.setting('remove.dups') == 'true':
                stotal = len(self.sources)
                self.sources = list(self.unique_sources(self.sources))
                dupes = str(stotal - len(self.sources))
                control.infoDialog(control.lang(32089).format(dupes), icon='INFO')
            else:
                self.sources
        except Exception:
            import traceback
            failure = traceback.format_exc()
            c.log('DUP - Exception: ' + str(failure))
            control.infoDialog('Dupes filter failed', icon='INFO')
            self.sources
        #END


        #torrentSources = self.sourcesProcessTorrents([i for i in self.sources if 'magnet:' in i['url']])
        torrentSources = self.sourcesProcessTorrents([i for i in self.sources if 'magnet:' in i['url']])
        filter = []

        for d in debrid.debrid_resolvers:
            valid_hoster = set([i['source'] for i in self.sources])
            valid_hoster = [i for i in valid_hoster if d.valid_url('', i)]
            if control.setting('check.torr.cache') == 'true':
                try:
                    for i in self.sources:
                        if 'magnet:' in i['url']:
                            i['debrid'] = d.name

                    torrentSources = self.sourcesProcessTorrents([i for i in self.sources if 'magnet:' in i['url']])
                    cached = [i for i in torrentSources if i.get('source') == 'cached torrent']
                    filter += cached
                    unchecked = [i for i in torrentSources if i.get('source').lower() == 'torrent']
                    filter += unchecked
                    if remove_uncached == 'false' or len(cached) == 0:
                        uncached = [i for i in torrentSources if i.get('source') == 'uncached torrent']
                        filter += uncached
                    filter += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]
                except Exception:
                    filter += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i.get('source').lower() == 'torrent']
                    filter += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]
            else:
                filter += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i.get('source').lower() == 'torrent']
                filter += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]

        if debrid_only == 'false' or debrid.status() is False:
            filter += [i for i in self.sources if i['source'].lower() not in self.hostprDict and i['debridonly'] is False]

        self.sources = filter

        for i in range(len(self.sources)):
            if self.sources[i]['quality'] in ['hd', 'HD'] :
                self.sources[i].update({'quality': '720p'})

        quality_levels = [
            ('4k', 0),
            ('1440p', 1),
            ('1080p', 2),
            ('720p', 3),
            ('sd', 4)
        ]

        for quality, level in quality_levels:
            if quality_setting <= level:
                filtered_sources.extend(
                    src for src in self.sources
                    if src['quality'].lower() == quality and (
                        'debrid' in src or
                        ('memberonly' in src if 'debrid' not in src else False))
                )

        if show_cams_enabled:
            filtered_sources.extend(
                src for src in self.sources
                if src['quality'].lower() in ['scr', 'cam']
            )

        self.sources = filtered_sources

        if not captcha_enabled:
            filtered_sources = [src for src in self.sources if src['source'].lower() in self.hostcapDict and 'debrid' not in src]
            self.sources = [src for src in self.sources if src not in filtered_sources]

        filtered_sources = [src for src in self.sources if src['source'].lower() in self.hostblockDict and 'debrid' not in src]
        self.sources = [src for src in self.sources if src not in filtered_sources]

        languages = {src['language'] for src in self.sources}
        multi_language = len(languages) > 1

        if multi_language:
            self.sources = [src for src in self.sources if src['language'] != 'en'] + [src for src in self.sources if src['language'] == 'en']

        max_sources = int(control.setting('returned.sources'))
        self.sources = self.sources[:max_sources]

        return self.sources

    def sourcesFilter(self):
        """
        Filter sources based on quality, provider, hoster, debrid, screener, etc.
        """
        provider = control.setting('hosts.sort.provider') or 'false'
        debrid_only = control.setting('debrid.only') or 'false'
        sortthecrew = control.setting('torrent.sort.the.crew') or 'false'
        quality = int(control.setting('hosts.quality')) or 0
        captcha = control.setting('hosts.captcha') or 'true'

        remove_uncached = control.setting('remove.uncached') or 'false'


        quality_setting = int(control.setting('hosts.quality'))
        captcha_enabled = control.setting('hosts.captcha') or 'true'
        show_cams_enabled = control.setting('hosts.screener') or 'true'


        HEVC = control.setting('HEVC')

        #random.shuffle(self.sources)
        #self.sources = [i for i in self.sources if not i['source'].lower() in self.hostblockDict]

        #c.log(f"[CM Debug @ 1528 in sources.py] sources = {self.sources}")

        if sortthecrew == 'true':
            self.sources = sorted(self.sources, key=lambda k: k['source'], reverse=True)
            self.sources = sorted(
                self.sources,
                key=lambda k: (1 if "torrent" in k['source'] else 0, k['source']),
                reverse=True
            )

        if provider == 'true':
            self.sources = sorted(self.sources, key=lambda k: k['provider'])

        hevc_list = ['hevc', 'HEVC', 'h265', 'H265', 'h.265', 'H.265', 'x265', 'X265', 'x.265', 'X.265']

        if not HEVC == 'true':
            self.sources = [i for i in self.sources if not any(value in (i['url']).lower() for value in hevc_list)]# and not any(s in i.get('name').lower for s in hevc_list)

        local = [i for i in self.sources if 'local' in i and i['local'] is True]
        for i in local:
            i.update({'language': self._getPrimaryLang() or 'en'})
        self.sources = [i for i in self.sources if i not in local]

        #Filter-out duplicate links
        try:
            if control.setting('remove.dups') == 'true':
                stotal = len(self.sources)
                self.sources = list(self.unique_sources(self.sources))
                dupes = str(stotal - len(self.sources))
                control.infoDialog(control.lang(32089).format(dupes), icon='INFO')
            else:
                self.sources
        except Exception:
            import traceback
            failure = traceback.format_exc()
            c.log('DUP - Exception: ' + str(failure))
            control.infoDialog('Dupes filter failed', icon='INFO')
            self.sources
        #END


        #torrentSources = self.sourcesProcessTorrents([i for i in self.sources if 'magnet:' in i['url']])
        torrentSources = self.sourcesProcessTorrents([i for i in self.sources if 'magnet:' in i['url']])
        filter_sources = []

        for d in debrid.debrid_resolvers:
            valid_hoster = set([i['source'] for i in self.sources])
            valid_hoster = [i for i in valid_hoster if d.valid_url('', i)]
            if control.setting('check.torr.cache') == 'true':
                try:
                    for i in self.sources:
                        if 'magnet:' in i['url']:
                            i['debrid'] = d.name

                    torrentSources = self.sourcesProcessTorrents([i for i in self.sources if 'magnet:' in i['url']])
                    cached = [i for i in torrentSources if i.get('source') == 'cached torrent']
                    filter_sources += cached
                    unchecked = [i for i in torrentSources if i.get('source').lower() == 'torrent']
                    filter_sources += unchecked
                    if remove_uncached == 'false' or len(cached) == 0:
                        uncached = [i for i in torrentSources if i.get('source') == 'uncached torrent']
                        filter_sources += uncached
                    filter_sources += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]
                except Exception:
                    filter_sources += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i.get('source').lower() == 'torrent']
                    filter_sources += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]
            else:
                filter_sources += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i.get('source').lower() == 'torrent']
                filter_sources += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]

        if debrid_only == 'false' or debrid.status() is False:
            filter_sources += [i for i in self.sources if i['source'].lower() not in self.hostprDict and i['debridonly'] is False]

        self.sources = filter_sources

        for i in range(len(self.sources)):
            if self.sources[i]['quality'] in ['hd', 'HD'] :
                self.sources[i].update({'quality': '720p'})

        quality_levels = [
            ('4k', 0),
            ('1440p', 1),
            ('1080p', 2),
            ('720p', 3),
            ('sd', 4)
        ]

        filtered_sources = []

        for quality, level in quality_levels:
            if quality_setting <= level:
                filtered_sources.extend(
                    src for src in self.sources
                    if src['quality'].lower() == quality and (
                        'debrid' in src or
                        ('memberonly' in src if 'debrid' not in src else False))
                )

        if show_cams_enabled:
            filtered_sources.extend(
                src for src in self.sources
                if src['quality'].lower() in ['scr', 'cam']
            )

        self.sources = filtered_sources

        if not captcha_enabled:
            filtered_sources = [src for src in self.sources if src['source'].lower() in self.hostcapDict and 'debrid' not in src]
            self.sources = [src for src in self.sources if src not in filtered_sources]

        filtered_sources = [src for src in self.sources if src['source'].lower() in self.hostblockDict and 'debrid' not in src]
        self.sources = [src for src in self.sources if src not in filtered_sources]

        languages = {src['language'] for src in self.sources}
        multi_language = len(languages) > 1



        if multi_language:
            self.sources = [src for src in self.sources if src['language'] != 'en'] + [src for src in self.sources if src['language'] == 'en']

        max_sources = int(control.setting('returned.sources'))
        self.sources = self.sources[:max_sources]

        extra_info = control.setting('sources.extrainfo')
        prem_identify = control.setting('prem.identify') or 'gold'
        torr_identify = control.setting('torrent.identify') or 'blue'

        prem_identify = self.get_prem_color(prem_identify)
        torr_identify = self.get_prem_color(torr_identify)

        for i in range(len(self.sources)):

            if extra_info == 'true':
                t = source_utils.get_file_type(self.sources[i]['url'])
            else:
                t = None

            u = self.sources[i]['url']
            p = self.sources[i]['provider']
            q = self.sources[i]['quality']
            s = self.sources[i]['source']
            s = s.rsplit('.', 1)[0]
            l = self.sources[i]['language']

            try:
                f = (' | '.join(['[I]%s [/I]' % info.strip() for info in self.sources[i]['info'].split('|')]))
            except Exception:
                f = ''

            try:
                d = self.sources[i]['debrid']
            except Exception:
                d = self.sources[i]['debrid'] = ''

            if d.lower() == 'alldebrid':
                d = 'AD'
            if d.lower() == 'debrid-link.fr':
                d = 'DL.FR'
            if d.lower() == 'linksnappy':
                d = 'LS'
            if d.lower() == 'megadebrid':
                d = 'MD'
            if d.lower() == 'premiumize.me':
                d = 'PM'
            if d.lower() == 'torbox':
                d = 'TB'
            if d.lower() == 'real-debrid':
                d = 'RD'
            if d.lower() == 'zevera':
                d = 'ZVR'
            if not d == '':
                #label = '%02d | %s | %s | %s | ' % (int(i+1), d, q, p)
                label = f'{int(i+1):02d} | {d} | {q} | {p} | '
            else:
                #label = '%02d | %s | %s | ' % (int(i+1), q, p)
                label = f'{int(i+1):02d} | {q} | {p} | '

            if multi_language and l != 'en':
                label += f'{l} | '

            multiline_label = label

            if t is not None:
                if f is not None:
                    multiline_label += '%s \n       %s | %s' % (s, f, t)
                    label += '%s | %s | %s' % (s, f, t)
                else:
                    multiline_label += '%s \n       %s' % (s, t)
                    label += '%s | %s' % (s, t)
            else:
                if f is not None:
                    multiline_label += '%s \n       %s' % (s, f)
                    label += '%s | %s' % (s, f)
                else:
                    multiline_label += '%s' % s
                    label += '%s' % s
            label = label.replace('| 0 |', '|').replace(' | [I]0 [/I]', '')
            label = re.sub(r'\[I\]\s+\[/I\]', ' ', label)
            label = re.sub(r'\|\s+\|', '|', label)
            label = re.sub(r'\|(?:\s+|)$', '', label)

            if d:
                if 'torrent' in s.lower():
                    if not torr_identify == 'nocolor':
                        self.sources[i]['multiline_label'] = ('[COLOR %s]' % (torr_identify)) + multiline_label.upper() + '[/COLOR]'
                        self.sources[i]['label'] = ('[COLOR %s]' % (torr_identify)) + label.upper() + '[/COLOR]'
                    else:
                        self.sources[i]['multiline_label'] = multiline_label.upper()
                        self.sources[i]['label'] = label.upper()
                else:
                    if not prem_identify == 'nocolor':
                        self.sources[i]['multiline_label'] = ('[COLOR %s]' % (prem_identify)) + multiline_label.upper() + '[/COLOR]'
                        self.sources[i]['label'] = ('[COLOR %s]' % (prem_identify)) + label.upper() + '[/COLOR]'
                    else:
                        self.sources[i]['multiline_label'] = multiline_label.upper()
                        self.sources[i]['label'] = label.upper()
            else:
                self.sources[i]['multiline_label'] = multiline_label.upper()
                self.sources[i]['label'] = label.upper()

        try:
            if not HEVC == 'true':
                self.sources = [i for i in self.sources if not 'HEVC' or 'multiline_label' in i]

        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 2080 in sources.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 2080 in sources.py]Exception raised. Error = {e}')


        self.sources = [i for i in self.sources if 'label' or 'multiline_label' in i['label']]
        #c.log(f"[CM Debug @ 2605 in sources.py] sources = {self.sources}")

        return self.sources

    def sourcesResolve(self, item, info=False):
        try:
            self.url = None

            u = url = item['url']

            d = item['debrid']
            direct = item['direct']
            local = item.get('local', False)

            provider = item['provider']
            call = [i[1] for i in self.sourceDict if i[0] == provider][0]
            u = url = call.resolve(url)
            #if url is None or (not '://' in str(url) and not local and 'magnet' not in str(url)): raise Exception()
            if not url or ('://' not in url and 'magnet' not in url and not local ):
                raise Exception()

            if not local:
                url = url[8:] if url.startswith('stack:') else url

                urls = []
                for part in url.split(' , '):
                    u = part
                    if not d == '':
                        part = debrid.resolver(part, d)
                    elif direct is not True:
                        hmf = resolveurl.HostedMediaFile(url=u, include_disabled=True, include_universal=False)
                        if hmf.valid_url() is True:
                            part = hmf.resolve()
                    urls.append(part)

                url = 'stack://' + ' , '.join(urls) if len(urls) > 1 else urls[0]

            if url is False or url is None:
                raise Exception()

            ext = url.split('?')[0].split('&')[0].split('|')[0].rsplit('.')[-1].replace('/', '').lower()
            if ext == 'rar':
                raise Exception()

            try:
                headers = url.rsplit('|', 1)[1]
            except Exception:
                headers = ''
            headers = quote_plus(headers).replace('%3D', '=') if ' ' in headers else headers
            headers = dict(parse_qsl(headers))

            # if url.startswith('http') and '.m3u8' in url:
            #     try: result = client.request(url.split('|')[0], headers=headers, output='geturl', timeout='20')
            #     except Exception: pass

            # elif url.startswith('http'):
            #     try: result = client.request(url.split('|')[0], headers=headers, output='chunk', timeout='20')
            #     except Exception: pass

            self.url = url
            return url
        except Exception:
            if info is True:
                self.errorForSources()
            return

    def sourcesDialog(self, items):
        try:

            labels = [i['label'] for i in items]

            select = control.selectDialog(labels)
            if select == -1:
                return 'close://'

            _next = [y for x, y in enumerate(items) if x >= select]
            prev = [y for x, y in enumerate(items) if x < select][::-1]

            items = [items[select]]
            items = [i for i in items+_next+prev][:40]

            header = control.addonInfo('name')
            header2 = header.upper()

            progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
            progressDialog.create(header, '')

            block = None

            for i in range(len(items)):
                try:
                    if items[i]['source'] == block:
                        raise Exception()

                    w = workers.Thread(self.sourcesResolve, items[i])
                    w.start()

                    try:
                        if progressDialog.iscanceled():
                            break
                        progressDialog.update(int((100 / float(len(items))) * i), str(items[i]['label']))
                    except Exception:
                        progressDialog.update(int((100 / float(len(items))) * i), str(header2) + '\n' + str(items[i]['label']))

                    m = ''

                    for x in range(3600):
                        try:
                            if control.monitor.abortRequested():
                                return sys.exit()
                            if progressDialog.iscanceled():
                                return progressDialog.close()
                        except Exception:
                            pass

                        k = control.condVisibility('Window.IsActive(virtualkeyboard)')
                        if k:
                            m += '1'
                            m = m[-1]
                        if (w.is_alive() is False or x > 30) and not k:
                            break
                        k = control.condVisibility('Window.IsActive(yesnoDialog)')
                        if k:
                            m += '1'
                            m = m[-1]
                        if (w.is_alive() is False or x > 30) and not k:
                            break
                        time.sleep(0.5)

                    for x in range(30):
                        try:
                            if control.monitor.abortRequested():
                                return sys.exit()
                            if progressDialog.iscanceled():
                                return progressDialog.close()
                        except Exception:
                            pass

                        if m == '':
                            break
                        if w.is_alive() is False:
                            break
                        time.sleep(0.5)

                    if w.is_alive() is True:
                        block = items[i]['source']

                    if self.url is None:
                        raise Exception()

                    self.selectedSource = items[i]['label']

                    try:
                        progressDialog.close()
                    except Exception:
                        pass

                    control.execute('Dialog.Close(virtualkeyboard)')
                    control.execute('Dialog.Close(yesnoDialog)')
                    return self.url
                except Exception:
                    pass

            try:
                progressDialog.close()
            except Exception:
                pass
            del progressDialog

        except Exception as e:
            try:
                progressDialog.close()
            except Exception:
                pass
            del progressDialog
            c.log(f'[CM Debug @ 2422 in sources.py]Error {e}', 1)

    def sourcesDirect(self, items):
        """
        Filters and resolves a list of source items based on specified criteria.

        This method processes a list of media source items, applying filters to exclude
        certain sources based on host capabilities, host blocks, autoplay settings, and quality.
        It then attempts to resolve the URL for each remaining source, updating a progress dialog
        to reflect the current processing status.

        Args:
            items (list): A list of dictionaries, where each dictionary represents a media source
                        with keys such as 'source', 'debrid', 'autoplay', and 'quality'.

        Returns:
            str or None: The resolved URL of the first successfully processed source item,
                        or None if no source could be resolved.
        """
        _filter = [i for i in items if i['source'].lower() in self.hostcapDict and not i.get('debrid')]
        items = [i for i in items if i not in _filter]

        _filter = [i for i in items if i['source'].lower() in self.hostblockDict]# and not i.get('debrid')]
        items = [i for i in items if i not in _filter]

        items = [i for i in items if ('autoplay' in i and i['autoplay'] is True) or 'autoplay' not in i]

        if control.setting('autoplay.sd') == 'true':
            items = [i for i in items if i['quality'] not in ['4K', '1440p', '1080p', 'HD']]

        u = None

        header = control.addonInfo('name')
        header2 = header.upper()

        try:
            control.sleep(1000)

            progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
            progressDialog.create(header, '')
            #progressDialog.update(0)
        except Exception:
            pass

        for i in range(len(items)):
            try:
                if progressDialog.iscanceled():
                    break
                progressDialog.update(int((100 / float(len(items))) * i), str(items[i]['label']))
            except Exception:
                progressDialog.update(int((100 / float(len(items))) * i), str(header2) + ' ' + str(items[i]['label']))


            try:
                if control.monitor.abortRequested(): return sys.exit()

                url = self.sourcesResolve(items[i])
                if u is None:
                    u = url
                if url is not None:
                    break
            except Exception:
                pass

        try:
            progressDialog.close()
        except Exception:
            pass
        del progressDialog

        return u

    def errorForSources(self):
        control.infoDialog(control.lang(32401), sound=False, icon='INFO')

    def getLanguage(self):
        langDict = {
            'English': ['en'],
            'German': ['de'],
            'German+English': ['de', 'en'],
            'French': ['fr'],
            'French+English': ['fr', 'en'],
            'Portuguese': ['pt'],
            'Portuguese+English': ['pt', 'en'],
            'Polish': ['pl'],
            'Polish+English': ['pl', 'en'],
            'Korean': ['ko'],
            'Korean+English': ['ko', 'en'],
            'Russian': ['ru'],
            'Russian+English': ['ru', 'en'],
            'Spanish': ['es'],
            'Spanish+English': ['es', 'en'],
            'Greek': ['gr'],
            'Italian': ['it'],
            'Italian+English': ['it', 'en'],
            'Greek+English': ['gr', 'en']}
        name = control.setting('providers.lang')
        return langDict.get(name, ['en'])

    def getLocalTitle(self, title, imdb, tmdb, content):
        lang = self._getPrimaryLang()
        if not lang:
            return title

        if content == 'movie':
            t = trakt.getMovieTranslation(imdb, lang)
        else:
            t = trakt.getTVShowTranslation(imdb, lang)

        return t or title

    def getAliasTitles(self, imdb, localtitle, content):
        lang = self._getPrimaryLang()

        try:
            t = trakt.getMovieAliases(imdb) if content == 'movie' else trakt.getTVShowAliases(imdb)
            t = [i for i in t if i.get('country', '').lower() in [lang, '', 'us']
                and i.get('title', '').lower() != localtitle.lower()]
            return t
        except Exception:
            return []

    def _getPrimaryLang(self):
        langDict = {
            'English': 'en', 'German': 'de', 'German+English': 'de', 'French': 'fr', 'French+English': 'fr',
            'Portuguese': 'pt', 'Portuguese+English': 'pt', 'Polish': 'pl', 'Polish+English': 'pl', 'Korean': 'ko',
            'Korean+English': 'ko', 'Russian': 'ru', 'Russian+English': 'ru', 'Spanish': 'es', 'Spanish+English': 'es',
            'Italian': 'it', 'Italian+English': 'it', 'Greek': 'gr', 'Greek+English': 'gr'}
        name = control.setting('providers.lang')
        lang = langDict.get(name)
        return lang

    def getTitle(self, title):
        title = cleantitle.normalize(title)
        return title

    def getConstants(self):
        self.itemProperty = 'plugin.video.thecrew.container.items'
        self.metaProperty = 'plugin.video.thecrew.container.meta'

        from resources.lib.sources import sources

        self.sourceDict = sources()

        try:
            self.hostDict = resolveurl.relevant_resolvers(order_matters=True)
            self.hostDict = [i.domains for i in self.hostDict if '*' not in i.domains]
            self.hostDict = [i.lower() for i in reduce(lambda x, y: x+y, self.hostDict)]
            self.hostDict = [x for y, x in enumerate(self.hostDict) if x not in self.hostDict[:y]]
        except Exception:
            self.hostDict = []

        self.hostprDict = [
            '1fichier.com', 'oboom.com', 'rapidgator.net', 'rg.to', 'uploaded.net', 'uploaded.to', 'uploadgig.com',
            'ul.to', 'filefactory.com', 'nitroflare.com', 'turbobit.net', 'uploadrocket.net', 'multiup.org']

        self.hostcapDict = [
            'openload.io', 'openload.co', 'oload.tv', 'oload.stream', 'oload.win', 'oload.download', 'oload.info',
            'oload.icu', 'oload.fun', 'oload.life', 'openload.pw', 'vev.io', 'vidup.me', 'vidup.tv', 'vidup.io',
            'vshare.io', 'vshare.eu', 'flashx.tv', 'flashx.to', 'flashx.sx', 'flashx.bz', 'flashx.cc', 'hugefiles.net',
            'hugefiles.cc', 'thevideo.me', 'streamin.to', 'extramovies.guru', 'extramovies.trade', 'extramovies.host' ]

        self.hosthqDict = [
            'gvideo', 'google.com', 'thevideo.me', 'raptu.com', 'filez.tv', 'uptobox.com', 'uptostream.com',
            'xvidstage.com', 'xstreamcdn.com', 'idtbox.com']

        self.hostblockDict = [
            'zippyshare.com', 'youtube.com', 'facebook.com', 'twitch.tv', 'streamango.com', 'streamcherry.com',
            'openload.io', 'openload.co', 'openload.pw', 'oload.tv', 'oload.stream', 'oload.win', 'oload.download',
            'oload.info', 'oload.icu', 'oload.fun', 'oload.life', 'oload.space', 'oload.monster', 'openload.pw',
            'rapidvideo.com', 'rapidvideo.is', 'rapidvid.to']

    def get_prem_color(self, n):
        """Return the color associated with a given premium status."""
        colors = {
            '0': 'blue',
            '1': 'red',
            '2': 'yellow',
            '3': 'deeppink',
            '4': 'cyan',
            '5': 'lawngreen',
            '6': 'gold',
            '7': 'magenta',
            '8': 'yellowgreen',
            '9': 'nocolor',
        }
        return colors.get(n, 'blue')
