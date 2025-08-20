# -*- coding: utf-8 -*-

'''
    OathScrapers module

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
import requests

from six import ensure_text

#try: from urlparse import parse_qs, urljoin
#except ImportError: from urllib.parse import parse_qs, urljoin
##try: from urllib import urlencode, quote_plus
#except ImportError: from urllib.parse import urlencode, quote_plus


from urllib.parse import urlparse, parse_qs, urljoin, urlencode, quote_plus

from resources.lib.modules import debrid
from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import source_utils
from resources.lib.modules import log_utils
from resources.lib.modules.crewruntime import c

class source:
    def __init__(self):
        self.priority = 0
        self.language = ['en']
        self.domains = ['btdig.com']
        self.base_link = 'https://www.torrentdownload.info'
        self.search_link = '/search?q=%s'
        self.session = requests.Session()

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            c.log('tdl0 - Exception', 1)
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            c.log('tdl1 - Exception', 1)
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None: return

            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except:
            c.log('tdl2 - Exception', 1)
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if debrid.status() is False:
                return sources

            if url is None:
                c.log(f"[CM Debug @ 85 in tordl.py] url = {url}")
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            query = '%s s%02de%02d' % (data['tvshowtitle'], int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (data['title'], data['year'])
            query = re.sub(r'(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query).lower()
            #orig_query = query
            #query =query.replace(' ', '+')

            url = urljoin(self.base_link, self.search_link % quote_plus(query))

            r = client.request(url)
            #r = scraper.get(url).content
            r = ensure_text(r, errors='replace').strip()

            posts = client.parseDom(r, 'table', attrs={'class': 'table2', 'cellspacing': '0'})
            posts = client.parseDom(posts, 'tr')[1:]

            for post in posts:
                if 'php' or '/feed' in post:
                    continue
                links = client.parseDom(post, 'a', ret='href')[0]
                c.log(f"[CM Debug @ 108 in tordl.py] links = {links} with type = {type(links)}")
                links = client.replaceHTMLCodes(links).lstrip('/')
                hash = links.split('/')[0]
                name = links.split('/')[1]
                if len(hash) != 40:
                    c.log(f"[CM Debug @ 112 in tordl.py] continueing in tordl sources with hash = {hash}")
                    continue

                url = f'magnet:?xt=urn:btih:{hash}'
                c.log(f"[CM Debug @ 115 in tordl.py] url = {url}")

                if query not in str(cleantitle.get_title(name)):
                    c.log(f"[CM Debug @ 110 in tordl.py] continueing in tordl sources with title = {name} and query = {query}")
                    continue

                quality, info = source_utils.get_release_quality(name)
                try:
                    #size = client.parseDom(post, 'td', attrs={'class': 'tdnormal'})[1]
                    size = client.parseDom(post, 'td', attrs={'class': 'tdnormal'})[1]
                    dsize, isize = source_utils._size(size)
                except:
                    dsize, isize = 0.0, ''

                info.insert(0, isize)

                info = ' | '.join(info)

                sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en', 'url': url, 'info': info,
                                'direct': False, 'debridonly': True, 'size': dsize, 'name': name})

            return sources
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 130 in tordl.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 130 in tordl.py]Exception raised. Error = {e}')

        #except Exception as e:
            #c.log(f'tdl3 - Exception raised:: {e}', 1)
            return sources

    def resolve(self, url):
        return url
