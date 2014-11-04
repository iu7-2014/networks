import socket
import logging
import json
import sys
import fcntl
import struct

import zmq
from pymouse import PyMouse
from pykeyboard import PyKeyboard

from PyQt5.QtCore import QBuffer, QByteArray, QIODevice
from PyQt5.QtWidgets import QApplication


class Configuration:
    udp_broadcast_ip = "255.255.255.255"
    udp_presence_message = b"rc client"
    udp_respond_message = b"rc server"
    password_hash = "b884f389d08277b0540e8f0fbfdf3a8c"


class Authenticator:
    def __init__(self, hash):
        self.hash = hash

    def authenticate(self, hash):
        return self.hash == hash


class UserIOControl:
    def __init__(self):
        self.__mouse = PyMouse()
        self.__keyboard = PyKeyboard()
        self.__app = QApplication([])
        self.__screen = self.__app.primaryScreen()

    def click(self, x, y, button=1):
        self.__mouse.click(x, y, button)

    def press_key(self, key):
        self.__keyboard.press_key(key)

    def take_screenshot(self):
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)

        image = self.__screen.grabWindow(QApplication.desktop().winId())
        image.save(buffer, "PNG")

        return str(byte_array.toBase64())[1:]


class Server:
    def __setup_udp(self):
        self.__udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.__udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.__udp_socket.bind(("", self.port_number))

        logging.info("{0}\tПрослушивание UDP сокета. Порт:\t{1}".format(self.ip, self.port_number))

    def __setup_zmq_socket(self):
        self.__context = zmq.Context()
        self.__zmq_socket = self.__context.socket(zmq.PAIR)
        self.__zmq_socket.bind("tcp://*:{0}".format(self.port_number))

    def __setup_poller(self):
        self.__poller = zmq.Poller()
        self.__poller.register(self.__zmq_socket, zmq.POLLIN)

    def __get_ip(self):
        def get_interface_ip(ifname, s):
            return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s',
                                    ifname[:15].encode("utf-8")))[20:24])

        #ip = socket.gethostbyname(socket.gethostname())
        #if ip.startswith("127."):
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

        self.__authenticated = False

        self.__authenticator = Authenticator(Configuration.password_hash)
        self.__user_io_control = UserIOControl()

        self.ip = self.__get_ip()
        self.clinet_address = (None, None)

        logging.info("{0}\tСтарт новой сессии\tУспешно".format(self.ip))

        self.__setup_udp()
        self.__setup_zmq_socket()
        self.__setup_poller()

    def __get_udp_ping(self):
        udp_poller = zmq.Poller()
        udp_poller.register(self.__udp_socket, zmq.POLLIN)

        events = dict(udp_poller.poll(self.recv_timeout))

        if self.__udp_socket.fileno() in events:
            msg, self.client_address = self.__udp_socket.recvfrom(10)

            if msg == Configuration.udp_presence_message:
                logging.info("{0}\tЗапрос списка серверов".format(self.client_address[0]))
                self.__send_udp_ping()
                logging.info("{0}\tОтправка ответа о своем присутсвии\tУспешно".format(self.ip))

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
        logging.error("{0}\tРазрыв соединения с клиентом".format(self.client_address[0]))
        self.__authenticated = False
        return False

    def __handle_message(self, json_msg):
        if json_msg["type"] == "close_connection":
            if self.__authenticated:
                logging.info("{0}\tЗавершение соединения".format(json_msg["ip"]))
                self.__authenticated = False
            return True
        elif json_msg["type"] == "estimate_connection":
            logging.info("{0}\tПолучение запроса на соединение\tУспешно".format(json_msg["ip"]))

            self.__authenticated = self.__authenticator.authenticate(json_msg["token"])
            if self.__authenticated:
                self.client_address = (json_msg["ip"], self.client_address[1])
                if not self.__send_message({"type": "auth_complete"}):
                    return self.__abort()
                logging.info("{0}\tЗавершение аутентификации\tУспешно".format(self.client_address[0]))
                return True
            else:
                if not self.__send_message({"type": "invalid_token"}):
                    return self.__abort()
                logging.info("{0}\tЗавершение аутентификации\tОшибка\tПричина: неправильный логин или пароль".format(self.client_address[0]))
                return False
        elif self.__authenticated:
            if json_msg["type"] == "mouse_event":
                logging.info("{0}\tЗапрос на клик курсором\t{1},{2},{3}".format(self.client_address[0],
                                                                                json_msg["x"],
                                                                                json_msg["y"],
                                                                                json_msg["key"]))
                self.__user_io_control.click(json_msg["x"], json_msg["y"], json_msg["key"])
                if not self.__send_message({"type": "done"}):
                    return self.__abort()
                return True
            elif json_msg["type"] == "keyboard_event":
                self.__user_io_control.press_key(json_msg["key"])
                if not self.__send_message({"type": "done"}):
                    return self.__abort()
                return True
            elif json_msg["type"] == "request_screenshot":
                if not self.__send_message({"type": "screenshot",
                                            "image": self.__user_io_control.take_screenshot()}):
                    return self.__abort()
                return True

        logging.error("{0}\tНеизвестное сообщение от клиента: \t{1}".format(self.client_address[0], json_msg))
        if not self.__send_message({"type": "invalid_response"}):
            return self.__abort()

    def run(self):
        timeout = self.recv_timeout
        while True:
            self.__get_udp_ping()

            try:
                msg = self.__receive_message()
            except TimeoutError:
                if self.__authenticated:
                    self.__abort()
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

    s = Server(50000, 200)
    s.run()


if __name__ == '__main__':
    main()
