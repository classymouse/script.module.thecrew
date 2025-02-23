# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file sources.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

import json


import datetime
import random
import re
import sys
import time
import traceback
import base64
#import functools
#import urllib

from urllib.parse import quote_plus, parse_qsl
from functools import reduce

from . import trakt
#from . import tvmaze
#from . import cache
from . import control
from . import cleantitle
#from . import client
from . import debrid
from . import workers
from . import source_utils
from . import log_utils
from . import playcount
from .listitem import ListItemInfoTag
from .player import player
from .crewruntime import c




import sqlite3 as database
import resolveurl
import xbmc

import six
#from six.moves import reduce #zip,

class sources:
    def __init__(self):
        self.getConstants()
        self.sources = []
        self.url = ''
        self.dev_mode = False
        if(control.setting('dev_pw') == c.ensure_text(base64.b64decode(b'dGhlY3Jldw=='))):
            self.dev_mode = True
        c.log(f"[CM Debug @ 63 in sources.py] devmode is {self.dev_mode}")

    def play(self, title, year, imdb, tmdb, season, episode, tvshowtitle, premiered, meta, select='1'):
        try:
            url = None

            items = self.getSources(title, year, imdb, tmdb, season, episode, tvshowtitle, premiered)
            c.log(f"[CM Debug @ 73 in sources.py] items = {repr(items)}")
            select = control.setting('hosts.mode') if not select else select # cm - this is ALWAYS select, always 1

            metadata = json.loads(meta) if meta is not None else {}
            c.log(f"[CM Debug @ 77 in sources.py] meta = {metadata}")
            mediatype = metadata['mediatype'] if 'mediatype' in metadata else ''

            if mediatype != 'movie':
                if tvshowtitle is not None:
                    title = tvshowtitle if len(tvshowtitle) > 0 else title
                    pass

            if len(items) > 0:

                if select == '1' and 'plugin' in control.infoLabel('Container.PluginName'):
                    control.window.clearProperty(self.itemProperty)
                    control.window.setProperty(self.itemProperty, json.dumps(items))

                    control.window.clearProperty(self.metaProperty)
                    control.window.setProperty(self.metaProperty, meta)

                    control.sleep(200)

                    return control.execute('Container.Update(%s?action=addItem&title=%s)' % (sys.argv[0], quote_plus(title)))

                elif select == '0' or select == '1':
                    url = self.sourcesDialog(items)
                else:
                    url = self.sourcesDirect(items)

            if url == 'close://' or not url:
                self.url = url
                return self.errorForSources()

            try:
                meta = json.loads(meta)
            except Exception:
                pass


            player().run(title, year, season, episode, imdb, tmdb, url, meta)
        except Exception:
            pass

    def addItem(self, title):

        addon_poster, addon_banner = c.addon_poster(), c.addon_banner()
        addon_fanart = c.addon_fanart()
        setting_fanart = control.setting('fanart')
        addon_clearlogo, addon_clearart = c.addon_clearlogo(), c.addon_clearart()
        addon_thumb, addon_discart = c.addon_thumb(), c.addon_discart()

        indicators = playcount.getMovieIndicators(refresh=True)

        c.log(f"[CM Debug @ 124 in sources.py] inside addItem function, addon_poster = {addon_poster}")

        control.playlist.clear()

        items = control.window.getProperty(self.itemProperty)
        items = json.loads(items)

        #c.log(f"[CM Debug @ 131 in sources.py] items = {items}")

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

        downloads = True if control.setting('downloads') == 'true' and\
            not (control.setting('movie.download.path') == '' or\
                control.setting('tv.download.path') == '') else False

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

        meta = control.tagdataClean(meta)
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

                if downloads is True:
                    cm.append((download_menu, f'RunPlugin({sysaddon}?action=download&name={sysname}&image={sysimage}&source={syssource})'))

                cm.append(('CM Test', f'RunPlugin({sysaddon}?action=classytest&title={systitle}&source={syssource})'))
                item_list = control.item(label=label)

                info_tag = ListItemInfoTag(item_list, 'video')
                infolabels = control.tagdataClean(meta)
                info_tag.set_info(infolabels)


                item_list.setArt({
                    'icon': poster, 'thumb': thumb, 'poster': poster, 'banner': banner,
                    'fanart': fanart, 'landscape': fanart, 'clearlogo': clearlogo,
                    'clearart': clearart, 'discart': discart
                    })

                video_streaminfo = {'codec': 'h264'}
                item_list.addStreamInfo('video', video_streaminfo)

                item_list.addContextMenuItems(cm)
                item_list.setInfo(type='Video', infoLabels=meta)

                control.addItem(handle=syshandle, url=sysurl, listitem=item_list, isFolder=False)
            except Exception as e:
                import traceback
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


    def getSources2(self, title, year, imdb, tmdb, season, episode, tvshowtitle, premiered, quality='HD', timeout=30):

        start_time = time.time()
        progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
        progressDialog.create(control.addonInfo('name'), '')
        progressDialog.update(0)
        start_time = time.time()
        limit_results = control.setting('max.limit.sources') or 25
        #create tables if necessary
        self.prepareSources()

        sourceDict = self.sourceDict
        progressDialog.update(0, control.lang(32600))

        content = 'movie' if tvshowtitle is None else 'episode'
        if content == 'movie':
            sourceDict = [(i[0], i[1], getattr(i[1], 'movie', None)) for i in sourceDict]
            genres = trakt.getGenre('movie', 'imdb', imdb)
        else:
            sourceDict = [(i[0], i[1], getattr(i[1], 'tvshow', None)) for i in sourceDict]
            genres = trakt.getGenre('show', 'imdb', imdb)


        sourceDict = [(i[0], i[1], i[2]) for i in sourceDict if not hasattr(i[1], 'genre_filter') or not i[1].genre_filter or any(x in i[1].genre_filter for x in genres)]
        sourceDict = [(i[0], i[1]) for i in sourceDict if i[2] is not None]

        language = self.getLanguage()
        sourceDict = [(i[0], i[1], i[1].language) for i in sourceDict]
        sourceDict = [(i[0], i[1]) for i in sourceDict if any(x in i[2] for x in language)]

        try:
            sourceDict = [(i[0], i[1], control.setting('provider.' + i[0])) for i in sourceDict]
        except Exception:
            sourceDict = [(i[0], i[1], 'true') for i in sourceDict]
        sourceDict = [(i[0], i[1]) for i in sourceDict if i[2] != 'false']

        sourceDict = [(i[0], i[1], i[1].priority) for i in sourceDict]
        #random.shuffle(sourceDict)
        sourceDict = sorted(sourceDict, key=lambda i: i[2])
        #for i in sourceDict:
            #c.log(f"[CM Debug @ 459 in sources.py] i[0] = {i[0]}|i[1] = {type(i[1])}|i[2] = {type(i[2])} with val = {repr(i[2])}")
        threads = []

        if content == 'movie':
            title = self.getTitle(title)
            c.log(f"[CM Debug @ 465 in sources.py] title={title}")
            localtitle = self.getLocalTitle(title, imdb, tmdb, content)
            aliases = self.getAliasTitles(imdb, localtitle, content)
            for i in sourceDict:
                threads.append(workers.Thread(self.getMovieSource, title, localtitle, aliases, year, imdb, i[0], i[1]))
        else:
            tvshowtitle = self.getTitle(tvshowtitle)
            localtvshowtitle = self.getLocalTitle(tvshowtitle, imdb, tmdb, content)
            aliases = self.getAliasTitles(imdb, localtvshowtitle, content)

            for i in sourceDict:
                threads.append(workers.Thread(self.getEpisodeSource, title, year, imdb, tmdb, season, episode, tvshowtitle, localtvshowtitle, aliases, premiered, i[0], i[1]))


        s = [i[0] + (i[1],) for i in zip(sourceDict, threads)]
        s = [(i[3].getName(), i[0], i[2]) for i in s]

        mainsourceDict = [i[0] for i in s if i[2] == 0]
        c.log(f"[CM Debug @ 482 in sources.py] mainsourceDict = {mainsourceDict}")
        sourcelabelDict = dict([(i[0], i[1].upper()) for i in s])

        #[i.start() for i in threads]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        #[i.join() for i in threads]

        string1 = control.lang(32404)
        string2 = control.lang(32405)
        string3 = control.lang(32406)
        string4 = control.lang(32601)
        string5 = control.lang(32602)
        string6 = control.lang(32606)
        string7 = control.lang(32607)

        #cm changfed 18-11-2024
        timeout = int(control.setting('scrapers.timeout.1')) or 30

        #fixed oh 27-4-2021
        quality = int(control.setting('hosts.quality')) or 0
        debrid_only = control.setting('debrid.only') or 'false'

        line1 = line2 = line3 = ""

        pre_emp =  control.setting('preemptive.termination')
        pre_emp_limit = int(control.setting('preemptive.limit'))
        source_4k = d_source_4k = 0
        source_1080 = d_source_1080 = 0
        source_720 = d_source_720 = 0
        source_sd = d_source_sd = 0
        total = debrid_total = 0

        debrid_resolvers = debrid.debrid_resolvers
        debrid_status = debrid.status()

        total_format = '[COLOR %s][B]%s[/B][/COLOR]'
        pdiag_format = ' 4K: %s | 1080p: %s | 720p: %s | SD: %s | %s: %s'.split('|')
        pdiag_bg_format = '4K:%s(%s)|1080p:%s(%s)|720p:%s(%s)|SD:%s(%s)|T:%s(%s)'.split('|')

        #for i in range(0, 4 * timeout): #max 120
        #for i in range(0, 2 * timeout): #max 120
        for i in range(timeout): #max 120
            c.log(f"[CM Debug @ 484 in sources.py] i = {i}")
            if str(pre_emp) == 'true':
                if quality in [0, 1]:
                    if (source_4k + d_source_4k) >= int(pre_emp_limit):
                        break
                elif quality == 1:
                    if (source_1080 + d_source_1080) >= int(pre_emp_limit):
                        break
                elif quality == 2:
                    if (source_720 + d_source_720) >= int(pre_emp_limit):
                        break
                elif quality == 3:
                    if (source_sd + d_source_sd) >= int(pre_emp_limit):
                        break
                else:
                    if (source_sd + d_source_sd) >= int(pre_emp_limit):
                        break
            try:
                if control.monitor.abortRequested():
                    return sys.exit()

                try:
                    if progressDialog.iscanceled():
                        break
                except Exception:
                    pass

                #c.log(f"[CM Debug @ 545 in sources.py] debrid_status = {debrid_status}")
                #d_4k_label = d_1080_label = d_720_label = d_sd_label = total_format = d_total_label = ''
                #source_4k_label = source_1080_label = source_720_label = source_sd_label = source_total_label = ''

                if len(self.sources) > 0:
                    source_counts = {
                        '4K': len([e for e in self.sources if e['quality'].upper() == '4K' and e['debridonly'] is False]),
                        '1080p': len([e for e in self.sources if e['quality'] in ['1440p','1080p'] and e['debridonly'] is False]),
                        '720p': len([e for e in self.sources if e['quality'] in ['720p','HD'] and e['debridonly'] is False]),
                        'SD': len([e for e in self.sources if e['quality'].upper() == 'SD' and e['debridonly'] is False]),
                    }
                    total = sum(source_counts.values())
                    if debrid_status:
                        debrid_source_counts = {
                            '4K': sum([len([e for e in self.sources if e['quality'].upper() == '4K' and d.valid_url(e['url'], e['source'])]) for d in debrid_resolvers]),
                            '1080p': sum([len([e for e in self.sources if e['quality'] in ['1440p','1080p'] and d.valid_url(e['url'], e['source'])]) for d in debrid_resolvers]),
                            '720p': sum([len([e for e in self.sources if e['quality'] in ['720p','HD'] and d.valid_url(e['url'], e['source'])]) for d in debrid_resolvers]),
                            'SD': sum([len([e for e in self.sources if e['quality'].upper() == 'SD' and d.valid_url(e['url'], e['source'])]) for d in debrid_resolvers]),
                        }
                        debrid_total = sum(debrid_source_counts.values())

                    pdiag_list = [source_counts['4K'], source_counts['1080p'], source_counts['720p'], source_counts['SD'], total]
                    pdiag_list_debrid = [debrid_source_counts['4K'], debrid_source_counts['1080p'], debrid_source_counts['720p'], debrid_source_counts['SD'], debrid_total]
                    #c.log(f"[CM Debug @ 566 in sources.py] pdiag_list_debrid = {pdiag_list_debrid}")

                    if debrid_status:
                        d_4k_label = total_format % ('red', pdiag_list_debrid[0]) if pdiag_list_debrid[0] == 0 else total_format % ('lime', pdiag_list_debrid[0])
                        d_1080_label = total_format % ('red', pdiag_list_debrid[1]) if pdiag_list_debrid[1] == 0 else total_format % ('lime', pdiag_list_debrid[1])
                        d_720_label = total_format % ('red', pdiag_list_debrid[2]) if pdiag_list_debrid[2] == 0 else total_format % ('lime', pdiag_list_debrid[2])
                        d_sd_label = total_format % ('red', pdiag_list_debrid[3]) if pdiag_list_debrid[3] == 0 else total_format % ('lime', pdiag_list_debrid[3])
                        d_total_label = total_format % ('red', pdiag_list_debrid[4]) if pdiag_list_debrid[4] == 0 else total_format % ('lime', pdiag_list_debrid[4])
                    source_4k_label = total_format % ('red', pdiag_list[0]) if pdiag_list[0] == 0 else total_format % ('lime', pdiag_list[0])
                    source_1080_label = total_format % ('red', pdiag_list[1]) if pdiag_list[1] == 0 else total_format % ('lime', pdiag_list[1])
                    source_720_label = total_format % ('red', pdiag_list[2]) if pdiag_list[2] == 0 else total_format % ('lime', pdiag_list[2])
                    source_sd_label = total_format % ('red', pdiag_list[3]) if pdiag_list[3] == 0 else total_format % ('lime', pdiag_list[3])
                    source_total_label = total_format % ('red', pdiag_list[4]) if pdiag_list[4] == 0 else total_format % ('lime', pdiag_list[4])
                else:
                    #no sources
                    c.log(f"[CM Debug @ 549 in sources.py] len(self.sources) = {len(self.sources)}")
                    raise StopIteration





                mainleft = info = []
                for x in threads:
                    c.log(f"[CM Debug @ 550 in sources.py] x = repr(x) = {repr(x)} with name = {x.getName()} and is_alive is {x.is_alive()}")
                    if x.is_alive() is True:
                        if x.getName() in mainsourceDict:
                            mainleft.append(sourcelabelDict[x.getName()])
                        else:
                            info.append(sourcelabelDict[x.getName()])

                #if (i / 2) < timeout: # --> for i in range(0, timeout) - cm - huh?
                if (time.time() - start_time) < (timeout / 2):
                    try:
                        if i >= timeout and len(mainleft) == 0 and len(self.sources) >= 100 * len(info):
                            break # improve responsiveness
                        if len(self.sources) > int(limit_results):
                            break
                        if debrid_status:
                            if quality == 0:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format)) % (string6, d_4k_label, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format)) % (string7, source_4k_label, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                    print (line1 + '\n' + line2)
                                    c.log(f"[CM Debug @ 599 in sources.py] msg = {line1}\n{line2}")
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[:-1]) % (source_4k_label, d_4k_label, source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label, d_sd_label)
                            elif quality == 1:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[1:])) % (string6, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[1:])) % (string7, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[1:]) % (source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label, d_total_label)
                            elif quality == 2:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[1:])) % (string6, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[1:])) % (string7, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[1:]) % (source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label, d_total_label)
                            elif quality == 3:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[2:])) % (string6, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[2:])) % (string7, source_720_label, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[2:]) % (source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label, d_total_label)
                            else:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[3:])) % (string6, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[3:])) % (string7, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[3:]) % (source_sd_label, d_sd_label, source_total_label, d_total_label)
                        else:
                            if quality == 0:
                                line1 = '|'.join(pdiag_format) % (source_4k_label, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                            elif quality == 1:
                                line1 = '|'.join(pdiag_format[1:]) % (source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                            elif quality == 2:
                                line1 = '|'.join(pdiag_format[1:]) % (source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                            elif quality == 3:
                                line1 = '|'.join(pdiag_format[2:]) % (source_720_label, source_sd_label, str(string4), source_total_label)
                            else:
                                line1 = '|'.join(pdiag_format[3:]) % (source_sd_label, str(string4), source_total_label)

                        if self.dev_mode:
                            string_dev= f'[COLOR lime]Devmode - Elapsed: {str(int(time.time() - start_time))} secs[/COLOR]'

                        if debrid_status:
                            if len(info) > 6:
                                info_message = string3 % (str(len(info)))
                                c.log(f"[CM Debug @ 666 in sources.py] len(info) = {len(info)}")
                            elif len(info) > 0:
                                info_message = string3 % (', '.join(info))
                            else:
                                break
                            progress = int(100 * float(i) / (2 * timeout) + 0.5)
                            if self.dev_mode:
                                progressDialog.update(max(1, progress), line1 + '\n' + line2 + '\n' + info_message + '\n' + string_dev)
                            else:
                                progressDialog.update(max(1, progress), line1 + '\n' + line2 + '\n' + info_message)
                        else:
                            if len(info) > 6:
                                info_message = string3 % (str(len(info)))
                                c.log(f"[CM Debug @ 679in sources.py] len(info) = {len(info)}")
                            elif len(info) > 0:
                                info_message = string3 % (', '.join(info))
                            else:
                                break
                            progress = int(100 * float(i) / (2 * timeout) + 0.5)
                            progressDialog.update(max(1, progress), line1 + '\n' + info_message)
                    except Exception as e:
                        c.log(f'[CM Debug @ 688 in sources.py]Exception Raised:{e}', 1)
                else:
                    try:
                        #@todo fix for double duty mainleft and info
                        mainleft = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() is True and x.getName() in mainsourceDict]
                        info = mainleft
                        if debrid_status:
                            if len(info) > 6:
                                line3 = f'Waiting for: {str(len(info))}'
                            elif len(info) > 0:
                                line3 = f"Waiting for:{', '.join(info)}"
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5) % 100
                            if not progressDialog == control.progressDialogBG:
                                progressDialog.update(max(1, percent), line1 + '\n' +  line2 + '\n' +  line3)
                            else:
                                progressDialog.update(max(1, percent), line1 + '\n' + line3)
                        else:
                            if len(info) > 6:
                                line2 = f"Waiting for: {str(len(info))}"
                            elif len(info) > 0:
                                line2 = f"Waiting for: {', '.join(info)}"
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5) % 100
                            progressDialog.update(max(1, percent), line1 + line2)
                    except Exception:
                        break

                time.sleep(0.5)
            except Exception:
                pass
        try:
            progressDialog.close()
        except Exception:
            pass

        self.sourcesFilter()
        end_time = time.time()
        c.log(f'Sources for "{title}" ({year}) took {str(int(end_time - start_time))} seconds')
        return self.sources











    def getSources2(self, title, year, imdb, tmdb, season, episode, tvshowtitle, premiered, quality='HD', timeout=30):

        """
        Retrieves and filters media sources for movies or TV episodes based on various criteria.

        This function initializes and updates a progress dialog, prepares media sources, and
        filters them according to genre, language, provider settings, and priority. It spawns
        threads to resolve movie or episode sources, updates the progress dialog with current
        status, and applies preemptive termination based on quality limits. The function
        returns a list of filtered media sources.

        Args:
            title (str): The title of the movie or TV show.
            year (str): The release year of the movie or TV show.
            imdb (str): The IMDb ID for the movie or TV show.
            tmdb (str): The TMDb ID for the movie or TV show.
            season (str): The season number for TV shows.
            episode (str): The episode number for TV shows.
            tvshowtitle (str): The title of the TV show (if applicable).
            premiered (str): The premiere date of the episode (if applicable).
            quality (str): The desired quality of the sources (default is 'HD').
            timeout (int): The time limit for resolving sources (default is 30).

        Returns:
            list: A list of resolved media source dictionaries.
        """
        start_time = time.time()
        progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
        progressDialog.create(control.addonInfo('name'), '')
        progressDialog.update(0)
        start_time = time.time()
        limit_results = control.setting('max.limit.sources') or 25





        #create tables if necessary
        self.prepareSources()

        sourceDict = self.sourceDict
        progressDialog.update(0, control.lang(32600))

        content = 'movie' if tvshowtitle is None else 'episode'
        if content == 'movie':
            sourceDict = [(i[0], i[1], getattr(i[1], 'movie', None)) for i in sourceDict]
            genres = trakt.getGenre('movie', 'imdb', imdb)
        else:
            sourceDict = [(i[0], i[1], getattr(i[1], 'tvshow', None)) for i in sourceDict]
            genres = trakt.getGenre('show', 'imdb', imdb)


        sourceDict = [(i[0], i[1], i[2]) for i in sourceDict if not hasattr(i[1], 'genre_filter') or not i[1].genre_filter or any(x in i[1].genre_filter for x in genres)]
        sourceDict = [(i[0], i[1]) for i in sourceDict if i[2] is not None]

        language = self.getLanguage()
        sourceDict = [(i[0], i[1], i[1].language) for i in sourceDict]
        sourceDict = [(i[0], i[1]) for i in sourceDict if any(x in i[2] for x in language)]



        try:
            sourceDict = [(i[0], i[1], control.setting('provider.' + i[0])) for i in sourceDict]
        except Exception:
            sourceDict = [(i[0], i[1], 'true') for i in sourceDict]
        sourceDict = [(i[0], i[1]) for i in sourceDict if i[2] != 'false']

        sourceDict = [(i[0], i[1], i[1].priority) for i in sourceDict]

        #random.shuffle(sourceDict)
        sourceDict = sorted(sourceDict, key=lambda i: i[2])


        #for i in sourceDict:
            #c.log(f"[CM Debug @ 459 in sources.py] i[0] = {i[0]}|i[1] = {type(i[1])}|i[2] = {type(i[2])} with val = {repr(i[2])}")

        threads = []

        if content == 'movie':
            title = self.getTitle(title)
            c.log(f"[CM Debug @ 465 in sources.py] title={title}")
            localtitle = self.getLocalTitle(title, imdb, tmdb, content)
            aliases = self.getAliasTitles(imdb, localtitle, content)
            for i in sourceDict:
                threads.append(workers.Thread(self.getMovieSource, title, localtitle, aliases, year, imdb, i[0], i[1]))
        else:
            tvshowtitle = self.getTitle(tvshowtitle)
            localtvshowtitle = self.getLocalTitle(tvshowtitle, imdb, tmdb, content)
            aliases = self.getAliasTitles(imdb, localtvshowtitle, content)

            for i in sourceDict:
                threads.append(workers.Thread(self.getEpisodeSource, title, year, imdb, tmdb, season, episode, tvshowtitle, localtvshowtitle, aliases, premiered, i[0], i[1]))


        s = [i[0] + (i[1],) for i in zip(sourceDict, threads)]
        s = [(i[3].getName(), i[0], i[2]) for i in s]

        mainsourceDict = [i[0] for i in s if i[2] == 0]
        c.log(f"[CM Debug @ 482 in sources.py] mainsourceDict = {mainsourceDict}")
        sourcelabelDict = dict([(i[0], i[1].upper()) for i in s])

        #[i.start() for i in threads]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        #[i.join() for i in threads]

        string1 = control.lang(32404)
        string2 = control.lang(32405)
        string3 = control.lang(32406)
        string4 = control.lang(32601)
        string5 = control.lang(32602)
        string6 = control.lang(32606)
        string7 = control.lang(32607)

        #cm changfed 18-11-2024
        timeout = int(control.setting('scrapers.timeout.1')) or 30

        #fixed oh 27-4-2021
        quality = int(control.setting('hosts.quality')) or 0
        debrid_only = control.setting('debrid.only') or 'false'

        line1 = line2 = line3 = ""

        pre_emp =  control.setting('preemptive.termination')
        pre_emp_limit = int(control.setting('preemptive.limit'))
        source_4k = d_source_4k = 0
        source_1080 = d_source_1080 = 0
        source_720 = d_source_720 = 0
        source_sd = d_source_sd = 0
        total = debrid_total = 0

        debrid_resolvers = debrid.debrid_resolvers
        debrid_status = debrid.status()

        total_format = '[COLOR %s][B]%s[/B][/COLOR]'
        pdiag_format = ' 4K: %s | 1080p: %s | 720p: %s | SD: %s | %s: %s'.split('|')
        pdiag_bg_format = '4K:%s(%s)|1080p:%s(%s)|720p:%s(%s)|SD:%s(%s)|T:%s(%s)'.split('|')

        #for i in range(0, 4 * timeout): #max 120
        for i in range(0, 2 * timeout): #max 120
            if str(pre_emp) == 'true':
                if quality in [0, 1]:
                    if (source_4k + d_source_4k) >= int(pre_emp_limit):
                        break
                elif quality == 1:
                    if (source_1080 + d_source_1080) >= int(pre_emp_limit):
                        break
                elif quality == 2:
                    if (source_720 + d_source_720) >= int(pre_emp_limit):
                        break
                elif quality == 3:
                    if (source_sd + d_source_sd) >= int(pre_emp_limit):
                        break
                else:
                    if (source_sd + d_source_sd) >= int(pre_emp_limit):
                        break
            try:
                if control.monitor.abortRequested():
                    return sys.exit()

                try:
                    if progressDialog.iscanceled():
                        break
                except Exception:
                    pass

                #c.log(f"[CM Debug @ 545 in sources.py] debrid_status = {debrid_status}")
                d_4k_label = d_1080_label = d_720_label = d_sd_label = total_format = d_total_label = ''

                if len(self.sources) > 0:
                    source_counts = {
                        '4K': len([e for e in self.sources if e['quality'].upper() == '4K' and e['debridonly'] is False]),
                        '1080p': len([e for e in self.sources if e['quality'] in ['1440p','1080p'] and e['debridonly'] is False]),
                        '720p': len([e for e in self.sources if e['quality'] in ['720p','HD'] and e['debridonly'] is False]),
                        'SD': len([e for e in self.sources if e['quality'].upper() == 'SD' and e['debridonly'] is False]),
                    }
                    total = sum(source_counts.values())
                    if debrid_status:
                        debrid_source_counts = {
                            '4K': sum([len([e for e in self.sources if e['quality'].upper() == '4K' and d.valid_url(e['url'], e['source'])]) for d in debrid_resolvers]),
                            '1080p': sum([len([e for e in self.sources if e['quality'] in ['1440p','1080p'] and d.valid_url(e['url'], e['source'])]) for d in debrid_resolvers]),
                            '720p': sum([len([e for e in self.sources if e['quality'] in ['720p','HD'] and d.valid_url(e['url'], e['source'])]) for d in debrid_resolvers]),
                            'SD': sum([len([e for e in self.sources if e['quality'].upper() == 'SD' and d.valid_url(e['url'], e['source'])]) for d in debrid_resolvers]),
                        }
                        debrid_total = sum(debrid_source_counts.values())

                    pdiag_list = [source_counts['4K'], source_counts['1080p'], source_counts['720p'], source_counts['SD'], total]
                    pdiag_list_debrid = [debrid_source_counts['4K'], debrid_source_counts['1080p'], debrid_source_counts['720p'], debrid_source_counts['SD'], debrid_total]
                    #c.log(f"[CM Debug @ 566 in sources.py] pdiag_list_debrid = {pdiag_list_debrid}")

                    if debrid_status:
                        d_4k_label = total_format % ('red', pdiag_list_debrid[0]) if pdiag_list_debrid[0] == 0 else total_format % ('lime', pdiag_list_debrid[0])
                        d_1080_label = total_format % ('red', pdiag_list_debrid[1]) if pdiag_list_debrid[1] == 0 else total_format % ('lime', pdiag_list_debrid[1])
                        d_720_label = total_format % ('red', pdiag_list_debrid[2]) if pdiag_list_debrid[2] == 0 else total_format % ('lime', pdiag_list_debrid[2])
                        d_sd_label = total_format % ('red', pdiag_list_debrid[3]) if pdiag_list_debrid[3] == 0 else total_format % ('lime', pdiag_list_debrid[3])
                        d_total_label = total_format % ('red', pdiag_list_debrid[4]) if pdiag_list_debrid[4] == 0 else total_format % ('lime', pdiag_list_debrid[4])
                    source_4k_label = total_format % ('red', pdiag_list[0]) if pdiag_list[0] == 0 else total_format % ('lime', pdiag_list[0])
                    source_1080_label = total_format % ('red', pdiag_list[1]) if pdiag_list[1] == 0 else total_format % ('lime', pdiag_list[1])
                    source_720_label = total_format % ('red', pdiag_list[2]) if pdiag_list[2] == 0 else total_format % ('lime', pdiag_list[2])
                    source_sd_label = total_format % ('red', pdiag_list[3]) if pdiag_list[3] == 0 else total_format % ('lime', pdiag_list[3])
                    source_total_label = total_format % ('red', pdiag_list[4]) if pdiag_list[4] == 0 else total_format % ('lime', pdiag_list[4])

                mainleft = info = []
                for x in threads:
                    #c.log(f"[CM Debug @ 587 in sources.py] x = repr(x) = {repr(x)} with name = {x.getName()} and is_alive is {x.is_alive()}")
                    if x.is_alive() is True:
                        if x.getName() in mainsourceDict:
                            mainleft.append(sourcelabelDict[x.getName()])
                        else:
                            info.append(sourcelabelDict[x.getName()])

                if (i / 2) < timeout:
                    try:
                        if i >= timeout and len(mainleft) == 0 and len(self.sources) >= 100 * len(info):
                            break # improve responsiveness
                        if len(self.sources) > int(limit_results):
                            break
                        if debrid_status:
                            if quality == 0:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format)) % (string6, d_4k_label, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format)) % (string7, source_4k_label, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                    print (line1 + '\n' + line2)
                                    c.log(f"[CM Debug @ 599 in sources.py] msg = {line1}\n{line2}")
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[:-1]) % (source_4k_label, d_4k_label, source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label, d_sd_label)
                            elif quality == 1:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[1:])) % (string6, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[1:])) % (string7, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[1:]) % (source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label, d_total_label)
                            elif quality == 2:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[1:])) % (string6, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[1:])) % (string7, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[1:]) % (source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label, d_total_label)
                            elif quality == 3:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[2:])) % (string6, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[2:])) % (string7, source_720_label, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[2:]) % (source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label, d_total_label)
                            else:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[3:])) % (string6, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[3:])) % (string7, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[3:]) % (source_sd_label, d_sd_label, source_total_label, d_total_label)
                        else:
                            if quality == 0:
                                line1 = '|'.join(pdiag_format) % (source_4k_label, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                            elif quality == 1:
                                line1 = '|'.join(pdiag_format[1:]) % (source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                            elif quality == 2:
                                line1 = '|'.join(pdiag_format[1:]) % (source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                            elif quality == 3:
                                line1 = '|'.join(pdiag_format[2:]) % (source_720_label, source_sd_label, str(string4), source_total_label)
                            else:
                                line1 = '|'.join(pdiag_format[3:]) % (source_sd_label, str(string4), source_total_label)

                        if self.dev_mode:
                            string_dev= f'[COLOR lime]Devmode - Elapsed: {str(int(time.time() - start_time))} secs[/COLOR]'

                        if debrid_status:
                            if len(info) > 6:
                                info_message = string3 % (str(len(info)))
                                c.log(f"[CM Debug @ 666 in sources.py] len(info) = {len(info)}")
                            elif len(info) > 0:
                                info_message = string3 % (', '.join(info))
                            else:
                                break
                            progress = int(100 * float(i) / (2 * timeout) + 0.5)
                            if self.dev_mode:
                                progressDialog.update(max(1, progress), line1 + '\n' + line2 + '\n' + info_message + '\n' + string_dev)
                            else:
                                progressDialog.update(max(1, progress), line1 + '\n' + line2 + '\n' + info_message)
                        else:
                            if len(info) > 6:
                                info_message = string3 % (str(len(info)))
                                c.log(f"[CM Debug @ 679in sources.py] len(info) = {len(info)}")
                            elif len(info) > 0:
                                info_message = string3 % (', '.join(info))
                            else:
                                break
                            progress = int(100 * float(i) / (2 * timeout) + 0.5)
                            progressDialog.update(max(1, progress), line1 + '\n' + info_message)
                    except Exception as e:
                        c.log(f'[CM Debug @ 688 in sources.py]Exception Raised:{e}', 1)
                else:
                    try:
                        #@todo fix for double duty mainleft and info
                        mainleft = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() is True and x.getName() in mainsourceDict]
                        info = mainleft
                        if debrid_status:
                            if len(info) > 6:
                                line3 = f'Waiting for: {str(len(info))}'
                            elif len(info) > 0:
                                line3 = f"Waiting for:{', '.join(info)}"
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5) % 100
                            if not progressDialog == control.progressDialogBG:
                                progressDialog.update(max(1, percent), line1 + '\n' +  line2 + '\n' +  line3)
                            else:
                                progressDialog.update(max(1, percent), line1 + '\n' + line3)
                        else:
                            if len(info) > 6:
                                line2 = f'Waiting for: {str(len(info))}'
                            elif len(info) > 0:
                                line2 = f"Waiting for: {', '.join(info)}"
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5) % 100
                            progressDialog.update(max(1, percent), line1 + line2)
                    except Exception:
                        break

                time.sleep(0.5)
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 1018 in sources.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 1018 in sources.py]Exception raised. Error = {e}')
                pass
        try:
            progressDialog.close()

        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 1027 in sources.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 1027 in sources.py]Exception raised. Error = {e}')
            pass


        self.sourcesFilter()
        end_time = time.time()
        c.log(f'Sources for "{title}" ({year}) took {str(int(end_time - start_time))} seconds')
        return self.sources



    def getSources(self, title, year, imdb, tmdb, season, episode, tvshowtitle, premiered, quality='HD', timeout=30):

        progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
        progressDialog.create(control.addonInfo('name'), '')
        progressDialog.update(0)

        self.prepareSources()

        sourceDict = self.sourceDict

        progressDialog.update(0, control.lang(32600))

        content = 'movie' if tvshowtitle is None else 'episode'
        if content == 'movie':
            sourceDict = [(i[0], i[1], getattr(i[1], 'movie', None)) for i in sourceDict]
            genres = trakt.getGenre('movie', 'imdb', imdb)
        else:
            sourceDict = [(i[0], i[1], getattr(i[1], 'tvshow', None)) for i in sourceDict]
            genres = trakt.getGenre('show', 'imdb', imdb)

        sourceDict = [(i[0], i[1], i[2]) for i in sourceDict if not hasattr(i[1], 'genre_filter') or not i[1].genre_filter or any(x in i[1].genre_filter for x in genres)]
        sourceDict = [(i[0], i[1]) for i in sourceDict if i[2] is not None]

        language = self.getLanguage()
        sourceDict = [(i[0], i[1], i[1].language) for i in sourceDict]
        sourceDict = [(i[0], i[1]) for i in sourceDict if any(x in i[2] for x in language)]

        try:
            sourceDict = [(i[0], i[1], control.setting('provider.' + i[0])) for i in sourceDict]
        except Exception:
            sourceDict = [(i[0], i[1], 'true') for i in sourceDict]
        sourceDict = [(i[0], i[1]) for i in sourceDict if not i[2] == 'false']

        sourceDict = [(i[0], i[1], i[1].priority) for i in sourceDict]

        random.shuffle(sourceDict)
        sourceDict = sorted(sourceDict, key=lambda i: i[2])

        threads = []

        if content == 'movie':
            title = self.getTitle(title)
            localtitle = self.getLocalTitle(title, imdb, tmdb, content)
            aliases = self.getAliasTitles(imdb, localtitle, content)
            for i in sourceDict:
                threads.append(workers.Thread(self.getMovieSource, title, localtitle, aliases, year, imdb, i[0], i[1]))
        else:
            tvshowtitle = self.getTitle(tvshowtitle)
            localtvshowtitle = self.getLocalTitle(tvshowtitle, imdb, tmdb, content)
            aliases = self.getAliasTitles(imdb, localtvshowtitle, content)

            for i in sourceDict:
                threads.append(workers.Thread(self.getEpisodeSource, title, year, imdb, tmdb, season, episode, tvshowtitle, localtvshowtitle, aliases, premiered, i[0], i[1]))


        s = [i[0] + (i[1],) for i in zip(sourceDict, threads)]
        s = [(i[3].getName(), i[0], i[2]) for i in s]

        mainsourceDict = [i[0] for i in s if i[2] == 0]
        sourcelabelDict = dict([(i[0], i[1].upper()) for i in s])

        [i.start() for i in threads]

        string1 = control.lang(32404)
        string2 = control.lang(32405)
        string3 = control.lang(32406)
        string4 = control.lang(32601)
        string5 = control.lang(32602)
        string6 = control.lang(32606)
        string7 = control.lang(32607)

        try:
            timeout = int(control.setting('scrapers.timeout.1'))
            c.log(f"[CM Debug @ 1127 in sources.py] timeout = {timeout}")
        except Exception:
            pass

        #fixed oh 27-4-2021
        quality = int(control.setting('hosts.quality')) or 0
        debrid_only = control.setting('debrid.only') or 'false'

        line1 = line2 = line3 = ""

        pre_emp =  control.setting('preemptive.termination')
        pre_emp_limit = int(control.setting('preemptive.limit'))
        source_4k = d_source_4k = 0
        source_1080 = d_source_1080 = 0
        source_720 = d_source_720 = 0
        source_sd = d_source_sd = 0
        total = d_total = 0

        debrid_list = debrid.debrid_resolvers
        debrid_status = debrid.status()

        total_format = '[COLOR %s][B]%s[/B][/COLOR]'
        pdiag_format = ' 4K: %s | 1080p: %s | 720p: %s | SD: %s | %s: %s'.split('|')
        pdiag_bg_format = '4K:%s(%s)|1080p:%s(%s)|720p:%s(%s)|SD:%s(%s)|T:%s(%s)'.split('|')

        for i in range(0, 4 * timeout):
            if str(pre_emp) == 'true':
                if quality in [0, 1]:
                    if (source_4k + d_source_4k) >= int(pre_emp_limit):
                        break
                elif quality == 1:
                    if (source_1080 + d_source_1080) >= int(pre_emp_limit):
                        break
                elif quality == 2:
                    if (source_720 + d_source_720) >= int(pre_emp_limit):
                        break
                elif quality == 3:
                    if (source_sd + d_source_sd) >= int(pre_emp_limit):
                        break
                else:
                    if (source_sd + d_source_sd) >= int(pre_emp_limit):
                        break
            try:
                if control.monitor.abortRequested():
                    return sys.exit()

                try:
                    if progressDialog.iscanceled():
                        break
                except Exception:
                    pass

                #for e in self.sources:
                    #c.log(f"[CM Debug @ 1180 in sources.py] e = {repr(e)}")

                if len(self.sources) > 0:
                    if quality == 0:
                        source_4k = len([e for e in self.sources if e['quality'] == '4K' and e['debridonly'] is False])
                        source_1080 = len([e for e in self.sources if e['quality'] in ['1440p','1080p'] and e['debridonly'] is False])
                        source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and e['debridonly'] is False])
                        source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] is False])
                    elif quality == 1:
                        source_1080 = len([e for e in self.sources if e['quality'] in ['1440p','1080p'] and e['debridonly'] is False])
                        source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and e['debridonly'] is False])
                        source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] is False])
                    elif quality == 2:
                        source_1080 = len([e for e in self.sources if e['quality'] in ['1080p'] and e['debridonly'] is False])
                        source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and e['debridonly'] is False])
                        source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] is False])
                    elif quality == 3:
                        source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and e['debridonly'] is False])
                        source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] is False])
                    else:
                        source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] is False])

                    total = source_4k + source_1080 + source_720 + source_sd

                    if debrid_status:
                        if quality == 0:
                            for d in debrid_list:
                                d_source_4k = len([e for e in self.sources if e['quality'] in ['4k', '4K'] and d.valid_url(e['url'], e['source'])])
                                d_source_1080 = len([e for e in self.sources if e['quality'] in ['1440p','1080p'] and d.valid_url(e['url'], e['source'])])
                                d_source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and d.valid_url(e['url'], e['source'])])
                                d_source_sd = len([e for e in self.sources if e['quality'] in ['sd', 'SD'] and d.valid_url(e['url'], e['source'])])
                        elif quality == 1:
                            for d in debrid_list:
                                d_source_1080 = len([e for e in self.sources if e['quality'] in ['1440p','1080p'] and d.valid_url(e['url'], e['source'])])
                                d_source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and d.valid_url(e['url'], e['source'])])
                                d_source_sd = len([e for e in self.sources if e['quality'] == 'SD' and d.valid_url(e['url'], e['source'])])
                        elif quality == 2:
                            for d in debrid_list:
                                d_source_1080 = len([e for e in self.sources if e['quality'] in ['1080p'] and d.valid_url(e['url'], e['source'])])
                                d_source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and d.valid_url(e['url'], e['source'])])
                                d_source_sd = len([e for e in self.sources if e['quality'] == 'SD' and d.valid_url(e['url'], e['source'])])
                        elif quality == 3:
                            for d in debrid_list:
                                d_source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and d.valid_url(e['url'], e['source'])])
                                d_source_sd = len([e for e in self.sources if e['quality'] == 'SD' and d.valid_url(e['url'], e['source'])])
                        else:
                            for d in debrid_list:
                                d_source_sd = len([e for e in self.sources if e['quality'] == 'SD' and d.valid_url(e['url'], e['source'])])

                        d_total = d_source_4k + d_source_1080 + d_source_720 + d_source_sd

                    if debrid_status:
                        d_4k_label = total_format % ('red', d_source_4k) if d_source_4k == 0 else total_format % ('lime', d_source_4k)
                        d_1080_label = total_format % ('red', d_source_1080) if d_source_1080 == 0 else total_format % ('lime', d_source_1080)
                        d_720_label = total_format % ('red', d_source_720) if d_source_720 == 0 else total_format % ('lime', d_source_720)
                        d_sd_label = total_format % ('red', d_source_sd) if d_source_sd == 0 else total_format % ('lime', d_source_sd)
                        d_total_label = total_format % ('red', d_total) if d_total == 0 else total_format % ('lime', d_total)
                    source_4k_label = total_format % ('red', source_4k) if source_4k == 0 else total_format % ('lime', source_4k)
                    source_1080_label = total_format % ('red', source_1080) if source_1080 == 0 else total_format % ('lime', source_1080)
                    source_720_label = total_format % ('red', source_720) if source_720 == 0 else total_format % ('lime', source_720)
                    source_sd_label = total_format % ('red', source_sd) if source_sd == 0 else total_format % ('lime', source_sd)
                    source_total_label = total_format % ('red', total) if total == 0 else total_format % ('lime', total)


                if (i / 2) < timeout:
                    try:
                        mainleft = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() is True and x.getName() in mainsourceDict]
                        info = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() is True]
                        #if i >= timeout and len(mainleft) == 0 and len(self.sources) >= 100 * len(info):
                        if i >= timeout and len(mainleft) == 0 and len(self.sources) >= 100 * len(info):
                            break # improve responsiveness
                        if debrid_status:
                            if quality == 0:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format)) % (string6, d_4k_label, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format)) % (string7, source_4k_label, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                    print (line1 + '\n' + line2)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[:-1]) % (source_4k_label, d_4k_label, source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label, d_sd_label)
                            elif quality == 1:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[1:])) % (string6, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[1:])) % (string7, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[1:]) % (source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label, d_total_label)
                            elif quality == 2:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[1:])) % (string6, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[1:])) % (string7, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[1:]) % (source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label, d_total_label)
                            elif quality == 3:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[2:])) % (string6, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[2:])) % (string7, source_720_label, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[2:]) % (source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label, d_total_label)
                            else:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[3:])) % (string6, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[3:])) % (string7, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[3:]) % (source_sd_label, d_sd_label, source_total_label, d_total_label)
                        else:
                            if quality == 0:
                                line1 = '|'.join(pdiag_format) % (source_4k_label, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                            elif quality == 1:
                                line1 = '|'.join(pdiag_format[1:]) % (source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                            elif quality == 2:
                                line1 = '|'.join(pdiag_format[1:]) % (source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                            elif quality == 3:
                                line1 = '|'.join(pdiag_format[2:]) % (source_720_label, source_sd_label, str(string4), source_total_label)
                            else:
                                line1 = '|'.join(pdiag_format[3:]) % (source_sd_label, str(string4), source_total_label)

                        if debrid_status:
                            if len(info) > 6:
                                line3 = string3 % (str(len(info)))
                            elif len(info) > 0:
                                line3 = string3 % (', '.join(info))
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5)
                            if not progressDialog == control.progressDialogBG:
                                progressDialog.update(max(1, percent), line1 +'\n' + line2 +'\n' + line3)
                            else:
                                progressDialog.update(max(1, percent), line1 + '\n' + line3)
                        else:
                            if len(info) > 6:
                                line2 = string3 % (str(len(info)))
                            elif len(info) > 0:
                                line2 = string3 % (', '.join(info))
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5)
                            progressDialog.update(max(1, percent), line1 + '\n' + line2)
                    except Exception as e:
                        c.log(f'Exception Raised: {e}', 1)
                else:
                    try:
                        #@todo fix for double duty mainleft and info
                        mainleft = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() is True and x.getName() in mainsourceDict]
                        info = mainleft
                        if debrid_status:
                            if len(info) > 6:
                                line3 = 'Waiting for: %s' % (str(len(info)))
                            elif len(info) > 0:
                                line3 = 'Waiting for: %s' % (', '.join(info))
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5) % 100
                            if not progressDialog == control.progressDialogBG:
                                progressDialog.update(max(1, percent), line1 + '\n' +  line2 + '\n' +  line3)
                            else:
                                progressDialog.update(max(1, percent), line1 + '\n' + line3)
                        else:
                            if len(info) > 6:
                                line2 = 'Waiting for: %s' % (str(len(info)))
                            elif len(info) > 0:
                                line2 = 'Waiting for: %s' % (', '.join(info))
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5) % 100
                            progressDialog.update(max(1, percent), line1 + line2)
                    except Exception:
                        break

                time.sleep(0.5)
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 1349 in sources.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 1349 in sources.py]Exception raised. Error = {e}')

        try:
            progressDialog.close()
        except Exception as e:
            c.log(f"[CM Debug @ 1355 in sources.py] exception raised. Error = {e}")


        self.sourcesFilter()

        return self.sources

    #checked OH - 26-04-2021
    def prepareSources(self):
        try:
            control.makeFile(control.dataPath)

            self.sourceFile = control.providercacheFile

            dbcon = database.connect(self.sourceFile)
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
            #dbcur.execute("CREATE TABLE IF NOT EXISTS rel_url (""source TEXT, ""imdb_id TEXT, ""season TEXT, ""episode TEXT, ""rel_url TEXT, UNIQUE(source, imdb_id, season, episode));")
            #dbcur.execute("CREATE TABLE IF NOT EXISTS rel_src (""source TEXT, ""imdb_id TEXT, ""season TEXT, ""episode TEXT, ""hosts TEXT, ""added TEXT, UNIQUE(source, imdb_id, season, episode));")

        except Exception as e:
            c.log(f"[CM Debug @ 1069 in sources.py] Exception raised: {e}", 1)
            pass

    def getMovieSource(self, title, localtitle, aliases, year, imdb, source, call):
        try:
            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
        except Exception:
            pass

        #Fix to stop items passed with a 0 IMDB id pulling old unrelated sources from the database.
        if imdb == '0':
            try:
                dbcur.execute("DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
                dbcur.execute("DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
                dbcon.commit()
            except Exception:
                pass
        #END

        try:
            sources = []
            dbcur.execute("SELECT * FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            match = dbcur.fetchone()
            t1 = int(re.sub('[^0-9]', '', str(match[5])))
            t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            update = abs(t2 - t1) > 60
            if update is False:
                sources = eval(c.ensure_str(match[4]))
                #c.log(f"[CM Debug @ 1087 in sources.py] sources = {repr(sources)}")
                return self.sources.extend(sources)
        except Exception:
            pass

        try:
            url = None
            dbcur.execute("SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            url = dbcur.fetchone()
            url = eval(c.ensure_str(url[4]))
        except Exception:
            pass

        try:
            if url is None:
                url = call.movie(imdb, title, localtitle, aliases, year)
            if url is None:
                raise Exception()
            dbcur.execute("DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, '', '', repr(url)))
            dbcon.commit()
        except Exception:
            pass

        try:
            sources = []
            sources = call.sources(url, self.hostDict, self.hostprDict)
            if sources is None or sources == []:
                raise Exception()
            sources = [json.loads(t) for t in set(json.dumps(d, sort_keys=True) for d in sources)]
            for i in sources:
                i.update({'provider': source})
            self.sources.extend(sources)
            dbcur.execute("DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            dbcur.execute("INSERT INTO rel_src Values (?, ?, ?, ?, ?, ?)", (source, imdb, '', '', repr(sources), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
            dbcon.commit()
        except Exception:
            pass

    def getEpisodeSource(self, title, year, imdb, tmdb, season, episode, tvshowtitle, localtvshowtitle, aliases, premiered, source, call):
        try:
            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
        except Exception:
            pass

        try:
            sources = []
            dbcur.execute("SELECT * FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode))
            match = dbcur.fetchone()
            t1 = int(re.sub('[^0-9]', '', str(match[5])))
            t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            update = abs(t2 - t1) > 60
            if update is False:
                sources = eval(c.ensure_str(match[4]))
                return self.sources.extend(sources)
        except Exception:
            pass

        try:
            url = None
            query = "SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', '')
            dbcur.execute(query)
            url = dbcur.fetchone()
            url = eval(c.ensure_str(url[4]))
        except Exception:
            pass

        try:
            if url is None:
                url = call.tvshow(imdb, tmdb, tvshowtitle, localtvshowtitle, aliases, year)
            if url is None:
                raise Exception()
            dbcur.execute(
                "DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, '', '', repr(url)))
            dbcon.commit()
        except Exception:
            pass

        try:
            ep_url = None
            query = "SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode)
            dbcur.execute(query)
            ep_url = dbcur.fetchone()
            ep_url = eval(c.ensure_str(ep_url[4]))
        except Exception:
            pass

        try:
            if url is None:
                raise Exception()
            if ep_url is None:
                ep_url = call.episode(url, imdb, tmdb, title, premiered, season, episode)
            if ep_url is None:
                raise Exception()
            dbcur.execute("DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode))
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, season, episode, repr(ep_url)))
            dbcon.commit()
        except Exception:
            pass

        try:
            sources = []
            sources = call.sources(ep_url, self.hostDict, self.hostprDict)
            if sources is None or sources == []:
                raise Exception()
            sources = [json.loads(t) for t in set(json.dumps(d, sort_keys=True) for d in sources)]
            for i in sources: i.update({'provider': source})
            self.sources.extend(sources)
            dbcur.execute("DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode))
            dbcur.execute("INSERT INTO rel_src Values (?, ?, ?, ?, ?, ?)", (source, imdb, season, episode, repr(sources), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
            dbcon.commit()
        except Exception:
            pass

    def alterSources(self, url, meta):
        try:
            if control.setting('hosts.mode') == '2':
                url += '&select=1'
            else:
                url += '&select=2'
            control.execute('RunPlugin(%s)' % url)
        except Exception:
            pass

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

    def uniqueSourcesGen(self, sources):
        uniqueURLs = set()
        for source in sources:
            url = source.get('url')
            if isinstance(url, six.string_types):
                if 'magnet:' in url:
                    url = url[:60]
                    #url = re.findall(u'btih:(\w{40})', url)[0]
                if url not in uniqueURLs:
                    uniqueURLs.add(url)
                    yield source # Yield the unique source.
                else:
                    pass # Ignore duped sources.
            else:
                yield source # Always yield non-string url sources.

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
            self.sources = list(self.uniqueSourcesGen(self.sources))
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

        filtered_sources = local_sources

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
                self.sources = list(self.uniqueSourcesGen(self.sources))
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

        filter = []
        filter += local

        if quality == 0:
            filter += [i for i in self.sources if i['quality'] in ['4k', '4K'] and 'debrid' in i]
            filter += [i for i in self.sources if i['quality'] in ['4k', '4k'] and 'debrid' not in i and 'memberonly' in i]
            filter += [i for i in self.sources if i['quality'] in ['4k', '4k'] and 'debrid' not in i and 'memberonly' not in i]

        if quality <= 1:
            filter += [i for i in self.sources if i['quality'] in ['1440p','1440P'] and 'debrid' in i]
            filter += [i for i in self.sources if i['quality'] in ['1440p','1440P'] and 'debrid' not in i and 'memberonly' in i]
            filter += [i for i in self.sources if i['quality'] in ['1440p','1440P'] and 'debrid' not in i and 'memberonly' not in i]


        if quality <= 2:
            filter += [i for i in self.sources if i['quality'] in ['1080p', '1080P'] and 'debrid' in i]
            filter += [i for i in self.sources if i['quality'] in ['1080p', '1080P'] and 'debrid' not in i and 'memberonly' in i]
            filter += [i for i in self.sources if i['quality'] in ['1080p', '1080P'] and 'debrid' not in i and 'memberonly' not in i]


        if quality <= 3:
            filter += [i for i in self.sources if i['quality'] in ['720p', '720P'] and 'debrid' in i]
            filter += [i for i in self.sources if i['quality'] in ['720p', '720P'] and 'debrid' not in i and 'memberonly' in i]
            filter += [i for i in self.sources if i['quality'] in ['720p', '720P'] and 'debrid' not in i and 'memberonly' not in i]
            filter += [i for i in self.sources if i['quality'] in ['sd', 'SD'] and 'debrid' in i]

        if quality <= 4:
            filter += [i for i in self.sources if i['quality'] in ['sd', 'SD'] and 'debrid' in i]

        if show_cams == 'true':
            filter += [i for i in self.sources if i['quality'] in ['scr', 'cam', 'SCR', 'CAM']]

        self.sources = filter

        if not captcha == 'true':
            filter = [i for i in self.sources if i['source'].lower() in self.hostcapDict and 'debrid' not in i]
            self.sources = [i for i in self.sources if i not in filter]

        filter = [i for i in self.sources if i['source'].lower() in self.hostblockDict and 'debrid' not in i]

        multi = [i['language'] for i in self.sources]
        multi = [x for y, x in enumerate(multi) if x not in multi[:y]]
        multi = True if len(multi) > 1 else False

        if multi is True:
            self.sources = [i for i in self.sources if not i['language'] == 'en'] + [i for i in self.sources if i['language'] == 'en']

        self.sources = self.sources[:int(control.setting('returned.sources'))]
        #self.sources = self.sources[:4000] - OH 04/28/21 keeping for reference

        extra_info = control.setting('sources.extrainfo')
        prem_identify = control.setting('prem.identify') or 'blue'
        torr_identify = control.setting('torrent.identify') or 'cyan'

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
                label = f'{int(i)+1:02d} | {d} | {q} | {p} | '
            else:
                #label = '%02d | %s | %s | ' % (int(i+1), q, p)
                label = f'{int(i)+1:02d} | {q} | {p} | '

            if multi is True and not l != 'en':
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
            #if url is None or (not '://' in str(url) and not local and 'magnet:' not in str(url)): raise Exception()
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
            c.log(f'Error {e}', 1)

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
