import copy
import functools
import json
import re
import logging
import os.path

import py.path
import requests
import responses
import six

from pytest_vts.logic._compat.cookie_parsing_library_errors import is_failing_parsing

_logger = logging.getLogger(__name__)


class InvalidCassetteLocation(Exception):
    pass


class RequestBodyDoesntMatchTrack(Exception):
    pass


def ensure_text_silent(s, *args, **kwargs):
    if s is None:
        return s
    return six.ensure_text(s, *args, **kwargs)

def function_name(pytest_req):
    return pytest_req.node.name


def class_function_name(pytest_req):
    function_name = pytest_req.node.name
    class_name = pytest_req.cls.__name__ if getattr(pytest_req, "cls") else ""
    rv = ".".join([class_name, function_name])
    return rv.strip(".")


def no_op(func):
    @functools.wraps(func)
    def _inner(prep_req, *args, **kwargs):
        return func(prep_req, *args, **kwargs)
    return _inner


def _make_urllib3(http_prep_req):
    try:
        # carefull with this since it's silencing any Insecure SSL warnings
        requests.packages.urllib3.disable_warnings()
        pm = requests.packages.urllib3.PoolManager()
        resp = pm.urlopen(
            method=http_prep_req.method,
            url=http_prep_req.url,
            body=http_prep_req.body,
            headers=http_prep_req.headers,
            redirect=False,
            assert_same_host=False,
            preload_content=False,
            decode_content=True,
            retries=3,
        )
    except:
        raise
    else:
        try:
            body = json.loads(resp.data.decode("utf-8"))
            bodys = json.dumps(body)
        except ValueError:
            body = bodys = resp.data.decode("utf-8")
        return resp.status, dict(resp.headers.items()), bodys


class Recorder(object):
    """Video Test System, name inspired by VHS

    Able to record/playback cassettes. Each cassette is made of tracks (one
    HTTP request-response pair).

    Depends of py.test and responses (or a http mocking lib which support
    callbacks as stub reponse)

    While .responses already keeps a collection of `.calls`, they're not
    directly json serializable therefore a json version of the `.cassette` is
    being constructed from `.calls`
    """
    def __init__(self, pytest_req, basedir=None, cassette_name=function_name):
        self.cassette = []
        self.has_recorded = False
        self.is_recording = self.is_playing = False
        self._pytst_req = pytest_req
        self._basedir = basedir
        self._cass_dir = self._init_destination(basedir)
        self._init_cassette_name(cassette_name)
        self.strict_body = False
        self.responses = responses.RequestsMock(
            assert_all_requests_are_fired=False)

    def _init_cassette_name(self, cassette_name):
        if cassette_name and callable(cassette_name):
            self.cassette_name = cassette_name(self._pytst_req)
        else:
            self.cassette_name = cassette_name

    @classmethod
    def clone(cls, other):
        cloned = cls(other._pytst_req, other._basedir, other.cassette_name)
        cloned._cass_dir = other._cass_dir
        return cloned

    def _init_destination(self, basedir):
        if not basedir:
            return self._pytst_req.fspath.dirpath().join("cassettes")
        return py.path.local(basedir, expanduser=True)

    def setup(self, basedir=None, cassette_name=function_name, **kwargs):
        if basedir:
            self._cass_dir = self._init_destination(basedir)
        self._init_cassette_name(cassette_name)
        self.responses.start()
        force_recording = os.environ.get("PYTEST_VTS_FORCE_RECORDING", False)
        if not self.has_cassette or force_recording:
            self.setup_recording(
                kwargs.get("request_wrapper", no_op),
                **kwargs.get("rec_kwargs", {}))
        else:
            self.setup_playback(
                kwargs.get("request_wrapper", no_op),
                **kwargs.get("play_kwargs", {}))

    def setup_recording(self, request_wrapper=no_op, **kwargs):
        _logger.info("setup recording ...")
        self.is_recording = True
        self.is_playing = False
        self.responses.reset()
        all_requests_re = re.compile("http.*")
        methods = (responses.GET, responses.POST, responses.PUT,
                   responses.PATCH, responses.DELETE, responses.HEAD,
                   responses.OPTIONS)
        callback = self.record(request_wrapper(_make_urllib3))
        for http_method in methods:
            self.responses.add_callback(
                http_method, all_requests_re,
                match_querystring=False,
                callback=callback)

    def setup_playback(self, request_wrapper=no_op, **kwargs):
        _logger.info("setup playback ...")
        self.is_recording = False
        self.is_playing = True
        self._insert_cassette()
        self.responses.reset()  # reset recording matchers
        self.rewind_cassette(request_wrapper, **kwargs)

    def teardown(self):
        _logger.info("teardown ...")
        self.responses.stop()
        self.responses.reset()
        if self.has_recorded and self._test_has_passed:
            self._save_cassette()

    def _save_cassette(self):
        self._cass_file().write(
            json.dumps(self.cassette, indent=4),
            ensure=True)

    def _flip_mode(self):
        self.is_playing = not self.is_playing
        self.is_recording = not self.is_recording
        self.has_recorded = not self.has_recorded

    @property
    def _test_has_passed(self):
        # set by the hookwrapper
        if not hasattr(self._pytst_req.node, "rep_call"):
            return False
        return self._pytst_req.node.rep_call.passed

    def _test_name(self):
        filename = self.cassette_name.replace(os.path.sep, "_")
        return ".".join((filename, "json"))

    def _cass_file(self):
        return self._cass_dir.join(self._test_name())

    @property
    def has_cassette(self):
        return self._cass_file().exists()

    def play(self, track, **kwargs):
        recorded_req = track["request"]
        resp = _adjust_headers_for_responses(track["response"])

        def _callback(crt_http_req):
            same_body = _compare_bodies(crt_http_req.body,
                                        recorded_req.get("body"))
            if kwargs.get("strict_body") or self.strict_body:
                assert same_body, "Recorded body doesn't match the current request's body."
            elif not same_body:
                err_msg = ("Requests body doesn't match recorded track's "
                           "body!!:\n{}\n!=\n{}").format(
                               crt_http_req.body, recorded_req.get("body"))
                _logger.warn(err_msg)
            return (resp["status_code"],
                    resp["headers"],
                    json.dumps(resp["body"]))
        return _callback

    def rewind_cassette(self, request_wrapper, **kwargs):
        for track in self.cassette:
            req = track["request"]
            callback = request_wrapper(self.play(track, **kwargs))
            self.responses.add_callback(
                req["method"], req["url"],
                match_querystring=True,
                callback=callback)

    def _insert_cassette(self):
        if not self.has_recorded:
            data = self._cass_file().read_text("utf8")
            self.cassette = json.loads(data)

    def record(self, _make_func=_make_urllib3):
        """Uses urllib3 to fetch the urls which needs to be
        recorded. Having the request already prepacked for requests would
        make it easier to use requests, it means we need to temporarily
        stop responses until we fetch the response. This introduces
        isolation problems since HTTP requests made by other execution
        units (green thread, os threads) while responses is stopped won't
        be intercepted and persisted in the cassette."""
        def _callback(http_prep_req):
            status, headers, body = _make_func(http_prep_req)
            track = self.build_track(http_prep_req,
                                     status, headers, _json_or_str(body))
            self.cassette.append(track)
            self.has_recorded = True
            responses_friendly_headers = _adjust_headers_for_responses(
                track["response"])["headers"]
            return status, responses_friendly_headers, body

        return _callback

    def build_track(self, http_prep_req, status, headers, body):
        track = {}
        track["request"] = {
            "method": http_prep_req.method,
            "url": http_prep_req.url,
            "path": http_prep_req.path_url,
            "headers": dict(http_prep_req.headers.items()),
            "body": ensure_text_silent(http_prep_req.body),
        }
        track["response"] = {
            "status_code": status,
            "headers": headers,
            "body": body,
        }
        return track

    @property
    def requested_urls(self):
        return [track['request']['url'] for track in self.cassette]

    def tracks(self, url, ignore_qs=False):
        ffilter = _only_path if ignore_qs else _whole_url
        tracks = [tr for tr in self.cassette
                  if ffilter(tr["request"]["url"]) == ffilter(url)]
        return tracks

    def record_old(self):
        def _callback(http_prep_req):
            """Uses urllib3 to fetch the urls which needs to be
            recorded. Having the request already prepacked for requests would
            make it easier to use requests, it means we need to temporarily
            stop responses until we fetch the response. This introduces
            isolation problems since HTTP requests made by other execution
            units (green thread, os threads) while responses is stopped won't
            be intercepted and persisted in the cassette."""
            track = {}
            track["request"] = {
                "method": http_prep_req.method,
                "url": http_prep_req.url,
                "path": http_prep_req.path_url,
                "headers": dict(http_prep_req.headers.items()),
                "body": http_prep_req.body,
            }
            try:
                # carefull with this since it's silencing any Insecure SSL warnings
                requests.packages.urllib3.disable_warnings()
                pm = requests.packages.urllib3.PoolManager()
                resp = pm.urlopen(
                    method=http_prep_req.method,
                    url=http_prep_req.url,
                    body=http_prep_req.body,
                    headers=http_prep_req.headers,
                    redirect=False,
                    assert_same_host=False,
                    preload_content=False,
                    decode_content=True,
                    retries=3,
                )
            except:
                raise
            else:
                try:
                    body = json.loads(resp.data.decode("utf-8"))
                    bodys = json.dumps(body)
                except ValueError:
                    body = bodys = resp.data.decode("utf-8")
                track["response"] = {
                    "status_code": resp.status,
                    "headers": dict(resp.headers.items()),
                    "body": ensure_text_silent(body),
                }
                self.cassette.append(track)
                self.has_recorded = True
                return (track["response"]["status_code"],
                        _adjust_headers_for_responses(track["response"])["headers"],
                        bodys)
        return _callback


def _only_path(url):
    return url.split("?")[0]


def _whole_url(url):
    return url


def _adjust_headers_for_responses(track_response):
    replica = copy.deepcopy(track_response)
    replica["headers"] = {
        key.upper(): val
        for key, val in six.iteritems(replica["headers"])}
    content_encoding = replica["headers"].get("CONTENT-ENCODING", "")
    if "gzip" in content_encoding:
            # the body has already been decoded by the actual http call
            # made during recording (using
            # requests.Sessions.send). Keeping the gzip encoding in the
            # response headers of will force the calling functions
            # (during recording or replaying) (using requests) to try
            # to decode it again.

            # when urllib3 sees a Content-Encoding header will try
            # to decode the response using the specified encoding,
            # thus we need to remove it since it"s been already
            # decoded
        del replica["headers"]["CONTENT-ENCODING"]
    transfer_encoding = replica["headers"].get("TRANSFER-ENCODING", "")
    if "chunked" in transfer_encoding:
        """doesn't make senses passing Transfer-Encoding when chunked since
        responses will build an urllib3.response.HTTPResponse object with the
        body wrapped into a StringIO and if chunked is passed to it it will try
        to read the body of the response from a socket like object which will
        fail since StringIO is not a socket object (e.g. lacks an _fp
        attribute)"""

        del replica["headers"]["TRANSFER-ENCODING"]
    set_cookie = replica["headers"].get("SET-COOKIE")
    if set_cookie and is_failing_parsing(set_cookie):
        del replica["headers"]["SET-COOKIE"]
    return replica


def _json_or_str(body):
    try:
        body_j = json.loads(body)
    except ValueError:
        return body
    return body_j



def _compare_bodies(left, right):
    """rely on the fact that within the same process the hashing of dicts
    should be consistent"""
    try:
        lobj = json.loads(left)
        robj = json.loads(right)
    except Exception:
        return False
    return lobj == robj
