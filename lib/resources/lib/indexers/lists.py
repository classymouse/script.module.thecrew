# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ******
'''

import os
import re
import sys
import hashlib
import json
import base64
import random
import datetime
import six
#import urllib
from urllib.parse import urlparse, parse_qs, quote_plus, unquote_plus, parse_qsl
import xbmc
#from six.moves import urllib_parse, zip, range



import sqlite3 as database


from ..modules import cache
from ..modules import metacache
from ..modules import client
#from six import PY2, PY3
from ..modules import control
from ..modules import regex
from ..modules import trailer
from ..modules import workers
from ..modules import youtube
from ..modules import views
from ..modules.crewruntime import c


#placeholder for external calls
def six_encode_old(txt, char='utf-8'):
    return c.encode(txt, char)


#placeholder for external calls
def six_decode_old(txt, char='utf-8'):
    return c.decode(txt, char)


def six_encode(txt, char='utf-8', errors='replace'):
    if six.PY2 and isinstance(txt, six.text_type):
        txt = txt.encode(char, errors=errors)
    return txt

def six_decode(txt, char='utf-8', errors='replace'):
    if six.PY3 and isinstance(txt, six.binary_type):
        txt = txt.decode(char, errors=errors)
    return txt
class indexer:
    def __init__(self):
        self.list = []
        self.hash = []
        self.imdb_info_link = 'http://www.omdbapi.com/?i=%s&plot=full&r=json'
        self.tvmaze_info_link = 'http://api.tvmaze.com/lookup/shows?thetvdb=%s'
        self.lang = 'en'
        self.meta = []

    def root_porn(self):
        self.create_list('https://raw.githubusercontent.com/posadka/pinkhat/main/pinkhat/xxx.xml')
        #self.create_list('https://classymouse.github.io/temp/xxx.xml')

    def root_base(self):
        self.create_list('https://pastebin.com/raw/K3YSAUsD')

    def root_waste(self):
        self.create_list('http://dystopiabuilds.xyz/waste/main.xml')

    def root_titan(self):
        self.create_list('http://magnetic.website/Mad%20Titan/main.xml')

    def root_greyhat(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/kids/greyhat_main.xml')

    def root_debridkids(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/kids/debridkids.xml')

    def root_waltdisney(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/kids/disney_years/main.xml')

    def root_learning(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/kids/learning.xml')

    def root_songs(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/kids/songs.xml')

    def root_yellowhat(self):
        self.create_list('https://pastebin.com/raw/d5cb3Wxw')

    def root_redhat(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/standup/main.xml')

    def root_blackhat(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/fitness/main.xml')

    def root_food(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/food/food_main.xml')

    def root_greenhat(self):
        self.create_list('http://thechains24.com/GREENHAT/green.xml')

    def root_whitehat(self):
        self.create_list('https://pastebin.com/raw/tMSGGbxc')

    def root_absolution(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/absolution/absolution_main.xml')

    def root_ncaa(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/ncaa/ncaa.xml')

    def root_ncaab(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/ncaa/ncaab.xml')

    def root_lfl(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/lfl/lfl.xml')

    def root_mlb(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/mlb/mlb.xml')

    def root_nfl(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/nfl/nfl.xml')

    def root_nhl(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/nhl/nhl.xml')

    def root_nba(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/nba/nba.xml')

    def root_ufc(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/ufc_mma/ufc.xml')

    def root_motogp(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/motor/motogp.xml')

    def root_boxing(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/boxing/boxing.xml')

    def root_fifa(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/fifa/fifa.xml')

    def root_wwe(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/wwe/wwe.xml')

    def root_sports_channels(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/channels/channels.xml')

    def root_sreplays(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/replays/replays.xml')

    def root_misc_sports(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/misc/misc_sports.xml')

    def root_tennis(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/tennis/tennis.xml')

    def root_f1(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/motor/f1.xml')

    def root_pga(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/pga/pga.xml')

    def root_kiddo(self):
        self.create_list('http://cellardoortv.com/kiddo/master/main.xml')

    def root_purplehat(self):
        self.create_list('https://bitbucket.org/team-crew/purplehat/raw/master/CCcinema.xml')


    def root_classy(self):
        self.create_list('https://raw.githubusercontent.com/classymouse/cc/main/CCcinema.xml')





    def root_personal(self):
        self.create_personal('personal.list')

    def root_git(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/iptv/main.xml')

    def root_nascar(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/nascar/nascar.xml')

    def root_xfl(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/xfl/xfl.xml')

    def root_tubi(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/iptv/tubitv.xml')

    def root_pluto(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/iptv/pluto.xml')

    def root_bumble(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/iptv/bumblebee.xml')

    def root_xumo(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/iptv/xumo.xml')

    def root_distro(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/iptv/distro.xml')

    def root_cricket(self):
        self.create_list('https://raw.githubusercontent.com/posadka/xmls2/main/sports/cricket/cricket.xml')

#OH added 1-5-2021
    def create_list(self, url):
        try:
            c.log(f"[CM Debug @ 341 in lists.py]url = {url}")
            regex.clear()
            c.log(f"[CM Debug @ 343 in lists.py]url = {url}")

            self.list = self.the_crew_list(url)
            c.log(f"[CM Debug @ 343 in lists.py]self.list = {self.list}")
            for i in self.list:
                i.update({'content': 'addons'})
            self.addDirectory(self.list)
            return self.list
        except:
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
        except:
            pass

#OH - checked
    def get(self, url):
        try:
            self.list = self.the_crew_list(url)
            self.worker()
            self.addDirectory(self.list)
            return self.list
        except:
            pass


#TODO: check if this is working
    def getq(self, url):
        try:
            self.list = self.the_crew_list(url)
            self.worker()
            self.addDirectory(self.list, queue=True)
            return self.list
        except:
            pass

#TODO: check if this is working
    def getx(self, url, worker=False):
        try:
            c.log(f"[CM Debug @ 401 in lists.py] url = {url}")
            r, x = re.findall(r'(.+?)\|regex=(.+?)$', url)[0]
            x = regex.fetch(x)
            r += unquote_plus(x)
            c.log(f"[CM Debug @ 405 in lists.py] r = {repr(r)} and x = {repr(x)}")
            url = regex.resolve(r)
            self.list = self.the_crew_list('', result=url)
            self.addDirectory(self.list)
            return self.list
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 397 in lists.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 397 in lists.py]Exception raised. Error = {e}')
            pass
        #except:
            #pass


    def get_x_url(self, url):
        try:
            r, x = re.findall(r'(.+?)\|regex=(.+?)$', url)[0]
            x = regex.fetch(x)
            r = unquote_plus(x)
            c.log(f"[CM Debug @ 425 in lists.py] r = {r} and x = {x}")
            url = regex.resolve(r)
            self.list = self.the_crew_list('', result=url)
            return url

        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 432 in lists.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 433 in lists.py]Exception raised. Error = {e}')
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
        except:
            pass



    #TODO getting key from trailers is just plain wrong. Needs a key from yt or settings
    def youtube(self, url, action):
        try:
            key = trailer.trailers().key_link.split('=', 1)[-1]
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
                    i.update({
                        'name': i['title'], 'poster': i['image'],
                        'action': 'plugin', 'folder': False
                        })
                if 'Tuner2' in action:
                    self.list = sorted(self.list, key=lambda x: random.random())
                self.addDirectory(self.list, queue=True)
            else:
                for i in self.list:
                    i.update({
                        'name': i['title'], 'poster': i['image'], 'nextaction': action,
                        'action': 'play', 'folder': False
                        })
                self.addDirectory(self.list)
            return self.list
        except:
            pass


#OH - checked
    def the_crew_list(self, url, result=None):
        try:
            if result is None:
                result = cache.get(client.request, 0, url)

            if result.strip().startswith('#EXTM3U') and '#EXTINF' in result:
                try:
                    result = re.compile(
                        r'#EXTINF:.+?\,(.+?)\n(.+?)\n', re.MULTILINE|re.DOTALL).findall(result)
                    result = [
                        f'<item><title>{i[0]}</title><link>{i[1]}</link></item>' for i in result
                        ]
                    result = ''.join(result)
                except ValueError:
                    pass

            try:
                r = base64.b64decode(result)
                c.log(f"[CM Debug @ 477 in lists.py] r = {r}")
                #r= c.decode(r)
                r = six_decode(r)
                c.log(f"[CM Debug @ 491 in lists.py] r = {r}")
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 479 in lists.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 479 in lists.py]Exception raised. Error = {e}')
                r = ''
            #except ValueError:
            #    r = ''

            if '</link>' in r:
                result = r

            info = result.split('<item>')[0].split('<dir>')[0]

            try:
                vip = re.findall('<poster>(.+?)</poster>', info)[0]
            except:
                vip = '0'

            try:
                image = re.findall('<thumbnail>(.+?)</thumbnail>', info)[0]
            except:
                image = '0'

            try:
                fanart = re.findall('<fanart>(.+?)</fanart>', info)[0]
            except:
                fanart = '0'

            # items = re.compile(
            #     '((?:<item>.+?</item>|<dir>.+?</dir>|<plugin>.+?</plugin>|<info>.+?</info>|<name>[^<]+</name><link>[^<]+</link><thumbnail>[^<]+</thumbnail><mode>[^<]+</mode>|<name>[^<]+</name><link>[^<]+</link><thumbnail>[^<]+</thumbnail><date>[^<]+</date>))',
            #     re.MULTILINE|re.DOTALL
            #     ).findall(result)


            pattern = re.compile(
                '((?:<item>.+?</item>|<dir>.+?</dir>|<plugin>.+?</plugin>|<info>.+?</info>|<name>[^<]+</name><link>[^<]+</link><thumbnail>[^<]+</thumbnail><mode>[^<]+</mode>|<name>[^<]+</name><link>[^<]+</link><thumbnail>[^<]+</thumbnail><date>[^<]+</date>))',
                re.MULTILINE|re.DOTALL
                )
            items = pattern.findall(result)

            for item in items:
                regdata = re.compile('(<regex>.+?</regex>)', re.MULTILINE|re.DOTALL).findall(item)
                regdata = ''.join(regdata)
                reglist = re.compile(
                    '(<listrepeat>.+?</listrepeat>)', re.MULTILINE|re.DOTALL).findall(regdata)
                regdata = quote_plus(regdata)

                reghash = hashlib.md5()
                for i in regdata:
                    reghash.update(i.encode('utf-8'))

                reghash = str(reghash.hexdigest())

                item = item.replace('\r','').replace('\n','').replace('\t','').replace('&nbsp;','')

                item = re.sub('<regex>.+?</regex>','', item)
                item = re.sub(
                    r'<sublink></sublink>|<sublink\s+name=(?:\'|\").*?(?:\'|\")></sublink>','', item
                    )
                item = re.sub('<link></link>','', item)

                name = re.sub('<meta>.+?</meta>','', item)
                try:
                    name = re.findall('<title>(.+?)</title>', name)[0]
                except:
                    name = re.findall('<name>(.+?)</name>', name)[0]

                try:
                    date = re.findall('<date>(.+?)</date>', item)[0]
                except:
                    date = ''

                if re.search(r'\d+', date):
                    name += f' [COLOR red] Updated {date}[/COLOR]'

                try:
                    image2 = re.findall('<thumbnail>(.+?)</thumbnail>', item)[0]
                except:
                    image2 = image


                try:
                    fanart2 = re.findall('<fanart>(.+?)</fanart>', item)[0]
                except:
                    fanart2 = fanart

                try:
                    meta = re.findall('<meta>(.+?)</meta>', item)[0]
                except:
                    meta = '0'

                try:
                    url = re.findall('<link>(.+?)</link>', item)[0]
                except:
                    url = '0'

                url = url.replace('>search<', f'><preset>search</preset>{meta}<')
                url = f'<preset>search</preset>{meta}' if url == 'search' else url
                url = url.replace('>searchsd<', f'><preset>searchsd</preset>{meta}<')
                url = f'<preset>searchsd</preset>{meta}'  if url == 'searchsd' else url
                url = re.sub(
                    r'<sublink></sublink>|<sublink\s+name=(?:\'|\").*?(?:\'|\")></sublink>','', url
                    )

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
                    url += f'|regex={reghash}'

                if action in ['directory', 'xdirectory', 'plugin']:
                    folder = True
                else:
                    folder = False

                try:
                    content = re.findall('<content>(.+?)</content>', meta)[0]
                except:
                    content = '0'

                if content == '0':
                    try:
                        content = re.findall('<content>(.+?)</content>', item)[0]
                    except:
                        content = '0'

                if content != '0':
                    content += 's'

                if 'tvshow' in content and not url.strip().endswith('.xml'):
                    url = f'<preset>tvindexer</preset><url>{url}</url><thumbnail>{image2}</thumbnail><fanart>{fanart2}</fanart>{meta}'
                    action = 'tvtuner'

                if 'tvtuner' in content and not url.strip().endswith('.xml'):
                    url = f'<preset>tvtuner</preset><url>{url}</url><thumbnail>{image2}</thumbnail><fanart>{fanart2}</fanart>{meta}'
                    action = 'tvtuner'

                try:
                    imdb = re.findall('<imdb>(.+?)</imdb>', meta)[0]
                except:
                    imdb = '0'

                try:
                    tvdb = re.findall('<tvdb>(.+?)</tvdb>', meta)[0]
                except:
                    tvdb = '0'

                try:
                    tvshowtitle = re.findall('<tvshowtitle>(.+?)</tvshowtitle>', meta)[0]
                except:
                    tvshowtitle = '0'


                try:
                    title = re.findall('<title>(.+?)</title>', meta)[0]
                except:
                    title = '0'


                if title == '0' and tvshowtitle != '0':
                    title = tvshowtitle

                try:
                    year = re.findall('<year>(.+?)</year>', meta)[0]
                except:
                    year = '0'

                try:
                    premiered = re.findall('<premiered>(.+?)</premiered>', meta)[0]
                except:
                    premiered = '0'

                try:
                    season = re.findall('<season>(.+?)</season>', meta)[0]
                except:
                    season = '0'

                try:
                    episode = re.findall('<episode>(.+?)</episode>', meta)[0]
                except:
                    episode = '0'

                self.list.append({
                    'name': name, 'vip': vip, 'url': url, 'action': action, 'folder': folder,
                    'poster': image2, 'banner': '0', 'fanart': fanart2,
                    'content': content, 'imdb': imdb, 'tvdb': tvdb, 'tmdb': '0', 'title': title,
                    'originaltitle': title, 'tvshowtitle': tvshowtitle, 'year': year,
                    'premiered': premiered, 'season': season, 'episode': episode
                    })

            regex.insert(self.hash)
            return self.list

        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 649 in lists.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 650 in lists.py]Exception raised. Error = {e}')
            pass

#cm - checked
    def worker(self):
        try:
            total = len(self.list)

            if total == 0:
                return

            for i in range(total):
                self.list[i].update({'metacache': False})
            self.list = metacache.fetch(self.list, self.lang)

            multi = [i['imdb'] for i in self.list]
            multi = [x for y,x in enumerate(multi) if x not in multi[:y]]
            if len(multi) == 1:
                self.movie_info(0)
                self.tv_info(0)
                if self.meta:
                    metacache.insert(self.meta)

            for i in range(total):
                self.list[i].update({'metacache': False})
            self.list = metacache.fetch(self.list, self.lang)

            for r in range(0, total, 50):
                threads = []
                for i in list(range(r, r+50)):
                    if i <= total:
                        threads.append(workers.Thread(self.movie_info, i))
                    if i <= total:
                        threads.append(workers.Thread(self.tv_info, i))
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()

                if self.meta:
                    metacache.insert(self.meta)

            if self.meta:
                metacache.insert(self.meta)
        except:
            pass

    def movie_info(self, i):
        try:
            if self.list[i]['metacache'] is True or not self.list[i]['content'] == 'movies':
                #raise Exception()
                return

            #if not self.list[i]['content'] == 'movies':
            #    raise Exception()

            imdb = self.list[i]['imdb']
            if imdb == '0':
                raise Exception()

            url = self.imdb_info_link % imdb

            item = client.request(url, timeout='10')
            item = json.loads(item)

            if 'Error' in item and 'incorrect imdb' in item['Error'].lower():
                return self.meta.append({
                    'imdb': imdb, 'tmdb': '0', 'tvdb': '0', 'lang': self.lang,
                    'item': {'code': '0'}
                    })

            title = item['Title']
            if not title == '0':
                self.list[i].update({'title': title})

            year = item['Year']
            if year != '0':
                self.list[i].update({'year': year})

            imdb = item['imdbID']
            if imdb in ['', None, 'N/A']:
                imdb = '0'
            if imdb != '0':
                self.list[i].update({'imdb': imdb, 'code': imdb})

            premiered = item['Released']
            if premiered in ['', None, 'N/A']:
                premiered = '0'
            premiered = re.findall(r'(\d*) (.+?) (\d*)', premiered)
            try:
                premiered = '%s-%s-%s' % (
                    premiered[0][2],
                    {
                        'Jan':'01', 'Feb':'02', 'Mar':'03', 'Apr':'04', 'May':'05', 'Jun':'06',
                        'Jul':'07', 'Aug':'08', 'Sep':'09', 'Oct':'10', 'Nov':'11', 'Dec':'12'
                    }[premiered[0][1]],
                    premiered[0][0]
                    )
            except:
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
            except:
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
            except:
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
            except:
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
            if not plot == '0':
                self.list[i].update({'plot': plot})

            #director = writer = ''
            #if 'crew' in people and 'directing' in people['crew']:
            #    director = ', '.join([director['person']['name'] for director in people['crew']['directing'] if director['job'].lower() == 'director'])
            #if 'crew' in people and 'writing' in people['crew']:
            #    writer = ', '.join([writer['person']['name'] for writer in people['crew']['writing'] if writer['job'].lower() in ['writer', 'screenplay', 'author']])

            #cast = []
            #for person in people.get('cast', []):
            #    cast.append(
            #        {'name': person['person']['name'], 'role': person['character']})
            #cast = [(person['name'], person['role']) for person in cast]

            self.meta.append({
                'imdb': imdb, 'tmdb': '0', 'tvdb': '0', 'lang': self.lang,
                'item': {
                    'title': title, 'year': year, 'code': imdb, 'imdb': imdb,
                    'premiered': premiered, 'genre': genre, 'duration': duration,
                    'rating': rating, 'votes': votes, 'mpaa': mpaa,
                    'director': director, 'writer': writer, 'cast': cast, 'plot': plot
                    }
                })
        except:
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
                return self.meta.append({
                    'imdb': '0', 'tmdb': '0', 'tvdb': tvdb, 'lang': self.lang, 'item': {'code': '0'}
                    })

            item = json.loads(item[0])

            tvshowtitle = item['name']
            c.ensure_str(tvshowtitle)
            if not tvshowtitle == '0':
                self.list[i].update({'tvshowtitle': tvshowtitle})

            year = item['premiered']
            year = re.findall(r'(\d{4})', year)[0]
            c.ensure_str(year)
            if not year == '0':
                self.list[i].update({'year': year})

            try:
                imdb = item['externals']['imdb']
            except:
                imdb = '0'
            if imdb == '' or imdb is None:
                imdb = '0'
            c.ensure_str(imdb)
            if self.list[i]['imdb'] == '0' and not imdb == '0':
                self.list[i].update({'imdb': imdb})

            try:
                studio = item['network']['name']
            except:
                studio = '0'
            if studio == '' or studio is None:
                studio = '0'
            c.ensure_str(studio)
            if not studio == '0':
                self.list[i].update({'studio': studio})

            genre = item['genres']
            if genre == '' or genre is None or genre == []:
                genre = '0'
            genre = ' / '.join(genre)
            c.ensure_str(genre)
            if not genre == '0':
                self.list[i].update({'genre': genre})

            try:
                duration = str(item['runtime'])
            except:
                duration = '0'

            if duration in ['', None]:
                duration = '0'
            try:
                duration = str(int(duration) * 60)
            except:
                pass
            c.ensure_str(duration)
            if not duration == '0':
                self.list[i].update({'duration': duration})

            rating = str(item['rating']['average'])
            if rating == '' or rating is None:
                rating = '0'
            c.ensure_str(rating)
            if not rating == '0':
                self.list[i].update({'rating': rating})

            plot = item['summary']
            if plot == '' or plot is None:
                plot = '0'
            plot = re.sub(r'\n|<.+?>|</.+?>|.+?#\d*:', '', plot)
            c.ensure_str(plot)
            if not plot == '0':
                self.list[i].update({'plot': plot})

            self.meta.append({
                'imdb': imdb, 'tmdb': '0', 'tvdb': tvdb, 'lang': self.lang,
                'item': {
                    'tvshowtitle': tvshowtitle, 'year': year, 'code': imdb, 'imdb': imdb,
                    'tvdb': tvdb, 'studio': studio, 'genre': genre,
                    'duration': duration, 'rating': rating, 'plot': plot
                    }
                })
        except:
            pass

    def addDirectory(self, items, queue=False):
        if items is None or len(items) == 0:
            return

        c.log(f"[CM Debug @ 1027 in lists.py] items = {repr(items)}")



        sysaddon = sys.argv[0]
        addonPoster = addonBanner = control.addonInfo('icon')
        addonFanart = control.addonInfo('fanart')

        playlist = control.playlist
        if queue is not False:
            playlist.clear()

        try:
            devmode = True if 'testings.xml' in control.listDir(control.dataPath)[1] else False
        except FileNotFoundError:
            devmode = False

        content_type = next((item['content'] for item in items if 'content' in item), None)
        mode = {
            'movies': 'movies',
            'tvshows': 'tvshows',
            'seasons': 'seasons',
            'episodes': 'episodes',
            'videos': 'videos'
        }.get(content_type, 'addons')

        for i in items:
            try:
                name = control.lang(int(i['name']))
            except (ValueError, TypeError):
                name = i['name']

            url = f"{sysaddon}?action={i['action']}"

            try:
                url += f"&url={quote_plus(i['url'])}"
            except ValueError:
                pass

            try:
                url += f"&content={quote_plus(i['content'])}"
            except ValueError:
                pass

            if i['action'] == 'plugin' and 'url' in i:
                url = i['url']

            try:
                devurl = dict(parse_qsl(urlparse(url).query)).get('action')
            except ValueError:
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
            meta = dict((k,v) for k, v in i.items() if not v == '0')

            cm = []

            if content in ['movies', 'tvshows']:
                meta.update({'trailer': f'{sysaddon}?action=trailer&name={quote_plus(name)}'})
                cm.append((control.lang(30707), f'RunPlugin({sysaddon}?action=trailer&name={quote_plus(name)})'))

            if content in ['movies', 'tvshows', 'seasons', 'episodes']:
                cm.append((control.lang(30708), 'XBMC.Action(Info)'))

            if (folder is False and '|regex=' not in str(i.get('url'))) or (folder is True and content in ['tvshows', 'seasons']):
                cm.append((control.lang(30723), f'RunPlugin({sysaddon}?action=queueItem)'))

            if content == 'movies':
                dfile = f"{i['title']} ({i['year']})" or name
                cm.append((control.lang(30722),  f"RunPlugin({sysaddon}?action=addDownload&name={quote_plus(dfile)}&url={quote_plus(i['url'])}&image={quote_plus(poster)})"))

            elif content == 'episodes':
                dfile = f"{i['tvshowtitle']} S{int(i['season']):02d}E{int(i['episode']):02d}" or name
                cm.append((control.lang(30722),  f"RunPlugin({sysaddon}?action=addDownload&name={quote_plus(dfile)}&url={quote_plus(i['url'])}&image={quote_plus(poster)})"))

            elif content == 'songs':
                cm.append((control.lang(30722), f"RunPlugin({sysaddon}?action=addDownload&name={quote_plus(name)}&url={quote_plus(i['url'])}&image={quote_plus(poster)})"))

            if mode == 'movies':
                c.log(f"[CM Debug @ 1033 in lists.py] lang = {control.lang(30711)}")
                cm.append((control.lang(30711), f"RunPlugin({sysaddon}?action=addView&content=movies)"))
            elif mode == 'tvshows':
                cm.append((control.lang(30712), f"RunPlugin({sysaddon}?action=addView&content=tvshows)"))
            elif mode == 'seasons':
                cm.append((control.lang(30713), f"RunPlugin({sysaddon}?action=addView&content=seasons)"))
            elif mode == 'episodes':
                cm.append((control.lang(30714), f"RunPlugin({sysaddon}?action=addView&content=episodes)"))

            if devmode is True:
                cm.append(('Open in browser',f"RunPlugin({sysaddon}?action=browser&url={quote_plus(i['url'])}"))

            item = control.item(label=name)

            try:
                item.setArt({
                    'icon': poster, 'thumb': poster, 'poster': poster, 'tvshow.poster': poster,
                    'season.poster': poster, 'banner': banner, 'tvshow.banner': banner,
                    'season.banner': banner
                    })
            except:
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

            url = f"{sysaddon}?action={i['nextaction']}&url={quote_plus(i['next'])}"
            item = control.item(label=control.lang(30500).encode('utf-8'))
            item.setArt({
                'addonPoster': addonPoster, 'thumb': addonPoster, 'poster': addonPoster,
                'tvshow.poster': addonPoster, 'season.poster': addonPoster, 'banner': addonPoster,
                'tvshow.banner': addonPoster, 'season.banner': addonPoster
                })
            item.setProperty('addonFanart_Image', addonFanart)

            control.addItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=True)
        except:
            pass

        if mode is not None:
            control.content(int(sys.argv[1]), mode)
        control.directory(int(sys.argv[1]), cacheToDisc=True)
        if mode in ['movies', 'tvshows', 'seasons', 'episodes']:
            views.set_view(mode, {'skin.estuary': 55})


class resolver:
    def browser(self, url):
        try:
            url = self.get(url)
            if url is False:
                return
            control.execute(f'RunPlugin(plugin://plugin.program.chrome.launcher/?url={quote_plus(url)}&mode=showSite&stopPlayback=no)')
        except:
            pass


    def link(self, url):
        try:
            url = self.get(url)
            if url is False:
                return

            control.execute('ActivateWindow(busydialognocancel)')
            url = self.process(url)

            control.execute('Dialog.Close(busydialognocancel)')

            if url is None:
                return control.infoDialog(control.lang(32401))
            return url
        except:
            pass

    def get(self, url):
        try:
            items = re.compile('<sublink(?:\s+name=|)(?:\'|\"|)(.*?)(?:\'|\"|)>(.+?)</sublink>').findall(url)

            if len(items) == 0:
                return url
            if len(items) == 1:
                return items[0][1]

            items = [(f'Link {int(items.index(i))+1}' if i[0] == '' else i[0], i[1]) for i in items]

            select = control.selectDialog([i[0] for i in items], control.infoLabel('listitem.label'))

            if select == -1:
                return False
            else:
                return items[select][1]
        except:
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
            except:
                proxy = None

            try:
                proxy_use_chunks = json.loads(params['proxy_for_chunks'][0])
            except:
                proxy_use_chunks = True

            try:
                maxbitrate = int(params['maxbitrate'][0])
            except:
                maxbitrate = 0

            try:
                simpleDownloader = json.loads(params['simpledownloader'][0])
            except:
                simpleDownloader = False

            try:
                auth_string = params['auth'][0]
            except:
                auth_string = ''

            try:
                streamtype = params['streamtype'][0]
            except:
                streamtype = 'TSDOWNLOADER' if ext == 'ts' else 'HDS'


            try:
                swf = params['swf'][0]
            except:
                swf = None

            from F4mProxy import f4mProxyHelper
            return f4mProxyHelper().playF4mLink(url, name, proxy, proxy_use_chunks, maxbitrate, simpleDownloader, auth_string, streamtype, False, swf)
        except:
            pass

    def process(self, url, direct=True):
        try:
            if not any(i in url for i in ['.jpg', '.png', '.gif']):
                raise Exception()
            ext = url.split('?')[0].split('&')[0].split('|')[0].rsplit('.')[-1].replace('/', '').lower()
            if ext not in ['jpg', 'png', 'gif']:
                raise Exception()
            try:
                i = os.path.join(control.dataPath,'img')
                control.deleteFile(i)
                f = control.openFile(i, 'w')
                f.write(client.request(url))
                f.close()

                control.execute(f'ShowPicture("{i}")')
                return False
            except:
                return
        except:
            pass

        try:
            r, x = re.findall('(.+?)\|regex=(.+?)$', url)[0]
            x = regex.fetch(x)
            r += unquote_plus(x)
            if not '</regex>' in r:
                raise Exception()
            u = regex.resolve(r)
            if not u is None:
                url = u
        except:
            pass

        try:
            if not url.startswith('rtmp'):
                raise Exception()
            if len(re.compile('\s*timeout=(\d*)').findall(url)) == 0:
                url += ' timeout=10'
            return url
        except:
            pass

        try:
            if not any(i in url for i in ['.m3u8', '.f4m', '.ts']):
                raise Exception()
            ext = url.split('?')[0].split('&')[0].split('|')[0].rsplit('.')[-1].replace('/', '').lower()
            if not ext in ['m3u8', 'f4m', 'ts']:
                raise Exception()
            return url
        except:
            pass

        try:
            preset = re.findall('<preset>(.+?)</preset>', url)[0]

            if not 'search' in preset:
                raise Exception()

            title = re.findall('<title>(.+?)</title>', url)[0]
            year = re.findall('<year>(.+?)</year>', url)[0]
            imdb = re.findall('<imdb>(.+?)</imdb>', url)[0]

            try:
                tvdb = re.findall('<tvdb>(.+?)</tvdb>', url)[0]
                tvshowtitle = re.findall('<tvshowtitle>(.+?)</tvshowtitle>', url)[0]
                premiered = re.findall('<premiered>(.+?)</premiered>', url)[0]
                season = re.findall('<season>(.+?)</season>', url)[0]
                episode = re.findall('<episode>(.+?)</episode>', url)[0]
            except:
                tvdb = tvshowtitle = premiered = season = episode = None

            direct = False
            quality = 'HD' if not preset == 'searchsd' else 'SD'

            from ..modules import sources2

            u = sources2.sources().getSources(title, year, imdb, tvdb, season, episode, tvshowtitle, premiered, quality)

            if u is not None:
                return u
        except:
            pass

        try:
            from ..modules import sources2

            u = sources2.sources().getURISource(url)

            if u is not False:
                direct = False
            if u is None or u is False:
                raise Exception()

            return u
        except:
            pass

        try:
            if '.google.com' not in url:
                raise Exception()
            from ..modules import directstream
            u = directstream.google(url)[0]['url']
            return u
        except:
            pass

        try:
            if 'filmon.com/' not in url:
                raise Exception()
            from resources.lib.modules import filmon
            u = filmon.resolve(url)
            return u
        except:
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
        except:
            pass

        if direct is True:
            return url


class player(xbmc.Player):
    def __init__ (self):
        self.totalTime = 0
        self.currentTime = 0
        self.name = ''
        self.title = ''
        self.year = ''
        self.season = None
        self.episode = None
        self.DBID = None
        self.getbookmark = False
        self.offset = '0'
        self.imdb = None
        self.tmdb = None

        xbmc.Player.__init__(self)


    def play(self, url, content=None):
        base = url

        c.log(f"[CM Debug @ 1397 in lists.py] inside lists.player.play(), url = {url}")

        if '$doregex[playurl]|' in url:
            url = indexer().get_x_url(url)
            c.log(f"[CM Debug @ 1439 in lists.py] url = {url}")



        url = resolver().get(url)
        if url is False:
            c.log(f"[CM Debug @ 1445 in lists.py] url (False) = {url}")
            return

        control.execute('ActivateWindow(busydialog)')
        url = resolver().process(url)
        control.execute('Dialog.Close(busydialog)')

        if url is None:
            #return control.infoDialog(control.lang(30705))
            return control.infoDialog('No working url found')
        if url is False:
            return

        meta = {}
        for i in [
            'title', 'originaltitle', 'tvshowtitle', 'year', 'season', 'episode', 'genre',
            'rating', 'votes', 'director', 'writer', 'plot', 'tagline'
            ]:
            try:
                meta[i] = control.infoLabel(f'listitem.{i}')
            except:
                pass
        meta = dict((k,v) for k, v in meta.items() if not v == '')
        if 'title' not in meta:
            meta['title'] = control.infoLabel('listitem.label')
        icon = control.infoLabel('listitem.icon')


        self.name = meta['title']
        self.year = meta['year'] if 'year' in meta else '0'
        self.getbookmark = True if content in ['episodes', 'movies'] else False
        self.offset = bookmarks().get(self.name, self.year)

        f4m = resolver().f4m(url, self.name)
        if f4m is not None:
            return


        item = control.item(path=url)
        try:
            item.setArt({'icon': icon})
        except:
            pass
        item.setInfo(type='Video', infoLabels = meta)
        control.player.play(url, item)
        control.resolve(int(sys.argv[1]), True, item)

        self.totalTime = 0
        self.currentTime = 0

        for _ in range(240):
            if self.isPlayingVideo():
                break
            control.sleep(1000)
        while self.isPlayingVideo():
            try:
                self.totalTime = self.getTotalTime()
                self.currentTime = self.getTime()
            except:
                pass
            control.sleep(2000)
        control.sleep(5000)

    def onPlayBackStarted(self):
        control.execute('Dialog.Close(all,true)')
        if self.getbookmark is True and self.offset != '0':
            self.seekTime(float(self.offset))

    def onPlayBackStopped(self):
        if self.getbookmark is True:
            bookmarks().reset(self.currentTime, self.totalTime, self.name, self.year)

    def onPlayBackEnded(self):
        self.onPlayBackStopped()


class bookmarks:
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

            if self.offset == '0':
                raise Exception()

            minutes, seconds = divmod(float(self.offset), 60) ; hours, minutes = divmod(minutes, 60)
            label = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
            label = control.lang(32502) % label

            try:
                yes = control.dialog.contextmenu([label, control.lang(32501), ])
            except:
                yes = control.yesnoDialog(label, '', '', str(name), control.lang(32503), control.lang(32501))

            if yes:
                self.offset = '0'

            return self.offset
        except:
            return offset

    def reset(self, currentTime, totalTime, name, year='0'):
        try:
            #if not control.setting('bookmarks') == 'true': raise Exception()
            timeInSeconds = str(currentTime)
            ok = int(currentTime) > 180 and (currentTime / totalTime) <= .92

            idFile = hashlib.md5()
            for i in name:
                idFile.update(str(i))
            for i in year:
                idFile.update(str(i))
            idFile = str(idFile.hexdigest())

            control.makeFile(control.dataPath)
            dbcon = database.connect(control.bookmarksFile)
            dbcur = dbcon.cursor()
            dbcur.execute("CREATE TABLE IF NOT EXISTS bookmark (""idFile TEXT, ""timeInSeconds TEXT, ""UNIQUE(idFile)"");")
            dbcur.execute("DELETE FROM bookmark WHERE idFile = '%s'" % idFile)
            if ok: dbcur.execute("INSERT INTO bookmark Values (?, ?)", (idFile, timeInSeconds))
            dbcon.commit()
        except:
            pass