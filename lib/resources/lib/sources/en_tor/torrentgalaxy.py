# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on - Scraper Module
 *
 *
 * @file torrentgalaxy.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2025, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
  ***********************************************************cm*
'''

import re
from urllib.parse import urlencode, quote_plus, parse_qs, urljoin

from resources.lib.modules import cleantitle
from resources.lib.modules import debrid
from resources.lib.modules import source_utils
from resources.lib.modules.crewruntime import c
from resources.lib.modules import client



class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['torrentgalaxy.to']
        #self.base_link = 'https://torrentgalaxy.to' # cm - eu blocked
        self.base_link = "https://tgx.rs"
        #self.search_link = '/torrents.php?search=%s&sort=seeders&order=desc'
        self.search_link = '/torrents.php?search=%s'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
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
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url is None:
                return sources
            if debrid.status() is False:
                raise Exception()
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']

            hdlr = f"S{int(data['season']):02d}E{int(data['episode']):02d}" if 'tvshowtitle' in data else data['year']

            query = f"{data['tvshowtitle']} s{int(data['season']):02d}e{int(data['episode']):02d}" if 'tvshowtitle' in data else f"{data['title']} {data['year']}"
            query = re.sub(r'(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)

            url = self.search_link % quote_plus(query)
            url = urljoin(self.base_link, url)

            try:
                r = client.request(url)
                posts = client.parseDom(r, 'div', attrs={'class': 'tgxtable'})
                for post in posts:
                    link = re.findall('a href="(magnet:.+?)"', post, re.DOTALL)
                    try:
                        size = re.findall(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GiB|MiB|GB|MB))', post)[0]
                        div = 1 if size.endswith('GB') else 1024
                        size = float(re.sub('[^0-9|/.|/,]', '', size.replace(',', '.'))) / div
                        size = f"{size:.2f} GB"
                    except Exception:
                        size = '0'
                    for url in link:
                        if hdlr not in url:
                            continue
                        quality, info = source_utils.get_release_quality(url)

                        url = url.split('&dn=', 1)[0]

                        #cm - this will never happen, only btih magnet link left
                        if any(x in url for x in ['FRENCH', 'Ita', 'italian', 'TRUEFRENCH', '-lat-', 'Dublado']):
                            continue

                        info.append(size)
                        info = ' | '.join(info)

                        sources.append({
                            'source': 'Torrent', 'quality': quality, 'language': 'en', 'url': url,
                            'info': info, 'direct': False, 'debridonly': True
                            })
            except:
                return
            return sources
        except:
            return sources

    def resolve(self, url):
        return url
