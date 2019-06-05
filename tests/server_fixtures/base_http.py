import socket


def pick_a_port():
    ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # reuse the socket right away, don't keep it in TIME_WAIT
    ss.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ss.bind(("", 0))
    port = ss.getsockname()[1]
    ss.close()
    return port


def create_server(port):
    ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # reuse the socket right away, don't keep it in TIME_WAIT
    ss.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ss.bind(("", port))
    ss.listen(0)
    print("Server started and listening on port {}".format(port))
    return ss
