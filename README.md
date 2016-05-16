# pytest-vts
Automatic recorder for http stubbed [pytest][](s) using [responses][]
library. VTS stands for Video Tests System and has been inspired from
[VHS][Videotape format war wiki].

# How to use it

  1. Add as dependency/Install via pip:
  - from PyPI (**recommended**): `pytest-vts`
  - from github: `git+https://github.com/bhodorog/pytest-vts.git`

  *Note: During installation [pytest][] is automatically installed as
   well if missing.*

  2. Once installed the package provides a [pytest fixture][] named `vts`which
  you can use for your tests.

## Simple example, showing available assertions

### Source Code

```python
# content of github_client.py
import requests

def list_repositories(user="bhodorog"):
    url = "https://api.github.com/search/repositories?q=user:{}".format(user)
    headers = {"Accept": "application/vnd.github.v3+json"}
    resp = requests.get(url, headers)
    return resp


# content of test_github_client.py

def test_list_repositories(vts):
    github_client.list_repositories()
    assert vts.responses  # exposes underlying responses requests mock

    # asserts vs any information normally exposed by responses
    assert vts.responses.calls
    assert vts.responses.calls[0].request
    assert vts.responses.calls[0].request.url
    assert vts.responses.calls[0].response
    assert vts.responses.calls[0].response.headers
    # look at responses' documentation/code for more available info to assert against

    # you can asserts vs vts' recorded cassete as well
    # since it's just json based duplicated information, using exposed
    # responses instead might be better code style
    assert vts.cassette[0]["request"]
    assert vts.cassette[0]["request"]["url"]
    assert vts.cassette[0]["response"]
    assert vts.cassette[0]["response"]["headers"]

```

### Command line usage

```bash
$ ls ./cassettes
ls: ./cassettes: No such file or directory
$ ls ./
github_client.py test_github_client.py 
# recording
$ py.test test_github_client.py::test_func
# vts will use requests library to forward the request to
# api.github.com and save the request-response pair into a cassette
$ ls ./cassettes
test_list_repositories.json

# playback-ing
$ py.test test_github_client.py::test_func
# all http requests are handled by responses based on the existing
# cassette
```

## Customize vts fixture (injection mode)
When using the *injection mode* of the vts fixture (declaring it as a
test function argument), if the automatically determined location and
the name for a cassette are not convenable you can customize these as
well.

  - using keyword arguments:
```python
import pytest

@pytest.mark.parametrize("vts", [{"basedir": "", "cassette_name": ""}], indirect=["vts"])
def test_list_repositories(vts):
    github_client.list_repositories()
    assert vts.calls
```

  - using arguments lists (parametrize a collection):
```python
import pytest

@pytest.mark.parametrize("vts", [("/store/cassette/here", "cassette_name")], indirect=["vts"])
def test_list_repositories(vts):
    github_client.list_repositories()
    assert vts.calls
```

  - customize just the basedir (just a value is automatically assigned to basedir):
```python
import pytest

@pytest.mark.parametrize("vts", ["/store/cassette/here"], indirect=["vts"])
def test_list_repositories(vts):
    github_client.list_repositories()
    assert vts.calls
```

## Customize vts fixture (non-injection mode)
If vts fixture handle is not needed inside the test there is no need
to declare it as an argument to a test function. Use
`pytest.mark.usefixtures` instead. As a bonus, this allows to turn on
the vts fixture only once for a collection of test methods, grouped inside
a class.

```python
import pytest

@pytest.mark.usefixtures("vts")
@pytest.mark.parametrize("vts", ["/store/cassette/here"], indirect=["vts"])
class TestMoreTests(object):
    def test_list_repositories_once(self):
        github_client.list_repositories()

    def test_list_repositories_twice(self):
        github_client.list_repositories()
```



# How does it actually work?
The vts fixture exposes an instance of a `vts.Recorder` class which
initialize it's own copy of `responses.RequestsMock` object. This is
to allow `vts` to manage its own `responses.start|stop|reset()` cycles
without interfering with the default `responses.RequestsMock` object
exposed by default by [responses][] through `response.*`
interface. This way you can continue using `import response;
response.start|add|add_callback|reset|stop` in parallel with `vts`.

Beside its own copy of `response.RequestsMock` vts is responsible of:

  - building an internal copy of most information exposed by
    `responses` as a json copy. As well as other recording libraries
    **vts** refers to this as a *cassette*.
  - based on the test module's location and the current test
    function/method name decides the location of the cassette.
  - if the cassette does not already exist, it will *record* one,
    otherwise it will *playback* the existing one.


# Why this and not other http mocking and recording library?
Because the current available options have some shortcommings which
**vts** tries to address, probably not without introducing some of
its own :) :

  - [betamax][], [vcr.py][], [httpretty][]: are all saving the
    gzipped/deflated responses verbatim which is
    [considerate](https://betamax.readthedocs.io/en/latest/implementation_details.html#gzip-content-encoding)
    but not very useful when visually inspecting the cassettes.
  - [httpretty][]: recording/playback-ing feature is not mentioned in the
    docs which suggests an experimental status.
  - [betamax][]: while mocking only requests is not an issue, providing a
    handle to the session object might be inconvenient in
    some use cases

# Why a pytest plugin and not standalone?
Because, among a lot of features, [pytest][] offers fixtures and tests
introspections out of the box, complemented by an awesome development
support (to name just a few: pytester builtin fixture,
pytest-localserver).

Test introspections have been very useful implementing convenience
features such as:

  - automatic naming of the cassette files based on the test name
  - automatic deciding the location of the cassettes based on the
    tests modules
  - saving the cassette only if the test has passed

The above examples of how to customize the vts fixture are in fact
pytest's fixtures features.

# Why supporting [responses][] and not others?
Because I think its API is familiar and proved itself as a very
reliable option.

# Future features?
  1. implement various strategies of handling new/missing requests from
  cassette-recorded. Currently when a new request not recorded for a
  test happens the behaviour defined by the mocking library happens.
  (e.g. [responses][] will raise a `requests.exceptions.ConnectionError`)
  2. serialize requests' `response.history` to cassette json.
  3. support other http-mocking libraries (probably those with
     callbacks as mock responses? - most of them have that).
  4. add suppport for filtering sensitive information (e.g. passwords,
     auth headers) from cassettes in case they're publicly available
     (e.g. vcs stored on a public vcs service).
  5. add an information text about test being recorded/playbacked in
     the -vv output of pytest.
  6. consider having tracks saved in their own files to avoid having
     cassettes to big
  7. consider not saving duplicated tracks
  8. handle `tracks` with duplicated `['request']` but different
     `['response']`. Keep the first one? The last one? Raise? Keep?
    - make use of [responses][]' `assert_all_requests_are_fired`? Keep
      all duplicates and support responses' functionality.
  9. have separate objects (sides?) for tracks recorded during tests
     vs recorded during fixture setup/teardown?


[betamax]: https://betamax.readthedocs.org/
[vcr.py]: https://vcrpy.readthedocs.org/
[httpretty]: https://github.com/gabrielfalcao/HTTPretty
[responses]: https://github.com/getsentry/responses
[pytest]: http://pytest.org/latest/
[pip]: https://pip.pypa.io/en/stable/
[pytest fixture]: http://pytest.org/latest/fixture.html#fixture
[Videotape format war wiki]: https://en.wikipedia.org/wiki/Videotape_format_war
