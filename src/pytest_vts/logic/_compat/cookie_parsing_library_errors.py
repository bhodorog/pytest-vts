"""This particular compatibility module deals with various libraries
difficulties of parsing certain Set-Cookie header values, such as:
  - 'Expires=Fri, 24 Feb 2017 00:58:28 GMT'

The purpose of this compabitility module is to allow pytest-vts to work with
any version of responses (which mightbe locked in by other dependency.). For
now I prefer this solution to vendoring responses entirely.

`responses` library has been using various libraries for parsing the Set-Cookie
header value.
  1. `responses <0.10.0` used cookies library
  2. `responses ==0.10.0,==0.10.1` used biscuits library
  3. `responses >=0.10.2` has been using http.cookies (for python3) and cookie
      for (python2)

Note: since it's quite hard to actually detect what cookie parsing library is used by responses
  - older releases didn't extracted the cookie parsing code in it's own method.
or to dynamically detect the installed version of responses:
  - pkg_resources has been known to fail detecting the version of the installed
    package on some ocasions assumptions are made by the following code. The
first library successfully loaded will be the one assumed to be used by
responses. This approach might fail in complex virtualenvs with multiple cookie
parsing libraries installed, but should cover most common cases.
"""

COOKIE_PARSING_LIBRARY_LOADED = ''

if not COOKIE_PARSING_LIBRARY_LOADED:
    try:
        # http.cookies is being used for python>3.4 and responses >=0.10.2
        import http.cookies
    except ImportError:
        pass
    else:
        COOKIE_PARSING_LIBRARY_LOADED = 'http.cookies'
        def is_failing_parsing(set_cookie_header):
            cc = http.cookies.SimpleCookie()
            cc.load(set_cookie_header)
            # http.cookies won't raise when it fails to parse a cookie header
            return False


if not COOKIE_PARSING_LIBRARY_LOADED:
    try:
        # cookies is still being used for python <3.4 by responses
        import cookies
    except ImportError:
        pass
    else:
        COOKIE_PARSING_LIBRARY_LOADED = 'cookies'
        def is_failing_parsing(set_cookie_header):
            try:
                cookies.Cookies.from_request(set_cookie_header)
            except Exception:
                """it seems cookies library has difficulties in parsing a set-cookie
                header containing 'Expires=Fri, 24 Feb 2017 00:58:28 GMT'."""
                return True
            else:
                return False

if not COOKIE_PARSING_LIBRARY_LOADED:
    try:
        # biscuits was used by responses ==0.10.0, ==0.10.1
        import biscuits
        COOKIE_PARSING_LIBRARY_LOADED = 'biscuits'
        def is_failing_parsing(set_cookie_header):
            try:
                biscuits.parse(set_cookie_header)
            except Exception:
                """it seems cookies library has difficulties in parsing a
                set-cookie header containing 'Expires=Fri, 24 Feb 2017 00:58:28
                GMT'. This code tries to be defensive about it for alternative
                libraries used by responses"""
                return True
            else:
                return False
    except ImportError:
        pass

if not COOKIE_PARSING_LIBRARY_LOADED:
    def is_failing_parsing(set_cookie_header):
        return False
