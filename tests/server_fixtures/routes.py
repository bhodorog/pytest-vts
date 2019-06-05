import cherrypy


class Root(object):
    @cherrypy.expose
    def index(self):
        return b"pong"

    @cherrypy.expose
    def ping(self):
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
        cherrypy.response.cookie["test"] = "withdate"
        cherrypy.response.cookie["test"]["path"] = "/"
        cherrypy.response.cookie["test"]["expires"] = "Fri, 24 Feb 2017 00:58:28 GMT"
        cherrypy.response.cookie["test"]["httponly"] = True
        return b"date based set-cookie header"

    @cherrypy.expose
    def set_cookie_no_date(self):
        cherrypy.response.cookie["test"] = "dateless"
        cherrypy.response.cookie["test"]["path"] = "/"
        cherrypy.response.cookie["test"]["httponly"] = True
        return b"dateless set-cookie header"

    # @cherrypy.expose
    # def multiple_set_cookie(self):
    #     cherrypy.response.headers["Set-Cookie"] = ",".join(["one=1; path=/one; HttpOnly; secure", "two=2; path=/two; HttpOnly; secure"])
    #     print(cherrypy.response.headers)
    #     return b"multiple set-cookie headers"

    @cherrypy.expose
    def foreground(self):
        return "foreground"

    @cherrypy.expose
    def background(self):
        return "background"

    @cherrypy.expose
    def not_recorded(self):
        return "not-recorded"

    @cherrypy.expose
    def kings_landing(self):
        return "redirects (and kings) apparently land here"

    @cherrypy.expose
    def set_cookie_redirect(self):
        cherrypy.response.cookie["one"] = "1"
        cherrypy.response.cookie["one"]["path"] = "/one"
        cherrypy.response.cookie["one"]["version"] = "1"
        cherrypy.response.cookie["two"] = "2"
        cherrypy.response.cookie["two"]["path"] = "/two"
        cherrypy.response.cookie["two"]["version"] = "2"
        cherrypy.response.cookie["two"]["httponly"] = True
        raise cherrypy.HTTPRedirect("/kings-landing")

    @cherrypy.expose
    def logging_tree(self):
        try:
            import logging_tree.format
        except ImportError:
            msg = ('It seems logging_tree library is not available. '
                   'Maybe `pip install logging_tree`?')
            raise cherrypy.HTTPError(status=500, message=msg)
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        return logging_tree.format.build_description(),
