import functools
import json
import random
import logging
import six.moves.urllib as urllib
import zlib

import cherrypy
import mock
import pytest
import requests
import six

import pytest_vts
import pytest_vts.logic._compat.cookie_parsing_library_errors as cookie_parsing_compat

from tests.server_fixtures.multiple_set_cookie import multiple_set_cookie_headers

def make_req(request):
    sess = requests.Session()
    prep = sess.prepare_request(request)
    return sess.send(prep)


def unparse_qsl(qs_parts):
    return "&".join("=".join(urllib.quote(field), urllib.quote(value))
                    for field, value in qs_parts)


def sorted_qs(qs):
    # we use parse_qsl to avoid getting multiple values as list and to preserve
    # the order of the qs_params
    qs_parts = urllib.parse.parse_qsl(qs)
    qs_parts_sorted = sorted(qs_parts)
    return urllib.urlencode(qs_parts_sorted)


def shuffle_qs(qs):
    qs_parts = urllib.parse.parse_qsl(qs)
    random.shuffle(qs_parts)
    return urllib.urlencode(qs_parts)


class QueryStrings(object):
    @cherrypy.expose
    def index(self):
        return "pong"

    @cherrypy.expose
    def unsorted_qs(self, **qs_params):
        return "ok"


@pytest.mark.parametrize("http_request", [
    requests.Request(method="GET",
                     url="/unsorted-qs?ddd=3&bbb=1&aaa=0&ccc=2")])
@pytest.mark.parametrize("root_chpy", [QueryStrings])
def test_playback_orders_qs(vts_recording, chpy_custom_server, http_request):
    assert vts_recording.tracks(http_request.url, ignore_qs=True)
    track = vts_recording.tracks(http_request.url)[0]
    _, url_qs = http_request.url.split("?")
    _, track_qs = track["request"]["url"].split("?")
    assert url_qs == track_qs
    vts_recording.setup_playback()
    vts_playing = vts_recording
    # make the request against vts in playback mode
    # assert the request is matched considering the qs
    resp = make_req(http_request)
    assert resp


@pytest.fixture
def record_cassette(vts_rec_on, movie_server, http_get):
    http_get(movie_server.url)
    return vts_rec_on


def test_vts_recording(vts_rec_on, movie_server, sample_output, http_get):
    resp = http_get(movie_server.url)
    assert resp.status_code == 200
    assert vts_rec_on.responses
    assert vts_rec_on.responses.calls
    assert vts_rec_on.responses.calls[0]
    assert vts_rec_on.responses.calls[0].request.url == movie_server.url + "/"
    assert vts_rec_on.responses.calls[0].response
    assert vts_rec_on.cassette
    assert len(vts_rec_on.cassette) == 1
    track = vts_rec_on.cassette[0]
    assert track["request"]
    assert track["request"]["method"] == "GET"
    assert track["request"]["url"] == movie_server.url + "/"
    assert "Accept" in track["request"]["headers"]
    assert track["request"]["body"] is None
    assert track["response"]
    assert track["response"]["status_code"] == 200
    assert track["response"]["headers"]
    assert track["response"]["headers"]["X-VTS-Testing"] == "Reporting"
    assert track["response"]["body"] == sample_output


def test_unrecorded_http_call(record_cassette):
    record_cassette.setup_playback()
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get("https://circleci.com")


@pytest.mark.parametrize("url", [
    "illegal_url",
    "http://illegal.host.name/admin/",
])
def test_vts_illegal_urls(vts, url):
    with pytest.raises(Exception):
        requests.get(url)


@pytest.mark.parametrize("poison_test_name", ["/some/path/like/name"])
def test_cassette_is_always_file(record_cassette, poison_test_name):
    cassette_dirname = record_cassette._cass_file().dirname
    assert record_cassette._cass_dir == cassette_dirname


def test_recording_gzipped_responses_as_text(vts_rec_on, httpserver):
    data = "Hello!"
    # http://stackoverflow.com/a/22310760
    gzip_compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
    gzipped = gzip_compressor.compress(data.encode()) + gzip_compressor.flush()
    httpserver.serve_content(
        gzipped, 200,
        headers={"Content-Encoding": "gzip"})
    url = "{}/".format(httpserver.url)
    resp = requests.get(url)
    assert resp.status_code == 200
    assert resp.text == data
    assert len(vts_rec_on.cassette) == 1
    track = vts_rec_on.cassette[0]
    assert track['request']['url'] == url
    assert "Content-Encoding" in track['response']['headers']
    assert track['response']['body'] == data


# enable pytester fixture which allows running pytests within tests
pytest_plugins = "pytester"


def test_not_saving_cassette_when_it_fails(testdir):
    testdir.makepyfile("""
        import requests

        def test_always_failing(vts):
            requests.get("https://api.github.com/search/repositories?q=user:bhodorog")
            assert False
    """)
    testdir.plugins.append("pytest-vts")
    testdir.runpytest()
    cassettes_dir = testdir.tmpdir.join("cassettes")
    assert not cassettes_dir.check()


def test_saving_cassette_when_it_passes(testdir):
    testdir.makepyfile("""
        import requests

        def test_always_passes(vts):
            requests.get("https://api.github.com/search/repositories?q=user:bhodorog")
            assert True
    """)
    testdir.plugins.append("pytest-vts")
    testdir.runpytest()
    cassettes_dir = testdir.tmpdir.join("cassettes")
    assert cassettes_dir.check()
    assert list(cassettes_dir.visit("*.json"))


def test_match_strict_body_against_recorded_requests(vts_machine,
                                                     movie_server,
                                                     monkeypatch,
                                                     tmpdir):
    # use vts_machine to manually control .teardown()
    vts_machine.setup(basedir=tmpdir)
    assert vts_machine.cassette == []
    resp = requests.post(movie_server.url,
                         headers={"Accept": "application/json", "Content-Type": "application/json"},
                         data=json.dumps({"msg": "Hello"}))
    assert vts_machine.cassette
    # hack to coerce the fixture to properly teardown
    vts_machine._pytst_req.node.rep_call = mock.Mock(passed=True)
    vts_machine.teardown()
    vts_play_on = pytest_vts.Recorder.clone(vts_machine)
    vts_play_on.setup()
    recorded_body = vts_play_on.cassette[0]["request"]["body"]
    assert recorded_body
    vts_play_on.strict_body = True
    with pytest.raises(AssertionError):
        requests.post(movie_server.url,
                      headers={"Accept": "application/json"},
                      json={"msg": "not the recorded body"})


def test_recording_chunked_response(chpy_http_server, vts_rec_on):
    url = "{}/chunked".format(chpy_http_server)
    print("requesting data")
    resp = requests.get(url)
    assert resp.status_code == 200
    expected_data = {"message": "Hello world"}
    assert resp.text == json.dumps(expected_data)
    assert len(vts_rec_on.cassette) == 1
    track = vts_rec_on.cassette[0]
    assert track["request"]["url"] == url
    lower_headers = {
        hh.lower(): vv for hh, vv
        in six.iteritems(track["response"]["headers"])}
    assert "transfer-encoding" in lower_headers
    assert track["response"]["body"] == expected_data


def old_test_recording_chunked_response(httpserver, vts_rec_on):
    data = {"message": "content is chunked"}
    bodys = json.dumps(data)
    httpserver.serve_content(
        bodys, 200,
        headers={"Transfer-Encoding": "chunked",
                 "Content-Type": "application/json"})
    url = "{}/".format(httpserver.url)
    resp = requests.get(url)
    assert resp.status_code == 200
    assert resp.text == bodys
    assert resp.json() == data
    assert len(vts_rec_on.cassette) == 1
    track = vts_rec_on.cassette[0]
    assert track['request']['url'] == url
    assert "Transfer-Encoding" in track['response']['headers']
    assert track['response']['body'] == data


def test_recording_set_cookie_with_date_not_recorded(
        chpy_http_server, vts_rec_on):
    url = "{}/set-cookie-date".format(chpy_http_server)
    resp = requests.get(url)
    assert resp.status_code == 200
    if cookie_parsing_compat.COOKIE_PARSING_LIBRARY_LOADED == 'cookies':
        assert "set-cookie" not in resp.headers
    else:
        assert "set-cookie" in resp.headers


def test_recording_set_cookie_no_date_recorded(
        chpy_http_server, vts_rec_on):
    url = "{}/set-cookie-no-date".format(chpy_http_server)
    resp = requests.get(url)
    assert resp.status_code == 200
    assert "set-cookie" in resp.headers


def test_recording_ignore_qs(chpy_http_server, vts_rec_on):
    pass


def test_requests_post_using_json(chpy_http_server, vts_rec_on):
    url = "{}/json".format(chpy_http_server)
    payload = {'query': 'what do you say'}
    resp = requests.post(url, json=payload)
    assert resp.status_code == 200
    assert len(vts_rec_on.cassette) == 1
    track = vts_rec_on.cassette[0]
    body_0 = track['request']['body']
    resp = requests.post(url, data=json.dumps(payload))
    assert resp.status_code == 200
    assert len(vts_rec_on.cassette) == 2
    track = vts_rec_on.cassette[1]
    body_1 = track['request']['body']
    # both should have the same type on python3 (preferable string, not binary
    # - the encoding to binary will be handled by json.dumps)
    assert body_0 == body_1
    # ultimatelly save the cassette file to rule out any other issue
    vts_rec_on._save_cassette()


@pytest.mark.parametrize("handler", [multiple_set_cookie_headers])
def test_multiple_set_cookie(http_custom_server, vts_rec_on):
    """Enable detailed logging using pytest's cli options:
           tox -- --log-cli-level DEBUG
    """
    url = "{}/multiple-set-cookie".format(http_custom_server)
    resp = requests.get(url)
    assert resp
    assert resp.headers
    assert resp.cookies
    assert len(resp.cookies) == 2
