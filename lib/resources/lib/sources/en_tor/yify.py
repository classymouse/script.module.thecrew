# -*- coding: utf-8 -*-

'''
********************************************************cm*
* The Crew Add-on
*
* @file yify.py
* @package script.module.thecrew
*
* @copyright (c) 2025, The Crew
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''

import re

from urllib.parse import urlencode, quote, parse_qs, urljoin

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import cache
from resources.lib.modules import control
from resources.lib.modules import debrid
from resources.lib.modules import source_utils
from resources.lib.modules.crewruntime import c



class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['yts.am', 'yts.hn','yts.rs', 'yts-official.mx']
        self.base_link = None
        self.search_link = '/browse-movies/%s'
        self.min_seeders = int(control.setting('torrent.min.seeders'))



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
        if debrid.status(True) is False:
            return

        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except Exception:
            return

    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []

            c.log(f"[CM Debug @ 67 in yify.py] url = {url}")

            if url is None:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            query = f"{data['title']} {data['year']}"

            url = self.search_link % quote(query)
            url = urljoin(self.base_link, url)
            c.log(f"[CM Debug @ 79 in yify.py] url = {url}")
            html = client.request(url)

            try:
                results = client.parseDom(html, 'div', attrs={'class': 'row'})[2]
                c.log(f"[CM Debug @ 84 in yify.py] results = {results}")
            except Exception:
                return sources

            items = re.findall(r'class="browse-movie-bottom">(.+?)</div>\s</div>', results, re.DOTALL)
            c.log(f"[CM Debug @ 89 in yify.py] items = {items}")
            if items is None:
                return sources

            for entry in items:
                try:
                    try:
                        link, name = re.findall('<a href="(.+?)" class="browse-movie-title">(.+?)</a>', entry, re.DOTALL)[0]
                        name = client.replaceHTMLCodes(name)
                        if cleantitle.get(name) != cleantitle.get(data['title']):
                            continue
                    except Exception:
                        continue
                    y = entry[-4:]
                    if y != data['year']:
                        continue

                    response = client.request(link)
                    try:
                        entries = client.parseDom(response, 'div', attrs={'class': 'modal-torrent'})
                        for torrent in entries:
                            link, name = re.findall('href="magnet:(.+?)" class="magnet-download download-torrent magnet" title="(.+?)"', torrent, re.DOTALL)[0]
                            link = f'magnet:{link}'
                            link = str(client.replaceHTMLCodes(link).split('&tr')[0])
                            quality, info = source_utils.get_release_quality(name, name)
                            try:
                                size = re.findall(r'((?:\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|MB|MiB))', torrent)[-1]
                                div = 1 if size.endswith(('GB', 'GiB')) else 1024
                                size = float(re.sub('[^0-9|/.|/,]', '', size)) / div
                                size = f'{size:.2f} GB'
                                info.append(size)
                            except Exception:
                                pass
                            info = ' | '.join(info)
                            sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en',
                                            'url': link, 'info': info, 'direct': False, 'debridonly': True})
                    except Exception:
                        continue
                except Exception:
                    continue

            return sources
        except Exception as e:
            c.log(f"[CM Debug @ 127 in yify.py] Exception in sources: {e}", 1)
            return sources




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
