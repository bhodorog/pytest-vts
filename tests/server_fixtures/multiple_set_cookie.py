""" Currently this is not used. Keep it around for the example sake.
"""
import datetime
import time
import socket
import logging

from . import base_http

logger = logging.getLogger(__name__)


def write_response(wfile, status_line, headers, body):
    headers += "Content-Length: {}\n\n".format(len(body.encode('utf8')))
    http_headers = headers.lstrip('\n').replace("\n", "\r\n")
    status_headers = "{}\r\n{}".format(status_line, http_headers)
    logger.debug("response:\r\n{}{}".format(status_headers.replace('\r\n', '<EOL>\n'), body.replace('\r\n', '<EOL>\n')))
    wfile.write(status_headers.encode('utf8'))
    wfile.write(body.encode('utf8'))


def read_request(rfile):
    line = ""
    request = []
    while line != "\r\n":
        line = rfile.readline().decode('utf8')
        request.append(line)
    logger.debug("request:\r\n{}\r\n\r\n".format(" ".join(request)))
    return request


def multiple_set_cookie_with_redirects_newconn(
        port, redirect_path="/kings-landing"):
    ss = base_http.create_server(port)
    while True:
        conn, addr = ss.accept()
        logger.debug('conn: {}, peer addr: {}'.format(conn._sock.getsockname(), addr))
        rfile = conn.makefile("rb", -1)  # this uses the a buffered fileobj with default_size = 8192 see: socket._fileobject
        wfile = conn.makefile("wb", 0)  # this uses an unbuffered fileobj
        request = read_request(rfile)
        method, path, http_ver = request[0].split(" ")
        if path != redirect_path:
            redirect_url = "http://127.0.0.1:{}{}".format(port, redirect_path)
            write_response(
                wfile,
                status_line="HTTP/1.1 301 OK",
                headers="""
Date: {},
Content-Type: text/plain;charset=utf-8,
Server: bhg/1.0,
Set-Cookie: one=1; path=/; HttpOnly
Set-Cookie: two=2; path=/two; HttpOnly; secure
Location: {}
""".format(
    datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
    redirect_url),
                body=""
            )
        else:
            write_response(
                wfile,
                status_line="HTTP/1.1 200 OK",
                headers="""
Date: {},
Content-Type: text/plain;charset=utf-8,
Server: bhg/1.0,
Set-Cookie: one=1; path=/; HttpOnly
Set-Cookie: two=2; path=/two; HttpOnly; secure
""".format(
    datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')),
                body="OK\r\n"
            )
        if not wfile.closed:
            try:
                wfile.flush()
            except socket.error as exc:
                # A final socket error may have occurred here such as the
                # local error ECONNABORTED
                print(exc)
        rfile.close()
        wfile.close()


def close_conn(rfile, wfile):
    if not wfile.closed:
        try:
            wfile.flush()
        except socket.error as exc:
            # A final socket error may have occurred here such as the
            # local error ECONNABORTED
            logger.exception()
    rfile.close()
    wfile.close()


def multiple_set_cookie_with_redirects(
        port, redirect_path="/kings-landing"):
    ss = base_http.create_server(port)
    while True:
        conn, addr = ss.accept()
        logger.debug('conn: {}, peer addr: {}'.format(conn.getsockname(), conn.getpeername()))
        rfile = conn.makefile("rb", -1)  # this uses the a buffered fileobj with default_size = 8192 see: socket._fileobject
        wfile = conn.makefile("wb", 0)  # this uses an unbuffered fileobj
        request = read_request(rfile)
        method, path, http_ver = request[0].split(" ")
        if path == '/ping':
            write_response(
                wfile,
                status_line="HTTP/1.1 200 OK",
                body="pong",
                headers="""
Date: {},
Content-Type: text/plain;charset=utf-8,
Server: bhg/1.0,
""".format(
    datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')),
            )
            close_conn(rfile, wfile)
        else:
            while path != redirect_path:
                """Reusing the same connection"""
                redirect_url = "http://127.0.0.1:{}{}".format(port, redirect_path)
                write_response(
                    wfile,
                    status_line="HTTP/1.1 301 OK",
                    body="",
                    headers="""
Date: {},
Content-Type: text/plain;charset=utf-8,
Server: bhg/1.0,
Set-Cookie: one=1; path=/; HttpOnly
Set-Cookie: two=2; path=/two; HttpOnly; secure
Location: {}
""".format(
    datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
    redirect_url),
                )
                request = read_request(rfile)
                method, path, http_ver = request[0].split(" ")

            write_response(
                wfile,
                status_line="HTTP/1.1 200 OK",
                body="OK\r\n",
                headers="""
Date: {},
Content-Type: text/plain;charset=utf-8,
Server: bhg/1.0,
Set-Cookie: one=1; path=/; HttpOnly
Set-Cookie: two=2; path=/two; HttpOnly; secure
""".format(
    datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')),
            )
            close_conn(rfile, wfile)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    port = base_http.pick_a_port()
    print('http://127.0.0.1:{}'.format(port))
    multiple_set_cookie_with_redirects(9999)
