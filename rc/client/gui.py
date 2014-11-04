import logging
import webbrowser

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QInputDialog, QGraphicsScene, QMessageBox, QDialog
from PyQt5.QtGui import QPixmap, QKeySequence
from PyQt5.QtCore import QByteArray

from client import Client

client_form = uic.loadUiType("form.ui")[0]

class Widget(QMainWindow, client_form):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.refreshLabel.setVisible(False)
        self.client = Client(50000, 3000)

        self.refreshButton.clicked.connect(self.refresh)
        self.connectButton.clicked.connect(self.connect)

        self._graphics_scene = QGraphicsScene(self)
        self.graphicsView.setScene(self._graphics_scene)
        self._graphics_scene.mousePressEvent = self.mouse_pressed
        self.exit_action.triggered.connect(self.exit)
        self.help_action.triggered.connect(self.show_help)
        self.bullshit_action.triggered.connect(self.send_incorrect_message)
        self.viewlog_action.triggered.connect(lambda: webbrowser.open('./client.log'))
        self.connected = False

    def exit(self):
        if self.connected:
            self.revert()
            self.client.disconnect()

        self.close()

    def show_help(self):
        mb = QMessageBox.information(
            self, "О программе",
            "Программа удаленного управления рабочим столом.\n\n"
            "Создатели:\n"
            "Алексей Абакумкин, ИУ7-72\n"
            "Роман Инфлянскас, ИУ7-71\n"
            "(c) 2014, Москва, МГТУ им. Н. Э. Баумана")

    def critical(self, msg, log=True):
        self.revert()
        QMessageBox.critical(self, "Ошибка", msg)
        if log:
            logging.error("{ip}\t{msg}\tОшибка".format(ip=self.client.ip, msg=msg))

    def send_incorrect_message(self):
        if self.connected:
            try:
                self.client.send_incorrect_message()
            except:
                # mb = QMessageBox.critical(self, "Ошибка", "Сервер перестал отвечать")
                self.critical("Сервер перестал отвечать")

    def refresh(self):
        self.serverList.clear()
        self.refreshLabel.setVisible(True)
        self.repaint()

        for x in self.client.refresh_server_list():
            self.serverList.addItem("{0}:{1}".format(x[0], x[1]))

        self.refreshLabel.setVisible(False)

    def connect(self):
        if self.connected:
            self.revert()
            self.client.disconnect()
            return

        try:
            login, login_ok = QInputDialog.getText(self, 'Логин', 'Введите логин:')
            if login_ok:
                passwd, password_ok = QInputDialog.getText(self, 'Пароль', 'Введите пароль:', 2)
                if password_ok:
                    server_item = self.serverList.currentItem()
                    try:
                        address = server_item.text().split(":")
                    except:
                        # server_item = self.serverList.findItems('', 0)[0]
                        self.serverList.setCurrentRow(0)
                        server_item = self.serverList.currentItem()
                        address = server_item.text().split(":")
                    if self.client.connect_to_server(address, login, passwd):
                        self.connectButton.setText("Отключиться")
                        self.connected = True
                    else:
                        self.critical("Неверный логин или пароль!", log=False)
                        # mb = QMessageBox.critical(self, "Ошибка", "Неверный логин или пароль!")

        except TimeoutError:
            self.critical("Сервер перестал отвечать")
            # mb = QMessageBox.critical(self, "Ошибка", "Сервер перестал отвечать")

    def revert(self):
        self._graphics_scene.clear()
        self.connectButton.setText("Присоединиться")
        self.connected = False

    def paintEvent(self, QPaintEvent):
        if self.connected:
            try:
                self.image_base_64 = self.client.recieve_screenshot()
            except TimeoutError:
                self.critical("Сервер перестал отвечать")
                # mb = QMessageBox.critical(self, "Ошибка", "Сервер перестал отвечать")
                return


            self.data = QByteArray.fromBase64(self.image_base_64)
            self.pm = QPixmap()
            self.pm.loadFromData(self.data, "PNG")

            self._graphics_scene.clear()
            self._graphics_scene.addPixmap(self.pm)
            self.update()

    def mouse_pressed(self, event):
        if self.connected:
            x = int(event.scenePos().x())
            y = int(event.scenePos().y())

            button = event.button()
            if button == 4:
                button = 3

            try:
                self.client.send_mouse_event(x, y, button)
            except:
                self.critical("Сервер перестал отвечать")
                # mb = QMessageBox.critical(self, "Ошибка", "Сервер перестал отвечать")
                self.revert()
