import logging
import os

import cherrypy
import tests.server_fixtures.routes as routes


def main():
    port = int(os.environ.get("X-PORT", "12345"))
    logging.getLogger("cherrypy").setLevel(logging.DEBUG)
    cherrypy.config.update({
        "server.socket_port": port,
        "engine.autoreload.on": False,
        # "engine.timeout_monitor.on": False,  # removed by cherrypy > 12.0.0
        # "log.screen": False
    })
    cherrypy.quickstart(routes.Root(), "/")


if __name__ == "__main__":
    main()
