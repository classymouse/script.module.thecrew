# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file orion_api.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2025, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import os

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import math

from orion import Orion
from .crewruntime import c
from . import keys
from . import control
from . import source_utils


class orionApi:
    def __init__(self):
        self.base_url = 'https://api.orionoid.com'
        self.appkey = keys.orion_key
        self.testkey = 'TESTTESTTESTTESTTESTTESTTESTTEST'
        self.token = c.get_setting('orion.token')
        self.orion_installed = self.is_orion_installed()
        self.session = requests.Session()
        self.retries = Retry(total=3, backoff_factor=0.5)
        self.session.mount(self.base_url, HTTPAdapter(max_retries=self.retries))
        self.orion = Orion(self.appkey)


    def get_orion(self, mode, action, data):
        try:
            headers = {
                'Content-Type': 'application/json',
            }
            addonID = xbmcaddon.Addon().getAddonInfo("id")
            c.log(f"[CM Debug @ 61 in orion_api.py] addonID = {addonID}")

            data = json.dumps(data) if data else None
            #build url

            response = self.session.post(url, json=data, headers=headers)

            c.log(f"[CM Debug @ 76 in orion_api.py] response = {response.text}")
            c.log(f"[CM Debug @ 77 in orion_api.py] response_code = {response.status_code}")

        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 55 in orion_api.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 55 in orion_api.py]Exception raised. Error = {e}')
            pass





    def is_orion_installed(self):# -> Any:
        return xbmc.getCondVisibility('System.HasAddon(script.module.orion)')

    def get_credentials_info(self) -> bool:
        orion = Orion(self.appkey)


        if not c.get_setting('orion.token'):
            return False
        return True

    # ! TODO change limit
    def get_movie(self,imdb, limit=250) -> dict:
        results = self.orion.streams(type = Orion.TypeMovie, idImdb = imdb, limitCount = limit)
        return results

    def get_episode(self,imdb=0, tmdb=0, title ='', season = 0, episode = 0, limit=250) -> dict:

        if imdb == 0:
            results = self.orion.streams(type = Orion.TypeShow, idTmdb = tmdb, numberSeason = season, numberEpisode = episode, limitCount = limit)
        elif tmdb != 0:
            results = self.orion.streams(type = Orion.TypeShow, idImdb = imdb, numberSeason = season, numberEpisode = episode, limitCount = limit)
        elif title != '':
            results = self.orion.streams(type = Orion.TypeShow, query = title, limitCount = limit)
        else:
            return None
        return results

    def do_orion_scrape(self, data, _type='movie'):
        try:
            sources = []
            if data is not None:
                for item in data:
                    c.log(f"\n\n\n===================================================================\nORION DATA\n===============================================\n\n[CM Debug @ 98 in orion_api.py] len data = {len(data)}\n\n data = {repr(item)}\n\n\n")
            if _type == 'movie':
                for i, item in enumerate(data):
                    #c.log(f"[CM Debug @ 110 in orion_api.py] type item = (type) {type(item)}")
                    links = item.get("links", [])
                    url = ''
                    for link in links:
                        if link.startswith("magnet:") and url == '':
                            url = link
                        else:
                            continue

                    fileinfo = item.get("file")
                    name = fileinfo.get("name")
                    size = fileinfo.get("size")
                    hash = fileinfo.get("hash")
                    pack = fileinfo.get("pack")

                    quality, info = source_utils.get_release_quality(name)

                    try:
                        dsize, isize = source_utils.file_size(size)
                        c.log(f"[CM Debug @ 132 in orion_api.py] dsize = {dsize}")
                    except:
                        dsize, isize = 0.0, ''

                    info.insert(0, isize)
                    sources.append({'provider' : 'Orion', 'source': 'Torrent', 'quality': quality, 'language': 'en', 'url': url, 'info': info,'direct': False, 'debridonly': True, 'size': dsize, 'name': name})


                #c.log(f"[CM Debug @ 146 in orion_api.py] sources = {sources}")

                return sources
            else:
                c.log(f"[CM Debug @ 142 in orion_api.py] len data = {len(data)} data = {repr(data)}")
                for i, item in enumerate(data):
                    #c.log(f"[CM Debug @ 110 in orion_api.py] type item = (type) {type(item)}")
                    links = item.get("links", [])
                    url = ''
                    for link in links:
                        if link.startswith("magnet:") and url == '':
                            url = link
                        else:
                            continue

                    fileinfo = item.get("file",)
                    c.log(f"[CM Debug @ 111 in orion_api.py] fileinfo = {fileinfo}")

                    name = fileinfo.get("name",)
                    size = fileinfo.get("size")
                    hash = fileinfo.get("hash")
                    pack = fileinfo.get("pack")

                    quality, info = source_utils.get_release_quality(name)

                    try:
                        dsize, isize = source_utils._size(size)
                        c.log(f"[CM Debug @ 164 in orion_api.py] dsize = {dsize} isize = {isize}")
                    except:
                        dsize, isize = 0.0, '*'

                    info.insert(0, isize)
                    sources.append({'provider' : 'Orion', 'source': 'Torrent', 'quality': quality, 'language': 'en', 'url': url, 'info': info,'direct': False, 'debridonly': True, 'size': dsize, 'name': name})

                c.log(f"[CM Debug @ 139 in orion_api.py] something wron: type={_type}")
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 137 in orion_api.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 137 in orion_api.py]Exception raised. Error = {e}')
            pass





    def authorize_orion(self):
        #self.get_orion('user', 'authenticate', '')
        orion = Orion(self.appkey)
        result = orion.userDialog()
        c.log(f"[CM Debug @ 110 in orion_api.py] result = {result}")

    def settings_orion(self):
        #self.get_orion('user', 'authenticate', '')
        orion = Orion(self.appkey)
        result = orion.settingsLaunch()
        c.log(f"[CM Debug @ 113 in orion_api.py] result = {result}")

    def info_orion(self):
        results = self.get_movie('tt5519340')
        c.log(f"[CM Debug @ 128 in orion_api.py] results = {results}")

    @classmethod
    def auth_orion(self):
        try:
            if not self.get_credentials_info():
                result= control.yesnoDialog(control.lang(32511) + '[CR]' + control.lang(32512), heading='Orion')
                if result is True:
                    #clear current account
                    c.log(f"[CM Debug @ 116 in orion_api.py] result = {result}")
                elif result is False:
                    pass


            expires_in = 120

            progressDialog = control.progressDialog
            progressDialog.create('Orion')

            for i in range(0, expires_in):
                try:
                    percent = int(100/expires_in) * i
                    progressDialog.update(max(1, percent), verification_url + '[CR]' + user_code)
                    if progressDialog.iscanceled():
                        break

                    time.sleep(1)
                    if not float(i) % interval == 0:
                        raise Exception()
                    r = getTraktAsJson(
                            '/oauth/device/token',
                        {
                            'client_id': CLIENT_ID,
                            'client_secret': CLIENT_SECRET,
                            'code': device_code
                        })
                    if 'access_token' in r:
                        break
                except:
                    pass

            try:
                progressDialog.close()
            except:
                pass

            token, refresh = r['access_token'], r['refresh_token']

            headers = {
                        'Content-Type': 'application/json',
                        'trakt-api-key': CLIENT_ID,
                        'trakt-api-version': 2,
                        'Authorization': f'Bearer {token}'
                    }

            result = client.request(urljoin(BASE_URL, '/users/me'), headers=headers)
            result = utils.json_loads_as_str(result)

            user = result['username']
            authed = '' if user == '' else str('yes')

            control.setSetting(id='trakt.user', value=user)
            control.setSetting(id='trakt.token', value=token)
            control.setSetting(id='trakt.refresh', value=refresh)
            raise Exception()
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 127 in orion_api.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 127 in orion_api.py]Exception raised. Error = {e}')
            pass
        #except:
            #control.openSettings('3.1')





oa = orionApi()
####################################################################################################


def window():
    file = 'LogViewer_QR.xml'
    path = c.artworkPath
    skin = c.appearance()
    resolution = '1080i'
    return xbmcgui.WindowXMLDialog(file, path, skin, resolution)

def get_orion_qr():
    try:
        #r = open(CHANGELOG_FILE)
        #text = r.read()
        header = "authenticate orion"
        url = "https%3A%2F%2Ftrakt.tv%2Factivate%2FECFABC3" # test for now
        size = "260"
        text = "for now just some text"
        qr_code = f"https://api.qrserver.com/v1/create-qr-code/?data={url}&size={size}x{size}"
        c.log(f"[CM Debug @ 56 in orion_api.py] qr_code = {qr_code}")
        #view_orion_qr(window(),header, str(text), qr_code)
        # Call the function to show the dialog
        show_custom_dialog()
    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 58 in orion_api.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 58 in orion_api.py]Exception raised. Error = {e}')
        pass





def view_orion_qr(xml, header, message, qr_code) -> None:
    class orionQRViewer(xbmcgui.WindowXMLDialog):
        def __init__(self, xml, header, message, qr_code):
            if not header or not message or not qr_code:
                c.log(f"[CM Debug @ 66 in orion_api.py] One of the parameters passed to orion_qr_viewer is empty/None. Skipping this.")
                return
            super().__init__()
            self.initialize(self)
            self.header = header
            self.message = message
            self.qr_code = qr_code
            self.xml = xml

        def initialize(self):
            #key id's
            self.KEY_NAV_ENTER = 7
            self.KEY_NAV_ESC = 10
            self.KEY_NAV_BACK = 92

            self.KEY_NAV_MOVEUP = 3
            self.KEY_NAV_MOVEDOWN = 4
            self.KEY_NAV_PAGEUP = 5
            self.KEY_NAV_PAGEDOWN = 6

            #xml id's
            self.HEADERLABEL = 101
            self.TEXT = 502
            self.QR_IMAGE = 501
            self.CLOSEBUTTON = 503

            self.TITLE = '[B]' + c.module_addon + ' v.' + c.moduleversion + '[/B]'


        def onInit(self):
            HEADERTITLE = self.TITLE if header == '' else header
            self.getControl(self.HEADERLABEL).setLabel(HEADERTITLE)
            self.getControl(self.TEXT).setText(message)
            self.getcontrol(self.QR_IMAGE).setImage(qr_code)

        def onAction(self, action):
            try:
                actionID = action.getId()
            except:
                c.log(f"[CM Debug @ 94 in orion_api.py] Exception raised. Error = {action}")
                return

            if actionID in[self.KEY_NAV_BACK, self.KEY_NAV_ENTER, self.KEY_NAV_ESC]:
                self.close()

            if actionID in [self.KEY_NAV_MOVEUP, self.KEY_NAV_PAGEUP]:
                self.getControl(self.TEXT).scroll(1)

            if actionID in [self.KEY_NAV_MOVEDOWN, self.KEY_NAV_PAGEDOWN]:
                self.getControl(self.TEXT).scroll(-1)

        def onClick(self, controlId):
            try:
                if controlId == self.CLOSEBUTTON:
                    self.close()
            except:
                c.log(f"[CM Debug @ 110 in orion_api.py] Exception raised. Error = {controlId}")
                pass




    try:
        d = orionQRViewer(header, message, qr_code)
        d.doModal()
        del d
    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 138 in orion_api.py]Traceback:: {failure}')
        c.log(f'[CM Debug @ 138 in orion_api.py]Exception raised. Error = {e}')
        pass
















class CustomDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize necessary variables for the dialog
        self.label = None
        self.title = None
        self.background = None
        self.qr_code = None

    def onInit(self):
        # Called when the dialog is initialized (window is loaded)
        self.background_id = 100
        self.header_id = 101
        self.qr_code_id = 501
        self.qr_code_text_id = 502
        self.button_id = 503

        self.set_title("Default Title")
        self.set_label("Default Label")
        self.set_background("logviewer_bg.png")
        c.log(f"[CM Debug @ 192 in orion_api.py] inside onInit method, Title = {self.title}")

    def onAction(self, action):
        """Handle all keystrokes."""
        if action is None:
            return

        keycode = action.getId()
        c.log(f"[CM Debug @ 210 in orion_api.py] keycode {keycode} of type {type(keycode)} pressed")

        if keycode == xbmcgui.ACTION_NAV_BACK:
            # Example: Close the dialog if the back button is pressed
            self.close()
        elif keycode == xbmcgui.ACTION_SELECT_ITEM:
            # Handle the select button (Enter key) if needed
            c.log("Select key pressed.")
        elif keycode == xbmcgui.ACTION_MOVE_UP:
            # Handle up movement
            c.log("Up key pressed.")
        elif keycode == xbmcgui.ACTION_MOVE_DOWN:
            # Handle down movement
            c.log("Down key pressed.")
        else:
            if keycode != "107":
                c.log(f"Keycode {keycode} pressed.")

    def set_label(self, text):
        """Set the text for the label in the dialog."""
        if self.label:
            self.label.setLabel(text)
        else:
            c.log("Label not found!")

    def set_title(self, title):
        """Set the title for the dialog."""
        if title:
            self.getLabel(self.header_id).setLabel(title)
        else:
            c.log("Title not found!")

    def set_background(self, background_image):
        """Set the background image."""
        if self.background:
            self.getLabel(self.background_id).setImage(background_image)
        else:
            c.log("Background image not found!")

    def load_custom_elements(self):
        """Load the custom elements from the XML (e.g., label, title, background)."""
        # Example: Assuming the label is a control named 'label' in the XML  # Example control ID for the label
        try:
            self.title = self.getControl(101)  # Example control ID for the title
            self.background = self.getControl("100")
            self.qr_code = self.getControl("501")  # Example control ID for the background image
            self.qr_txt = self.getControl("502")  # Example control ID for the background image
            self.button = self.getControl("503")  # Example control ID for the background image
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 250 in orion_api.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 250 in orion_api.py]Exception raised. Error = {e}')
            pass

# Function to create and show the dialog
def show_custom_dialog(*args, **kwargs):
    # Path to your custom XML file. Make sure to replace this with your actual file path.
    try:
        xml_path = "LogViewer_QR.xml"  # Replace with your actual path

        # Path to the skin directory (required for non-standard XML files)
        #skin_path = xbmcvfs.translatePath("special://skin/")

        skin_path = c.artworkPath # Using Kodi's special path for skin location
        temp = c.get_artwork_path()
        c.log(f"[CM Debug @ 256 in orion_api.py] temp = {temp}")

        skin_path = temp +  "resources/skins/thecrew/1080i/"

        c.log(f"[CM Debug @ 258 in orion_api.py] path = {skin_path}")

        # Create an instance of the custom dialog class
        #dialog = CustomDialog(xml_path, skin_path, "default", "1080i")
        ARTADDON_PATH = xbmcaddon.Addon('script.thecrew.artwork').getAddonInfo('path')
        dialog = CustomDialog('LogViewer_QR.xml', ARTADDON_PATH, c.appearance(), '1080i')



        # Load custom elements (like label, title, background)
        #dialog.load_custom_elements()

        # Show the dialog
        dialog.doModal()

        # Cleanup after dialog is closed
        del dialog
    except Exception as e:
        c.log(f"Failed to load custom dialog: {str(e)}")

# Call the function to show the dialog
#show_custom_dialog()
