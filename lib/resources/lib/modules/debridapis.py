# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file sources.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

import requests
import random

from . import utils
from . import cache

from .crewruntime import c

class realdebrid():
    def __init__(self):
        self.name = 'RealDebrid'
        self.url = 'https://realdebrid.com'
        self.api = 'https://api.realdebrid.com'
        self.rest_base_url = 'https://api.real-debrid.com/rest/1.0/'
        self.oauth_url = 'https://api.real-debrid.com/oauth/v2/'
        self.token = c.get_setting('rd.token')
        self.secret = c.get_setting('rd.secret')
        self.client_id = c.get_setting('rd.client_id') or 'X245A4XAIBGVM' # RealDebrid Client ID - limited!
        self.refresh = c.get_setting('rd.refresh')
        self.account_id = c.get_setting('rd.account_id')
        self.enabled = c.get_setting('rd.enabled')
        self.device_code = c.get_setting('rd.device_code')
        self.user_agent = cache.get(self.randomagent, 12)

    def _get(self, url):
        original_url = url
        url = self.rest_base_url + url
        if '?' not in url:
            url += "?auth_token=%s" % self.token
        else:
            url += "&auth_token=%s" % self.token
        response = requests.get(url).text
        try:
            resp = utils.json_loads_as_str(response)
        except Exception as e:
            c.log(f"[CM Debug @ 51 in debridcheck.py] exception: error = {e}")
            resp = utils.byteify(response)
        return resp

    def _post(self, url, data={}):
        result = None
        if self.token == '':
            return None
        url = self.rest_base_url + url + '?agent=%s&apikey=%s' % (self.user_agent, self.token)

        resp = requests.post(url, data=data).json()
        if resp.get('status') == 'success':
            if 'data' in resp:
                resp = resp['data']['magnets']
        return resp

    def _put(self, url, data={}):
        result = None
        if self.token == '':
            return None
        url = self.rest_base_url + url + '?agent=%s&apikey=%s' % (self.user_agent, self.token)
        resp = requests.put(url, data=data).json()
        if resp.get('status') == 'success':
            if 'data' in resp:
                resp = resp['data']['magnets']
        return resp

    def _delete(self, url, data={}):
        result = None
        if self.token == '': return None
        url = self.base_url + url + '?agent=%s&apikey=%s' % (self.user_agent, self.token)
        resp = requests.delete(url, data=data).json()
        if resp.get('status') == 'success':
            if 'data' in resp:
                resp = resp['data']['magnets']
        return resp

    def refreshToken(self):
        data = {'grant_type': 'refresh_token', 'refresh_token': self.refresh}
        response = requests.post(self.oauth_url + 'token', data=data, timeout=30).json()
        self.token = response['access_token']
        self.refresh = response['refresh_token']
        c.set_setting('rd.token', self.token)
        c.set_setting('rd.refresh', self.refresh)

        return True

    def revoke(self):
        c.set_setting('rd.client_id', 'empty_setting')
        c.set_setting('rd.secret', 'empty_setting')
        c.set_setting('rd.refresh', 'empty_setting')
        c.set_setting('rd.token', 'empty_setting')
        c.set_setting('rd.account_id', 'empty_setting')
        c.set_setting('rd.enabled', 'false')
        c.set_setting('rd.device_code', 'empty_setting')

        return True

    def auth(self):
        self.client_id = c.get_setting('rd.client_id')
        self.secret = c.get_setting('rd.secret')
        self.refresh = c.get_setting('rd.refresh')
        self.token = c.get_setting('rd.token')
        self.account_id = c.get_setting('rd.account_id')
        self.enabled = c.get_setting('rd.enabled')
        self.device_code = c.get_setting('rd.device_code')

        return True

    def check(self):
        self.client_id = c.get_setting('rd.client_id')
        self.secret = c.get_setting('rd.secret')
        self.refresh = c.get_setting('rd.refresh')
        self.token = c.get_setting('rd.token')
        self.account_id = c.get_setting('rd.account_id')
        self.enabled = c.get_setting('rd.enabled')
        self.device_code = c.get_setting('rd.device_code')

        return True

    def enabled(self):
        self.client_id = c.get_setting('rd.client_id')
        self.secret = c.get_setting('rd.secret')
        self.refresh = c.get_setting('rd.refresh')
        self.token = c.get_setting('rd.token')
        self.account_id = c.get_setting('rd.account_id')
        self.enabled = c.get_setting('rd.enabled')
        self.device_code = c.get_setting('rd.device_code')

        return True

    def disable(self):
        self.client_id = c.get_setting('rd.client_id')
        self.secret = c.get_setting('rd.secret')
        self.refresh = c.get_setting('rd.refresh')
        self.token = c.get_setting('rd.token')
        self.account_id = c.get_setting('rd.account_id')
        self.enabled = c.get_setting('rd.enabled')
        self.device_code = c.get_setting('rd.device_code')

        return True

    def randomagent():
        BR_VERS = [
            ['%s.0' % i for i in range(18, 50)],
            [
                '37.0.2062.103', '37.0.2062.120', '37.0.2062.124', '38.0.2125.101', '38.0.2125.104', '38.0.2125.111',
                '39.0.2171.71', '39.0.2171.95', '39.0.2171.99', '40.0.2214.93', '40.0.2214.111', '40.0.2214.115',
                '42.0.2311.90', '42.0.2311.135', '42.0.2311.152', '43.0.2357.81', '43.0.2357.124', '44.0.2403.155',
                '44.0.2403.157', '45.0.2454.101', '45.0.2454.85', '46.0.2490.71', '46.0.2490.80', '46.0.2490.86',
                '47.0.2526.73', '47.0.2526.80', '48.0.2564.116', '49.0.2623.112', '50.0.2661.86', '51.0.2704.103',
                '52.0.2743.116', '53.0.2785.143', '54.0.2840.71', '61.0.3163.100'
            ],
            ['11.0'],
            ['8.0', '9.0', '10.0', '10.6']]
        WIN_VERS = ['Windows NT 10.0', 'Windows NT 7.0', 'Windows NT 6.3', 'Windows NT 6.2',
                    'Windows NT 6.1', 'Windows NT 6.0', 'Windows NT 5.1', 'Windows NT 5.0']
        FEATURES = ['; WOW64', '; Win64; IA64', '; Win64; x64', '']
        RAND_UAS = ['Mozilla/5.0 ({win_ver}{feature}; rv:{br_ver}) Gecko/20100101 Firefox/{br_ver}',
                    'Mozilla/5.0 ({win_ver}{feature}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{br_ver} Safari/537.36',
                    'Mozilla/5.0 ({win_ver}{feature}; Trident/7.0; rv:{br_ver}) like Gecko',
                    'Mozilla/5.0 (compatible; MSIE {br_ver}; {win_ver}{feature}; Trident/6.0)']
        index = random.randrange(len(RAND_UAS))
        return RAND_UAS[index].format(
            win_ver=random.choice(WIN_VERS),
            feature=random.choice(FEATURES),
            br_ver=random.choice(BR_VERS[index]))
