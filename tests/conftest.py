import multiprocessing
import socket
import time

import cherrypy
import gevent
import gevent.monkey
import pytest
import six


def pick_a_port():
    ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # reuse the socket right away, don't keep it in TIME_WAIT
    ss.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ss.bind(("", 0))
    port = ss.getsockname()[1]
    ss.close()
    return port


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


def run_cherrypy(port):
    import logging
    logging.getLogger("cherrypy").setLevel(logging.DEBUG)
    cherrypy.config.update({
        "server.socket_port": port,
        "engine.autoreload.on": False,
        "engine.timeout_monitor.on": False,
        # "log.screen": False
    })
    cherrypy.quickstart(Root(), "/")


def _yield_to_others(sleep):
    if any(
        [gevent.monkey.is_module_patched(mod)
         for mod in ["socket", "subprocess"]]):
        gevent.wait(timeout=sleep)
    else:
        time.sleep(sleep)


def _wait_for_server(host, port, max_retries=10):
    retries = max_retries
    sleep = 0.5
    _yield_to_others(sleep)
    while retries:
        retries -= 1
        print("retry #{}".format(max_retries - retries))
        try:
            sock = socket.create_connection((host, port))
            to_send = "GET / HTTP/1.1\r\nHost: {}:{}\r\n\r\n".format(host, port)
            sock.sendall(to_send.encode("utf-8"))
            data = sock.recv(1024)
        except Exception as exc:
            print(exc)
            pass
        else:
            if b"200 OK" in data:
                return True
    import ipdb; ipdb.set_trace()
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
    port = pick_a_port()
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
