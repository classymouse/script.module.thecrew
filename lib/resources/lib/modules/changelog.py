# -*- coding: utf-8 -*-

'''
********************************************************cm*
* The Crew Add-on
*
* @file changelog.py
* @package script.module.thecrew
*
* @copyright (c) 2025, The Crew
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''
import os

import xbmcgui
import xbmcaddon


from . import control
from .crewruntime import c


ADDON = xbmcaddon.Addon()
ADDON_INFO = ADDON.getAddonInfo
ADDON_PATH = control.transPath(ADDON_INFO('path'))
ARTADDON_PATH = xbmcaddon.Addon('script.thecrew.artwork').getAddonInfo('path')
MODULEADDON_PATH = xbmcaddon.Addon('script.module.thecrew').getAddonInfo('path')
CHANGELOG_FILE = os.path.join(MODULEADDON_PATH, 'changelog.txt')


TITLE = '[B]' + ADDON_INFO('name') + ' v.' + ADDON_INFO('version') + '[/B]'


def get():
    try:
        r = open(CHANGELOG_FILE, 'r', encoding='utf-8')
        text = r.read()
        log_viewer(str(text))
    except Exception as e:
        c.log(f'Exception raised in changelog: error = {e}')

def log_viewer(message: str, header = ''):

    class LogViewer(xbmcgui.WindowXMLDialog):
        #key id's
        KEY_NAV_ENTER = 7
        KEY_NAV_ESC = 10
        KEY_NAV_BACK = 92

        KEY_NAV_MOVEUP = 3
        KEY_NAV_MOVEDOWN = 4
        KEY_NAV_PAGEUP = 5
        KEY_NAV_PAGEDOWN = 6

        #xml id's
        HEADER = 101
        TEXT = 102
        SCROLLBAR = 103
        CLOSEBUTTON = 201

        def onInit(self):
            HEADERTITLE = TITLE if header == '' else header
            self.getControl(self.HEADER).setLabel(HEADERTITLE)
            self.getControl(self.TEXT).setText(message)

        def onAction(self, action):
            action_id = action.getId()

            if action_id in[self.KEY_NAV_BACK, self.KEY_NAV_ENTER, self.KEY_NAV_ESC]:
                self.close()

            if action_id in [self.KEY_NAV_MOVEUP, self.KEY_NAV_PAGEUP]:
                self.getControl(self.TEXT).scroll(1)

            if action_id in [self.KEY_NAV_MOVEDOWN, self.KEY_NAV_PAGEDOWN]:
                self.getControl(self.TEXT).scroll(-1)

        def onClick(self, control_id):
            if control_id == self.CLOSEBUTTON:
                self.close()

    dialog = LogViewer('LogViewer.xml', ARTADDON_PATH, control.appearance(), '1080i')
    dialog.doModal()
    del dialog