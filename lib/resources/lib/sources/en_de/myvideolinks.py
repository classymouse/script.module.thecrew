# -*- coding: utf-8 -*-

'''
********************************************************cm*
* The Crew Add-on
*
* @file myvideolinks.py
* @package script.module.thecrew
*
* @copyright (c) 2025, The Crew
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''

import re


from resources.lib.modules import cleantitle
from resources.lib.modules import debrid
from resources.lib.modules import client
from resources.lib.modules import source_utils


from resources.lib.modules.crewruntime import c


from urllib.parse import parse_qs, urljoin, urlencode

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['iwantmyshow.tk', 'iwantmyshow.tk', 'go.myvideolinks.net', 'to.myvideolinks.net/', 'see.home.kg', 'to.myvideolinks.net']
        self.base_link = 'https://new.myvid.one/'
        self.search_link = '/?s=%s'

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
        try:
            sources = []

            if url is None:
                return sources

            if debrid.status() is False:
                raise Exception()

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data.get('tvshowtitle', data['title'])

            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            hostDict = hostprDict + hostDict

            items, urls, posts, links = [], [], [], []

            url = urljoin(self.base_link, self.search_link % data['imdb'])
            r = client.request(url)
            if 'CLcBGAs/s1600/1.jpg' in r:
                url = client.parseDom(r, 'a', ret='href')[0]
                self.base_link = url = urljoin(url, self.search_link % data['imdb'])
                r = client.request(url)
            posts = client.parseDom(r, 'article')
            if not posts and 'tvshowtitle' in data:
                url = urljoin(self.base_link, self.search_link % (cleantitle.geturl(title).replace('-','+') + '+' + hdlr))
                r = client.request(url, headers={'User-Agent': client.agent()})
                posts += client.parseDom(r, 'article')
                url = urljoin(self.base_link, self.search_link % cleantitle.geturl(title).replace('-','+'))
                r = client.request(url, headers={'User-Agent': client.agent()})
                posts += client.parseDom(r, 'article')

            if not posts: return sources
            for post in posts:
                try:
                    t = client.parseDom(post, 'img', ret='title')[0]
                    u = client.parseDom(post, 'a', ret='href')[0]
                    s = re.search('((?:\d+\.\d+|\d+\,\d+|\d+)\s*(?:GiB|MiB|GB|MB))', post)
                    s = s.groups()[0] if s else '0'
                    items += [(t, u, s, post)]
                except:
                    pass
            items = set(items)
            items = [i for i in items if cleantitle.get(title) in cleantitle.get(i[0])]

            for item in items:
                name = item[0]
                u = client.request(item[1])
                if 'tvshowtitle' in data:
                    if hdlr.lower() not in name.lower():
                        pattern = '''<p>\s*%s\s*<\/p>(.+?)<\/ul>''' % hdlr.lower()
                        r = re.search(pattern, u, flags = re.I|re.S)
                        if not r: continue
                        links = client.parseDom(r.groups()[0], 'a', ret='href')
                    else:
                        links = client.parseDom(u, 'a', ret='href')
                else: links = client.parseDom(u, 'a', ret='href')
                for url in links:
                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if not valid: continue
                    host = client.replaceHTMLCodes(host)
                    host = host.encode('utf-8')

                    info = []
                    quality, info = source_utils.get_release_quality(name, url)

                    try:
                        size = re.findall('((?:\d+\.\d+|\d+\,\d+|\d+) (?:GB|GiB|MB|MiB))', item[2])[0]
                        div = 1 if size.endswith(('GB', 'GiB')) else 1024
                        size = float(re.sub('[^0-9|/.|/,]', '', size)) / div
                        size = '%.2f GB' % size
                        info.append(size)
                    except:
                        pass

                    info = ' | '.join(info)
                    sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': False})

            return sources
        except:
            return sources

    def resolve(self, url):
        return url