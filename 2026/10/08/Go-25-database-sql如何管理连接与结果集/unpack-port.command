python3 -c 'import socket; sock=socket.socket(); sock.bind(("127.0.0.1",0)); print(sock.getsockname()[1]); sock.close()'
