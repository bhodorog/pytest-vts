import pytest

from .vts import Recorder


@pytest.fixture
def vtsrec(request):
    """defines a VTS recorder fixture which automatically records/playback http
    stubbed requests during a unittest"""
    rec = Recorder(request)
    rec.setup()
    request.addfinalizer(rec.teardown)
    return rec
