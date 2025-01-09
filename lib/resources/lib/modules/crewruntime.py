# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file crewruntime.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''


import os
import sys
import re
import platform
import json
import base64
from datetime import datetime
from io import open
#import traceback
from inspect import getframeinfo, stack

import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin



#from resources.lib.modules.listitem import ListItemInfoTag



#from resources.lib.modules import control

imageSizes = (
    {'poster': 'w185', 'fanart': 'w300', 'still': 'w300', 'profile': 'w185'},
    {'poster': 'w342', 'fanart': 'w780', 'still': 'w500', 'profile': 'w342'},
    {'poster': 'w780', 'fanart': 'w1280', 'still': 'w780', 'profile': 'h632'},
    {'poster': 'original', 'fanart': 'original', 'still': 'original', 'profile': 'original'}
)


class CrewRuntime:
    '''
    Global new superclass starting to run alongside the old code

    '''

    # ============================cm=
    # class variable shared by all instances
    # globals here

    transpath = xbmcvfs.translatePath
    lang = xbmcaddon.Addon().getLocalizedString
    listItem = xbmcgui.ListItem
    addonInfo = xbmcaddon.Addon().getAddonInfo

    # ============================cm=

    def __init__(self):

        '''
        # cm - can later be used on a child class as temp obj to super crewRuntime
        # super().__init__(self)
        # removed pylinting some lines for now, just setting up
        '''

        self.name = None
        self.platform = None
        self.kodiversion = None
        self.int_kodiversion = None

        self.moduleversion = None
        self.pluginversion = None
        self.addon = None
        self.toggle = None
        self.has_silent_boot = None

        self.artPoster = None
        self.artThumb = None
        self.artIcon = None
        self.artFanart = None
        self.artClearlogo = None
        self.artClearart = None
        self.artDiscart = None

        self.tmdb_postersize = ''
        self.tmdb_fanartsize = ''
        self.tmdb_stillsize = ''
        self.tmdb_profilesize = ''
        self.devmode = False

        self._theme = ''
        self.art = ''




        self.initialize_all()

    def __del__(self):
        '''
        On destruction of the class
        '''
        self.deinit()

    def deinit(self):
        '''
        cleanup
        '''
        self.toggle = None
        self.addon = None

    def initialize_all(self):
        '''
        initialize all vars
        '''
        self.addon = xbmcaddon.Addon
        self.plugin_id = self.addon().getAddonInfo("id")
        self.pluginversion = self.addon().getAddonInfo("version")
        self.name = self.addon().getAddonInfo('name')

        self.name = self.strip_tags(text=self.name).title()
        self.platform = self._get_current_platform()

        self.module_addon = xbmcaddon.Addon("script.module.thecrew")
        self.module_id = self.module_addon.getAddonInfo(id="id")
        self.moduleversion = self.module_addon.getAddonInfo(id="version")

        self.kodiversion = self._get_kodi_version(as_string=True, as_full=True)
        self.int_kodiversion = self._get_kodi_version(as_string=False, as_full=False)
        self.has_silent_boot = self._has_silent_boot()
        self.devmode = self.get_setting('dev_pw') == self.ensure_text(base64.b64decode(b'dGhlY3Jldw=='))


        self._theme = self.appearance()
        self.art = self.get_art_path()

        self.toggle = 1 # cm - internal debugging

        self.set_imagesizes()




    def _has_silent_boot(self) -> bool:
        return self.get_setting('silent.boot') == 'true'

    def log_boot_option(self) -> None:
        if self.has_silent_boot:
            self.log('User enabled silent boot option')
        else:
            self.log('User disabled silent boot option')

    def _get_current_platform(self):

        platform_name = platform.uname()
        _system = platform_name[0]
        # _sysname = platform_name[1]
        # _sysrelease = platform_name[2]
        _sysversion = platform_name[3]
        # _sysmachine = platform_name[4]
        # _sysprocessor = platform_name[5]
        is_64bits = sys.maxsize > 2**32
        # pf = platform.python_version() # pylint disable=snake-case

        _64bits = '64bits' if is_64bits else '32bits'

        return f"{_system} {_sysversion} ({_64bits})"

    def _get_kodi_version(self, as_string=False, as_full=False):
        version_raw = xbmc.getInfoLabel("System.BuildVersion").split(" ")

        v_temp = version_raw[0]

        if as_full is False:
            version = v_temp.split(".")[0]
            fversion = ''
        else:
            v_major = v_temp.split(".")[0]
            v_minor = v_temp.split(".")[1]
            fversion = f"{v_major}.{v_minor}"
            version = ''

        if as_string is True:
            return version if as_full is False else fversion

        return int(version)

    def log(self, msg, trace=0):
        '''
        General new log messages
        '''
        #logdebug = xbmc.LOGDEBUG
        begincolor = begininfocolor = endcolor = ''


        begincolor = begininfocolor = endcolor = ''

        debug_prefix = f'{begincolor}[ {self.name} {self.pluginversion} | {self.moduleversion} | {self.kodiversion} | {self.platform} | DEBUG ]{endcolor}'
        info_prefix = f'{begininfocolor}[ {self.name} {self.pluginversion}/{self.moduleversion} | INFO ]{endcolor}'

        log_path = xbmcvfs.translatePath('special://logpath')
        filename = 'the_crew.log'
        log_file = os.path.join(log_path, filename)
        debug_enabled = self.get_setting('addon_debug')
        debug_log = self.get_setting('debug.location')

        if not debug_enabled:
            return
        try:
            if not isinstance(msg, str):
                raise Exception('c.log() msg not of type str!')


            if trace == 1:
                caller = getframeinfo(stack()[1][0])
                #caller.filename, caller.lineno
                head = debug_prefix

                #failure = str(traceback.format_exc()){failure}
                _msg = f'\n     {msg}:\n    \n--> called from file {caller.filename} @ {caller.lineno}'
                #_msg = f'\n    {msg}'
            else:
                head = info_prefix
                _msg = f'\n    {msg}'

            if debug_log== '1':
                xbmc.log(f"\n\n--> addon name @ 147 = {self.name} | {self.pluginversion} | {self.moduleversion}  \n\n")

                if not os.path.exists(log_file):
                    _file = open(log_file, 'w', encoding="utf8")
                    _file.close()
                with open(log_file, 'a', encoding="utf8") as _file:
                    now = datetime.now()
                    _dt = now.strftime("%Y-%m-%d %H:%M:%S")

                    #line = f'[{_date} {_time}] {head}: {msg}'
                    line = f'[{_dt}] {head}: {msg}'
                    _file.write(line.rstrip('\r\n') + '\n\n')

        except Exception as exc:
            xbmc.log(f'[ {self.name} ] Logging Failure: {exc}', 1)

    def in_addon(self) -> bool:
        '''
        returns bool if we are inside addon
        '''
        return xbmc.getInfoLabel('Container.PluginName') == "plugin.video.thecrew"

    def get_setting(self, setting) -> str:
        '''
        return a setting value
        '''
        return xbmcaddon.Addon().getSetting(id=setting)

    def set_setting(self, setting, val) -> None:
        '''
        set a setting value
        .getSettingString
        .getSettingBool
        .getSettingNumber
        .setSettingInt
        .setSettingBool
        '''
        return xbmcaddon.Addon().setSetting(id=setting, value=val)

    def strip_tags(self, text) -> str:
        '''
        Strip the tags, added to the name in the addon.xml file
        '''

        clean = re.compile(r'\[.*?\]')
        return re.sub(clean, '', text)

    def ensure_str(self, s, encoding='utf-8', errors='strict') -> str:
        # Als de invoer een bytes-object is, decodeer het naar een string
        if isinstance(s, bytes):
            return s.decode(encoding, errors)
        # Als de invoer al een string is, geef het terug
        elif isinstance(s, str):
            return s
        # Voor andere typen, converteer naar string met str()
        else:
            return str(s)


    def ensure_text(self, input_value, errors='strict') -> str:
    # Check if the input is already a string
        if isinstance(input_value, str):
            return input_value  # Already a string, so return it

        # Check if the input is bytes
        elif isinstance(input_value, bytes):
            try:
                # Decode bytes to string using UTF-8 and specified error handling
                return input_value.decode('utf-8', errors)
            except UnicodeDecodeError as e:
                # Handle the case where decoding fails
                if errors == 'strict':
                    raise
                elif errors == 'ignore':
                    return ''  # Return empty on ignore
                elif errors == 'replace':
                    return input_value.decode('utf-8', 'replace')
                else:
                    raise ValueError(f"Unknown error handling option: {errors}") from e

        # If the input is neither a string nor bytes, typeconvert to string
        return str(input_value)

    def encode(self,s, encoding='utf-8') -> bytes:
        """
        Encodes a string to bytes using the specified encoding.

        Parameters:
            s (str): The string to be encoded. It can be a str (Python 3) or unicode (Python 2).
            encoding (str): The encoding type. Default is 'utf-8'.

        Returns:
            bytes: The encoded byte string.
        """

        # Check if the input is a string
        if isinstance(s, str):
            # In Python 3, 'str' is already Unicode, so we encode it.
            return s.encode(encoding)

        if isinstance(s, bytes):
            # If it's already bytes, just return it as is (Python 3)
            return s

        # If it's neither a string nor bytes, raise an error
        raise TypeError("Input must be a string or bytes, not '{}'".format(type(s).__name__))



    def decode(self,data, encoding='utf-8') -> str:

        # Check if the input data is already of type string
        """
        Decodes a byte string into a string.

        If the input data is already a string, it is returned unchanged.
        If the input data is not a byte string, a ValueError is raised.
        If the decoding fails, a UnicodeDecodeError is raised.

        Parameters
        ----------
        data : bytes
            The byte string to decode.
        encoding : str
            The encoding of the byte string. Defaults to 'utf-8'.

        Returns
        -------
        str
            The decoded string.

        Raises
        ------
        ValueError
            If the input data is not a byte string.
        UnicodeDecodeError
            If the decoding fails.
        """
        if isinstance(data, str):
            return data

        # Check if the input data is of type bytes
        if not isinstance(data, bytes):
            raise ValueError("Input data must be a byte string.")

        try:
            # Try to decode the byte string
            return data.decode(encoding)
        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(f"Decoding failed: {e}") from e


    def set_imagesizes(self) -> None:
        '''
        Return the correct image sizes according to settings
        '''
        resolutions = imageSizes[int(self.get_setting('fanart.quality'))]
        self.tmdb_postersize = resolutions.get('poster')
        self.tmdb_fanartsize = resolutions.get('fanart')
        self.tmdb_stillsize = resolutions.get('still')
        self.tmdb_profilesize = resolutions.get('profile')
        old_imagesetting = self.get_setting('fanart.quality.old')
        cur_imagesetting = self.get_setting('fanart.quality')
        if old_imagesetting != cur_imagesetting:
            self.clear_imagecaches()


    def clear_imagecaches(self) -> None:
        '''
        Clear the image cache
        '''
        self.set_setting('fanart.quality.old', self.get_setting('fanart.quality'))


    def now(self):
        '''
        Return the current time
        '''
        return datetime.now()


    def is_widget_listing_old(self):
        '''
        Check if the current window is a widget listing.

        This method is an older version of `is_widget_listing()` and is kept for backwards compatibility.

        Returns
        -------
        bool
            True if the current window is a widget listing, else False.
        '''
        _id = xbmcgui.getCurrentWindowId()
        if _id == 10000:
            return True
        return False

    def is_widget_listing(self) -> bool:
        """Check if the current window is a widget listing.

        Returns
        -------
        bool
            True if the current window is a widget listing, else False.
        """
        plugin_name = xbmc.getInfoLabel('Container.PluginName')
        return 'plugin' not in plugin_name


    #---Add Directory Method---#
    def addDirectoryItem(self, name, url, mode, icon, fanart, thumb, description='', page='', dir_name='', cm=None, labels=None, cast=None, the_id = '', season = '', episode = '', isAction = True, isFolder = True):
        sys_url = sys.argv[0]
        sys_handle = int(sys.argv[1])

        if isinstance(name, int):
            name = xbmcaddon.Addon().getLocalizedString(name)

        if description == '':
            description = name
        if cast is None:
            cast = []
        if labels is None:
            labels = {'title': name, 'plot': description, 'mediatype': 'video'}

        if mode == 'navigator':

            if sys_url not in url:
                url = f'{sys_url}?action={url}'

            #url = '%s?action=%s' % (sys_url, url) if isAction is True else query
            thumb = os.path.join(self.art, thumb) if self.art is not None else icon

            fanart = self.addon_fanart()

            li = self.listItem(name)
            vtag = li.getVideoInfoTag()
            vtag.setMediaType(labels.get("mediatype", "video"))
            vtag.setTitle(labels.get("title", self.lang(32566)))
            if cm is not None:
                li.addContextMenuItems(cm)
            li.setArt({'icon': icon, 'thumb': thumb, 'fanart': fanart, 'poster': thumb})

            if fanart is not None:
                li.setProperty('fanart', fanart)
        if mode == 'tvshow':
            self.log(f'[CM DEBUG in crewruntime.py @ 293] inside crewruntime addDirectory:: Mode = tvshow\nurl = {url}')

        xbmcplugin.addDirectoryItem(handle=sys_handle, url=url, listitem=li, isFolder=isFolder)


    def setContent(self, content: str) -> any:
        return xbmcplugin.setContent(int(sys.argv[1]), content)


    def endDirectory(self) -> None:
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    ######
    #
    # moving this over from control with better code
    def addon_icon(self) -> str:
        if self.art is not None and self._theme not in ['-', '']:
            return os.path.join(self.art, 'icon.png')
        return xbmcaddon.Addon().getAddonInfo('icon')

    def addon_thumb(self) -> str:
        if self.art is not None and self._theme not in ['-', '']:
            return os.path.join(self.art, 'thumb.jpg')
        return ''

    def addon_poster(self) -> str:
        if self.art is not None and self._theme not in ['-', '']:
            return os.path.join(self.art, 'poster.png')
        return 'DefaultVideo.png'

    def addon_banner(self) -> str:
        if self.art is not None and self._theme not in ['-', '']:
            return os.path.join(self.art, 'banner.png')
        return 'DefaultVideo.png'

    def addon_fanart(self) -> str:
        if self.art is not None and self._theme not in ['-', '']:
            fanart = os.path.join(self.art, 'fanart.jpg')
            if isinstance(fanart, tuple):
                return fanart[0]
            return fanart
        return xbmcaddon.Addon().getAddonInfo('fanart')

    def addon_clearart(self) -> str:
        if self.art is not None and self._theme not in ['-', '']:
            return os.path.join(self.art, 'clearart.png')
        return ''

    def addon_discart(self) -> str:
        if self.art is not None and self._theme not in ['-', '']:
            return os.path.join(self.art, 'discart.png')
        return ''

    def addon_clearlogo(self) -> str:
        if self.art is not None and self._theme not in ['-', '']:
            return os.path.join(self.art, 'clearlogo.png')
        return ''

    def addon_next(self) -> str:
        if self.art is not None and self._theme not in ['-', '']:
            return os.path.join(self.art, 'next.png')
        return 'DefaultVideo.png'

    def get_art_path(self) -> str:

        if self._theme in ['-', '']:
            return ''
        elif xbmc.getCondVisibility('System.HasAddon(script.thecrew.artwork)'):
            return os.path.join(
                xbmcaddon.Addon('script.thecrew.artwork').getAddonInfo('path'),
                'resources',
                'media',
                str(self._theme)
            )

    def appearance(self):
        return (
            self.get_setting('appearance.1').lower()
            if xbmc.getCondVisibility('System.HasAddon(script.thecrew.artwork)')
            else self.get_setting('appearance.alt').lower()
        )

    def artwork(self) -> None:
        xbmc.executebuiltin('RunPlugin(plugin://script.thecrew.artwork)')

    def capitalize_word(self, string) -> str:

        return string.title()

    def string_split_to_list(self, string) -> list:

        if string in ['0', None]:
            return []
        lst = string.split('/')
        lst = [s.strip() for s in lst]
        lst = [self.capitalize_word(s) for s in lst]

        return lst

    def search_tmdb_index_in_indicators(self, tmdb_id, indicator_list):
        try:

            if not indicator_list:
                return -1

            tmdb_id = str(tmdb_id)
            indices = [index for index, value in enumerate(indicator_list) if value[0] == tmdb_id]
            self.log(f'[CM Debug @ 587 in crewruntime.py]indices = {indices}')

            return indices[0] if indices else -1
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            self.log(f'[CM Debug @ 595 in crewruntime.py]Traceback:: {failure}')
            self.log(f'[CM Debug @ 596 in crewruntime.py]Exception raised. Error = {e}')

    def search_tmdb_index_in_indicators2(self, tmdb, indicators):

        if not indicators:
            return -1

        if not isinstance(tmdb, str):
            tmdb = str(tmdb)

        lst = [i for i, v in enumerate(indicators) if v[0] == tmdb]

        if len(lst) == 0:
            return -1
        else:
            return lst[0]


    def count_wachted_items_in_indicators(self, index, indicators):

        try:
            if not indicators[index]:
                return -1
            else:
                return len(indicators[index][2])

        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            self.log(f'[CM Debug @ 469 in crewruntime.py]Traceback:: {failure}')
            self.log(f'[CM Debug @ 469 in crewruntime.py]Exception raised. Error = {e}')


    def count_total_items_in_indicators(self, index, indicators):
        if not indicators[index]:
            return -1
        return indicators[index][1]

    def string_to_tuple(self, string):
        return tuple(map(str, string.split(',')))




    def unicode_art(self, _str) -> str:
        _str = re.sub('\\\\\\\\u([\\da-f]{4})', lambda x: chr(int(x.group(1), 16)), _str)
        return json.dumps(_str)



    def infoDialog(self, message, heading=addonInfo('name'), icon='', time=3000, sound=False) -> None:
        if icon == '':
            icon = self.addon_icon()
        elif icon == 'INFO':
            icon = xbmcgui.NOTIFICATION_INFO
        elif icon == 'WARNING':
            icon = xbmcgui.NOTIFICATION_WARNING
        elif icon == 'ERROR':
            icon = xbmcgui.NOTIFICATION_ERROR
        elif icon.endswith('.png'):
            icon = os.path.join(self.art, icon)
        xbmcgui.Dialog().notification(heading, message, icon, time, sound=sound)






c = CrewRuntime()
