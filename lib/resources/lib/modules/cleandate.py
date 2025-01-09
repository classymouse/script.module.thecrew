# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2015 lambda

    -Mofidied by The Crew
    -Copyright (C) 2019 The Crew


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

import time
import datetime




def iso_to_utc(iso_ts):
    if not iso_ts or iso_ts is None: return 0
    delim = -1
    if not iso_ts.endswith('Z'):
        delim = iso_ts.rfind('+')
        if delim == -1: delim = iso_ts.rfind('-')

    if delim > -1:
        ts = iso_ts[:delim]
        sign = iso_ts[delim]
        tz = iso_ts[delim + 1:]
    else:
        ts = iso_ts
        tz = None

    if ts.find('.') > -1:
        ts = ts[:ts.find('.')]

    try: d = datetime.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S')
    except TypeError: d = datetime.datetime(*(time.strptime(ts, '%Y-%m-%dT%H:%M:%S')[0:6]))

    dif = datetime.timedelta()
    if tz:
        hours, minutes = tz.split(':')
        hours = int(hours)
        minutes = int(minutes)
        if sign == '-':
            hours = -hours
            minutes = -minutes
        dif = datetime.timedelta(minutes=minutes, hours=hours)
    utc_dt = d - dif
    epoch = datetime.datetime.utcfromtimestamp(0)
    delta = utc_dt - epoch
    try: seconds = delta.total_seconds()  # works only on 2.7
    except: seconds = delta.seconds + delta.days * 24 * 3600  # close enough
    return seconds







def iso_to_utc2(iso_timestamp):
    """
    Convert ISO 8601-formatted timestamp to UTC epoch time in seconds.

    :param iso_timestamp: ISO 8601-formatted timestamp
    :type iso_timestamp: str
    :return: UTC epoch time in seconds
    :rtype: int
    """
    if not iso_timestamp:
        return 0

    ts_end = iso_timestamp.rfind('+')
    if ts_end == -1:
        ts_end = iso_timestamp.rfind('-')

    timestamp = iso_timestamp[:ts_end]
    tz_offset = iso_timestamp[ts_end:]

    if '.' in timestamp:
        timestamp = timestamp[:timestamp.find('.')]

    try:
        dt = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')
    except TypeError:
        dt = datetime.datetime(*time.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')[:6])

    tz_dif = datetime.timedelta()
    if tz_offset:
        tz_sign = tz_offset[0]
        tz_hours, tz_minutes = map(int, tz_offset[1:].split(':'))
        if tz_sign == '-':
            tz_hours = -tz_hours
            tz_minutes = -tz_minutes
        tz_dif = datetime.timedelta(minutes=tz_minutes, hours=tz_hours)

    utc_dt = dt - tz_dif
    epoch = datetime.datetime.fromtimestamp(0)
    delta = utc_dt - epoch
    return int(delta.total_seconds())
