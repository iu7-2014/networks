import socket
import json
import hashlib
import logging
import sys
import time

import zmq

class Configuration:
    udp_broadcast_ip = "255.255.255.255"
    udp_presence_message = b"rc client"
    udp_respond_message = b"rc server"
    refresh_server_list_counts = 5

class Client:
    def __setup_udp(self):
        self.__udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.__udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.__udp_socket.bind(("", self.port_number - 1))

        logging.info("UDP socket bound on port {0}".format(self.port_number - 1))

    def __setup_zmq_socket(self):
        self.__context = zmq.Context()
        self.__zmq_socket = self.__context.socket(zmq.PAIR)

    def __setup_poller(self):
        self.__poller = zmq.Poller()
        self.__poller.register(self.__zmq_socket, zmq.POLLIN)

    def __init__(self, port_number, recv_timeout):
        self.port_number = port_number
        self.recv_timeout = recv_timeout
        self.ip = socket.gethostbyname(socket.gethostname())
        self.server_list = []

        logging.info("My ip is {0}".format(self.ip))

        self.__setup_udp()
        self.__setup_zmq_socket()
        self.__setup_poller()

        logging.info("Waiting for connection on port {0}".format(port_number))

    def __send_udp_ping(self):
        self.__udp_socket.sendto(Configuration.udp_presence_message,
                                0,
                                (Configuration.udp_broadcast_ip, self.port_number))

    def __receive_upd_ping(self):
        udp_poller = zmq.Poller()
        udp_poller.register(self.__udp_socket, zmq.POLLIN)

        events = dict(udp_poller.poll(self.recv_timeout))
        if self.__udp_socket.fileno() in events:
            msg, address = self.__udp_socket.recvfrom(10)
            if msg == Configuration.udp_respond_message:
                return address

        return None

    def __add_server(self, address):
        if not address in self.server_list:
            self.server_list.append(address)

    def refresh_server_list(self):
        self.server_list = []

        for i in range(Configuration.refresh_server_list_counts):
            self.__send_udp_ping()
            time.sleep(1)
            self.__add_server(self.__receive_upd_ping())

        logging.info("New server list: {0}".format(self.server_list))

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

    def __exchange_data(self):
        i = 0
        while True:
            if i == 10:
                return False
            self.__send_message({"type": "message{0}".format(i)})

            try:
                json_msg = self.__receive_message()
                print(json_msg)
            except TimeoutError:
                logging.error("Server is not responding!")
                return False

            i += 1

    def __handle_message(self, json_msg):
        if json_msg["type"] == "invalid_token":
            logging.error("Wrong login or password!")
            return False
        elif json_msg["type"] == "auth_complete":
            logging.info("Authentication complete")
            return True
        elif json_msg["type"] == "done":
            return True
        elif json_msg["type"] == "invalid_request":
            logging.error("Invalid response!")
            return False
        else:
            logging.error("Invalid server message!")
            return False

    def __connect_to(self, address):
        self.connected_address = address
        logging.info("Connect to {0}:{1}".format(address[0], address[1]))
        self.__zmq_socket.connect("tcp://{0}:{1}".format(address[0], address[1]))

    def __disconnect(self):
        logging.info("Disconnect from {0}:{1}".format(self.connected_address[0], self.connected_address[1]))
        self.__zmq_socket.disconnect("tcp://{0}:{1}".format(self.connected_address[0], self.connected_address[1]))

    def __abort(self):
        logging.error("Server is not responding!")
        self.__disconnect()

    def connect_to_server(self, address, login, passwd):
        self.__connect_to(address)

        # Authenticate client
        logging.info("Sending token")
        if not self.__send_message({"type" : "estimate_connection",
                             "token" : hashlib.md5((login + "salt" + passwd).encode()).hexdigest(),
                             "ip" : self.ip}):
            self.__abort()

        try:
            json_msg = self.__receive_message()
        except TimeoutError:
            self.__abort()
            return False

        i = 0

        # Get authentication report
        if self.__handle_message(json_msg):
            while True:
                if i > 10:
                    break

                if not self.__send_message({"type": "click_mouse",
                                            "x":20,
                                            "y":75}):
                    self.__abort()

                # Get response
                try:
                    json_msg = self.__receive_message()
                except TimeoutError:
                    self.__abort()
                    break

                if not self.__handle_message(json_msg):
                    break

                i += 1

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
    c.refresh_server_list()
    c.connect_to_server(c.server_list[0], "rc_login", "rc_passwd")

if __name__ == '__main__':
    main()