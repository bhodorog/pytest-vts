# pytest-vts (WIP)
Automatic recorder for http stubbed pyt.tests

# How to use it


# Why this and not other http mocking/recording library?
Because the current available options have some shortcommings:

  - [betamax][], [vcr.py][], [httpretty][]: are all saving the
    gzipped/deflated responses verbatim which is
    [considerate](https://betamax.readthedocs.io/en/latest/implementation_details.html#gzip-content-encoding)
    but not very useful when visually inspecting the cassettes.
  - [httpretty][]: recording/playback-ing feature is not mentioned in the
    docs which suggests an experimental status.
  - [betamax][]: while mocking only requests is not an issue, providing a
    handle to the session object might be inconvenient in
    some use cases

# Why a py.test plugin and not standalone?
Beacuse [py.test][] offers tests introspections out of the box
complemented by an awesome development support (to name just a few:
pytester builtin fixture, pytest-localserver).

Test introspections have been very useful implementing convenience
features such as:

  - automatic naming of the cassette files based on the test name
  - automatic deciding the location of the cassettes based on the
    tests modules
  - saving the cassette only if the test has passed

# Why supporting [responses][] and not others?
Because I think its API is familiar and proved itself as the most
reliable option.

# Future features?
  1. implement various strategies of handling new/missing requests from
  cassette-recorded. Currently when a new request not recorded for a
  test happens the behaviour defined by the mocking library happens
  (e.g. [responses][] will raise a `requests.exceptions.ConnectionError`)
  2. serialize requests' `response.history` to cassette json
  3. support other http-mocking libraries (probably those with
     callbacks as mock responses? - which are most of them)


[betamax]: https://betamax.readthedocs.org/
[vcr.py]: https://vcrpy.readthedocs.org/
[httpretty]: https://github.com/gabrielfalcao/HTTPretty
[responses]: https://github.com/getsentry/responses
[py.test]: http://pytest.org/latest/


