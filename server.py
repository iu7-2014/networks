import socket
import logging
import json
import sys

import zmq
from pymouse import PyMouse

class Configuration:
    udp_broadcast_ip = "255.255.255.255"
    udp_presence_message = b"rc client"
    udp_respond_message = b"rc server"
    password_hash = "00f25bbfdc3c8356a57603990037a979"

class Authenticator:
    def __init__(self, hash):
        self.hash = hash

    def authenticate(self, hash):
        return self.hash == hash

class UserInputControl:
    def __init__(self):
        self.__mouse = PyMouse()

    def click(self, x, y):
        self.__mouse.click(x, y)

class Server:
    def __setup_udp(self):
        self.__udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.__udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.__udp_socket.bind(("", self.port_number))

        logging.info("UDP socket bound on port {0}".format(self.port_number))

    def __setup_zmq_socket(self):
        self.__context = zmq.Context()
        self.__zmq_socket = self.__context.socket(zmq.PAIR)
        self.__zmq_socket.bind("tcp://*:{0}".format(self.port_number))

    def __setup_poller(self):
        self.__poller = zmq.Poller()
        self.__poller.register(self.__zmq_socket, zmq.POLLIN)

    def __init__(self, port_number, recv_timeout):
        self.port_number = port_number
        self.recv_timeout = recv_timeout
        self.ip = socket.gethostbyname(socket.gethostname())
        self.__authenticated = False

        logging.info("My ip is {0}".format(self.ip))

        self.__authenticator = Authenticator(Configuration.password_hash)
        self.__user_input_control = UserInputControl()

        self.__setup_udp()
        self.__setup_zmq_socket()
        self.__setup_poller()

    def __get_udp_ping(self):
        udp_poller = zmq.Poller()
        udp_poller.register(self.__udp_socket, zmq.POLLIN)

        events = dict(udp_poller.poll(self.recv_timeout))

        if self.__udp_socket.fileno() in events:
            msg, address = self.__udp_socket.recvfrom(10)

            if msg == Configuration.udp_presence_message:
                logging.info("Ping from client {0}. Sending response".format(address[0]))
                self.__send_udp_ping()

    def __send_udp_ping(self):
        self.__udp_socket.sendto(Configuration.udp_respond_message,
                                0,
                                (Configuration.udp_broadcast_ip, self.port_number - 1))

    def __send_message(self, json_msg):
        try:
            self.__zmq_socket.send_json(json.dumps(json_msg), zmq.NOBLOCK)
            return True
        except zmq.error.Again:
            return False

    def __receive_message(self):
        events = dict(self.__poller.poll(self.recv_timeout))
        if self.__zmq_socket in events and events[self.__zmq_socket] == zmq.POLLIN:
            msg = self.__zmq_socket.recv_json()
            return json.loads(msg)
        else:
            raise TimeoutError

    def __abort(self):
        logging.error("Client stop responding")
        self.__authenticated = False
        return False

    def __handle_message(self, json_msg):
        if json_msg["type"] == "estimate_connection":
            logging.info("Client {0} is trying to connect".format(json_msg["ip"]))

            self.__authenticated = self.__authenticator.authenticate(json_msg["token"])
            if self.__authenticated:
                if not self.__send_message({"type": "auth_complete"}):
                    return self.__abort()
                logging.info("Authentication complete!")
                return True
            else:
                if not self.__send_message({"type": "invalid_token"}):
                    return self.__abort()
                logging.info("Invalid token")
                return False

        elif self.__authenticated:
            if json_msg["type"] == "click_mouse":
                self.__user_input_control.click(json_msg["x"], json_msg["y"])
                if not self.__send_message({"type": "done"}):
                    return self.__abort()
                return True

        logging.error("Invalid client response!")
        if not self.__send_message({"type": "invalid_response"}):
            return self.__abort()

    def run(self):
        timeout = self.recv_timeout
        while True:
            self.__get_udp_ping()

            try:
                msg = self.__receive_message()
            except TimeoutError:		
                continue

            self.__handle_message(msg)

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
    s = Server(50000, 0)
    s.run()


if __name__ == '__main__':
    main()