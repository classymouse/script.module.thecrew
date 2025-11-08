# -*- coding: utf-8 -*-

'''
********************************************************cm*
* The Crew Add-on
*
* @file piratebay.py
* @package script.module.thecrew
*
* @copyright (c) 2025, The Crew
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''

import re
import traceback
import ast
from urllib.parse import parse_qs, urljoin, urlencode, quote_plus

from resources.lib.modules import cache, cleantitle, client, control, debrid, source_utils
from resources.lib.modules.crewruntime import c


class source:
    def __init__(self):
        self.priority = 0
        self.language = ['en']
        self.domains = [
            'prbay.top','pirateproxy.live', 'thepiratebay.org', 'thepiratebay.fun',
            'thepiratebay.asia', 'tpb.party', 'thepiratebay3.org', 'thepiratebayz.org',
            'thehiddenbay.com', 'piratebay.live', 'thepiratebay.zone'
            ]
        #self._base_link = None
        #self.search_link = '/s/?q=%s&page=0&&video=on&orderby=99'
        self._base_link = "https://apibay.org"
        self.search_link = '/q.php?q=%s&cat=0'
        #self.search_link = '/search/%s/1/99/200' #-direct link can flip pages

        self.min_seeders = int(control.setting('torrent.min.seeders'))

    @property
    def base_url(self):
        """Return the base URL of the torrent site.

        The base URL is the URL of the torrent site without any query
        parameters. It is retrieved from cache and updated every 2
        minutes.
        """
        if self._base_link is None:
            default_url = f"https://{self.domains[0]}"
            self._base_link = cache.get(self.__get_base_url, 120, default_url)

        return self._base_link

    @base_url.setter
    def base_url(self, value):
        """Setter for the base_url property.

        This method sets the base URL of the torrent site. The base URL
        is the URL of the torrent site without any query parameters.
        """
        self._base_link = value

    def movie(self, imdb, title, localtitle, aliases, year):

        if debrid.status(True) is False:
            return

        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except Exception:
            failure = traceback.format_exc()
            c.log('TPB - Exception: \n' + str(failure))
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):

        if debrid.status(True) is False:
            return

        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except Exception:
            failure = traceback.format_exc()
            c.log('TPB - Exception: \n' + str(failure))
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):

        if debrid.status(True) is False:
            return

        try:
            if url is None:
                return

            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except Exception:
            failure = traceback.format_exc()
            c.log('TPB - Exception: \n' + str(failure))
            return

    def sources(self, url, hostDict, hostprDict):
        """
        {
            "id": "53458028",
            "name": "4400 S01E01 480p x264-mSD",
            "info_hash": "8EA36B7B4F7F381A4703CE5308BF9F751B8AACBE",
            "leechers": "0",
            "seeders": "1",
            "num_files": "0",
            "size": "170288742",
            "username": "jajaja",
            "added": "1635245412",
            "status": "vip",
            "category": "205",
            "imdb": ""
        }
        """
        try:
            sources = []

            if url is None:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])


            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            query = '%s S%02dE%02d' % (
                data['tvshowtitle'],
                int(data['season']),
                int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (
                data['title'],
                data['year'])
            query = re.sub(r'(\\\|/| -|:|;|\*|\?|"|<|>|\|)', ' ', query)
            url = self.search_link % quote_plus(query)

            url = urljoin(self.base_url, url)
            #c.log(f"[CM Debug @ 130 in piratebay.py] url = {url}")
            html = client.request(url)
            #c.log(f"[CM Debug @ 117 in piratebay.py] html: {html}")
            #c.log(f"[CM Debug @ 133 in piratebay.py] type html: {type(html)}")

            def process_entry(entry, title, hdlr):
                try:
                    name = entry['name']

                    if str(cleantitle.get(title)) not in str(cleantitle.get(name)):
                        return
                    y = re.findall(r'[\.|\(|\[|\s](\d{4}|S\d*E\d*|S\d*)[\.|\)|\]|\s]', name)
                    if y:
                        y = y[-1].upper()
                    if y != hdlr:
                        return

                    seeders = int(entry['seeders'])
                    if self.min_seeders > seeders:
                        return

                    link = f'magnet:?xt=urn:btih:{entry["info_hash"]}'
                    quality, info = source_utils.get_release_quality(name, name)

                    size = entry['size']
                    if size == 0:
                        size = '0.00 GB'
                    else:
                        size = float(size) / 1024 / 1024 / 1024
                        size = f'{size:.2f} GB'
                    info.insert(0, size)

                    info = ' | '.join(info)
                    sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en', 'url': link, 'info': info, 'direct': False, 'debridonly': True})
                except Exception as e:
                    failure = traceback.format_exc()
                    c.log(f'[CM Debug @ 178 in piratebay.py]Traceback:: {failure}')
                    c.log(f'[CM Debug @ 178 in piratebay.py]Exception raised. Error = {e}')

            if html.startswith('['):
                try:
                    # html is a list in text so i need to convert it to a plain list
                    # ast.literal_eval creates a safe envir for py 3.x
                    html = ast.literal_eval(html)
                    if not html:
                        return sources
                    for entry in html:
                        process_entry(entry, title, hdlr)
                except Exception as e:
                    failure = traceback.format_exc()
                    c.log(f'[CM Debug @ 188 in piratebay.py]Traceback:: {failure}')
                    c.log(f'[CM Debug @ 189 in piratebay.py]Exception raised. Error = {e}')            #we have a listing returned

                try:
                    # c.log(f"[CM Debug @ 211 in piratebay.py] html is of type: {type(html)} and = {html}")
                    # Ensure html is a decoded string if bytes
                    if isinstance(html, bytes):
                        # c.log(f"[CM Debug @ 213 in piratebay.py] type(html): {type(html)} is bytes, decoding to str")
                        html = html.decode('utf-8')
                    # If html is a string representation of a list, parse it into a Python list
                    if isinstance(html, str):
                        try:
                            html = ast.literal_eval(html)
                        except Exception:
                            # leave as-is if cannot parse; further checks will guard against wrong types
                            pass
                    if not html:
                        return sources
                    # Only iterate if html is a list-like of dicts
                    if not isinstance(html, (list, tuple)):
                        return sources
                    for entry in html:
                        try:
                            # skip non-dict entries (protects against bytes iter yielding ints)
                            if not isinstance(entry, dict):
                                continue
                            name = entry.get('name', '')
                            if str(cleantitle.get(title)) not in str(cleantitle.get(name)):
                                continue
                            y = re.findall(r'[\.|\(|\[|\s](\d{4}|S\d*E\d*|S\d*)[\.|\)|\]|\s]', name)
                            if y:
                                y = y[-1].upper()
                            if y != hdlr:
                                continue

                            seeders = int(entry.get('seeders', 0))
                            if self.min_seeders > seeders:
                                continue

                            link = f'magnet:?xt=urn:btih:{entry.get("info_hash", "")}'
                            quality, info = source_utils.get_release_quality(name, name)

                            size = entry.get('size', 0)
                            #c.log(f"[CM Debug @ 146 in piratebay.py] size in bytes = {size} with type = {type(size)}")
                            try:
                                if int(size) == 0:
                                    size = '0.00 GB'
                                else:
                                    size = float(size) / 1024 / 1024 / 1024
                                    size = f'{size:.2f} GB'
                            except Exception:
                                size = '0.00 GB'
                            #c.log(f"[CM Debug @ 150 in piratebay.py] size = {size} with type = {type(size)}")
                            info.insert(0, size)

                            info = ' | '.join(info)
                            sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en', 'url': link, 'info': info, 'direct': False, 'debridonly': True})
                        except Exception as e:
                            failure = traceback.format_exc()
                            c.log(f'[CM Debug @ 178 in piratebay.py]Traceback:: {failure}')
                            c.log(f'[CM Debug @ 178 in piratebay.py]Exception raised. Error = {e}')

                        #except Exception as e:
                        #    c.log(f'TPB2 - Failed to parse search results:{e}')
                        #    continue
                except Exception as e:
                    failure = traceback.format_exc()
                    c.log(f'[CM Debug @ 171 in piratebay.py]Traceback:: {failure}')
                    c.log(f'[CM Debug @ 171 in piratebay.py]Exception raised. Error = {e}')

            else:
                html = html.replace('&nbsp;', ' ')
                try:
                    #results = client.parseDom(html, 'table', attrs={'id': 'searchResult'})[0]
                    results = client.parseDom(html, 'table', attrs={'id': 'searchResult'})[0]
                except Exception as e:
                    c.log(f'TPB1 - Failed to parse search results:{e}')
                    return sources
                rows = re.findall('<tr(.+?)</tr>', results, re.DOTALL)
                if rows is None:
                    return sources

                for entry in rows:
                    try:
                        try:
                            name = re.findall('class="detLink" title=".+?">(.+?)</a>', entry, re.DOTALL)[0]
                            name = client.replaceHTMLCodes(name)
                            # t = re.sub('(\.|\(|\[|\s)(\d{4}|S\d*E\d*|S\d*|3D)(\.|\)|\]|\s|)(.+|)', '', name, flags=re.I)
                            t_title = cleantitle.get(title) or ''
                            t_name = cleantitle.get(name) or ''
                            if t_title not in t_name:
                                continue
                        except Exception:
                            continue
                        y = re.findall(r'[\.|\(|\[|\s](\d{4}|S\d*E\d*|S\d*)[\.|\)|\]|\s]', name)[-1].upper()
                        if y != hdlr:
                            continue

                        try:
                            seeders = int(re.findall('<td align="right">(.+?)</td>', entry, re.DOTALL)[0])
                        except Exception:
                            continue
                        if self.min_seeders > seeders:
                            continue

                        try:
                            link = 'magnet:%s' % (re.findall('a href="magnet:(.+?)"', entry, re.DOTALL)[0])
                            link = str(client.replaceHTMLCodes(link).split('&tr')[0])
                        except Exception:
                            continue

                        quality, info = source_utils.get_release_quality(name, name)

                        try:
                            size = re.findall(r'((?:\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|MB|MiB))', entry)[-1]
                            div = 1 if size.endswith(('GB', 'GiB')) else 1024
                            size = float(re.sub('[^0-9|/.|/,]', '', size)) / div
                            size = f'{size:.2f} GB'
                            info.append(size)
                        except Exception:
                            pass

                        info = ' | '.join(info)
                        sources.append({'source': 'Torrent', 'quality': quality, 'language': 'en', 'url': link, 'info': info, 'direct': False, 'debridonly': True})
                    except Exception:
                        failure = traceback.format_exc()
                        c.scraper_error(f'Exception: {str(failure)}', 'Piratebay')
                        continue

            check = [i for i in sources if i['quality'] != 'CAM']
            if check:
                sources = check

            return sources
        except Exception:
            failure = traceback.format_exc()
            c.log('TPB - Exception: \n' + str(failure))
            return sources


    def __get_base_url(self, fallback):
        try:
            for domain in self.domains:
                try:
                    url = f'https://{domain}'
                    # c.log(f"[CM Debug @ 204 in piratebay.py] url = {url}")
                    result = client.request(url, limit=1, timeout='10')
                    result = re.findall('<input type="submit" title="(.+?)"', result, re.DOTALL)[0]
                    if result and 'Pirate Search' in result:
                        return url
                except Exception as e:
                    c.log(f"[CM Debug @ 192 in piratebay.py] exception 1 in __get_base_url: {e}")

        except Exception as e:
            c.log(f"[CM Debug @ 195 in piratebay.py] exception 2 in __get_base_url: {e}")


        return fallback

    def resolve(self, url):
        return url
