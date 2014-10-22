from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QInputDialog, QGraphicsScene, QMessageBox, QDialog
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QByteArray

from client import Client

client_form = uic.loadUiType("client.ui")[0]
terminal_form = uic.loadUiType("terminal.ui")[0]

class TerminalWidget(QDialog, terminal_form):
    def __init__(self, parent=None, network_client=None, client_name=""):
        QWidget.__init__(self, parent)
        self.setupUi(self)
        self._graphics_scene = QGraphicsScene(self)
        self.graphicsView.setScene(self._graphics_scene)
        self.client = network_client
        self.setWindowTitle(client_name)
        self._graphics_scene.mousePressEvent = self.mouse_pressed

    def paintEvent(self, QPaintEvent):
        try:
            self.image_base_64 = self.client.recieve_screenshot()
        except TimeoutError:
            mb = QMessageBox.critical(self, "Error", "Server is not responding!")
            self.close()
            return


        self.data = QByteArray.fromBase64(self.image_base_64)
        self.pm = QPixmap()
        self.pm.loadFromData(self.data, "PNG")

        self._graphics_scene.clear()
        self._graphics_scene.addPixmap(self.pm)
        self.update()

    def closeEvent(self, event):
        super(TerminalWidget, self).closeEvent(event)
        self.client.disconnect()

    def mouse_pressed(self, event):
        x = int(event.scenePos().x())
        y = int(event.scenePos().y())

        button = event.button()
        if button == 4:
            button = 3

        try:
            self.client.send_mouse_event(x, y, button)
        except:
            mb = QMessageBox.critical(self, "Error", "Server is not responding!")
            self.close()

    # def keyPressEvent(self, event):
    #     key = event.key()
    #     try:
    #         self.client.send_keybord_event(key)
    #     except:
    #         mb = QMessageBox.critical(self, "Error", "Server is not responding!")
    #         self.close()




class Widget(QWidget, client_form):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setupUi(self)
        self.refreshLabel.setVisible(False)
        self.client = Client(50000, 3000)

        self.refreshButton.clicked.connect(self.refresh)
        self.connectButton.clicked.connect(self.connect)


    def refresh(self):
        self.serverList.clear()
        self.refreshLabel.setVisible(True)
        self.repaint()

        for x in self.client.refresh_server_list():
            self.serverList.addItem("{0}:{1}".format(x[0], x[1]))

        self.refreshLabel.setVisible(False)

    def connect(self):
        try:
            login, login_ok = QInputDialog.getText(self, 'Login', 'Enter login:')
            if login_ok:
                passwd, password_ok = QInputDialog.getText(self, 'Password', 'Enter password:')
                if password_ok:
                    address = self.serverList.currentItem().text().split(":")
                    if self.client.connect_to_server(address, login, passwd):
                        term = TerminalWidget(parent=None,
                                              network_client=self.client,
                                              client_name=address[0]+":"+address[1])
                        term.exec()
                    else:
                        mb = QMessageBox.critical(self, "Error", "Wrong login or password!")

        except TimeoutError:
            mb = QMessageBox.critical(self, "Error", "Server is not responding!")