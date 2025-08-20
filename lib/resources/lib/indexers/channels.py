# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file channels.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''
import sys
import re
import datetime
import json

from urllib.parse import parse_qsl, quote_plus

from ..modules import cleangenre
from ..modules import control
from ..modules import client
from ..modules import metacache
from ..modules import workers
from ..modules import trakt
from ..modules.crewruntime import c



params = dict(parse_qsl(sys.argv[2].replace('?',''))) if len(sys.argv) > 1 else dict()

action = params.get('action')

class channels:
    def __init__(self):
        self.list = []
        self.items = []

        self.uk_datetime = self.get_uk_datetime()
        self.systime = (self.uk_datetime).strftime('%Y%m%d%H%M%S%f')
        self.tm_img_link = 'https://image.tmdb.org/t/p/w%s%s'
        self.lang = control.apiLanguage()['trakt']

        self.sky_now_link = 'https://epgservices.sky.com/5.1.1/api/2.0/channel/json/%s/now/nn/3'
        self.sky_programme_link = 'https://tv.sky.com/programme/channel/%s/%s/%s.json'


    def get(self):
        channels = [
            ('01', 'Sky Premiere', '4021'),
            ('02', 'Sky Premiere +1', '1823'),
            ('03', 'Sky Hits', '4033'),
            ('04', 'Sky Greats', '4015'),
            ('05', 'Sky Disney', '4013'),
            ('06', 'Sky Family', '4018'),
            ('07', 'Sky Action', '4014'),
            ('08', 'Sky Comedy', '4019'),
            ('09', 'Sky Thriller', '4062'),
            ('10', 'Sky Drama', '4016'),
            ('11', 'Sky SciFi/Horror', '4017'),
            ('12', 'Sky Select', '4020'),
            ('13', 'Film4', '4044'),
            ('14', 'Film4 +1', '1629'),
            ('15', 'TCM', '3811'),
            ('16', 'TCM +1', '5275'),
        ]

        threads = []
        for i in channels:
            threads.append(workers.Thread(self.sky_list, i[0], i[1], i[2]))
        [i.start() for i in threads]
        [i.join() for i in threads]

        threads = []
        threads = [workers.Thread(self.items_list, item) for item in self.items]

        [i.start() for i in threads]
        [i.join() for i in threads]

        self.list = metacache.local(self.list, self.tm_img_link, 'poster2', 'fanart')

        try:
            self.list = sorted(self.list, key=lambda k: k['num'])
        except:
            pass

        self.channelDirectory(self.list)
        return self.list


    def sky_list(self, num, channel, id):
        try:
            url = self.sky_now_link % id
            result = client.request(url, timeout='10')
            result = json.loads(result)

            try:
                year = result['listings'][id][0]['d']
                year = re.findall('[(](\d{4})[)]', year)[0].strip()
                year = str(year)
            except:
                year = ''

            title = result['listings'][id][0]['t']
            title = title.replace(f'({year})', '').strip()
            title = client.replaceHTMLCodes(title)
            title = str(title)

            self.items.append((title, year, channel, num))
        except:
            pass


    def items_list(self, i):
        try:
            search_results = trakt.SearchAll(i[0], i[1], True)
            if search_results is not None and len(search_results) > 0:
                item = search_results[0]
            else:
                return

            # Ensure item is a dict before calling get
            if isinstance(item, list) and len(item) > 0:
                item = item[0]
            if isinstance(item, str):
                # If item is a string, skip processing
                return
            if not isinstance(item, dict):
                return

            content = item.get('movie') if isinstance(item, dict) else None
            if not content:
                content = item.get('show') if isinstance(item, dict) else None
            item = content if content else item

            title = item.get('title') if isinstance(item, dict) else ''
            title = client.replaceHTMLCodes(title)

            originaltitle = title

            year = item.get('year', 0)
            year = re.sub('[^0-9]', '', str(year))

            imdb = item.get('ids', {}).get('imdb', '0')
            imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))

            tmdb = str(item.get('ids', {}).get('tmdb', 0))

            premiered = item.get('released', '0')
            try:
                premiered_str = str(premiered)
                premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(premiered_str)[0]
            except:
                premiered = '0'

            genre = item.get('genres', [])
            genre = [x.title() for x in genre]
            genre = ' / '.join(genre).strip()
            if not genre:
                genre = '0'

            duration = str(item.get('Runtime', 0))

            rating = str(item.get('rating', '0'))
            if rating == '0.0':
                rating = '0'

            votes = str(int(item.get('votes', 0)))
            votes = f'{int(votes):,}'

            mpaa = item.get('certification', '0')
            if not mpaa:
                mpaa = '0'

            tagline = item.get('tagline', '0')

            plot = item.get('overview', '0')

            people = trakt.getPeople(imdb, 'movies')

            director = writer = ''

            if people is not None:
                if isinstance(people, dict) and 'crew' in people and isinstance(people['crew'], dict) and 'directing' in people['crew']:
                    director = ', '.join([director['person']['name'] for director in people['crew']['directing'] if director['job'].lower() == 'director'])
                if isinstance(people, dict) and 'crew' in people and isinstance(people['crew'], dict) and 'writing' in people['crew']:
                    writer = ', '.join([writer['person']['name'] for writer in people['crew']['writing'] if writer['job'].lower() in ['writer', 'screenplay', 'author']])

                cast = []
                for person in people.get('cast', []):
                    cast.append({
                        'name': person.get('person', ''),
                        'role': person.get('role', '')
                        })
                cast = [(person['name'], person['role']) for person in cast]

            try:
                if self.lang == 'en' or self.lang not in item.get('available_translations', [self.lang]): raise Exception()

                trans_item = trakt.getMovieTranslation(imdb, self.lang, full=True)

                title = trans_item.get('title') or title
                tagline = trans_item.get('tagline') or tagline
                plot = trans_item.get('overview') or plot
            except:
                pass

            self.list.append({'title': title, 'originaltitle': originaltitle, 'year': year, 'premiered': premiered, 'genre': genre, 'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa, 'director': director, 'writer': writer, 'cast': cast, 'plot': plot, 'tagline': tagline, 'imdb': imdb, 'tmdb': tmdb, 'poster': '0', 'channel': i[2], 'num': i[3]})
        except:
            pass


    def get_uk_datetime(self):
        dt = datetime.datetime.utcnow()
        d = datetime.datetime(dt.year, 4, 1)
        dston = d - datetime.timedelta(days=d.weekday() + 1)
        d = datetime.datetime(dt.year, 11, 1)
        dstoff = d - datetime.timedelta(days=d.weekday() + 1)
        if dston <=  dt < dstoff:
            return dt + datetime.timedelta(hours = 1)
        else:
            return dt

#TC 2/01/19 started
    def channelDirectory(self, items):
        if items is None or len(items) == 0:
            control.idle()
            sys.exit()

        sysaddon = sys.argv[0]

        syshandle = int(sys.argv[1])

        addonPoster, addonBanner = control.addonPoster(), control.addonBanner()

        addonFanart, settingFanart = control.addonFanart(), control.setting('fanart')

        try:
            isOld = False
            control.item().getArt('type')
        except:
            isOld = True

        isPlayable = 'true' if not 'plugin' in control.infoLabel('Container.PluginName') else 'false'
        playbackMenu = str(control.lang(32063)) if control.setting('hosts.mode') == '2' else str(control.lang(32064))
        queueMenu = str(control.lang(32065))
        refreshMenu = str(control.lang(32072))
        infoMenu = str(control.lang(32101))


        for i in items:
            try:
                label = '[B]%s[/B] : %s (%s)' % (i['channel'].upper(), i['title'], i['year'])
                sysname = quote_plus('%s (%s)' % (i['title'], i['year']))
                systitle = quote_plus(i['title'])
                imdb, tmdb, year = i['imdb'], i['tmdb'], i['year']

                meta = dict((k,v) for k, v in i.items() if not v == '0')
                meta.update({'code': imdb})
                meta.update({'imdb_id': imdb})
                meta.update({'tmdb_id': tmdb})
                meta.update({'mediatype': 'movie'})
                meta.update({'trailer': '%s?action=trailer&name=%s' % (sysaddon, sysname)})
                #meta.update({'trailer': 'plugin://script.extendedinfo/?info=playtrailer&&id=%s' % imdb})
                meta.update({'playcount': 0, 'overlay': 6})
                try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
                except: pass

                sysmeta = quote_plus(json.dumps(meta))


                url = '%s?action=play&title=%s&year=%s&imdb=%s&meta=%s&t=%s' % (sysaddon, systitle, year, imdb, sysmeta, self.systime)
                sysurl = quote_plus(url)


                cm = []

                cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))
                cm.append((refreshMenu, 'RunPlugin(%s?action=refresh)' % sysaddon))
                cm.append((playbackMenu, 'RunPlugin(%s?action=alterSources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))

                if isOld is True:
                    cm.append((infoMenu, 'Action(Info)'))
                item = control.item(label=label)

                art = {}

                if 'poster2' in i and not i['poster2'] == '0':
                    art.update({'icon': i['poster2'], 'thumb': i['poster2'], 'poster': i['poster2']})
                elif 'poster' in i and not i['poster'] == '0':
                    art.update({'icon': i['poster'], 'thumb': i['poster'], 'poster': i['poster']})
                else:
                    art.update({'icon': addonPoster, 'thumb': addonPoster, 'poster': addonPoster})

                art.update({'banner': addonBanner})

                if settingFanart == 'true' and 'fanart' in i and not i['fanart'] == '0':
                    item.setProperty('fanart', i['fanart'])
                elif addonFanart is not None:
                    item.setProperty('fanart', addonFanart)

                item.setArt(art)
                item.addContextMenuItems(cm)
                item.setProperty('IsPlayable', isPlayable)
                item.setInfo(type='Video', infoLabels = control.metadataClean(meta))

                video_streaminfo = {'codec': 'h264'}
                item.addStreamInfo('video', video_streaminfo)

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
            except:
                pass

        control.content(syshandle, 'files')
        control.directory(syshandle, cacheToDisc=True)