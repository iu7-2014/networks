import socket
import logging
import json
import sys

import zmq


class Authenticator:
    def __init__(self, hash):
        self.hash = hash

    def authenticate(self, hash):
        return self.hash == hash


class Server:
    def __init__(self, port_number, recv_timeout):
        self.port_number = port_number
        self.recv_timeout = recv_timeout

        self._authenticator = Authenticator("67a916544385cd0f8e267695c6d1d339")

        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._udp_socket.bind(('', port_number))
        logging.info("UDP socket bound on port %d" % port_number)

        context = zmq.Context()
        self._zmq_socket = context.socket(zmq.PAIR)

        self._poller = zmq.Poller()
        self._poller.register(self._zmq_socket, zmq.POLLIN)

    def _wait_for_client(self):
        logging.info("Listening broadcast and waiting for the client")

        msg = ""
        while msg != b"rc client":
            msg, address = self._udp_socket.recvfrom(30)

        logging.info("Found client %s" % address[0])

        self.client_address = address[0]
        return self.client_address

    def _connect_to_client(self):
        logging.info("Connect to client %s:%d" % (self.client_address, self.port_number))
        self._zmq_socket.connect("tcp://%s:%d" % (self.client_address, self.port_number))

    def _disconnect_from_client(self):
        logging.info("Disconnect from client %s:%d" % (self.client_address, self.port_number))
        self._zmq_socket.disconnect("tcp://%s:%d" % (self.client_address, self.port_number))

    def send_request(self, json_msg):
        self._zmq_socket.send_json(json.dumps(json_msg), zmq.NOBLOCK)

    def receive_reply(self):
        events = dict(self._poller.poll(self.recv_timeout))
        if self._zmq_socket in events and events[self._zmq_socket] == zmq.POLLIN:
            msg = self._zmq_socket.recv_json()
            return json.loads(msg)
        else:
            raise TimeoutError

    def run(self):
        while True:
            self._wait_for_client()
            self._connect_to_client()

            #Send auth request
            logging.info("Sending authentication request")
            try:
                self.send_request({"type": "auth_request"})
            except zmq.error.Again:
                logging.error("Client stop responding!")
                self._disconnect_from_client()
                continue

            #Authentication
            try:
                msg = self.receive_reply()
            except TimeoutError:
                logging.error("Client stop responding!")
                self._disconnect_from_client()
                continue

            try:
                if msg["type"] == "auth_reply":
                    if self._authenticator.authenticate(msg["token"]):
                        logging.info("Authentication complete")
                        self.send_request({"type": "auth_complete"})

                    else:
                        logging.error("Invalid token: %s!" % msg["token"])
                        self.send_request({"type": "invalid_token"})
                        self._disconnect_from_client()
                        continue
                else:
                    logging.error("Invalid client response!")
                    self.send_request({"type": "invalid_response"})
                    self._disconnect_from_client()
                    continue
            except zmq.error.Again:
                logging.error("Client not responding!")
                continue

            # Now exchange with data
            logging.info("Start exchanging with data")
            while True:
                try:
                    msg = self.receive_reply()
                    print(msg)
                except TimeoutError:
                    logging.error("Client not responding!")
                    self._disconnect_from_client()
                    break
                try:
                    self.send_request({"type": "request from server"})
                except zmq.error.Again:
                    logging.error("Client not responding!")
                    break


def main():
    logging.basicConfig(filename='server.log', level=logging.DEBUG,
                        format='%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)

    logging.info("=========== NEW SESSION ===========")
    s = Server(50000, 3000)
    s.run()


if __name__ == '__main__':
    main()
