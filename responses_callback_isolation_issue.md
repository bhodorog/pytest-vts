## Problem:

1. responses.start()
1. rex\_a.async\_get(url\_a)
1. rex\_b.async\_get(url\_b)
1. rex\_a.result()
  2. requests.get(url\_a)
  2. responses triggers callback
  2. pytest\_vts.vts.record.\_callback()
  2. responses.stop()
  2. requests.get(url\_a)
  2. greenlet switches to gevent main loop
gevent main loop picks another greenlet to run. Let's assume resumes with 1.
1. rex\_b.result()
    3. requests.get(url\_a)
    3. because of greenlet 2. stopping responses this requests goes through
    3. greenlet switches to gevent main loop
gevent main loop picks another greenlet to run. Let's assume resumes 2.
  2. requests.get(url\_a) finishes
  2. recorded to the cassette track
  2. responses.start()
  2. greenlet ends and switches to gevent main loop
gevent main loop picks another greenlet to run. Let's assume resumes 3.
    3. requests.get(url\_b) finishes
    3. since it wasn't executed in responses callback registered by vts => no cassette
    3. greenlet ends and switches to gevent main loop


The above example uses greenlets, but the same is valid for threads,
maybe even worse since threads are scheduled by OS and can switch
anywhere not only in blocking operations.


## Solution:
Instead of using requests to make the http call which should bypass
responses, use something else (e.g. urllib3) which is not patched by
responses. That way we can avoid stop-ing() start-ing() responses.

