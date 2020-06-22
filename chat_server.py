import server_socket
import argparse
import concurrent.futures
import logging
import logger
import threading


class Server:
    def __init__(self, IP, PORT):
        self.current_socket = server_socket.Socket(IP, PORT)
        self.clients = {}
        self.HEADER_LENGTH = 16
        self.lock = threading.Lock()
        self.instantiated_logger = logger.Logger(__name__)
        self.logger = self.instantiated_logger.initialise_logging()

    def remove_client(self, future):
        try:
            client_socket_to_remove = future.result()
            with self.lock:
                self.logger.info(
                    'Closed connection from: {}'.format(self.clients[client_socket_to_remove]['data'].decode('utf-8'))
                )
                del self.clients[client_socket_to_remove]
        except Exception as e:
            self.logger.exception(e)

    def add_client(self, name, socket):
        with self.lock:
            self.clients[socket] = name

    def read_message(self, socket_client):
        try:
            message_header = socket_client.recv(self.HEADER_LENGTH)

            if not len(message_header):
                return False

            message_length = int(message_header.decode('utf-8').strip())

            return {'header': message_header, 'data': socket_client.recv(message_length)}

        except Exception as e:
            print(f'error is {str(e)}')
            return False

    def broadcast_messages(self, read_socket, message):
        with self.lock:
            for client in self.clients:
                if client != read_socket:
                    sender_client = self.clients[read_socket]
                    client.send(sender_client['header'] + sender_client['data']
                                + message['header'] + message['data'])

    def run_client_socket(self, socket):
        while socket:
            message = self.read_message(socket)
            if message is False:
                return socket

            self.logger.info(f'Received message from {self.clients[socket]["data"].decode("utf-8")}:'
                             f'{message["data"].decode("utf-8")}')

            self.broadcast_messages(socket, message)


parser = argparse.ArgumentParser(
    prog='chat-server',
    usage='%(prog)s [options] IP PORT',
    description='Set up the chat window'
)

parser.add_argument(
    'IP',
    nargs='?',
    default='127.0.0.1',
    metavar='IP-address',
    type=str,
    help='the IP address of client socket'
)

parser.add_argument(
    'PORT',
    nargs='?',
    default=1234,
    metavar='Port',
    type=str,
    help='the port of the client socket'
)

if __name__ == '__main__':
    args = parser.parse_args()
    server = Server(args.IP, args.PORT)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        while True:
            client_socket, client_address = server.current_socket.accept()
            client_name = server.read_message(client_socket)
            if client_name is False:
                break

            server.add_client(client_name, client_socket)

            logging.info("Accepted new connection from {}:{}, name: {}".format(
                *client_address, client_name['data'].decode('utf-8'))
            )

            executor.submit(server.run_client_socket, client_socket).add_done_callback(server.remove_client)


