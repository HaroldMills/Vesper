"""
Utility functions concerning United States Naval Observatory (USNO) data.
"""


import math
import urllib
import urllib2


_PRE_BEGIN = '<pre>'
_PRE_END = '</pre>'


def get_angle_data(x):
    sign = get_sign(x)
    x = abs(x)
    degrees = int(math.floor(x))
    minutes = int(round(60 * (x - degrees)))
    return (sign, degrees, minutes)


def get_sign(x):
    return 1 if x >= 0 else -1


def get_utc_offset_data(utc_offset, lon):
    if utc_offset is None:
        utc_offset = 24 * (lon / 360.)
    sign = get_sign(utc_offset)
    offset = abs(utc_offset)
    return (sign, offset)


def download_table(url, values):
    
    data = urllib.urlencode(values)
    
    # While this function downloads sun and moon rise/set tables just fine,
    # I have not been able to download sun and moon altitude/azimuth tables
    # with it. Whenever I try to download and altitude/azimuth table, I get
    # an HTTP response with code 200 that contains the error message:
    # "Error:  Location/coordinates not defined".
    #
    # An example (with added line wrapping) of the URL of a Python request
    # that fails is:
    #
    #     http://aa.usno.navy.mil/cgi-bin/aa_altazw.pl?
    #         form=2&body=10&place=Ithaca%2C+NY&year=2016&month=2&day=10&
    #         intv_mag=10&lat_sign=1&lat_deg=42&lat_min=27&
    #         lon_sign=-1&lon_deg=76&lon_min=30&tz_sign=-1&tz=5
    #
    # When I fetch the same URL by pasting it into the Chrome address bar,
    # I get the expected altitude/azimuth table.
    #
    # I am not sure why HTTP requests that I send from Python result in
    # different responses than the requests that Chrome sends for the same
    # URL. I tried making my Python HTTP request headers identical to those
    # of Chrome's requests (see the commented-out code below), but that did
    # not help.
    
#     headers = {
#         'Accept': (
#             'text/html,application/xhtml+xml,application/xml;q=0.9,'
#             'image/webp,*/*;q=0.8'),
#         'Accept-Encoding': 'gzip, deflate, sdch',
#         'Accept-Language': 'en-US,en;q=0.8,es;q=0.6',
#         'Connection': 'keep-alive',
#         'Host': 'aa.usno.navy.mil',
#         'Referer': 'http://aa.usno.navy.mil/data/docs/AltAz.php',
#         'Upgrade-Insecure-Requests': '1',
#         'User-Agent': (
#             'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) '
#             'AppleWebKit/537.36 (KHTML, like Gecko) '
#             'Chrome/48.0.2564.109 Safari/537.36')
#     }
    headers = {}
    
    request = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(request)
    html = response.read()
    
    start = html.find(_PRE_BEGIN) + len(_PRE_BEGIN)
    end = html.find(_PRE_END)
    text = html[start:end].strip('\n') + '\n'
     
    return text
