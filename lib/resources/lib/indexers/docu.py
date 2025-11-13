# -*- coding: utf-8 -*-

'''
********************************************************cm*
* The Crew Add-on
*
* @file docu.py
* @package script.module.thecrew
*
* @copyright (c) 2025, The Crew
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''

import os
import re
import sys
import time
# import trace
import traceback

from urllib.parse import quote_plus, urlparse
import requests



import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin


# import urllib
# import six

import resolveurl
# from xbmcplugin import setResolvedUrl

from bs4 import BeautifulSoup as bs

from ..modules.listitem import ListItemInfoTag

from ..modules import cache
from ..modules import client
from ..modules import control
# from ..modules import workers
# from ..modules import log_utils
from ..modules.crewruntime import c

_handle = syshandle = int(sys.argv[1])

artPath = control.artPath()
addonFanart = control.addonFanart()


class Documentary:
    def __init__(self):
        self.list = []
        self.docu_link = 'https://topdocumentaryfilms.com/'
        self.docu_cat_list = 'https://topdocumentaryfilms.com/watch-online/'
        #BASE_URL = "https://documentaryheaven.com"
        self.session = requests.Session()
        self.addon = xbmcaddon.Addon
        self.session.headers = {
            "User-Agent": "kodi.tv",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip",
            "DNT": "1", # Do Not Track Request Header
            "Connection": "close"
        }
        #self.YOUTUBE_PLUGIN = "plugin://plugin.video.youtube/"
        self.YOUTUBE_PLUGIN = "plugin://plugin.video.youtube/"
        self.VIMEO_PLUGIN = "plugin://plugin.video.vimeo/"
        self.DAILYMOTION_PLUGIN = "plugin://plugin.video.dailymotion_com/"

    def get_html(self, url):
        # page_response = self.session.get(url)
        page_response = client.request(url)
        c.log(f"[CM Debug @ 77 in docu.py] url = {page_response}")
        return bs(page_response, "html.parser")

    def get_json(self, url):
        page_response = self.session.get(url)
        json = page_response.json()
        return json

    def root(self):
        """
        This function retrieves the documentary categories from the documentary heaven website,
        parses the HTML response, and adds the categories to the list. It then adds the list
        to the Kodi directory and returns the list.

        Returns:
            list: The list of documentary categories.

        Raises:
            Exception: If there is an error retrieving the HTML or parsing the categories.
        """
        try:
            # html = client.request(self.docu_cat_list) #cm - use client request because cf

            soup = self.get_html(self.docu_cat_list)
            c.log(f"[CM Debug @ 99 in docu.py] url = {soup}")
            # soup = BeautifulSoup(html, 'html.parser')
            # c.log(f"[CM Debug @ 87 in docu.py] soup = {soup}")

            links=[]
            soup = soup.find_all('div', attrs={'class':'sitemap-wraper'})
            for child in soup:
                links.append(child.find('h2').find_all('a'))

            for link in links:
                link = bs(str(link[0]), 'html.parser')
                c.log(f"[CM Debug @ 107 in docu.py] link = {link}")
                cat_url = link.find("a").attrs.get("href")
                c.log(f"[CM Debug @ 109 in docu.py] url = {cat_url}")
                cat_title = link.text
                cat_icon = control.addonIcon()
                cat_action = f'docuHeaven&docuCat={cat_url}'
                self.list.append({'name': cat_title, 'url': cat_url, 'image': cat_icon, 'action': cat_action})
        except Exception as e:

            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 119 in docu.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 119 in docu.py]Exception raised. Error = {e}')
        #     pass
        # except Exception as e:
        #     c.log(f'root() Exception: {e}')

        self.addDirectory(self.list)
        return self.list

    def docu_list(self, url):
        try:
            #html = client.request(url)



            # soup = BeautifulSoup(html, 'html.parser')
            soup = self.get_html(url)




            article_soup = soup.find_all('article', attrs={'class':'section--border'})
            c.log(f"[CM Debug @ 105 in docu.py] soup = {soup}")
            for item in article_soup:
                c.log(f'[CM DEBUG in docu.py @ 101] item = {item}')
                docu_img = item.find('img')
                docu_icon = docu_img.get("src")
                temp = item.find('source', attrs={'srcset': ''})
                link = item.find('a')
                docu_url = link.get('href')
                docu_title = link.get('title')
                docu_action = f'docuHeaven&docuPlay={docu_url}'

                self.list.append({'name': docu_title, 'url': docu_url, 'image': docu_icon, 'action': docu_action})
            try:
                soup = bs(html, 'html.parser')
                if soup := soup.find('div', attrs={'class': 'pagination module'}):
                    is_ytube = False
                    soup.find()
                    links = soup.find_all("a")

                    links =
                    link = links[(len(links)-1)]
                    docu_action = f'docuHeaven&docuCat={link}'
                    self.list.append({
                        'name': control.lang(32053),
                        'url': link,
                        'image': control.addonNext(),
                        'action': docu_action
                        })
                else:
                    docu_action = ''
                c.log(f'[CM DEBUG @ 115] docu_action = {docu_action}')
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 121 in docu.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 121 in docu.py]Exception raised. Error = {e}')
                pass

        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 131 in docu.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 132 in docu.py]Exception raised. Error = {e}')
            c.log(f'docu_list() Exception: {e}')
        self.addDirectory(self.list)
        return self.list

    def docu_play(self, url):
        """
        Retrieves the documentary video from the given URL and plays it.

        Args:
            url (str): The URL of the documentary video.

        Raises:
            Exception: If there is an error during the process.

        Returns:
            None
        """
        try:
            docu_page = client.request(url)
            docu_item = client.parseDOM(docu_page, 'meta', attrs={'itemprop':'embedUrl'}, ret='content')[0]
            if 'http:' not in docu_item and  'https:' not in docu_item:
                docu_item = 'https:' + docu_item
            url = docu_item
            #docu_title = client.parseDOM(docu_page, 'meta', attrs={'property':'og:title'}, ret='content')[0].encode('utf-8', 'ignore').decode('utf-8').replace("&amp;","&").replace('&#39;',"'").replace('&quot;','"').replace('&#39;',"'").replace('&#8211;',' - ').replace('&#8217;',"'").replace('&#8216;',"'").replace('&#038;','&').replace('&acirc;','')
            docu_title = client.parseDOM(docu_page, 'meta', attrs={'property':'og:title'}, ret='content')[0].replace("&amp;","&").replace('&#39;',"'").replace('&quot;','"').replace('&#39;',"'").replace('&#8211;',' - ').replace('&#8217;',"'").replace('&#8216;',"'").replace('&#038;','&').replace('&acirc;','')
            #c.log('[CLASSY @ 106] ' + str(docu_title))
            if 'youtube' in url:
                if 'videoseries' not in url:
                    video_id = url.split("/")[-1]
                    c.log(f'[CLASSY @ 110] video_id = {video_id}')
                    url = f'plugin://plugin.video.youtube/play/?video_id={video_id}'
                    #url = 'https://www.youtube.com/watch?v=' + video_id
                    c.log('[CLASSY @ 112] ' + str(url))
                else: pass
            elif 'dailymotion' in url:
                video_id = client.parseDOM(docu_page, 'div', attrs={'class':'youtube-player'}, ret='data-id')[0]
                url = self.getDailyMotionStream(video_id)
            else:
                c.log(f'Play Documentary: Unknown Host: {url}', trace=1)
                c.info_dialog(message=f'Unknown Host - Report To Developer: {url}', heading='Unknown Host', icon='ERROR', time=3000, sound=False)

            c.log(f'[CM DEBUG @ 170] PlayMedia({url})')




            listitem = xbmcgui.ListItem(label=docu_title, offscreen=True)
            listitem.setProperty('IsPlayable', 'true')
            listitem.setInfo('video', {'Title': docu_title, 'Genre': 'docu', 'Plot': 'Plot created by Classy ;-)'})


            #play_item = ListItem(path=url)
            #setResolvedUrl(self.addon.handle, True, listitem=play_item)


            #xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)
            #xbmc.Player().play(url, listitem)
            #xbmc.Player().play(playlist, listitem, windowed, startpos)

#            name = docu_title
#            icon = control.infoLabel('ListItem.Icon')
#
#            item = control.item(label=name, path=url)
#            item.setArt({'icon': icon, 'thumb': icon, 'poster': icon})
#            item.setInfo(type="video", infoLabels={"title": name})
#
#            item.setProperty('IsPlayable','true')
#            #control.resolve(handle=int(sys.argv[1]), succeeded=True, listitem=item)
            #xbmc.Player().play(url, listitem)
            #xbmc.Player().play(playlist, listitem, windowed, startpos)

            #print url
            hmf = resolveurl.HostedMediaFile(url)
            if hmf:
                resolved = hmf.resolve()
            item = xbmcgui.ListItem(path=resolved)
            item.setProperty('IsPlayable', 'true')
            xbmc.executebuiltin(f'PlayMedia({resolved})' )




            c.log(f'[CM DEBUG in docu.py @ 202] resolved = {resolved}')
            #xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)


            #control.player.play(url, item)
            xbmc.Player().play(url)

#            control.execute('PlayMedia(%s)' % url)
#           item = xbmcgui.ListItem(str(docu_title)) # iconImage and thumbnailImage removed in Kodi Matrix
#           item.setInfo(type='video', infoLabels={'Title': str(docu_title), 'Plot': str(docu_title)})
#           item.setProperty('IsPlayable','true')
#           item.setPath(url)
            #control.resolve(int(sys.argv[1]), True, item)
#            xbmc.Player().play(url)
            #xbmc.executebuiltin('PlayMedia(%s)' % url)
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log('[CM @ 210 in episodes]Traceback:: ' + str(failure))
            c.log('[CM @ 211 in episodes]Exception raised in docu_play. Error = ' + str(e))
            #c.log('tmdb-list1 Exception', 1)
            #c.log('docu_play() Exception: ' + str(e))




    # Code originally written by gujal, as part of the DailyMotion Addon in the official Kodi Repo. Modified to fit the needs here.
    def getDailyMotionStream(self, id):
        headers = {'User-Agent':'Android'}
        cookie = {'Cookie':"lang=en_US; ff=off"}
        r = requests.get(f"http://www.dailymotion.com/player/metadata/video/{id}", headers=headers, cookies=cookie, timeout=10)
        content = r.json()
        if content.get('error') is not None:
            error = (content['error']['title'])
            xbmc.executebuiltin('XBMC.Notification(Info:,'+ error +' ,5000)')
            return
        else:
            cc = content['qualities']
            cc = cc.items()
            cc = sorted(cc,key=self.sort_key,reverse=True)
            m_url = ''
            other_playable_url = []
            for source,json_source in cc:
                source = source.split("@")[0]
                for item in json_source:
                    m_url = item.get('url',None)
                    if m_url:
                        if source == "auto" :
                            continue
                        elif  int(source) <= 2 :
                            if 'video' in item.get('type', None):
                                return m_url
                        elif '.mnft' in m_url:
                            continue
                        other_playable_url.append(m_url)
            if len(other_playable_url) >0: # probably not needed, only for last resort
                for m_url in other_playable_url:
                    if '.m3u8?auth' in m_url:
                        rr = requests.get(m_url, cookies=r.cookies.get_dict() ,headers=headers, timeout=10)
                        if rr.headers.get('set-cookie'):
                            print('adding cookie to url')
                            strurl = re.findall(r'(http.+)', rr.text)[0].split('#cell')[0]+'|Cookie='+rr.headers['set-cookie']
                        else:
                            strurl = re.findall(r'(http.+)', rr.text)[0].split('#cell')[0]
                        return strurl

    def addDirectoryItem(self, name, query, thumb, icon, context=None, queue=False, is_action=True, is_folder=True) -> None:
        try:
            name = control.lang(name)
        except Exception:
            pass
        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])
        queueMenu = control.lang(32065)

        url = f'{sysaddon}?action={query}' if is_action is True else query
        thumb = os.path.join(artPath, thumb) if artPath is not None else icon
        cm = []
        if queue:
            cm.append((queueMenu, f'RunPlugin({sysaddon}?action=playlist_QueueItem)'))
        if context:
            cm.append((control.lang(context[0]), f'RunPlugin({sysaddon}?action={context[1]})'))
        try:
            item = control.item(label=name, offscreen=True)
        except Exception:
            item = control.item(label=name)



        item.setProperty('IsPlayable', 'true')

        infolabels={'title': name, 'plot': "Documentary"}

        info_tag = ListItemInfoTag(item, 'video')


        info_tag.set_info(infolabels)





        item.addContextMenuItems(cm)
        item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': addonFanart})
        control.addItem(handle=syshandle, url=url, listitem=item, isFolder=is_folder)

    def endDirectory(self):
        syshandle = int(sys.argv[1])
        control.content(syshandle, 'addons')
        control.directory(syshandle, cacheToDisc=True)

    def _add_folder_item(self, items, title, url, icon_url, fanart_url,
                            sort_title="", isfolder=True, isplayable=False,
                            date=None, info=None, context_menu_items=None,
                            offscreen=True):

        if fanart_url is None:
            fanart_url = os.path.join(self.addon.media, "fanart_blur.jpg")

        if icon_url is None:
            icon_url = os.path.join(self.addon.media, "icon_trans.png")

        list_item = ListItemInfoTag(label=title, offscreen=offscreen)
        list_item.setArt({"thumb": icon_url, "fanart": fanart_url})
        list_item.setInfo("video", {"title": title, "sorttitle": sort_title})

        if isplayable:
            list_item.setProperty("IsPlayable", "true")
        else:
            list_item.setProperty("IsPlayable", "false")

        if date is not None:
            list_item.setInfo("video", {"date": date})

        if info is not None:
            list_item.setInfo("video", {"plot": info})

        if context_menu_items is not None:
            list_item.addContextMenuItems(context_menu_items)

        items.append((url, list_item, isfolder))








    def addDirectory(self, items, queue=False, isFolder=True):
        if items is None or len(items) == 0:
            control.idle()
            control.infoDialog(message=control.lang(33049), heading='[CM]' + control.lang(32002), sound=True)
            #sys.exit()
        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])
        addonThumb = control.addonThumb()
        artPath = control.artPath()
        queueMenu = control.lang(32065)
        playRandom = control.lang(32535)
        addToLibrary = control.lang(32551)
        for i in items:
            try:
                name = i['name']
                if i['image'].startswith('http'):
                    thumb = i['image']
                elif artPath:
                    thumb = os.path.join(artPath, i['image'])
                else:
                    thumb = addonThumb
                try:
                    item = control.item(label=name, offscreen=True)
                except Exception:
                    item = control.item(label=name)

                url = f'{sysaddon}?action={i["action"]}'
                if 'url' in i:
                    url += f'&url={quote_plus(str(i["url"]))}'

                if isFolder:
                    item.setProperty('IsPlayable', 'false')
                else:
                    item.setProperty('IsPlayable', 'true')
                    item.setInfo("mediatype", "video")
                    item.setInfo("audio", '')

                item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': control.addonFanart()})
                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log(f'[CM Debug @ 430 in docu.py]Traceback:: {failure}')
                c.log(f'[CM Debug @ 430 in docu.py]Exception raised. Error = {e}')
                pass
            # except Exception as e:
            #     c.log(f'[CM DEBUG in docu.py @ 349] Exception in addDirectory: {e}')
            #     pass
        control.content(syshandle, 'addons')
        control.directory(syshandle, cacheToDisc=True)