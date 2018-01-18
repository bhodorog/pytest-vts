import cherrypy


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

    @cherrypy.expose
    def foreground(self):
        return "foreground"

    @cherrypy.expose
    def background(self):
        return "background"

    @cherrypy.expose
    def not_recorded(self):
        return "not-recorded"
