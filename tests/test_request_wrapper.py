import functools
import json

import pytest


def test_no_request_wrapper(vts_rec_on, movie_server, http_get):
    resp = http_get(movie_server.url)
    assert resp


def change_request_wrapper(func):
    @functools.wraps(func)
    def _inner(prep_req, *args, **kwargs):
        prep_req.url = prep_req.url + "?some=stuff"
        return func(prep_req, *args, **kwargs)
    return _inner


@pytest.mark.parametrize("vts_request_wrapper", [change_request_wrapper])
def test_request_wrapper(vts_rec_on, movie_server, http_get,
                         vts_request_wrapper):
    resp = http_get(movie_server.url)
    assert resp
    tracks = vts_rec_on.cassette
    assert tracks
    assert tracks[0]['request']['url'].endswith("?some=stuff")


def change_response_wrapper(func):
    @functools.wraps(func)
    def _inner(prep_req, *args, **kwargs):
        status, r_headers, body = func(prep_req, *args, **kwargs)
        r_headers['X-Added-By'] = 'vts-response-wrapper'
        try:
            loaded_body = json.loads(body)
            loaded_body['added_by'] = 'vts-response-wrapper'
        except Exception as exc:
            print(exc)
            return status, r_headers, body
        return status, r_headers, json.dumps(loaded_body)
    return _inner


def mock_response_wrapper(func):
    @functools.wraps(func)
    def _inner(prep_req, *args, **kwargs):
        return (
            200,
            {'X-Added-By': 'vts-response-wrapper'},
            json.dumps({'added_by': 'vts-response-wrapper'}))
    return _inner


@pytest.mark.parametrize("vts_request_wrapper", [
    change_response_wrapper,
    mock_response_wrapper])
def test_response_wrapper(vts_rec_on, movie_server, http_get,
                          vts_request_wrapper):
    def _test_func(vts_):
        resp = http_get(movie_server.url)
        assert resp
        assert 'X-Added-By' in resp.headers
        assert 'added_by' in resp.json()
        tracks = vts_.cassette
        assert tracks
        assert 'X-Added-By' in tracks[0]['response']['headers']
        assert 'added_by' in tracks[0]['response']['body']

    _test_recording_mode = _test_func
    _test_recording_mode(vts_rec_on)
    vts_rec_on.setup_playback(vts_request_wrapper)
    vts_play_on = vts_rec_on
    _test_playback_mode = _test_func
    _test_playback_mode(vts_play_on)
