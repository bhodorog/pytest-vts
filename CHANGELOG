# v0.2.0

  - add support for python3

  - *playback* mode: improved comparison of HTTP requests agains the
    recorded ones. By default a warning is being [logged][logging] or
    if "strict_body" is enabled the body is being
    [asserted][pytest assert]

  - *recording* mode: beside switching to this mode when a cassette
    file is missing, now it's possile to force this mode by using
    `PYTEST_VTS_FORCE_RECORDING` environment variable

  - remove almost all usages of external sites for unittests

# v0.1.5

  - disable the matching of requests' bodies to the recorded requests
    bodies.

# v0.1.1 - v.0.1.3 #

  - minor changes to description page on PyPI

# v0.1.0 #

  - *recording* mode: when a cassette file is missing all http calls are
    requested using [requests][] library and the HTTP request-response
    pair is saved to the cassette file
  - *playback* mode: when a cassette file is present, its information
    is being rewind-ed into [responses][] callback mocks.
  - an unrecognized HTTP request during *playback* will obey the
    default behaviour of [responses][]
  - cassettes names and locations are determined by default using test
    module location and name.
  - `vts` pytest fixture is now parametrizable, using `indirect=[]`

[requests]: http://docs.python-requests.org/en/lastest/
[responses]: https://github.com/getsentry/responses
[logging]: https://docs.python.org/3/library/logging.html?highlight=logging#module-logging
[pytest assert]: http://pytest.org/latest/assert.html#assert-with-the-assert-statement
