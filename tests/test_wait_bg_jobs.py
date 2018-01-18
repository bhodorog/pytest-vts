import time
import threading

import requests
import pytest

import tests.fixtures as fxt
import tests.server_fixtures.routes as routes


class BgTask(object):
    def __init__(self, url, delayed=True):
        self.url = url
        self.bg = threading.Thread(target=self.target)
        self.delayed = delayed

    def target(self):
        while self.delayed:
            time.sleep(0.2)
        try:
            self._rv = fxt.make_req(requests.Request(
                method="GET", url=self.url))
        except Exception as exc:
            self._exc = exc
            raise

    def join(self, delayed=False, *args, **kwargs):
        self.delayed = delayed
        self.bg.join(*args, **kwargs)

    @property
    def rv(self):
        if hasattr(self, "_exc"):
            raise self._exc
        return self._rv


@pytest.mark.parametrize("root_chpy", [routes.Root])
@pytest.mark.xfail(reason="The rougue background jobs which attempts an http request after teardown happened are not going through responses")
def test_threading(vts_machine, tmpdir, chpy_custom_server):
    """using rawer fixture vts_machine to allow to control when teardown is
    called"""
    # recording mode
    vts_machine.setup(basedir=tmpdir)
    assert vts_machine.is_recording
    # client function
    active = BgTask(
        "{}{}".format(chpy_custom_server, "/background"), delayed=False)
    fxt.make_req(requests.Request(method="GET",
                              url="{}/foreground".format(chpy_custom_server)))
    active.bg.start()
    active.join()
    assert active.rv
    # now switch to playback mode
    vts_machine.setup_playback()
    assert vts_machine.is_playing
    assert vts_machine.cassette
    # request should be served by vts from cassette
    fxt.make_req(requests.Request(method="GET",
                              url="{}/foreground".format(chpy_custom_server)))
    dormant = BgTask(
        "{}{}".format(chpy_custom_server, "/not-recorded"), delayed=True)
    dormant.bg.start()  # but is actually slower than this main thread
    # client function ends => test ends => teardown is called
    vts_machine.teardown()
    # dormant bg task gets a chance to execute
    dormant.join()
    # since the cassette doesn't have a track for /not-recorded a
    # ConnectionRefused should be raised
    with pytest.raises(Exception):
        dormant.rv
