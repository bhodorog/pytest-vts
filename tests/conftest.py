import json
import multiprocessing
import os
import shlex
import subprocess
import socket
import sys
import time

import cherrypy
import gevent
import gevent.monkey
import pytest
import requests

import tests.server_fixtures.base_http as base_http


class Root(object):
    @cherrypy.expose
    def index(self):
        return b"pong"

    @cherrypy.expose
    def text(self):
        return b"Hello world"

    @cherrypy.expose
    def no_content(self):
        cherrypy.response.status = 204
        return b""

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def json(self):
        return {"message": "Hello world"}

    @cherrypy.expose
    def chunked(self):
        cherrypy.response.headers["Content-Type"] = "application/json"

        def content():
            yield b'{"message": '
            yield b'"Hello'
            yield b' '
            yield b'world"'
            yield b'}'

        return content()
    chunked._cp_config = {"response.stream": True}

    @cherrypy.expose
    def set_cookie_date(self):
        cherrypy.response.headers["Set-Cookie"] = "Path=/; Expires=Fri, 24 Feb 2017 00:58:28 GMT; HttpOnly"
        return b"date based set-cookie header"

    @cherrypy.expose
    def set_cookie_no_date(self):
        cherrypy.response.headers["Set-Cookie"] = "Path=/"
        return b"dateless set-cookie header"


def run_cherrypy(port, root_kls=Root):
    import logging
    logging.getLogger("cherrypy").setLevel(logging.DEBUG)
    cherrypy.config.update({
        "server.socket_port": port,
        "engine.autoreload.on": False,
        # "engine.timeout_monitor.on": False,  # removed by cherrypy > 12.0.0
        # "log.screen": False
    })
    cherrypy.quickstart(root_kls(), "/")


def run_custom_chpy(port, request, response):
    class CustomRoot(object):
        @cherrypy.expose(request.url)
        @cherrypy.tools.allow(methods=[request.method])
        def index():
            return response

    run_cherrypy(port, root=CustomRoot)


def _yield_to_others(sleep):
    if False and any(
        [gevent.monkey.is_module_patched(mod)
         for mod in ["socket", "subprocess"]]):
        gevent.wait(timeout=sleep)
    else:
        time.sleep(sleep)


def _wait_for_server(host, port, max_retries=4):
    retries = max_retries
    sleep = 0.5
    _yield_to_others(sleep)
    while retries:
        retries -= 1
        try:
            sock = socket.create_connection((host, port))
            to_send = "GET / HTTP/1.1\r\nHost: {}:{}\r\n\r\n".format(host, port)
            sock.sendall(to_send.encode("utf-8"))
            data = sock.recv(1024)
        except Exception as exc:
            print(exc)
            _yield_to_others(sleep)
        else:
            if b"200 OK" in data:
                return True
    raise RuntimeError(
        "The background server on {}:{} hasn't started!\n"
        "Retried {} times for a total of {} seconds".format(
            host, port, max_retries, (max_retries-retries)*sleep))


@pytest.yield_fixture
def chpy_http_server():
    """Background server simulating different transfer-encoded http
    responses

    I ended up using cherrypy since I struggle a bit to implement a simple TCP
    server for chunked-encoded responses and decided to use a library which
    might be more reliable in the future for cases which it supports."""
    port = base_http.pick_a_port()
    server = multiprocessing.Process(
        target=run_cherrypy,
        args=(port,),
    )
    server.start()
    try:
        _wait_for_server("127.0.0.1", port)
    except Exception:
        server.terminate()
        raise
    url = "http://127.0.0.1:{}".format(port)
    yield url
    server.terminate()


@pytest.yield_fixture
def chpy_custom_server(root_chpy):
    port = base_http.pick_a_port()
    server = multiprocessing.Process(
        target=run_cherrypy,
        args=(port, root_chpy)
    )
    server.start()
    try:
        _wait_for_server("127.0.0.1", port)
    except Exception:
        server.terminate()
        raise
    url = "http://127.0.0.1:{}".format(port)
    yield url
    server.terminate()


@pytest.yield_fixture
def chpy_custom_server2():
    port = base_http.pick_a_port()
    cmd = "python -m tests.server_fixtures.cherry"
    os.environ.setdefault("X-PORT", str(port))
    server = subprocess.Popen(
        shlex.split(cmd),
        env=os.environ,
        stdout=open("/tmp/cherry.out", "w+"),
        stderr=open("/tmp/cherry.err", "w+"))
    try:
        _wait_for_server("127.0.0.1", port)
    except Exception:
        server.terminate()
        raise
    url = "http://127.0.0.1:{}".format(port)
    yield url
    server.terminate()


@pytest.fixture
def http_custom_server(handler):
    port = base_http.pick_a_port()
    url = "http://127.0.0.1:{}".format(port)
    server = multiprocessing.Process(
        target=handler,
        args=(port,)
    )
    server.start()
    try:
        _wait_for_server("127.0.0.1", port)
    except Exception:
        server.terminate()
        raise
    yield url
    server.terminate()


@pytest.fixture
def http_get():
    def __inner__(url):
        resp = requests.get(
            url, headers={"Accept": "application/json"})
        return resp
    return __inner__


@pytest.fixture
def vts_rec_on(vts_machine, tmpdir, vts_request_wrapper):
    vts_machine.setup(basedir=tmpdir, request_wrapper=vts_request_wrapper)
    yield vts_machine
    vts_machine.teardown()


@pytest.fixture
def http_request(movie_server):
    return requests.Request(method="GET", url=movie_server.url)


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
def vts_recording(vts_rec_on, chpy_custom_server, http_request):
    sep = "" if http_request.url.startswith("/") else "/"
    url = "{}{}{}".format(chpy_custom_server, sep, http_request.url)
    http_request.url = url
    sess = requests.Session()
    prep = sess.prepare_request(http_request)
    sess.send(prep)
    return vts_rec_on


# @pytest.fixture
# def vts_play_on(vts_recording):
#     vts_recording.setup_playback()
#     return vts_rec_on
