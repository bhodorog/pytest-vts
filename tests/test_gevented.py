import gevent
import gevent.pool
import gevent.monkey
import requests
import pytest

import tests.fixtures as fxt

gevent.monkey.patch_socket(dns=True)


def test_catch_all_gevented_requests(vts_rec_on, movie_server, http_get):
    """Keep this test at the very end to avoid messing up with the rest of the
    tests, since it's monkey patching the network related operations.

    Maybe write a custom pytest order enforcer later."""
    def _job():
        return http_get(movie_server.url)

    pool = gevent.pool.Pool()
    for x in range(10):
        pool.spawn(_job)
    pool.join()
    assert len(vts_rec_on.cassette) == 10


class BgTask(object):
    def __init__(self, url, delayed=True):
        self.url = url
        self.bg = gevent.Greenlet(self.target)
        self.delayed = delayed

    def target(self):
        while self.delayed:
            print("delayed is {}".format(self.delayed))
            gevent.sleep(0.2)
        return fxt.make_req(requests.Request(method="GET", url=self.url))

    def join(self, delayed=False, *args, **kwargs):
        self.delayed = delayed
        return self.bg.join(*args, **kwargs)

    @property
    def rv(self):
        return self.bg.get()


@pytest.mark.xfail(reason="The rougue background jobs which attempts an http request after teardown happened are not going through responses")
def test_threading(vts_machine, tmpdir, chpy_custom_server2):
    """using rawer fixture vts_machine to allow to control when teardown is
    called"""
    # recording mode
    domain = chpy_custom_server2
    vts_machine.setup(basedir=tmpdir)
    assert vts_machine.is_recording
    # client function
    active = BgTask(
        "{}{}".format(domain, "/background"), delayed=False)
    fxt.make_req(requests.Request(
        method="GET", url="{}/foreground".format(domain)))
    active.bg.start()
    active.join()
    assert active.rv
    # now switch to playback mode
    vts_machine.setup_playback()
    assert vts_machine.is_playing
    assert vts_machine.cassette
    # request should be served by vts from cassette
    fxt.make_req(requests.Request(
        method="GET", url="{}/foreground".format(domain)))
    dormant = BgTask(
        "{}{}".format(domain, "/not-recorded"), delayed=True)
    dormant.bg.start()  # but is actually slower than this main thread
    # client function ends => test ends => teardown is called
    vts_machine.teardown()
    # dormant bg task gets a chance to execute
    dormant.join()
    # since the cassette doesn't have a track for /not-recorded a
    # ConnectionRefused should be raised
    with pytest.raises(Exception):
        dormant.rv
