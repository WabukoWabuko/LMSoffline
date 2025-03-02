# main.py
import sys
from PyQt5.QtWidgets import QApplication
from database import init_db
from login import LoginWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    init_db(force_reset=False)
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec_())
