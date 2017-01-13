import json
import tempfile
import zlib

import mock
import pytest
import requests

import pytest_vts


@pytest.yield_fixture
def vts_rec_on(vts_recorder, tmpdir):
    vts_recorder.setup(basedir=tmpdir)
    yield vts_recorder
    vts_recorder.teardown()


def http_get(url):
    resp = requests.get(
        url, headers={"Accept": "application/json"})
    return resp


@pytest.fixture
def sample_output():
    return {
        "title": "A history of tape recorders",
    }


@pytest.yield_fixture
def movie_server(httpserver, sample_output):
    """Based on pytest_localserver.httpserver fixture.

    Server port needs to remain the same, so that responses will match the
    requests during tests against pre-recorded cassettes. Port has been choosen
    from IANA non-asigned ones:
    http://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml?search=56478"""

    from pytest_localserver import http
    server = http.ContentServer()  # port=56478)
    server.start()
    httpserver.serve_content(
        json.dumps(sample_output), 200,
        headers={"Content-Type": "application/json",
                 "X-VTS-Testing": "Reporting"})
    yield httpserver
    server.stop()


@pytest.fixture
def record_cassette(vts_rec_on, movie_server):
    http_get(movie_server.url)
    return vts_rec_on


def test_vts_recording(vts_rec_on, movie_server, sample_output):
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


@pytest.mark.parametrize(
    "vts",
    [{"basedir": tempfile.gettempdir(), "cassette_name": "expected_name"}, ],
    indirect=["vts"],
    ids=["kwargs"])
def test_vts_parametrize(vts):
    assert vts.cassette_name == "expected_name"
    assert vts._cass_dir == tempfile.gettempdir()


def test_match_strict_body_against_recorded_requests(vts_recorder,
                                                     movie_server,
                                                     monkeypatch,
                                                     tmpdir):
    # use vts_recorder to manually control .teardown()
    vts_recorder.setup(basedir=tmpdir)
    assert vts_recorder.cassette == []
    resp = requests.post(movie_server.url,
                         headers={"Accept": "application/json"},
                         json={"msg": "Hello"})
    assert vts_recorder.cassette
    # hack to coerce the fixture to properly teardown
    vts_recorder._pytst_req.node.rep_call = mock.Mock(passed=True)
    vts_recorder.teardown()
    vts_play_on = pytest_vts.Recorder.clone(vts_recorder)
    vts_play_on.setup()
    recorded_body = vts_play_on.cassette[0]["request"]["body"]
    assert recorded_body
    vts_play_on.strict_body = True
    with pytest.raises(AssertionError):
        requests.post(movie_server.url,
                      headers={"Accept": "application/json"},
                      json={"msg": "not the recorded body"})


def test_catch_all_gevented_requests(vts_rec_on, movie_server):
    def _job():
        return http_get(movie_server.url)

    from gevent.pool import Pool
    import gevent.monkey
    gevent.monkey.patch_socket(dns=True)

    pool = Pool()
    for x in range(10):
        pool.spawn(_job)
    pool.join()
    assert len(vts_rec_on.cassette) == 10
