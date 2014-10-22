import sys
from PyQt5.QtWidgets import QApplication
from gui import Widget
import logging

def setup_logging_system():
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

if __name__ == "__main__":
    setup_logging_system()
    app = QApplication(sys.argv)
    main_window = Widget(None)
    main_window.show()
    app.exec_()
