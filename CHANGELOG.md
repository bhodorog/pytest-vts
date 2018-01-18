This project uses [Semantic Versioning][] and follows [these][keepachangelog] changelog guidelines.

# Unreleased

#### Added:
  - allow more customizations for naming cassettes (based on callables)

#### Changed:
  - reseting the vts recorder now waits for any background jobs
    started by the tested code

#### Removed:

#### Fixed:
  - to be filled in


# v0.4.3 - 2017-06-05
#### Fixed:
  - proper comparison for warnings when comparing request body vs recorded tracks.

# v0.4.2 - 2017-06-05
#### Changed:
  - proper comparison for request bodies when matching against recorded tracks.
  - unittests vs python 2.7 and 3.6

# v0.4.1 - 2017-02-24

#### Changed
  - don't record set-cookie in case cookies library fails to parse
    it. This is to mitigate responses usage of cookies.

# v0.4.0 - 2017-02-13

#### Added
  - support for chunked http transactions

# v0.3.0 - 2017-02-01

#### Added
  - allow requests to be recorded in multi-(g)threaded environments.


# v0.2.1 - 2016-07-07

#### Fixed:
  - no change, expect pypi's fixed description for CHANGELOG link


# v0.2.0 - 2016-06-30

#### Added:

  - add support for python3

  - *playback* mode: improved comparison of HTTP requests agains the
    recorded ones. By default a warning is being [logged][logging] or
    if "strict_body" is enabled the body is being
    [asserted][pytest assert]

  - *recording* mode: beside switching to this mode when a cassette
    file is missing, now it's possile to force this mode by using
    `PYTEST_VTS_FORCE_RECORDING` environment variable

#### Removed:

  - remove almost all usages of external sites for unittests


# v0.1.4 - v0.1.5 - 2016-05-16

#### Removed:

  - disable the matching of requests' bodies to the recorded requests
    bodies.


# v0.1.1 - v.0.1.3 - 2016-05-16

#### Changed:

  - minor changes to description page on PyPI


# v0.1.0 - 2016-05-16

#### Added:

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
[keepachangelog]: http://keepachangelog.com/
[Semantic Versioning]: http://semver.org/
