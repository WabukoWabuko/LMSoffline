# login.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
import sqlite3
from dashboard import DashboardWindow
from database import hash_password

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("School LMS - Login")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()
        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Username")
        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.login_button = QPushButton("Login", self)
        self.login_button.clicked.connect(self.check_login)

        layout.addWidget(QLabel("Login to School LMS"))
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)
        self.setLayout(layout)

    def check_login(self):
        username = self.username_input.text()
        password = hash_password(self.password_input.text())
        print(f"Attempting login with username: {username}, hashed password: {password}")

        conn = sqlite3.connect("school_lms.db")
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE username=? AND password=?", 
                 (username, password))
        result = c.fetchone()
        print(f"Database query result: {result}")
        conn.close()

        if result:
            role = result[0]
            print(f"Login successful, role: {role}")
            self.open_dashboard(role, username)
        else:
            print("Login failed: Invalid credentials")
            QMessageBox.warning(self, "Error", "Invalid username or password")

    def open_dashboard(self, role, username):
        self.dashboard = DashboardWindow(role, username)
        self.dashboard.show()
        self.hide()
