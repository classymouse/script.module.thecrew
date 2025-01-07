# -*- coding: utf-8 -*-

'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


import re
import base64
import json

from resources.lib.modules import cache
from resources.lib.modules import control
from resources.lib.modules import client
from resources.lib.modules.crewruntime import c
from urllib.parse import parse_qs, urljoin, urlencode, quote_plus, quote



class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['ororo.tv']
        self.base_link = 'https://ororo.tv'
        self.moviesearch_link = '/api/v2/movies'
        self.tvsearch_link = '/api/v2/shows'
        self.movie_link = '/api/v2/movies/%s'
        self.show_link = '/api/v2/shows/%s'

        self.episode_link = '/api/v2/episodes/%s'

        self.user = control.setting('ororo.user')
        self.password = control.setting('ororo.pass')
        self.user = f'{self.user}:{self.password}'
        self.encoded = base64.b64encode(self.user.encode('utf-8')).decode('utf-8')
        self.headers = {
        'Authorization': 'Basic %s' % self.encoded,
        'User-Agent': 'Kodi'
        }


    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            if (self.user == '' or self.password == ''): raise Exception()

            #url = cache.get(self.ororo_moviecache, 60, self.user)
            url = self.ororo_moviecache(self.user)
            url = [i[0] for i in url if imdb == i[1]][0]
            url= self.movie_link % url

            return url
        except:
            return


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            if (self.user == '' or self.password == ''):
                raise Exception()

            url = cache.get(self.ororo_tvcache, 120, self.user)
            url = [i[0] for i in url if imdb == i[1]][0]
            url= self.show_link % url

            return url
        except:
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if (self.user == '' or self.password == ''): raise Exception()

            if url is None:
                return

            url = urljoin(self.base_link, url)

            r = client.request(url, headers=self.headers)
            r = json.loads(r)['episodes']
            r = [(str(i['id']), str(i['season']), str(i['number']), str(i['airdate'])) for i in r]

            url = [i for i in r if season == '%01d' % int(i[1]) and episode == '%01d' % int(i[2])]
            url += [i for i in r if premiered == i[3]]

            url= self.episode_link % url[0][0]

            return url
        except:
            return


    def ororo_moviecache(self, user):
        try:
            url = urljoin(self.base_link, self.moviesearch_link)
            c.log(f"[CM Debug @ 105 in ororo.py] url = {url}")

            r = client.request(url, headers=self.headers)
            c.log(f"[CM Debug @ 108 in ororo.py] r = {r}")
            r = json.loads(r)['movies']
            r = [(str(i['id']), str(i['imdb_id'])) for i in r]
            r = [(i[0], 'tt' + re.sub('[^0-9]', '', i[1])) for i in r]
            return r
        except:
            return


    def ororo_tvcache(self, user):
        try:
            url = urljoin(self.base_link, self.tvsearch_link)

            r = client.request(url, headers=self.headers)
            r = json.loads(r)['shows']
            r = [(str(i['id']), str(i['imdb_id'])) for i in r]
            r = [(i[0], 'tt' + re.sub(r'[^0-9]', '', i[1])) for i in r]
            return r
        except:
            return


    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []

            if url is None:
                return sources

            if (self.user == '' or self.password == ''):
                raise Exception()

            url = urljoin(self.base_link, url)
            url = client.request(url, headers=self.headers)
            c.log(f"[CM Debug @ 144 in ororo.py] url = {url}")
            url = json.loads(url)['url']

            sources.append({
                'source': 'ororo', 'quality': 'HD', 'language': 'en', 'url': url,
                'direct': True, 'debridonly': False
                })

            return sources
        except:
            return sources


    def resolve(self, url):
        return url
