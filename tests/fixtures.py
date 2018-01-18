import requests


def make_req(request):
    sess = requests.Session()
    prep = sess.prepare_request(request)
    return sess.send(prep)
