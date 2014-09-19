import socket
import json
import hashlib
import logging
import sys
import time

import zmq


class Client:
    def __init__(self, port_number, recv_timeout):
        self.port_number = port_number
        self.recv_timeout = recv_timeout

        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        context = zmq.Context()
        self._zmq_socket = context.socket(zmq.PAIR)
        self._zmq_socket.bind("tcp://*:%s" % port_number)
        logging.info("Waiting for connection on port %s" % port_number)

        self._poller = zmq.Poller()
        self._poller.register(self._zmq_socket, zmq.POLLIN)

    def _send_udp_ping(self):
        self._udp_socket.sendto(b"rc client", 0, ("255.255.255.255", self.port_number))

    def _send_reply(self, json_msg):
        self._zmq_socket.send_json(json.dumps(json_msg), zmq.NOBLOCK)

    def _receive_request(self):
        events = dict(self._poller.poll(self.recv_timeout))
        if self._zmq_socket in events and events[self._zmq_socket] == zmq.POLLIN:
            msg = self._zmq_socket.recv_json()
            return json.loads(msg)
        else:
            raise TimeoutError

    def _exchange_data(self):
        i = 0
        while True:
            if i == 10:
                return False
            self._send_reply({"type": "message%d" % i})

            try:
                json_msg = self._receive_request()
                print(json_msg)
            except TimeoutError:
                logging.error("Server not responding!")
                return False

            i += 1

    def _handle_authentication(self, json_msg):
        if json_msg["type"] == "auth_request":
            logging.info("Token required. Sending it")
            self._send_reply({"type": "auth_reply",
                              "token": hashlib.md5(("rclogin"+"salt"+"rcpasswd").encode()).hexdigest()})
            return True

        if json_msg["type"] == "invalid_token":
            logging.error("Wrong login or password!")
            return False

        if json_msg["type"] == "auth_complete":
            logging.info("Authentication complete")
            return self._exchange_data()

        if json_msg["type"] == "invalid_request":
            logging.error("Invalid response!")
            return False
        else:
            logging.error("Invalid request from server!")
            return False

    def run(self):
        connected = False
        while True:
            if not connected:
                self._send_udp_ping()

            try:
                json_msg = self._receive_request()
            except TimeoutError:
                if connected:
                    connected = False
                    logging.error("Server not responding! Restarting broadcast")
                continue

            try:
                connected = True
                if not self._handle_authentication(json_msg):
                    connected = False
                    logging.info("Restarting broadcast")
                    continue
            except zmq.error.Again:
                connected = False
                logging.error("Server not responding! Restarting broadcast")


def main():
    logging.basicConfig(filename='client.log',
                        level=logging.DEBUG,
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
    c = Client(50000, 3000)
    c.run()

if __name__ == '__main__':
    main()