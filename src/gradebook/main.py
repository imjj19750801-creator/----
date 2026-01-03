import sys

from PyQt5.QtWidgets import QApplication

from .gui import MainWindow


def run():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1100, 720)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run()
