# login.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QHBoxLayout
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor, QBrush
from PyQt5.QtCore import Qt
import sqlite3
from dashboard import DashboardWindow
from database import hash_password
import os

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WABUKOWABUKO SCHOOL - Login")
        self.setGeometry(100, 100, 400, 500)
        self.setStyleSheet("""
            QWidget { background: rgba(255, 255, 255, 0.9); border-radius: 10px; }
            QLabel { color: #333; }
            QLineEdit { padding: 8px; border: 1px solid #ccc; border-radius: 5px; }
            QPushButton { background-color: #4CAF50; color: white; padding: 10px; border-radius: 5px; }
            QPushButton:hover { background-color: #45a049; }
        """)

        # Background image
        self.setAutoFillBackground(True)
        palette = self.palette()
        background_path = "resources/background.jpg"
        if os.path.exists(background_path):
            pixmap = QPixmap(background_path).scaled(self.size(), Qt.KeepAspectRatioByExpanding)
            if not pixmap.isNull():  # Check if pixmap loaded successfully
                brush = QBrush(pixmap)
                palette.setBrush(QPalette.Window, brush)
            else:
                print(f"Warning: Could not load background image at {background_path}")
        else:
            print(f"Warning: Background image not found at {background_path}")
        self.setPalette(palette)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Logo
        logo_label = QLabel()
        logo_path = "resources/logo.png"
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path).scaled(100, 100, Qt.KeepAspectRatio)
            if not logo_pixmap.isNull():
                logo_label.setPixmap(logo_pixmap)
            else:
                print(f"Warning: Could not load logo image at {logo_path}")
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)

        # School branding
        school_name = QLabel("Springfield High School")
        school_name.setFont(QFont("Arial", 16, QFont.Bold))
        school_name.setAlignment(Qt.AlignCenter)
        layout.addWidget(school_name)

        motto = QLabel("Motto: 'Excellence in Learning'")
        motto.setFont(QFont("Arial", 10, QFont.StyleItalic))  # Fixed to use StyleItalic
        motto.setAlignment(Qt.AlignCenter)
        layout.addWidget(motto)

        vision = QLabel("Vision: Empowering students for a bright future.")
        vision.setFont(QFont("Arial", 10))
        vision.setAlignment(Qt.AlignCenter)
        vision.setWordWrap(True)
        layout.addWidget(vision)

        # Inputs
        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        # Login button
        self.login_button = QPushButton("Login", self)
        self.login_button.clicked.connect(self.check_login)
        layout.addWidget(self.login_button)

        layout.addStretch()
        self.setLayout(layout)

    def check_login(self):
        username = self.username_input.text()
        password = hash_password(self.password_input.text())
        print(f"Attempting login with username: {username}, hashed password: {password}")

        conn = sqlite3.connect("resources/school_lms.db")
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
