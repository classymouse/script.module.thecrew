# -*- coding: utf-8 -*-

'''
********************************************************cm*
* The Crew Add-on
*
* @file source_utils.py
* @package script.module.thecrew
*
* @copyright (c) 2025, The Crew
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''

import base64
import hashlib
import re

from urllib.parse import unquote, urlparse, quote_plus
import xbmc

from . import cleantitle
from . import client
from . import directstream
from . import trakt
from . import pyaes
from . import log_utils
from .crewruntime import c

RES_4K = [' 4k', ' hd4k', ' 4khd', ' uhd', ' ultrahd', ' ultra hd', ' 2160', ' 2160p', ' hd2160', ' 2160hd']
RES_1080 = [' 1080', ' 1080p', ' 1080i', ' hd1080', ' 1080hd', ' m1080p', ' fullhd', ' full hd', ' 1o8o', ' 1o8op']
RES_720 = [' 720', ' 720p', ' 720i', ' hd720', ' 720hd', ' 72o', ' 72op']
RES_SD = [' 576', ' 576p', ' 576i', ' sd576', ' 576sd', ' 480', ' 480p', ' 480i', ' sd480', ' 480sd', ' 360', ' 360p', ' 360i', ' sd360', ' 360sd', ' 240', ' 240p', ' 240i', ' sd240', ' 240sd']
SCR = [' scr', ' screener', ' dvdscr', ' dvd scr', ' r5', ' r6']
CAM = [' camrip', ' tsrip', ' hdcam', ' hd cam', ' cam rip', ' hdts', ' dvdcam', ' dvdts', ' cam', ' telesync', ' ts']

#function only used in 1 scraper that needs fixing
def supported_video_extensions():
    supported_video_extensions = xbmc.getSupportedMedia('video').split('|')
    return [i for i in supported_video_extensions if i != '' and i != '.zip']

def get_quality(term):
    """Return the video quality from a given string."""
    qualities = (
        ('4k', RES_4K),
        ('1080p', RES_1080),
        ('720p', RES_720),
        ('sd', RES_SD),
        ('scr', SCR),
        ('cam', CAM),
    )

    for quality, patterns in qualities:
        if any(pattern in term.lower() for pattern in patterns):
            return quality

#unused
def is_anime(content_type, content_id, genre_type):
    try:
        genres = trakt.getGenre(content_type, content_id, genre_type)
        return any(genre in genres for genre in ['anime', 'animation'])
    except Exception:
        return False

def get_release_quality(release_name, release_link=None):

    try:
        if release_name is None:
            return 'sd', []

        quality = None
        release_name = cleantitle.get_title(release_name)
        quality = get_quality(release_name)

        if not quality:
            if release_link:
                release_link = cleantitle.get_title(release_link)
                quality = get_quality(release_link)
                if not quality:
                    quality = 'sd'
            else:
                quality = 'sd'
        info = []
        return quality, info
    except Exception as e:
        c.log(f'Exception in get_release_quality: {e}')
        return 'sd', []


def get_file_type(url):
    """Get the file type from a given URL."""
    url = client.replaceHTMLCodes(url)
    url = unquote(url)
    url = url.lower()
    url = re.sub('[^a-z0-9 ]+', ' ', url)

    file_types = []

    if any(i in url for i in ['bluray', 'blu ray']):
        file_types.append('Bluray')
    if any(i in url for i in ['bd r', 'bdr', 'bd rip', 'bdrip', 'br rip', 'brrip']):
        file_types.append('BDRip')
    if 'remux' in url:
        file_types.append('Remux')
    if any(i in url for i in ['dvdrip', 'dvd rip']):
        file_types.append('DVDRip')
    if any(i in url for i in ['dvd', 'dvdr', 'dvd r']):
        file_types.append('DVD')
    if any(i in url for i in ['webdl', 'web dl', 'web', 'web rip', 'webrip']):
        file_types.append('Web')
    if 'hdtv' in url:
        file_types.append('HDTV')
    if 'sdtv' in url:
        file_types.append('SDTV')
    if any(i in url for i in ['hdrip', 'hd rip']):
        file_types.append('HDRip')
    if any(i in url for i in ['uhdrip', 'uhd rip']):
        file_types.append('UHDRip')
    if 'r5' in url:
        file_types.append('R5')
    if any(i in url for i in ['cam', 'hdcam', 'hd cam', 'cam rip', 'camrip']):
        file_types.append('CAM')
    if any(i in url for i in ['ts', 'telesync', 'hdts', 'pdvd']):
        file_types.append('TS')
    if any(i in url for i in ['tc', 'telecine', 'hdtc']):
        file_types.append('TC')
    if any(i in url for i in ['scr', 'screener', 'dvdscr', 'dvd scr']):
        file_types.append('SCR')
    if 'xvid' in url:
        file_types.append('XVID')
    if 'avi' in url:
        file_types.append('AVI')
    if any(i in url for i in ['h 264', 'h264', 'x264', 'avc']):
        file_types.append('H.264')
    if any(i in url for i in ['h 265', 'h256', 'x265', 'hevc']):
        file_types.append('HEVC')
    if 'hi10p' in url:
        file_types.append('HI10P')
    if '10bit' in url:
        file_types.append('10BIT')
    if '3d' in url:
        file_types.append('3D')
    if any(i in url for i in ['hdr', 'hdr10', 'hlg']):
        file_types.append('HDR')
    if any(i in url for i in ['dolby vision', 'dolbyvision']):
        file_types.append('DV')
    if 'imax' in url:
        file_types.append('IMAX')
    if any(i in url for i in ['ac3', 'ac 3']):
        file_types.append('AC3')
    if 'aac' in url:
        file_types.append('AAC')
    #cm doubles - AAC is already checked, 5.1 also
    #if 'aac5 1' in url:
        #file_types.append('AAC / 5.1')
    if any(i in url for i in ['ddplus', 'dd plus', 'ddp', 'eac3', 'eac 3']):
        file_types.append('DD+')
    if any(i in url for i in ['dd', 'dolby', 'dolbydigital', 'dolby digital']) and 'DD' not in file_types and 'DD+' not in file_types:
        file_types.append('DD')
    if any(i in url for i in ['truehd', 'true hd']):
        file_types.append('TRUEHD')
    if 'atmos' in url:
        file_types.append('ATMOS')
    if 'dts' in url:
        file_types.append('DTS')
    if any(i in url for i in ['hdma', 'hd ma']):
        file_types.append('HD.MA')
    if any(i in url for i in ['hdhra', 'hd hra']):
        file_types.append('HD.HRA')
    if any(i in url for i in ['dtsx', 'dts x']):
        file_types.append('DTS:X')
    #cm doubles
    #if 'dd5 1' in url:
        #file_types.append('DD / 5.1')
    #if 'ddp5 1' in url:
        #file_types.append('DD+ / 5.1')
    if any(i in url for i in ['5 1', '6ch']):
        file_types.append('5.1')
    if any(i in url for i in ['7 1', '8ch']):
        file_types.append('7.1')
    if 'korsub' in url:
        file_types.append('HC-SUBS')
    if any(i in url for i in ['subs', 'subbed', 'sub']):
        file_types.append('SUBS')
    if any(i in url for i in ['dub', 'dubbed', 'dublado']):
        file_types.append('DUB')
    if 'repack' in url:
        file_types.append('REPACK')
    if 'proper' in url:
        file_types.append('PROPER')
    if 'nuked' in url:
        file_types.append('NUKED')

    return '[COLOR lawngreen] / [/COLOR]'.join(file_types)



def getFileType_bak(url):

    try:
        url = c.ensure_str(url)
        url = client.replaceHTMLCodes(url)
        url = unquote(url)
        url = url.lower()
        url = re.sub('[^a-z0-9 ]+', ' ', url)
    except Exception:
        url = str(url)
    type = ''

    if any(i in url for i in [' bluray ', ' blu ray ']):
        type += ' BLURAY /'
    if any(i in url for i in [' bd r ', ' bdr ', ' bd rip ', ' bdrip ', ' br rip ', ' brrip ']):
        type += ' BD-RIP /'
    if ' remux ' in url:
        type += ' REMUX /'
    if any(i in url for i in [' dvdrip ', ' dvd rip ']):
        type += ' DVD-RIP /'
    if any(i in url for i in [' dvd ', ' dvdr ', ' dvd r ']):
        type += ' DVD /'
    if any(i in url for i in [' webdl ', ' web dl ', ' web ', ' web rip ', ' webrip ']):
        type += ' WEB /'
    if ' hdtv ' in url:
        type += ' HDTV /'
    if ' sdtv ' in url:
        type += ' SDTV /'
    if any(i in url for i in [' hdrip ', ' hd rip ']):
        type += ' HDRIP /'
    if any(i in url for i in [' uhdrip ', ' uhd rip ']):
        type += ' UHDRIP /'
    if ' r5 ' in url:
        type += ' R5 /'
    if any(i in url for i in [' cam ', ' hdcam ', ' hd cam ', ' cam rip ', ' camrip ']):
        type += ' CAM /'
    if any(i in url for i in [' ts ', ' telesync ', ' hdts ', ' pdvd ']):
        type += ' TS /'
    if any(i in url for i in [' tc ', ' telecine ', ' hdtc ']):
        type += ' TC /'
    if any(i in url for i in [' scr ', ' screener ', ' dvdscr ', ' dvd scr ']):
        type += ' SCR /'
    if ' xvid ' in url:
        type += ' XVID /'
    if ' avi' in url:
        type += ' AVI /'
    if any(i in url for i in [' h 264 ', ' h264 ', ' x264 ', ' avc ']):
        type += ' H.264 /'
    if any(i in url for i in [' h 265 ', ' h256 ', ' x265 ', ' hevc ']):
        type += ' HEVC /'
    if ' hi10p ' in url:
        type += ' HI10P /'
    if ' 10bit ' in url:
        type += ' 10BIT /'
    if ' 3d ' in url:
        type += ' 3D /'
    if any(i in url for i in [' hdr ', ' hdr10 ', ' dolby vision ', ' hlg ']):
        type += ' HDR /'
    if ' imax ' in url:
        type += ' IMAX /'
    if any(i in url for i in [' ac3 ', ' ac 3 ']):
        type += ' AC3 /'
    if ' aac ' in url:
        type += ' AAC /'
    if ' aac5 1 ' in url:
        type += ' AAC / 5.1 /'
    if any(i in url for i in [' dd ', ' dolby ', ' dolbydigital ', ' dolby digital ']):
        type += ' DD /'
    if any(i in url for i in [' truehd ', ' true hd ']):
        type += ' TRUEHD /'
    if ' atmos ' in url:
        type += ' ATMOS /'
    if any(i in url for i in [' ddplus ', ' dd plus ', ' ddp ', ' eac3 ', ' eac 3 ']):
        type += ' DD+ /'
    if ' dts ' in url:
        type += ' DTS /'
    if any(i in url for i in [' hdma ', ' hd ma ']):
        type += ' HD.MA /'
    if any(i in url for i in [' hdhra ', ' hd hra ']):
        type += ' HD.HRA /'
    if any(i in url for i in [' dtsx ', ' dts x ']):
        type += ' DTS:X /'
    if ' dd5 1 ' in url:
        type += ' DD / 5.1 /'
    if ' ddp5 1 ' in url:
        type += ' DD+ / 5.1 /'
    if any(i in url for i in [' 5 1 ', ' 6ch ']):
        type += ' 5.1 /'
    if any(i in url for i in [' 7 1 ', ' 8ch ']):
        type += ' 7.1 /'
    if ' korsub ' in url:
        type += ' HC-SUBS /'
    if any(i in url for i in [' subs ', ' subbed ', ' sub ']):
        type += ' SUBS /'
    if any(i in url for i in [' dub ', ' dubbed ', ' dublado ']):
        type += ' DUB /'
    if ' repack ' in url:
        type += ' REPACK /'
    if ' proper ' in url:
        type += ' PROPER /'
    if ' nuked ' in url:
        type += ' NUKED /'
    type = type.rstrip('/')
    return type

def check_sd_url(release_link):
    try:
        release_link = re.sub('[^A-Za-z0-9]+', ' ', release_link)
        release_link = release_link.lower()
        try:
            release_link = c.ensure_str(release_link)
        except Exception:
            pass
        quality = get_quality(release_link)
        if not quality:
            quality = 'sd'
        return quality
    except Exception:
        return 'sd'


def check_direct_url(url):
    try:
        url = re.sub('[^A-Za-z0-9]+', ' ', url)
        url = c.ensure_str(url)
        url = url.lower()
        quality = get_quality(url)
        if not quality:
            quality = 'sd'
        return quality
    except Exception:
        return 'sd'

def check_url(url):
    try:
        url = client.replaceHTMLCodes(url)
        url = unquote(url)
        url = re.sub('[^A-Za-z0-9]+', ' ', url)
        url = c.ensure_str(url)
        url = url.lower()
    except Exception:
        url = str(url)

    try:
        quality = get_quality(url)
        if not quality:
            quality = 'sd'
        return quality
    except Exception:
        return 'sd'

def label_to_quality(label):
    try:
        try:
            label = int(re.search('(\d+)', label).group(1))
        except Exception:
            label = 0

        if label >= 2160:
            return '4K'
        elif label >= 1080:
            return '1080p'
        elif 720 <= label < 1080:
            return '720p'
        elif label < 720:
            return 'sd'
    except Exception:
        return 'sd'

def strip_domain(url):
    try:
        url = c.ensure_str(url)
        if url.lower().startswith('http') or url.startswith('/'):
            url = re.findall('(?://.+?|)(/.+)', url)[0]
        url = client.replaceHTMLCodes(url)
        return url
    except Exception:
        return


def is_host_valid(url, domains):
    try:
        url = c.ensure_str(url).lower()
        if any(x in url for x in ['.rar.', '.zip.', '.iso.']) or any(url.endswith(x) for x in ['.rar', '.zip', '.idx', '.sub', '.srt']):
            return False, ''
        if any(x in url for x in ['sample', 'trailer', 'zippyshare', 'facebook', 'youtu']):
            return False, ''
        host = __top_domain(url)
        hosts = [domain.lower() for domain in domains if host and host in domain.lower()]

        if hosts and '.' not in host:
            host = hosts[0]
        if hosts and any([h for h in ['google', 'picasa', 'blogspot'] if h in host]):
            host = 'gvideo'
        if hosts and any([h for h in ['akamaized','ocloud'] if h in host]):
            host = 'CDN'
        return any(hosts), host
    except Exception:
        return False, ''


def __top_domain(url):
    if not (url.startswith('//') or url.startswith('http://') or url.startswith('https://')):
        url = '//' + url
    elements = urlparse(url)
    domain = elements.netloc or elements.path
    domain = domain.split('@')[-1].split(':')[0]
    regex = "(?:www\.)?([\w\-]*\.[\w\-]{2,3}(?:\.[\w\-]{2,3})?)$"
    res = re.search(regex, domain)
    if res:
        domain = res.group(1)
    domain = domain.lower()
    return domain

def aliases_to_array(aliases, filter=None):
    try:
        if not filter:
            filter = []
        if isinstance(filter, str):
            filter = [filter]

        return [x.get('title') for x in aliases if not filter or x.get('country') in filter]
    except Exception:
        return []


def append_headers(headers):
    return '|%s' % '&'.join(['%s=%s' % (key, quote_plus(headers[key])) for key in headers])


def _size(siz):
    if siz in ['0', 0, '', None]:
        return 0.0, ''
    div = 1 if siz.lower().endswith(('gb', 'gib')) else 1024
    float_size = float(re.sub('[^0-9|/.|/,]', '', siz.replace(',', '.'))) / div
    str_size = str('%.2f GB' % float_size)
    return float_size, str_size

def file_size(siz):
    if siz in ['0', 0, '', None]:
        return 0.0, ''
    div = 1 if siz.lower().endswith(('gb', 'gib')) else 1024
    float_size = float(re.sub('[^0-9|/.|/,]', '', siz.replace(',', '.'))) / div
    str_size = str('%.2f GB' % float_size)
    return float_size, str_size



def get_size(url):
    try:
        size = client.request(url, output='file_size')
        if size == '0':
            size = False
        size = convert_size(size)
        return size
    except Exception:
        return False


def convert_size_old(size_bytes):
    import math
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    if size_name[i] == 'B' or size_name[i] == 'KB':
        return None
    return "%s %s" % (s, size_name[i])

def convert_size(size_bytes):
    import math
    if size_bytes == 0:
        return "0B"
    units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    index = int(math.floor(math.log(size_bytes, 1024)))
    power = math.pow(1024, index)
    size = round(size_bytes / power, 2)
    if units[index] in ('B', 'KB'):
        return None
    return f"{size} {units[index]}"



def check_directstreams(url, hoster='', quality='SD'):
    urls = []
    host = hoster

    if 'google' in url or any(x in url for x in ['youtube.', 'docid=']):
        urls = directstream.google(url)
        if not urls:
            tag = directstream.googletag(url)
            if tag:
                urls = [{'quality': tag[0]['quality'], 'url': url}]
        if urls:
            host = 'gvideo'
    elif 'ok.ru' in url:
        urls = directstream.odnoklassniki(url)
        if urls:
            host = 'vk'
    elif 'vk.com' in url:
        urls = directstream.vk(url)
        if urls:
            host = 'vk'
    elif any(x in url for x in ['akamaized', 'blogspot', 'ocloud.stream']):
        urls = [{'url': url}]
        if urls:
            host = 'CDN'

    direct = True if urls else False

    if not urls:
        urls = [{'quality': quality, 'url': url}]

    return urls, host, direct

def scraper_error(name):
    c.log('An exception error in scraper "' + name + '" occurred.')


# if salt is provided, it should be string
# ciphertext is base64 and passphrase is string
def evp_decode(cipher_text, passphrase, salt=None):
    cipher_text = base64.b64decode(cipher_text)
    if not salt:
        salt = cipher_text[8:16]
        cipher_text = cipher_text[16:]
    data = evpKDF(passphrase, salt)
    decrypter = pyaes.Decrypter(pyaes.AESModeOfOperationCBC(data['key'], data['iv']))
    plain_text = decrypter.feed(cipher_text)
    plain_text += decrypter.feed()
    return plain_text


def evpKDF(passwd, salt, key_size=8, iv_size=4, iterations=1, hash_algorithm="md5"):
    target_key_size = key_size + iv_size
    derived_bytes = ""
    number_of_derived_words = 0
    block = None
    hasher = hashlib.new(hash_algorithm)
    while number_of_derived_words < target_key_size:
        if block is not None:
            hasher.update(block)

        hasher.update(passwd)
        hasher.update(salt)
        block = hasher.digest()
        hasher = hashlib.new(hash_algorithm)

        for _i in range(1, iterations):
            hasher.update(block)
            block = hasher.digest()
            hasher = hashlib.new(hash_algorithm)

        derived_bytes += block[0: min(len(block), (target_key_size - number_of_derived_words) * 4)]

        number_of_derived_words += len(block) / 4

    return {
        "key": derived_bytes[0: key_size * 4],
        "iv": derived_bytes[key_size * 4:]
    }
