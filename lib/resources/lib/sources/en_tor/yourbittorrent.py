# -*- coding: utf-8 -*-

'''
********************************************************cm*
* The Crew Add-on
*
* @file yourbittorrent.py
* @package script.module.thecrew
*
* @copyright (c) 2025, The Crew
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''


import re

from urllib.parse import urlencode, quote_plus,  parse_qs, urljoin

from resources.lib.modules import cache
from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import debrid
from resources.lib.modules import source_utils
from resources.lib.modules import workers
from resources.lib.modules import utils
from resources.lib.modules.crewruntime import c


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['yourbittorrent.com', 'yourbittorrent2.com']
        #self.base_link = 'https://yourbittorrent.com'
        self.base_link = None
        self.search_link = '?q=%s'
        self.aliases = []
        self.sources_list = []


    @property
    def base_link(self):
        if not self._base_link:
            #self._base_link = cache.get(self.__get_base_url, 120, 'https://%s' % self.domains[0])
            self._base_link = cache.get(self.__get_base_url, 0, 'https://%s' % self.domains[0])
        return self._base_link

    @base_link.setter
    def base_link(self, value):
        self._base_link = value

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            c.log('YourBT0 - Exception', 1)
            return


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            c.log('YourBT1 - Exception', 1)
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None:
                return
            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except:
            c.log('YourBT2 - Exception', 1)
            return


    def sources(self, url, hostDict, hostprDict):

        try:

            c.log(f"[CM Debug @ 91 in yourbittorrent.py] url = {url}")
            if url is None:
                return self.sources_list

            if debrid.status() is False:
                return self.sources_list

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            self.title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            self.title = self.title.replace('&', 'and').replace('Special Victims Unit', 'SVU')

            self.hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']
            self.year = data['year']

            query = ' '.join((self.title, self.hdlr))
            query = re.sub('[^A-Za-z0-9\s\.-]+', '', query)

            url = self.search_link % quote_plus(query)
            url = urljoin(self.base_link, url).replace('+', '-')
            c.log(f"[CM Debug @ 113 in yourbittorrent.py]\n\n\n url = {url} \n\n\n")

            try:
                result = client.request(url)
                c.log(f"[CM Debug @ 116 in yourbittorrent.py] r = {result}")
                links = re.findall('<a href="(/torrent/.+?)"', result, re.DOTALL)

                c.log(f"[CM Debug @ 118 in yourbittorrent.py] links = {repr(links)}")

                threads = []
                for link in links:
                    threads.append(workers.Thread(self.get_sources, link))

                [i.start() for i in threads]
                [i.join() for i in threads]

                return self.sources_list
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 133 in yourbittorrent.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 134 in yourbittorrent.py]Exception raised. Error = {e}')
                return self.sources_list
            #except Exception as e:
            #    c.log(f'YourBT3 - Exception: {e}', 1)
            #    return self.sources_list

        except Exception as e:
            c.log(f'YourBT4 - Exception: {e}', 1)
            return self.sources_list


    def get_sources(self, link):
        try:
            url = urljoin(self.base_link, link)
            c.log(f"[CM Debug @ 128 in yourbittorrent.py] url = {url}")
            result = client.request(url)

            info_hash = re.findall('<kbd>(.+?)<', result, re.DOTALL)[0]
            url = f'magnet:?xt=urn:btih:{info_hash}'

            name = re.findall('<h3 class="card-title">(.+?)<', result, re.DOTALL)[0]
            #url = '%s%s%s' % (url, '&dn=', str(name))
            url = f"{url}&dn={name}"

            size = re.findall('<div class="col-3">File size:</div><div class="col">(.+?)<', result, re.DOTALL)[0]

            if url in str(self.sources_list):
                return

            if any(x in url.lower() for x in ['french', 'italian', 'spanish', 'truefrench', 'dublado', 'dubbed']):
                return

            title = name.split(self.hdlr)[0].replace(self.year, '').replace('(', '').replace(')', '').replace('&', 'and').replace('+', ' ')

            if str(cleantitle.get(title)) not in str(cleantitle.get(self.title)):
                return

            if self.hdlr not in name:
                return

            quality, info = source_utils.get_release_quality(name, url)

            try:
                size = re.findall('<div class="col-3">File size:</div><div class="col">(.+?)<', result, re.DOTALL)[0]
                size = re.findall(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GiB|MiB|GB|MB))', size)[0]
                div = 1 if size.endswith('GB') else 1024
                size = float(re.sub('[^0-9|/.|/,]', '', size.replace(',', '.'))) / div
                #size = '%.2f GB' % size
                size = f'{size:.2f} GB'
                info.insert(0, size)
            except Exception as e:
                c.log(f"[CM Debug @ 172 in yourbittorrent.py] Exception YBT: {e}", 1)
                size = '0'
                pass

            info = ' | '.join(info)

            self.sources_list.append({
                'source': 'torrent', 'quality': quality, 'language': 'en', 'url': url,
                'info': info, 'direct': False, 'debridonly': True
                })

        except:
            c.log('YourBT5 - Exception', 1)
            pass




    def __get_base_url(self, fallback):
        try:
            for domain in self.domains:
                try:
                    url = 'https://%s' % domain
                    result = client.request(url, timeout=7)
                    result = c.ensure_text(result, errors='ignore')
                    search_n = re.findall('<title>(.+?)</title>', result, re.DOTALL)[0]
                    if result and '1337x' in search_n:
                        return url
                except Exception:
                    pass
        except Exception:
            pass

        return fallback



    def resolve(self, url):
        return url