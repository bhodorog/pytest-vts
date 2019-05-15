import time
import socket
import logging

from . import base_http

logger = logging.getLogger(__name__)


def multiple_set_cookie_headers(port):
    ss = base_http.create_server(port)
    while True:
        conn, addr = ss.accept()
        now = time.time()
        rfile = conn.makefile("rb", -1)  # this uses the a buffered fileobj with default_size = 8192 see: socket._fileobject
        wfile = conn.makefile("wb", 0)  # this uses an unbuffered fileobj
        line = ""
        request = []
        while line != "\r\n":
            line = rfile.readline().decode('utf8')
            request.append(line)
        logger.debug("[{}] request:\r\n{}\r\n\r\n".format(now, " ".join(request)))
        body = "OK\r\n"
        headers = "HTTP/1.1 200 OK\r\nDate: Tue, 07 Feb 2019 06:06:53 GMT\r\nContent-Type: text/plain;charset=utf-8\r\nServer: bhg/1.0\r\nSet-Cookie: one=1; path=/one; HttpOnly; secure\r\nSet-Cookie: two=2; path=/two; HttpOnly; secure\r\nContent-Length: {}\r\n\r\n".format(len(body))
        logger.debug("[{}] response:\r\n{}{}".format(now, headers, body))
        wfile.write(headers.encode('utf8'))
        wfile.write(body.encode('utf8'))
        if not wfile.closed:
            try:
                wfile.flush()
            except socket.error as exc:
                # A final socket error may have occurred here such as the
                # local error ECONNABORTED
                print(exc)
        rfile.close()
        wfile.close()
