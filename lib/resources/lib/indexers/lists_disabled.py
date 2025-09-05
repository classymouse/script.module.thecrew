# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file lists.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

import os
import re
import sys
import hashlib
import json
import base64
import random
#import datetime
import six
#import urllib
from urllib.parse import urlparse, parse_qs, parse_qsl, quote_plus, unquote_plus

import xbmc

#from six.moves import urllib_parse, zip, range

#try:
    #from sqlite3 import dbapi2 as database
#except Exception:
    #from pysqlite2 import dbapi2 as database
import sqlite3 as database # cm: sqlite3 import dbapi2 as database
from resources.lib.modules import cache
from resources.lib.modules import metacache
from resources.lib.modules import client
from resources.lib.modules import bookmarks
#from six import PY2, PY3
from resources.lib.modules import control
from resources.lib.modules import regex
from resources.lib.modules import trailer
from resources.lib.modules import workers
from resources.lib.modules import youtube
from resources.lib.modules import views
from resources.lib.modules.listitem import ListItemInfoTag as ListItem
from resources.lib.modules import log_utils
from resources.lib.modules.crewruntime import c

#def six_encode(txt, char='utf-8'):
#    if six.PY2 and isinstance(txt, six.text_type):
#        txt = txt.encode(char)
#    return txt

#def six_decode(txt, char='utf-8'):
#    if six.PY3 and isinstance(txt, six.binary_type):
#        txt = txt.decode(char)
#    return txt

class indexer:
    def __init__(self):
        self.list = []
        self.hash = []
        self.imdb_info_link = 'http://www.omdbapi.com/?i=%s&plot=full&r=json'
        self.tvmaze_info_link = 'http://api.tvmaze.com/lookup/shows?thetvdb=%s'
        self.lang = 'en'
        self.meta = []

    def root_porn(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/pinkhat/main/pinkhat/xxx.xml')
        except Exception:
            pass

    def root_base(self):
        try:
            self.create_list('https://pastebin.com/raw/K3YSAUsD')
        except Exception:
            pass

    def root_waste(self):
        try:
            self.create_list('http://dystopiabuilds.xyz/waste/main.xml')
        except Exception:
            pass

    def root_titan(self):
        try:
            self.create_list('http://magnetic.website/Mad%20Titan/main.xml')
        except Exception:
            pass

    def root_greyhat(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/kids/greyhat_main.xml')
        except Exception:
            pass

    def root_debridkids(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/kids/debridkids.xml')
        except Exception:
            pass

    def root_waltdisney(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/kids/disney_years/main.xml')
        except Exception:
            pass

    def root_learning(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/kids/learning.xml')
        except Exception:
            pass

    def root_songs(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/kids/songs.xml')
        except Exception:
            pass

    def root_yellowhat(self):
        try:
            self.create_list('https://pastebin.com/raw/d5cb3Wxw')
        except Exception:
            pass

    def root_redhat(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/standup/main.xml')
        except Exception:
            pass

    def root_blackhat(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/fitness/main.xml')
        except Exception:
            pass

    def root_food(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/food/food_main.xml')
        except Exception:
            pass

    def root_greenhat(self):
        try:
            self.create_list('http://thechains24.com/GREENHAT/green.xml')
        except Exception:
            pass

    def root_whitehat(self):
        try:
            self.create_list('https://pastebin.com/raw/tMSGGbxc')
        except Exception:
            pass

    def root_absolution(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/absolution/absolution_main.xml')
        except Exception:
            pass

    def root_ncaa(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/ncaa/ncaa.xml')
        except Exception:
            pass

    def root_ncaab(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/ncaa/ncaab.xml')
        except Exception:
            pass

    def root_lfl(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/lfl/lfl.xml')
        except Exception:
            pass

    def root_mlb(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/mlb/mlb.xml')
        except Exception:
            pass

    def root_nfl(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/nfl/nfl.xml')
        except Exception:
            pass

    def root_nhl(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/nhl/nhl.xml')
        except Exception:
            pass

    def root_nba(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/nba/nba.xml')
        except Exception:
            pass

    def root_ufc(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/ufc_mma/ufc.xml')
        except Exception:
            pass

    def root_motogp(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/motor/motogp.xml')
        except Exception:
            pass

    def root_boxing(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/boxing/boxing.xml')
        except Exception:
            pass

    def root_fifa(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/fifa/fifa.xml')
        except Exception:
            pass

    def root_wwe(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/wwe/wwe.xml')
        except Exception:
            pass

    def root_sports_channels(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/channels/channels.xml')
        except Exception:
            pass

    def root_sreplays(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/replays/replays.xml')
        except Exception:
            pass

    def root_misc_sports(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/misc/misc_sports.xml')
        except Exception:
            pass

    def root_tennis(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/tennis/tennis.xml')
        except Exception:
            pass

    def root_f1(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/motor/f1.xml')
        except Exception:
            pass

    def root_pga(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/pga/pga.xml')
        except Exception:
            pass

    def root_kiddo(self):
        try:
            self.create_list('http://cellardoortv.com/kiddo/master/main.xml')
        except Exception:
            pass

    def root_purplehat(self):
        try:
            self.create_list('https://bitbucket.org/team-crew/purplehat/raw/master/CCcinema.xml')
        except Exception:
            pass

    def root_personal(self):
        try:
            self.create_personal('personal.list')
        except Exception:
            pass

    def root_git(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/iptv/main.xml')
        except Exception:
            pass

    def root_nascar(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/nascar/nascar.xml')
        except Exception:
            pass

    def root_xfl(self):#
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/xfl/xfl.xml')
        except Exception:
            pass

    def root_tubi(self):#
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/iptv/tubitv.xml')
        except Exception:
            pass

    def root_pluto(self):#
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/iptv/pluto.xml')
        except Exception:
            pass

    def root_bumble(self):#
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/iptv/bumblebee.xml')
        except Exception:
            pass

    def root_xumo(self):#
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/iptv/xumo.xml')
        except Exception:
            pass

    def root_distro(self):#
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/iptv/distro.xml')
        except Exception:
            pass

    def root_cricket(self):
        try:
            self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/cricket/cricket.xml')
        except Exception:
            pass

#OH added 1-5-2021
    def create_list(self, url):
        try:
            regex.clear()
            self.list = self.the_crew_list(url)
            for i in self.list:
                i.update({'content': 'addons'})
            self.addDirectory(self.list)
            return self.list
        except Exception:
            pass

#WhiteHat added 6-20-2022
    def create_personal(self, url):
        try:
            regex.clear()
            url = control.setting('personal.list')
            self.list = self.the_crew_list(url)
            for i in self.list:
                i.update({'content': 'addons'})
            self.addDirectory(self.list)
            return self.list
        except Exception:
            pass

#OH - checked
    def get(self, url):
        try:
            self.list = self.the_crew_list(url)
            self.worker()
            self.addDirectory(self.list)
            return self.list
        except Exception:
            pass

#OH - checked
    def getq(self, url):
        try:
            self.list = self.the_crew_list(url)
            self.worker()
            self.addDirectory(self.list, queue=True)
            return self.list
        except Exception:
            pass

#OH - checked
    def getx(self, url):
        try:
            r, x = re.findall(r'(.+?)\|regex=(.+?)$', url)[0]
            x = regex.fetch(x)
            r += unquote_plus(x)
            url = regex.resolve(r)
            self.list = self.the_crew_list('', result=url)
            self.addDirectory(self.list)
            return self.list
        except Exception:
            pass

#OH - checked
    def developer(self):
        try:
            url = os.path.join(control.dataPath, 'testings.xml')
            f = control.openFile(url)
            result = f.read()
            f.close()

            self.list = self.the_crew_list('', result=result)
            for i in self.list:
                i.update({'content': 'videos'})
            self.addDirectory(self.list)
            return self.list
        except Exception:
            pass

    def youtube(self, url, action):
        try:
            key = trailer1.trailer().key_link.split('=', 1)[-1]
            if 'PlaylistTuner' in action:
                self.list = cache.get(youtube.youtube(key=key).playlist, 1, url)
            elif 'Playlist' in action:
                self.list = cache.get(youtube.youtube(key=key).playlist, 1, url, True)
            elif 'ChannelTuner' in action:
                self.list = cache.get(youtube.youtube(key=key).videos, 1, url)
            elif 'Channel' in action:
                self.list = cache.get(youtube.youtube(key=key).videos, 1, url, True)
            if 'Tuner' in action:
                for i in self.list:
                    i.update({'name': i['title'], 'poster': i['image'], 'action': 'plugin', 'folder': False})
                if 'Tuner2' in action:
                    self.list = sorted(self.list, key=lambda x: random.random())
                self.addDirectory(self.list, queue=True)
            else:
                for i in self.list:
                    i.update({'name': i['title'], 'poster': i['image'], 'nextaction': action, 'action': 'play', 'folder': False})
                self.addDirectory(self.list)
            return self.list
        except Exception:
            pass


#OH - checked
    def the_crew_list(self, url, result=None):
        if result == None:
            result = cache.get(client.request, 0, url)

        if result.strip().startswith('#EXTM3U') and '#EXTINF' in result:
            try:
                result = re.compile('#EXTINF:.+?\,(.+?)\n(.+?)\n', re.MULTILINE|re.DOTALL).findall(result)
                result = ['<item><title>%s</title><link>%s</link></item>' % (i[0], i[1]) for i in result]
                result = ''.join(result)
            except:
                pass

        try:
            r = base64.b64decode(result)
            r= six_decode(r)
        except: r = ''
        if '</link>' in r: result = r

        info = result.split('<item>')[0].split('<dir>')[0]

        try: vip = re.findall('<poster>(.+?)</poster>', info)[0]
        except: vip = '0'

        try: image = re.findall('<thumbnail>(.+?)</thumbnail>', info)[0]
        except: image = '0'

        try: fanart = re.findall('<fanart>(.+?)</fanart>', info)[0]
        except: fanart = '0'

        items = re.compile('((?:<item>.+?</item>|<dir>.+?</dir>|<plugin>.+?</plugin>|<info>.+?</info>|<name>[^<]+</name><link>[^<]+</link><thumbnail>[^<]+</thumbnail><mode>[^<]+</mode>|<name>[^<]+</name><link>[^<]+</link><thumbnail>[^<]+</thumbnail><date>[^<]+</date>))', re.MULTILINE|re.DOTALL).findall(result)

        for item in items:
            regdata = re.compile('(<regex>.+?</regex>)', re.MULTILINE|re.DOTALL).findall(item)
            regdata = ''.join(regdata)
            reglist = re.compile('(<listrepeat>.+?</listrepeat>)', re.MULTILINE|re.DOTALL).findall(regdata)
            regdata = urllib.parse.quote_plus(regdata)

            reghash = hashlib.md5()
            for i in regdata:
                reghash.update(i.encode('utf-8'))

            reghash = str(reghash.hexdigest())

            item = item.replace('\r','').replace('\n','').replace('\t','').replace('&nbsp;','')

            item = re.sub('<regex>.+?</regex>','', item)
            item = re.sub('<sublink></sublink>|<sublink\s+name=(?:\'|\").*?(?:\'|\")></sublink>','', item)
            item = re.sub('<link></link>','', item)

            name = re.sub('<meta>.+?</meta>','', item)
            try: name = re.findall('<title>(.+?)</title>', name)[0]
            except: name = re.findall('<name>(.+?)</name>', name)[0]

            try: date = re.findall('<date>(.+?)</date>', item)[0]
            except: date = ''

            if re.search(r'\d+', date): name += ' [COLOR red] Updated %s[/COLOR]' % date

            try: image2 = re.findall('<thumbnail>(.+?)</thumbnail>', item)[0]
            except: image2 = image


            try: fanart2 = re.findall('<fanart>(.+?)</fanart>', item)[0]
            except: fanart2 = fanart

            try: meta = re.findall('<meta>(.+?)</meta>', item)[0]
            except: meta = '0'

            try: url = re.findall('<link>(.+?)</link>', item)[0]
            except: url = '0'

            url = url.replace('>search<', '><preset>search</preset>%s<' % meta)
            url = '<preset>search</preset>%s' % meta if url == 'search' else url
            url = url.replace('>searchsd<', '><preset>searchsd</preset>%s<' % meta)
            url = '<preset>searchsd</preset>%s' % meta if url == 'searchsd' else url
            url = re.sub('<sublink></sublink>|<sublink\s+name=(?:\'|\").*?(?:\'|\")></sublink>','', url)

            if item.startswith('<item>'): action = 'play'
            elif item.startswith('<plugin>'): action = 'plugin'
            elif item.startswith('<info>') or url == '0': action = '0'
            else: action = 'directory'
            if action == 'play' and reglist: action = 'xdirectory'

            if not regdata == '':
                self.hash.append({'regex': reghash, 'response': regdata})
                url += '|regex=%s' % reghash

            if action in ['directory', 'xdirectory', 'plugin']: folder = True
            else: folder = False

            try: content = re.findall('<content>(.+?)</content>', meta)[0]
            except: content = '0'
            if content == '0':
                try: content = re.findall('<content>(.+?)</content>', item)[0]
                except: content = '0'

            if not content == '0':
                content += 's'

            if 'tvshow' in content and not url.strip().endswith('.xml'):
                url = '<preset>tvindexer</preset><url>%s</url><thumbnail>%s</thumbnail><fanart>%s</fanart>%s' % (url, image2, fanart2, meta)
                action = 'tvtuner'

            if 'tvtuner' in content and not url.strip().endswith('.xml'):
                url = '<preset>tvtuner</preset><url>%s</url><thumbnail>%s</thumbnail><fanart>%s</fanart>%s' % (url, image2, fanart2, meta)
                action = 'tvtuner'

            try: imdb = re.findall('<imdb>(.+?)</imdb>', meta)[0]
            except: imdb = '0'

            try: tvdb = re.findall('<tvdb>(.+?)</tvdb>', meta)[0]
            except: tvdb = '0'

            try: tvshowtitle = re.findall('<tvshowtitle>(.+?)</tvshowtitle>', meta)[0]
            except: tvshowtitle = '0'


            try: title = re.findall('<title>(.+?)</title>', meta)[0]
            except: title = '0'


            if title == '0' and not tvshowtitle == '0': title = tvshowtitle

            try: year = re.findall('<year>(.+?)</year>', meta)[0]
            except: year = '0'

            try: premiered = re.findall('<premiered>(.+?)</premiered>', meta)[0]
            except: premiered = '0'

            try: season = re.findall('<season>(.+?)</season>', meta)[0]
            except: season = '0'

            try: episode = re.findall('<episode>(.+?)</episode>', meta)[0]
            except: episode = '0'

            self.list.append({'name': name, 'vip': vip, 'url': url, 'action': action, 'folder': folder, 'poster': image2, 'banner': '0', 'fanart': fanart2, 'content': content, 'imdb': imdb, 'tvdb': tvdb, 'tmdb': '0', 'title': title, 'originaltitle': title, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered, 'season': season, 'episode': episode})

        regex.insert(self.hash)
        return self.list


#OH - checked
    def the_crew_list2(self, url, result=None):
        if result is None:
            result = cache.get(client.request, 0, url)
            #c.log(f"[CM Debug @ 447 in lists.py] result = {result}")

        if result.strip().startswith('#EXTM3U') and '#EXTINF' in result:
            try:
                result = re.compile(r'#EXTINF:.+?\,(.+?)\n(.+?)\n', re.MULTILINE|re.DOTALL).findall(result)
                result = [f"<item><title>{i[0]}</title><link>{i[1]}</link></item>" for i in result]
                result = ''.join(result)
            except Exception:
                pass

        try:
            r = base64.b64decode(result)
            #r= six_decode(r)
            r= c.decode(r)
        except Exception:
            r = ''
        if '</link>' in r:
            result = r

        info = result.split('<item>')[0].split('<dir>')[0]

        try:
            vip = re.findall('<poster>(.+?)</poster>', info)[0]
        except Exception:
            vip = '0'

        try:
            image = re.findall('<thumbnail>(.+?)</thumbnail>', info)[0]
        except Exception:
            image = '0'

        try:
            fanart = re.findall('<fanart>(.+?)</fanart>', info)[0]
        except Exception:
            fanart = '0'

        items = re.compile(r'((?:<item>.+?</item>|<dir>.+?</dir>|<plugin>.+?</plugin>|<info>.+?</info>|<name>[^<]+</name><link>[^<]+</link><thumbnail>[^<]+</thumbnail><mode>[^<]+</mode>|<name>[^<]+</name><link>[^<]+</link><thumbnail>[^<]+</thumbnail><date>[^<]+</date>))', re.MULTILINE|re.DOTALL).findall(result)
        c.log(f"[CM Debug @ 484 in lists.py] items = {items}")
        for item in items:
            regdata = re.compile('(<regex>.+?</regex>)', re.MULTILINE|re.DOTALL).findall(item)
            c.log(f"[CM Debug @ 492 in lists.py] regdata = {regdata}")
            regdata = ''.join(regdata)
            reglist = re.compile('(<listrepeat>.+?</listrepeat>)', re.MULTILINE|re.DOTALL).findall(regdata)
            regdata = quote_plus(regdata)

            reghash = hashlib.md5()
            for i in regdata:
                reghash.update(i.encode('utf-8'))

            reghash = str(reghash.hexdigest())

            item = item.replace('\r','').replace('\n','').replace('\t','').replace('&nbsp;','')

            item = re.sub('<regex>.+?</regex>','', item)
            c.log(f"[CM Debug @ 506 in lists.py] item = {item}")
            item = re.sub(r'<sublink></sublink>|<sublink\s+name=(?:\'|\").*?(?:\'|\")></sublink>','', item)
            item = re.sub('<link></link>','', item)

            name = re.sub('<meta>.+?</meta>','', item)
            try:
                name = re.findall('<title>(.+?)</title>', name)[0]
            except Exception:
                name = re.findall('<name>(.+?)</name>', name)[0]

            try:
                date = re.findall('<date>(.+?)</date>', item)[0]
            except Exception:
                date = ''

            if re.search(r'\d+', date):
                name += f' [COLOR red] Updated {date}[/COLOR]'

            try:
                image2 = re.findall('<thumbnail>(.+?)</thumbnail>', item)[0]
            except Exception:
                image2 = image


            try:
                fanart2 = re.findall('<fanart>(.+?)</fanart>', item)[0]
            except Exception:
                fanart2 = fanart

            try:
                meta = re.findall('<meta>(.+?)</meta>', item)[0]
            except Exception:
                meta = '0'

            try:
                url = re.findall('<link>(.+?)</link>', item)[0]
            except Exception:
                url = '0'

            url = url.replace('>search<', '><preset>search</preset>%s<' % meta)
            url = '<preset>search</preset>%s' % meta if url == 'search' else url
            url = url.replace('>searchsd<', '><preset>searchsd</preset>%s<' % meta)
            url = '<preset>searchsd</preset>%s' % meta if url == 'searchsd' else url
            url = re.sub(r'<sublink></sublink>|<sublink\s+name=(?:\'|\").*?(?:\'|\")></sublink>','', url)
            c.log(f"[CM Debug @ 548 in lists.py] url = {url}")

            if item.startswith('<item>'):
                action = 'play'
            elif item.startswith('<plugin>'):
                action = 'plugin'
            elif item.startswith('<info>') or url == '0':
                action = '0'
            else:
                action = 'directory'
            if action == 'play' and reglist:
                action = 'xdirectory'

            if not regdata == '':
                self.hash.append({'regex': reghash, 'response': regdata})
                url += '|regex=%s' % reghash
                #url += f'|regex{reghash}'

            if action in ['directory', 'xdirectory', 'plugin']:
                folder = True
            else:
                folder = False

            try:
                content = re.findall('<content>(.+?)</content>', meta)[0]
            except Exception:
                content = '0'
            if content == '0':
                try:
                    content = re.findall('<content>(.+?)</content>', item)[0]
                except Exception:
                    content = '0'

            if not content == '0':
                content += 's'

            if 'tvshow' in content and not url.strip().endswith('.xml'):
                url = '<preset>tvindexer</preset><url>%s</url><thumbnail>%s</thumbnail><fanart>%s</fanart>%s' % (url, image2, fanart2, meta)
                action = 'tvtuner'

            if 'tvtuner' in content and not url.strip().endswith('.xml'):
                url = '<preset>tvtuner</preset><url>%s</url><thumbnail>%s</thumbnail><fanart>%s</fanart>%s' % (url, image2, fanart2, meta)
                action = 'tvtuner'

            try:
                imdb = re.findall('<imdb>(.+?)</imdb>', meta)[0]
            except Exception:
                imdb = '0'

            try:
                tvdb = re.findall('<tvdb>(.+?)</tvdb>', meta)[0]
            except Exception:
                tvdb = '0'

            try:
                tmdb = re.findall('<tmdb>(.+?)</tmdb>', meta)[0]
            except Exception:
                tmdb = '0'

            try:
                tvshowtitle = re.findall('<tvshowtitle>(.+?)</tvshowtitle>', meta)[0]
            except Exception:
                tvshowtitle = '0'


            try:
                title = re.findall('<title>(.+?)</title>', meta)[0]
            except Exception:
                title = '0'


            if title == '0' and tvshowtitle != '0':
                title = tvshowtitle

            try:
                year = re.findall('<year>(.+?)</year>', meta)[0]
            except Exception:
                year = '0'

            try:
                premiered = re.findall('<premiered>(.+?)</premiered>', meta)[0]
            except Exception:
                premiered = '0'

            try:
                season = re.findall('<season>(.+?)</season>', meta)[0]
            except Exception:
                season = '0'

            try:
                episode = re.findall('<episode>(.+?)</episode>', meta)[0]
            except Exception:
                episode = '0'

            self.list.append({
                'name': name, 'vip': vip, 'url': url, 'action': action, 'folder': folder,
                'poster': image2, 'banner': '0', 'fanart': fanart2, 'content': content,
                'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, 'title': title, 'originaltitle': title,
                'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered, 'season': season,
                'episode': episode})

        regex.insert(self.hash)
        return self.list

#OH - checked
    def worker(self):
        try:
            total = len(self.list)
            if total== 0:
                return

            for i in range(total):
                #self.list[i].update({'metacache': False})
                self.list[i]['metacache'] = False
            self.list = metacache.fetch(self.list, self.lang)

            multi = [i['imdb'] for i in self.list]
            multi = [x for y,x in enumerate(multi) if x not in multi[:y]]
            if len(multi) == 1:
                self.movie_info(0)
                self.tv_info(0)
                if self.meta:
                    metacache.insert(self.meta)

            for i in list(range(0, total)):
                self.list[i].update({'metacache': False})
            self.list = metacache.fetch(self.list, self.lang)

            for r in list(range(0, total, 50)):
                threads = []
                for i in list(range(r, r+50)):
                    if i <= total:
                        threads.append(workers.Thread(self.movie_info, i))
                    if i <= total:
                        threads.append(workers.Thread(self.tv_info, i))
                #[i.start() for i in threads] # cm  - this will work, however bad practice. correct way should be:
                #started = [i.start() for i in threads] but this will still throw a warning, the var "started will neve be used."
                #[i.join() for i in threads]

                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()

            if self.meta:
                metacache.insert(self.meta)
        except Exception:
            pass

    def movie_info(self, i):
        try:
            c.log(f"[CM Debug @ 693 in lists.py] movie_info = {self.list[i]}")
            if self.list[i]['metacache'] is True:
                raise Exception()

            if not self.list[i]['content'] == 'movies':
                raise Exception()

            imdb = self.list[i]['imdb']
            if imdb == '0':
                raise Exception()

            url = self.imdb_info_link % imdb

            item = client.request(url, timeout='10')
            item = json.loads(item)

            if 'Error' in item and 'incorrect imdb' in item['Error'].lower():
                return self.meta.append({
                    'imdb': imdb,
                    'tmdb': '0',
                    'tvdb': '0',
                    'lang': self.lang,
                    'item': {'code': '0'}
                    })

            title = item['Title']
            if title != '0':
                self.list[i].update({'title': title})

            year = item['Year']
            if year != '0':
                self.list[i].update({'year': year})

            imdb = item['imdbID']
            if imdb is None or imdb == '' or imdb == 'N/A':
                imdb = '0'
            if imdb != '0':
                self.list[i].update({'imdb': imdb, 'code': imdb})

            premiered = item['Released']
            if premiered is None or premiered == '' or premiered == 'N/A':
                premiered = '0'
            premiered = re.findall(r'(\d*) (.+?) (\d*)', premiered)
            try:
                premiered = '%s-%s-%s' % (premiered[0][2], {'Jan':'01', 'Feb':'02', 'Mar':'03', 'Apr':'04', 'May':'05', 'Jun':'06', 'Jul':'07', 'Aug':'08', 'Sep':'09', 'Oct':'10', 'Nov':'11', 'Dec':'12'}[premiered[0][1]], premiered[0][0])
            except Exception:
                premiered = '0'
            if premiered != '0':
                self.list[i].update({'premiered': premiered})

            genre = item['Genre']
            if genre is None or genre == '' or genre == 'N/A':
                genre = '0'
            genre = genre.replace(', ', ' / ')
            if genre != '0':
                self.list[i].update({'genre': genre})

            duration = item['Runtime']
            if duration is None or duration == '' or duration == 'N/A':
                duration = '0'
            duration = re.sub('[^0-9]', '', str(duration))
            try:
                duration = str(int(duration) * 60)
            except Exception:
                pass
            if duration != '0':
                self.list[i].update({'duration': duration})

            rating = item['imdbRating']
            if rating is None or rating == '' or rating == 'N/A' or rating == '0.0':
                rating = '0'
            if rating != '0':
                self.list[i].update({'rating': rating})

            votes = item['imdbVotes']
            try:
                votes = str(format(int(votes),',d'))
            except Exception:
                pass
            if votes is None or votes == '' or votes == 'N/A':
                votes = '0'
            if votes != '0':
                self.list[i].update({'votes': votes})

            mpaa = item['Rated']
            if mpaa is None or mpaa == '' or mpaa == 'N/A':
                mpaa = '0'
            if mpaa != '0':
                self.list[i].update({'mpaa': mpaa})

            director = item['Director']
            if director is None or director == '' or director == 'N/A':
                director = '0'
            director = director.replace(', ', ' / ')
            director = re.sub(r'\(.*?\)', '', director)
            director = ' '.join(director.split())
            if director != '0':
                self.list[i].update({'director': director})

            writer = item['Writer']
            if writer is None or writer == '' or writer == 'N/A':
                writer = '0'
            writer = writer.replace(', ', ' / ')
            writer = re.sub(r'\(.*?\)', '', writer)
            writer = ' '.join(writer.split())
            if writer != '0':
                self.list[i].update({'writer': writer})

            cast = item['Actors']
            if cast is None or cast == '' or cast == 'N/A':
                cast = '0'
            cast = [x.strip() for x in cast.split(',') if not x == '']
            try:
                cast = [(c.ensure_str(x), '') for x in cast]
            except Exception:
                cast = []
            if cast == []:
                cast = '0'
            if not cast == '0':
                self.list[i].update({'cast': cast})

            plot = item['Plot']
            if plot is None or plot == '' or plot == 'N/A':
                plot = '0'
            plot = client.replaceHTMLCodes(plot)
            c.ensure_str(plot)
            if plot != '0':
                self.list[i].update({'plot': plot})

            director = writer = ''
            if 'crew' in people and 'directing' in people['crew']:
                director = ', '.join([director['person']['name'] for director in people['crew']
                                      ['directing'] if director['job'].lower() == 'director'])
            if 'crew' in people and 'writing' in people['crew']:
                writer = ', '.join([writer['person']['name'] for writer in people['crew']
                                    ['writing'] if writer['job'].lower() in ['writer', 'screenplay', 'author']])

            cast = []
            for person in people.get('cast', []):
                cast.append(
                    {'name': person['person']['name'], 'role': person['character']})
            cast = [(person['name'], person['role']) for person in cast]

            self.meta.append({'imdb': imdb, 'tmdb': '0', 'tvdb': '0', 'lang': self.lang,
                                'item': {
                                    'title': title, 'year': year, 'code': imdb, 'imdb': imdb,
                                    'premiered': premiered, 'genre': genre, 'duration': duration,
                                    'rating': rating, 'votes': votes, 'mpaa': mpaa,
                                    'director': director, 'writer': writer, 'cast': cast, 'plot': plot
                                    }
                                })
        except Exception as e:
            c.log(f"[CM Debug @ 844 in lists.py] Exception raised in movie_info: {e}")
            pass

    def tv_info(self, i):
        try:
            if self.list[i]['metacache'] is True:
                raise Exception()

            if self.list[i]['content'] not in ['tvshows', 'seasons', 'episodes']:
                raise Exception()

            tvdb = self.list[i]['tvdb']
            if tvdb == '0':
                raise Exception()

            url = self.tvmaze_info_link % tvdb

            item = client.request(url, output='extended', error=True, timeout='10')

            if item[1] == '404':
                return self.meta.append({'imdb': '0', 'tmdb': '0', 'tvdb': tvdb, 'lang': self.lang, 'item': {'code': '0'}})

            item = json.loads(item[0])

            tvshowtitle = item['name']
            tvshowtitle = c.ensure_str(tvshowtitle)
            if not tvshowtitle == '0':
                self.list[i].update({'tvshowtitle': tvshowtitle})

            premiered = item['premiered']
            year = re.findall('(\d{4})', premiered)[0]
            year = str(year)
            if year != '0':
                self.list[i].update({'year': year})

            try:
                imdb = item['externals']['imdb']
            except Exception:
                imdb = '0'
            if imdb == '' or imdb is None:
                imdb = '0'
            imdb = str(imdb)
            if self.list[i]['imdb'] == '0' and imdb != '0':
                self.list[i].update({'imdb': imdb})

            try:
                studio = item['network']['name']
            except Exception:
                studio = '0'
            if studio == '' or studio is None:
                studio = '0'
            studio = c.ensure_str(studio)
            if not studio == '0':
                self.list[i].update({'studio': studio})

            genre = item['genres']
            if genre == '' or genre is None or genre == []:
                genre = '0'
            genre = ' / '.join(genre)
            genre = c.ensure_str(genre)
            if genre != '0':
                self.list[i].update({'genre': genre})

            try:
                duration = str(item['runtime'])
            except Exception:
                duration = '0'
            if duration == '' or duration is None:
                duration = '0'
            try:
                duration = str(int(duration) * 60)
            except Exception:
                pass
            duration = str(duration)
            if duration != '0':
                self.list[i].update({'duration': duration})

            rating = str(item['rating']['average'])
            if rating == '' or rating is None:
                rating = '0'
            rating = str(rating)
            if rating != '0':
                self.list[i].update({'rating': rating})

            plot = item['summary']
            if plot == '' or plot is None:
                plot = '0'
            plot = re.sub(r'\n|<.+?>|</.+?>|.+?#\d*:', '', plot)
            plot = c.ensure_str(plot)
            if not plot == '0':
                self.list[i].update({'plot': plot})

            self.meta.append({
                'imdb': imdb, 'tmdb': '0', 'tvdb': tvdb, 'lang': self.lang,
                'item': {
                    'tvshowtitle': tvshowtitle, 'code': imdb, 'imdb': imdb,
                    'tvdb': tvdb, 'studio': studio, 'genre': genre, 'duration': duration,
                    'rating': rating, 'plot': plot}
                })
        except Exception as e:
            c.log(f"[CM Debug @ 943 in lists.py] Exception raised in tv_info: {e}")
            pass

    def addDirectory(self, items, queue=False):
        if items is None or len(items) == 0:
            return

        sysaddon = sys.argv[0]
        addonPoster = addonBanner = control.addonInfo('icon')
        addonFanart = control.addonInfo('fanart')

        playlist = control.playlist
        if queue is not False:
            playlist.clear()

        try:
            devmode = True if 'testings.xml' in control.listDir(control.dataPath)[1] else False
        except Exception:
            devmode = False

        mode = [i['content'] for i in items if 'content' in i]
        if 'movies' in mode:
            mode = 'movies'
        elif 'tvshows' in mode:
            mode = 'tvshows'
        elif 'seasons' in mode:
            mode = 'seasons'
        elif 'episodes' in mode:
            mode = 'episodes'
        elif 'videos' in mode:
            mode = 'videos'
        else:
            mode = 'addons'

        for i in items:
            try:
                name = control.lang(int(i['name']))
            except Exception:
                name = i['name']


            url = f"{sysaddon}?action={i['action']}"
            try:
                url += f"&url={ quote_plus(i['url'])}"
            except Exception:
                pass
            try:
                url += f"&content={quote_plus(i['content'])}"
            except Exception:
                pass

            if i['action'] == 'plugin' and 'url' in i:
                url = i['url']

            try:
                devurl = dict(parse_qsl(urlparse(url).query))['action']
            except Exception:
                devurl = None

            if devurl == 'developer' and devmode is not True:
                continue
            poster = i['poster'] if 'poster' in i else '0'
            banner = i['banner'] if 'banner' in i else '0'
            fanart = i['fanart'] if 'fanart' in i else '0'
            if poster == '0':
                poster = addonPoster
            if banner == '0' and poster == '0':
                banner = addonBanner
            elif banner == '0':
                banner = poster

            content = i['content'] if 'content' in i else '0'
            folder = i['folder'] if 'folder' in i else True
            #meta = dict((k,v) for k, v in six.iteritems(i) if not v == '0')
            meta = dict((k,v) for k, v in iter(i.items()) if not v == '0')

            cm = []

            if content in ['movies', 'tvshows']:
                meta.update({'trailer': f"{sysaddon}?action=trailer&name={quote_plus(name)}"})
                cm.append((control.lang(30707), 'RunPlugin(%s?action=trailer&name=%s)' % (sysaddon, quote_plus(name))))

            if content in ['movies', 'tvshows', 'seasons', 'episodes']:
                cm.append((control.lang(30708), 'XBMC.Action(Info)'))

            if (folder is False and '|regex=' not in str(i.get('url'))) or (folder is True and content in ['tvshows', 'seasons']):
                cm.append((control.lang(30723), 'RunPlugin(%s?action=queueItem)' % sysaddon))

            if content == 'movies':
                try:
                    dfile = f"{i['title']} ({i['year']})"
                except Exception:
                    dfile = name
                try:
                    cm.append((control.lang(30722),  'RunPlugin(%s?action=addDownload&name=%s&url=%s&image=%s)' % (sysaddon, quote_plus(dfile), quote_plus(i['url']), quote_plus(poster))))
                except Exception:
                    pass
            elif content == 'episodes':
                try:
                    dfile = '%s S%02dE%02d' % (i['tvshowtitle'], int(i['season']), int(i['episode']))
                except Exception:
                    dfile = name
                try:
                    cm.append((control.lang(30722),  'RunPlugin(%s?action=addDownload&name=%s&url=%s&image=%s)' % (sysaddon, quote_plus(dfile), quote_plus(i['url']), quote_plus(poster))))
                except Exception:
                    pass
            elif content == 'songs':
                try:
                    cm.append((control.lang(30722), 'RunPlugin(%s?action=addDownload&name=%s&url=%s&image=%s)' % (sysaddon, quote_plus(name), quote_plus(i['url']), quote_plus(poster))))
                except Exception:
                    pass


            if mode == 'movies':
                cm.append((control.lang(30711), f'RunPlugin({sysaddon}?action=addView&content=movies)'))
            elif mode == 'tvshows':
                cm.append((control.lang(30712), f'RunPlugin({sysaddon}?action=addView&content=tvshows)'))
            elif mode == 'seasons':
                cm.append((control.lang(30713), f'RunPlugin({sysaddon}?action=addView&content=seasons)'))
            elif mode == 'episodes':
                cm.append((control.lang(30714), f'RunPlugin({sysaddon}?action=addView&content=episodes)'))

            if devmode is True:
                try:
                    cm.append(('Open in browser', f"RunPlugin{sysaddon}?action=browser&url={quote_plus(i['url'])})"))
                except Exception:
                    pass

            item = control.item(label=name)

            try:
                item.setArt({
                    'icon': poster, 'thumb': poster, 'poster': poster, 'tvshow.poster': poster,
                    'season.poster': poster, 'banner': banner, 'tvshow.banner': banner,
                    'season.banner': banner})
            except Exception:
                pass

            if fanart != '0':
                item.setProperty('Fanart_Image', fanart)
            elif addonFanart is not None:
                item.setProperty('Fanart_Image', addonFanart)

            if queue is False:
                item.setInfo(type='Video', infoLabels = meta)
                item.addContextMenuItems(cm)
                control.addItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=folder)
            else:
                item.setInfo(type='Video', infoLabels = meta)
                playlist.add(url=url, listitem=item)


        if queue is not False:
            return control.player.play(playlist)

        try:
            i = items[0]
            if i['next'] == '':
                raise Exception()
            url = '%s?action=%s&url=%s' % (sysaddon, i['nextaction'], quote_plus(i['next']))
            item = control.item(label=control.lang(30500).encode('utf-8'))
            item.setArt({'addonPoster': addonPoster, 'thumb': addonPoster, 'poster': addonPoster, 'tvshow.poster': addonPoster, 'season.poster': addonPoster, 'banner': addonPoster, 'tvshow.banner': addonPoster, 'season.banner': addonPoster})
            item.setProperty('addonFanart_Image', addonFanart)
            control.addItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=True)
        except Exception:
            pass

        if mode is not None:
            control.content(int(sys.argv[1]), mode)
        control.directory(int(sys.argv[1]), cacheToDisc=True)
        if mode in ['movies', 'tvshows', 'seasons', 'episodes']:
            views.setView(mode, {'skin.estuary': 55})


class resolver:
    def browser(self, url):
        try:
            url = self.get(url)
            if url is False:
                return
            control.execute('RunPlugin(plugin://plugin.program.chrome.launcher/?url=%s&mode=showSite&stopPlayback=no)' % quote_plus(url))
        except Exception:
            pass


    def link(self, url):
        try:
            url = self.get(url)
            if url is False: return

            #control.execute('ActivateWindow(busydialog)')
            control.execute('ActivateWindow(busydialognocancel)')
            url = self.process(url)
            #control.execute('Dialog.Close(busydialog)')
            control.execute('Dialog.Close(busydialognocancel)')

            #if url is None: return control.infoDialog(control.lang(30705))
            if url is None:
                return control.infoDialog(control.lang(32401))
            return url
        except Exception:
            pass

    def get(self, url):
        try:
            items = re.compile('<sublink(?:\s+name=|)(?:\'|\"|)(.*?)(?:\'|\"|)>(.+?)</sublink>').findall(url)

            if len(items) == 0:
                return url
            if len(items) == 1:
                return items[0][1]

            items = [('Link %s' % (int(items.index(i))+1) if i[0] == '' else i[0], i[1]) for i in items]

            select = control.selectDialog([i[0] for i in items], control.infoLabel('listitem.label'))

            if select == -1:
                return False
            else:
                return items[select][1]
        except Exception:
            pass

    def f4m(self, url, name):
        try:
            if not any(i in url for i in ['.f4m', '.ts']):
                raise Exception()
            ext = url.split('?')[0].split('&')[0].split('|')[0].rsplit('.')[-1].replace('/', '').lower()
            if ext not in ['f4m', 'ts']:
                raise Exception()

            params = parse_qs(url)

            try:
                proxy = params['proxy'][0]
            except Exception:
                proxy = None

            try:
                proxy_use_chunks = json.loads(params['proxy_for_chunks'][0])
            except Exception:
                proxy_use_chunks = True

            try:
                maxbitrate = int(params['maxbitrate'][0])
            except Exception:
                maxbitrate = 0

            try:
                simpleDownloader = json.loads(params['simpledownloader'][0])
            except Exception:
                simpleDownloader = False

            try:
                auth_string = params['auth'][0]
            except Exception:
                auth_string = ''

            try:
                streamtype = params['streamtype'][0]
            except Exception:
                streamtype = 'TSDOWNLOADER' if ext == 'ts' else 'HDS'


            try:
                swf = params['swf'][0]
            except Exception:
                swf = None

            from F4mProxy import f4mProxyHelper
            return f4mProxyHelper().playF4mLink(url, name, proxy, proxy_use_chunks, maxbitrate, simpleDownloader, auth_string, streamtype, False, swf)
        except Exception:
            pass

    def process(self, url, direct=True):
        try:
            if not any(i in url for i in ['.jpg', '.png', '.gif']):
                raise Exception('not an image')
            ext = url.split('?')[0].split('&')[0].split('|')[0].rsplit('.')[-1].replace('/', '').lower()
            if ext not in ['jpg', 'png', 'gif']:
                raise Exception('ext not in jpg, png, gif')
            try:
                i = os.path.join(control.dataPath,'img')
                control.deleteFile(i)
                f = control.openFile(i, 'w')
                f.write(client.request(url))
                f.close()

                control.execute('ShowPicture("%s")' % i)
                return False
            except Exception as e:
                c.log(f"[CM Debug @ 1225 in lists.py] Exception 1 raised: {e}")
                return
        except Exception as e:
            c.log(f"[CM Debug @ 1225 in lists.py] Exception 2 raised: {e}")
            pass

        try:
            r, x = re.findall('(.+?)\|regex=(.+?)$', url)[0]
            x = regex.fetch(x)
            r += unquote_plus(x)
            if '</regex>' not in r:
                raise Exception()
            u = regex.resolve(r)
            if u is not None:
                url = u
        except Exception as e:
            c.log(f"[CM Debug @ 1225 in lists.py] Exception 3 raised: {e}")
            pass

        try:
            if not url.startswith('rtmp'):
                raise Exception('not rtmp')
            if len(re.compile(r'\s*timeout=(\d*)').findall(url)) == 0:
                url += ' timeout=10'
            return url
        except Exception as e:
            c.log(f"[CM Debug @ 1225 in lists.py] Exception 4 raised: {e}")
            pass

        try:
            if not any(i in url for i in ['.m3u8', '.f4m', '.ts']):
                raise Exception()
            ext = url.split('?')[0].split('&')[0].split('|')[0].rsplit('.')[-1].replace('/', '').lower()
            if ext not in ['m3u8', 'f4m', 'ts']:
                raise Exception()
            return url
        except Exception:
            pass

        try:
            preset = re.findall('<preset>(.+?)</preset>', url)[0]

            if 'search' not in preset:
                raise Exception('no search in preset')

            title = re.findall('<title>(.+?)</title>', url)[0].replace('+', ' ')
            year = re.findall('<year>(.+?)</year>', url)[0]
            imdb = re.findall('<imdb>(.+?)</imdb>', url)[0]

            try:
                tvdb = re.findall('<tvdb>(.+?)</tvdb>', url)[0]
                tmdb = re.findall('<tmdb>(.+?)</tmdb>', url)[0]
                tvshowtitle = re.findall('<tvshowtitle>(.+?)</tvshowtitle>', url)[0]
                premiered = re.findall('<premiered>(.+?)</premiered>', url)[0]
                season = re.findall('<season>(.+?)</season>', url)[0]
                episode = re.findall('<episode>(.+?)</episode>', url)[0]
            except Exception:
                tvdb = tvshowtitle = premiered = season = episode = None

            direct = False

            quality = 'HD' if not preset == 'searchsd' else 'SD'

            from resources.lib.modules import sources2

            u = sources2.sources().getSources(title, year, imdb, tvdb, season, episode, tvshowtitle, premiered, quality)

            if u is not None:
                return u
        except Exception:
            pass

        try:
            from resources.lib.modules import sources2

            u = sources2.sources().getURISource(url)

            if u is not False:
                direct = False
            if u is None or u is False:
                raise Exception()

            return u
        except Exception:
            pass

        try:
            if '.google.com' not in url:
                raise Exception()
            from resources.lib.modules import directstream
            u = directstream.google(url)[0]['url']
            return u
        except Exception:
            pass

        try:
            if 'filmon.com/' not in url:
                raise Exception()
            from resources.lib.modules import filmon
            u = filmon.resolve(url)
            return u
        except Exception:
            pass

        try:
            import resolveurl

            hmf = resolveurl.HostedMediaFile(url=url)

            if hmf.valid_url() is False:
                raise Exception()

            direct = False
            u = hmf.resolve()

            if u is not False:
                return u
        except Exception:
            pass

        if direct is True:
            return url


class player(xbmc.Player):
    def __init__ (self):
        xbmc.Player.__init__(self)


    def play(self, url, content=None):
        base = url

        url = resolver().get(url)
        if url is False:
            return

        control.execute('ActivateWindow(busydialog)')
        url = resolver().process(url)
        control.execute('Dialog.Close(busydialog)')

        if url is None:
            #return control.infoDialog(control.lang(30705))
            return control.infoDialog('URL is None')
        if url is False:
            return

        meta = {}
        for i in ['title', 'originaltitle', 'tvshowtitle', 'year', 'season', 'episode', 'genre', 'rating', 'votes', 'director', 'writer', 'plot', 'tagline']:
            try:
                meta[i] = control.infoLabel(f'listitem.{i}')
            except Exception:
                pass

        meta = dict((k,v) for k, v in meta.items() if not v == '')
        if 'title' not in meta:
            meta['title'] = control.infoLabel('listitem.label')
        icon = control.infoLabel('listitem.icon')


        self.name = meta['title']
        self.year = meta['year'] if 'year' in meta else '0'
        self.getbookmark = True if (content == 'movies' or content == 'episodes') else False
        self.offset = bookmarks().get(self.name, self.year)

        f4m = resolver().f4m(url, self.name)
        if f4m is not None:
            return


        item = control.item(path=url)
        try:
            item.setArt({'icon': icon})
        except Exception:
            pass
        item.setInfo(type='Video', infoLabels = meta)
        control.player.play(url, item)
        control.resolve(int(sys.argv[1]), True, item)

        self.totalTime = 0
        self.currentTime = 0

        for i in range(240):
            if self.isPlayingVideo():
                break
            control.sleep(1000)
        while self.isPlayingVideo():
            try:
                self.totalTime = self.getTotalTime()
                self.currentTime = self.getTime()
            except Exception:
                pass
            control.sleep(2000)
        control.sleep(5000)

    def onPlayBackStarted(self):
        control.execute('Dialog.Close(all,true)')
        if self.getbookmark is True and not self.offset == '0':
            self.seekTime(float(self.offset))

    def onPlayBackPaused(self):
        if self.getbookmark is True:
            bookmarks().reset(self.currentTime, self.totalTime, self.name, self.year)


    def onPlayBackStopped(self):
        if self.getbookmark is True:
            bookmarks().reset(self.currentTime, self.totalTime, self.name, self.year)

    def onPlayBackEnded(self):
        self.onPlayBackStopped()


class bookmarks_old:
    def get(self, name, year='0'):
        try:
            offset = '0'

            #if not control.setting('bookmarks') == 'true': raise Exception()
            idFile = hashlib.md5()
            for i in name:
                idFile.update(str(i))
            for i in year:
                idFile.update(str(i))
            idFile = str(idFile.hexdigest())

            dbcon = database.connect(control.bookmarksFile)
            dbcur = dbcon.cursor()
            dbcur.execute("SELECT * FROM bookmark WHERE idFile = '%s'" % idFile)
            match = dbcur.fetchone()
            self.offset = str(match[1])
            dbcon.commit()

            if self.offset == '0': raise Exception()

            minutes, seconds = divmod(float(self.offset), 60) ; hours, minutes = divmod(minutes, 60)
            label = '%02d:%02d:%02d' % (hours, minutes, seconds)
            label = (control.lang(32502) % label).encode('utf-8')

            try:
                yes = control.dialog.contextmenu([label, control.lang(32501), ])
            except Exception:
                yes = control.yesnoDialog(label, '', '', str(name), control.lang(32503), control.lang(32501))

            if yes:
                self.offset = '0'

            return self.offset
        except Exception:
            return offset

    def reset(self, currentTime, totalTime, name, year='0'):
        try:
            #if not control.setting('bookmarks') == 'true': raise Exception()
            timeInSeconds = str(currentTime)
            ok = int(currentTime) > 180 and (currentTime / totalTime) <= .92

            idFile = hashlib.md5()
            for i in name: idFile.update(str(i))
            for i in year: idFile.update(str(i))
            idFile = str(idFile.hexdigest())

            control.makeFile(control.dataPath)
            dbcon = database.connect(control.bookmarksFile)
            dbcur = dbcon.cursor()
            dbcur.execute("CREATE TABLE IF NOT EXISTS bookmark (""idFile TEXT, ""timeInSeconds TEXT, ""UNIQUE(idFile)"");")
            dbcur.execute("DELETE FROM bookmark WHERE idFile = '%s'" % idFile)
            if ok: dbcur.execute("INSERT INTO bookmark Values (?, ?)", (idFile, timeInSeconds))
            dbcon.commit()
        except Exception:
            pass