from PyQt5.QtCore import QBuffer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication
from PIL import Image, ImageChops


# QPixmap.


def make_screenshot():
	app = QApplication([])
	screen = app.primaryScreen()
	result = screen.grabWindow(QApplication.desktop().winId())
