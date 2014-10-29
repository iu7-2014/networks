import socket
import json
import hashlib
import logging
import time
import fcntl
import struct

import zmq


class Configuration:
    udp_broadcast_ip = "255.255.255.255"
    udp_presence_message = b"rc client"
    udp_respond_message = b"rc server"
    refresh_server_list_counts = 2


class Client:
    def __setup_udp(self):
        self.__udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.__udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.__udp_socket.bind(("", self.port_number - 1))

        logging.info("{0}\tПрослушивание UDP сокета. Порт:\t{1}".format(self.ip, self.port_number - 1))

    def __setup_zmq_socket(self):
        self.__context = zmq.Context()
        self.__zmq_socket = self.__context.socket(zmq.PAIR)

    def __setup_poller(self):
        self.__poller = zmq.Poller()
        self.__poller.register(self.__zmq_socket, zmq.POLLIN)

    def __get_ip(self):
        def get_interface_ip(ifname, s):
            return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s',
                                                                                ifname[:15].encode("utf-8")))[20:24])

        #ip = socket.gethostbyname(socket.gethostname())
        # if ip.startswith("127."):
        interfaces = [
                      "eth0",
                      "eth1",
                      "eth2",
                      "wlan0",
                      "wlan1",
                      "wifi0",
                      "ath0",
                      "ath1",
                      "ppp0",
                      ]
                      for ifname in interfaces:
                          try:
                              udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                                  ip = get_interface_ip(ifname, udp_socket)
                                      break
                                          except IOError:
                                              pass
                                          return ip


def __init__(self, port_number, recv_timeout):
    self.port_number = port_number
        self.recv_timeout = recv_timeout
        self.server_list = []

        self.ip = self.__get_ip()

        self.__setup_udp()
        self.__setup_zmq_socket()
        self.__setup_poller()

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

        logging.info("{0}\tПолучение нового списка серверов\t{1}".format(self.ip, self.server_list))

        if None in self.server_list:
            self.server_list.remove(None)

return self.server_list

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

def __handle_message(self, json_msg):
    if json_msg["type"] == "invalid_token":
        logging.error("{0}\tПопытка аутентификации\t Неудача. Неверный логин или пароль".format(self.ip))
            return False
        elif json_msg["type"] == "auth_complete":
            logging.error("{0}\tПопытка аутентификации\t Успех".format(self.ip))
            return True
    elif json_msg["type"] == "done":
        return True
        elif json_msg["type"] == "invalid_request":
            logging.error("{0}\tНеверный запрос".format(self.ip))
            return False
    elif json_msg["type"] == "screenshot":
        return json_msg["image"]
        else:
            logging.error("{0}\tНеверный запрос".format(self.connected_address))
            return False

def __connect_to(self, address):
    self.connected_address = address
        self.__zmq_socket.connect("tcp://{0}:{1}".format(address[0], address[1]))
        logging.info("{0}\tСоединение с {1}:{2}".format(self.ip, address[0], address[1]))

    def __disconnect(self):
        self.__send_message({"type": "close_connection",
                            "ip": self.ip})
                            self.__zmq_socket.disconnect("tcp://{0}:{1}".format(self.connected_address[0], self.connected_address[1]))
                            logging.info("{0}\tОтключение от {1}:{2}".format(self.ip, self.connected_address[0], self.connected_address[1]))

def __abort(self):
    logging.error("{0}:{1}\tСервер перестал отвечать".format(self.connected_address[0], self.connected_address[1]))
        self.__disconnect()
        raise TimeoutError

    def connect_to_server(self, address, login, passwd):
        self.__connect_to(address)

        # Authenticate client
        if not self.__send_message({"type": "estimate_connection",
                                   "token": hashlib.md5((login + "salt" + passwd).encode()).hexdigest(),
                                   "ip": self.ip}):
            self.__abort()

                                   try:
            json_msg = self.__receive_message()
                                   except TimeoutError:
            self.__abort()
            return False

                                   # Get authentication report
        return self.__handle_message(json_msg)

def disconnect(self):
    self.__disconnect()

    def recieve_screenshot(self):
        if not self.__send_message({"type": "request_screenshot"}):
            self.__abort()

        try:
            json_msg = self.__receive_message()
        except TimeoutError:
            self.__abort()
            return False

        return self.__handle_message(json_msg)

        # def send_keybord_event(self, key):
        #     logging.info("Sending keyboard event. Key {0}".format(key))
        #     if not self.__send_message({"type": "keyboard_event",
        #                                 "key": key}):
        #         self.__abort()
        #
        #     try:
        #         json_msg = self.__receive_message()
        #     except TimeoutError:
        #         self.__abort()
        #         return False

                return self.__handle_message(json_msg)

def send_mouse_event(self, pos_x, pos_y, key):
    logging.info("{0}\tОтправка события мыши:\t{1};{2};{3}".format(self.ip, pos_x, pos_y, key))
        if not self.__send_message({"type": "mouse_event",
                                   "key": key,
                                   "x": pos_x,
                                   "y": pos_y}):
            self.__abort()
                                   
                                   try:
            json_msg = self.__receive_message()
                                   except TimeoutError:
            self.__abort()
            return False
                                   
        return self.__handle_message(json_msg)
    
    def send_incorrect_message(self):
        logging.info("{0}\tОтправка некорректного события".format(self.ip))
        if not self.__send_message({"type": "some_event"}):
            self.__abort()
        
        try:
            json_msg = self.__receive_message()
        except TimeoutError:
            self.__abort()
            return False
        
        return self.__handle_message(json_msg)