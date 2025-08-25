# -*- coding: utf-8 -*-

'''
********************************************************cm*
* The Crew Add-on
*
* @file dom_parser.py
* @package script.module.thecrew
*
* Based on Parsedom for XBMC plugins
* Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen
*
* @copyright (c) 2025, The Crew
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''



import re

from collections import namedtuple

from .crewruntime import c

import six

DomMatch = namedtuple('DOMMatch', ['attrs', 'content'])
re_type = type(re.compile(''))


def __get_dom_content(html, name, match):
    if match.endswith('/>'):
        return ''

    # override tag name with tag from match if possible
    tag = re.match(r'<([^\s/>]+)', match)
    if tag:
        name = tag.group(1)

    start_str = f'<{name}'
    end_str = f"</{name}"

    # start/end tags without matching case cause issues
    start = html.find(match)
    end = html.find(end_str, start)
    pos = html.find(start_str, start + 1)

    while pos < end and pos != -1:  # Ignore too early </endstr> return
        tend = html.find(end_str, end + len(end_str))
        if tend != -1:
            end = tend
        pos = html.find(start_str, pos + 1)

    if start == -1 and end == -1:
        result = ''
    elif start > -1 and end > -1:
        result = html[start + len(match):end]
    elif end > -1:
        result = html[:end]
    elif start > -1:
        result = html[start + len(match):]
    else:
        result = ''

    return result


def __get_dom_elements(item, name, attrs):
    if not attrs:
        pattern = f'(<{name}' + r'(?:\s[^>]*>|/?>))'
        this_list = re.findall(pattern, item, re.M | re.S | re.I)
    else:
        last_list = None
        for key, value in attrs.items():
            value_is_regex = isinstance(value, re_type)
            value_is_str = isinstance(value, str)
            # pattern = '''(<{tag}[^>]*\s{key}=(?P<delim>['"])(.*?)(?P=delim)[^>]*>)'''.format(tag=name, key=key)
            pattern = f'(<{name}[^>]*\s{key}=(?P<delim>["\'])(.*?)(?P=delim)[^>]*>)'
            re_list = re.findall(pattern, item, re.M | re.S | re.I)
            if value_is_regex:
                this_list = [r[0] for r in re_list if re.match(value, r[2])]
            else:
                temp_value = [value] if value_is_str else value
                this_list = [r[0] for r in re_list if set(temp_value) <= set(r[2].split(' '))]

            if not this_list:
                has_space = (value_is_regex and ' ' in value.pattern) or (value_is_str and ' ' in value)
                if not has_space:
                    # pattern = '''(<{tag}[^>]*\s{key}=((?:[^\s>]|/>)*)[^>]*>)'''.format(tag=name, key=key)
                    pattern = f'(<{name}' + r'(?:[^>]*\s{key}=((?:[^\s>]|/>)*)[^>]*>)'
                    re_list = re.findall(pattern, item, re.M | re.S | re.I)
                    if value_is_regex:
                        this_list = [r[0] for r in re_list if re.match(value, r[1])]
                    else:
                        this_list = [r[0] for r in re_list if value == r[1]]

            if last_list is None:
                last_list = this_list
            else:
                last_list = [item for item in this_list if item in last_list]
        this_list = last_list

    if this_list is None:
        this_list = []

    return this_list


def __get_attribs(element):
    attribs = {}
    for match in re.finditer(r'\s+(?P<key>[^=]+)=\s*(?:(?P<delim>["\'])(?P<value1>.*?)(?P=delim)|(?P<value2>[^"\'][^>\s]*))', element):
        match = match.groupdict()
        value1 = match.get('value1')
        value2 = match.get('value2')
        value = value1 if value1 is not None else value2
        if value is None:
            continue
        attribs[match['key'].lower().strip()] = value
    return attribs

#TC 2/01/19 started
def parse_dom(html, name='', attrs=None, req=False, exclude_comments=False):
    if attrs is None:
        attrs = {}
    name = name.strip()
    if isinstance(html, (str, DomMatch)):
        html = [html]
    elif isinstance(html, bytes):
        try:
            html = [html.decode("utf-8")]  # Replace with chardet thingy
        except:
            try:
                html = [html.decode("utf-8", "replace")]
            except:
                html = [html]
    elif not isinstance(html, list):
        return ''

    if not name:
        return ''

    if not isinstance(attrs, dict):
        return ''

    if req:
        if not isinstance(req, list):
            req = [req]
        req = set([key.lower() if isinstance(key, str) else key for key in req])

    all_results = []
    for item in html:
        if isinstance(item, DomMatch):
            item = item.content

        if exclude_comments:
            if isinstance(item, bytes):
                item = item.decode("utf-8", "replace")
            item = re.sub(re.compile('<!--.*?-->', re.DOTALL), '', item)

        results = []
        for element in __get_dom_elements(item, name, attrs):
            attribs = __get_attribs(element)
            if req and not req <= set(attribs.keys()):
                continue
            temp = __get_dom_content(item, name, element).strip()
            results.append(DomMatch(attribs, temp))
            item = item[item.find(temp, item.find(element)):]
        all_results += results

    return all_results
