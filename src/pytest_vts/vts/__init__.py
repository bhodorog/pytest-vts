import copy
import json
import re
import logging
import os.path

import py.path
import requests
import responses
import six


_logger = logging.getLogger(__name__)


class InvalidCassetteLocation(Exception):
    pass

class RequestBodyDoesntMatchTrack(Exception):
    pass


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
    def __init__(self, pytest_req, basedir=None, cassette_name=None):
        self.cassette = []
        self.has_recorded = False
        self.is_recording = self.is_playing = False
        self._pytst_req = pytest_req
        self._basedir = basedir
        self._cass_dir = self._init_destination(basedir)
        self.cassette_name = cassette_name or self._pytst_req.node.name
        self.strict_body = False
        self.responses = responses.RequestsMock(
            assert_all_requests_are_fired=False)

    @classmethod
    def clone(cls, other):
        cloned = cls(other._pytst_req, other._basedir, other.cassette_name)
        cloned._cass_dir = other._cass_dir
        return cloned

    def _init_destination(self, basedir):
        if not basedir:
            return self._pytst_req.fspath.dirpath().join("cassettes")
        return py.path.local(basedir, expanduser=True)

    def setup(self, basedir=None, cassette_name=None, **kwargs):
        if basedir:
            self._cass_dir = self._init_destination(basedir)
        self.cassette_name = cassette_name or self._pytst_req.node.name
        self.responses.start()
        force_recording = os.environ.get("PYTEST_VTS_FORCE_RECORDING", False)
        if not self.has_cassette or force_recording:
            self.is_recording = True
            self.setup_recording(**kwargs.get("rec_kwargs", {}))
        else:
            self.is_playing = True
            self.setup_playback(**kwargs.get("play_kwargs", {}))

    def setup_recording(self, **kwargs):
        _logger.info("recording ...")
        self.responses.reset()
        all_requests_re = re.compile("http.*")
        methods = (responses.GET, responses.POST, responses.PUT,
                   responses.PATCH, responses.DELETE, responses.HEAD,
                   responses.OPTIONS)
        for http_method in methods:
            self.responses.add_callback(
                http_method, all_requests_re,
                match_querystring=False,
                callback=self.record())

    def setup_playback(self, **kwargs):
        _logger.info("playing back ...")
        self._insert_cassette()
        self.responses.reset()  # reset recording matchers
        self.rewind_cassette(**kwargs)

    def teardown(self):
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
            if kwargs.get("strict_body") or self.strict_body:
                assert crt_http_req.body == recorded_req.get("body"), "Recorded body doesn't match the current request's body."
            elif crt_http_req.body != recorded_req.get("body"):
                err_msg = ("Requests body doesn't match recorded track's "
                           "body!!:\n{}\n!=\n{}").format(
                               crt_http_req.body, recorded_req.get("body"))
                _logger.warn(err_msg)
            return (resp["status_code"],
                    resp["headers"],
                    json.dumps(resp["body"]))
        return _callback

    def rewind_cassette(self, **kwargs):
        for track in self.cassette:
            req = track["request"]
            self.responses.add_callback(
                req["method"], req["url"],
                match_querystring=True,
                callback=self.play(track, **kwargs))

    def _insert_cassette(self):
        if not self.has_recorded:
            data = self._cass_file().read_text("utf8")
            self.cassette = json.loads(data)

    def record(self):
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
                    "body": body,
                }
                self.cassette.append(track)
                self.has_recorded = True
                return (track["response"]["status_code"],
                        _adjust_headers_for_responses(track["response"])["headers"],
                        bodys)
        return _callback

    @property
    def requested_urls(self):
        return [track['request']['url'] for track in self.cassette]


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
    return replica
