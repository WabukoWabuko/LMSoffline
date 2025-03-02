# dashboard.py
import sqlite3
import os
import shutil
import re
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QListWidget, QFileDialog, QInputDialog, QMessageBox, 
                             QTabWidget, QStatusBar, QProgressBar, QTextEdit, QApplication,
                             QListWidgetItem, QCalendarWidget, QCheckBox, QDialog, QTextBrowser, QHBoxLayout, QGraphicsOpacityEffect)
from PyQt5.QtGui import QIcon, QFont, QPixmap, QTextCharFormat, QColor
from PyQt5.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtMultimedia import QSound
from PyQt5.QtChart import QChart, QChartView, QBarSeries, QBarSet, QPieSeries, QPieSlice, QBarCategoryAxis, QValueAxis
from PIL import Image
import io

class TutorialDialog(QDialog):
    def __init__(self, role, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Springfield LMS!")
        self.setGeometry(200, 200, 400, 300)
        self.setModal(True)

        layout = QVBoxLayout()
        self.text_browser = QTextBrowser()
        self.text_browser.setFont(QFont("Arial", 14))
        if role == "student":
            self.text_browser.setHtml("""
                <h2>Welcome, Student!</h2>
                <p>Explore courses, submit work, chat, and track progress!</p>
            """)
        elif role == "teacher":
            self.text_browser.setHtml("""
                <h2>Welcome, Teacher!</h2>
                <p>Create courses, grade work, and chat with students!</p>
            """)
        layout.addWidget(self.text_browser)

        ok_button = QPushButton("OK", self)
        ok_button.setFont(QFont("Arial", 14, QFont.Bold))
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)

        self.setLayout(layout)

class AchievementDialog(QDialog):
    def __init__(self, badge_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Achievement!")
        self.setGeometry(300, 300, 300, 200)
        self.setModal(True)

        layout = QVBoxLayout()
        label = QLabel(f"You earned\n'{badge_name}'!")
        label.setFont(QFont("Arial", 16, QFont.Bold))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        ok_button = QPushButton("OK", self)
        ok_button.setFont(QFont("Arial", 14, QFont.Bold))
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)

        self.setLayout(layout)

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(500)
        self.animation.setStartValue(QRect(300, 350, 300, 0))
        self.animation.setEndValue(QRect(300, 300, 300, 200))
        self.animation.setEasingCurve(QEasingCurve.OutBounce)
        self.animation.start()

class DashboardWindow(QMainWindow):
    def __init__(self, role, username):
        super().__init__()
        self.role = role
        self.username = username
        self.dark_mode = False
        self.calendar_cache = {}
        self.setWindowTitle(f"School LMS - {role.capitalize()}")
        self.setGeometry(150, 150, 900, 700)
        self.update_stylesheet()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setFont(QFont("Arial", 12))
        self.status_bar.showMessage("Ready")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout()

        welcome_label = QLabel(f"Welcome, {self.username}!")
        welcome_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.layout.addWidget(welcome_label)
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Arial", 14))
        self.setup_dashboard()
        self.layout.addWidget(self.tabs)

        mode_toggle = QCheckBox("Dark Mode", self)
        mode_toggle.setFont(QFont("Arial", 14))
        mode_toggle.stateChanged.connect(self.toggle_dark_mode)
        self.layout.addWidget(mode_toggle)

        logout_button = QPushButton("Logout", self)
        logout_button.setFont(QFont("Arial", 14, QFont.Bold))
        logout_button.clicked.connect(self.logout)
        self.layout.addWidget(logout_button)

        central_widget.setLayout(self.layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_due_dates)
        self.timer.start(60000)

        self.success_sound = QSound("resources/success.wav") if os.path.exists("resources/success.wav") else None

        self.animate_tabs()
        self.show_tutorial()

    def update_stylesheet(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow { background-color: #2d2d2d; color: #ffffff; }
                QTabWidget::pane { border: 1px solid #555; }
                QTabBar::tab { background: #424242; padding: 10px; color: #ffffff; }
                QTabBar::tab:selected { background: #1976d2; }
                QPushButton { background-color: #1976d2; color: white; padding: 6px; border-radius: 3px; }
                QPushButton:hover { background-color: #1565c0; }
                QLabel { font-family: Arial; color: #ffffff; }
                QListWidget { background-color: #333; color: #ffffff; }
                QListWidget::item[unread="true"] { background-color: #ff8f00; color: #ffffff; }
                QListWidget::item[user="true"] { background-color: #1976d2; color: #ffffff; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow { background-color: #ffffff; color: #000000; }
                QTabWidget::pane { border: 1px solid #ccc; }
                QTabBar::tab { background: #e0e0e0; padding: 10px; }
                QTabBar::tab:selected { background: #90caf9; }
                QPushButton { background-color: #4CAF50; color: white; padding: 6px; border-radius: 3px; }
                QPushButton:hover { background-color: #45a049; }
                QLabel { font-family: Arial; }
                QListWidget { background-color: #ffffff; color: #000000; }
                QListWidget::item[unread="true"] { background-color: #fff3e0; }
                QListWidget::item[user="true"] { background-color: #90caf9; color: #000000; }
            """)

    def animate_tabs(self):
        animation = QPropertyAnimation(self.tabs, b"geometry")
        animation.setDuration(500)
        animation.setStartValue(self.tabs.geometry().adjusted(0, 50, 0, 50))
        animation.setEndValue(self.tabs.geometry())
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()

    def toggle_dark_mode(self, state):
        self.dark_mode = bool(state)
        self.update_stylesheet()

    def show_tutorial(self):
        tutorial = TutorialDialog(self.role, self)
        tutorial.exec_()

    def show_achievement(self, badge_name):
        achievement = AchievementDialog(badge_name, self)
        if self.success_sound:
            self.success_sound.play()
        achievement.exec_()

    def validate_due_date(self, due_date):
        pattern = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(pattern, due_date):
            return False
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def award_points(self, student, points, reason):
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("INSERT INTO points (student, points, reason) VALUES (?, ?, ?)", (student, points, reason))
        
        total_points = self.get_total_points(student)
        if total_points >= 50 and not self.has_badge(student, "Star Student"):
            c.execute("INSERT INTO badges (student, badge_name, awarded_date) VALUES (?, ?, ?)",
                     (student, "Star Student", datetime.now().strftime("%Y-%m-%d")))
            c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)",
                     (student, "Earned 'Star Student'!"))
            self.show_achievement("Star Student")

        quiz_count = self.get_quiz_count(student)
        if quiz_count >= 5 and not self.has_badge(student, "Quiz Master"):
            c.execute("INSERT INTO badges (student, badge_name, awarded_date) VALUES (?, ?, ?)",
                     (student, "Quiz Master", datetime.now().strftime("%Y-%m-%d")))
            c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)",
                     (student, "Earned 'Quiz Master'!"))
            self.show_achievement("Quiz Master")

        if reason.startswith("Submitted assignment") and self.is_early_submission(student, reason):
            early_count = self.get_early_submission_count(student)
            if early_count >= 3 and not self.has_badge(student, "Early Bird"):
                c.execute("INSERT INTO badges (student, badge_name, awarded_date) VALUES (?, ?, ?)",
                         (student, "Early Bird", datetime.now().strftime("%Y-%m-%d")))
                c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)",
                         (student, "Earned 'Early Bird'!"))
                self.show_achievement("Early Bird")

        conn.commit()
        conn.close()

    def get_total_points(self, student):
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT SUM(points) FROM points WHERE student=?", (student,))
        total = c.fetchone()[0] or 0
        conn.close()
        return total

    def has_badge(self, student, badge_name):
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM badges WHERE student=? AND badge_name=?", (student, badge_name))
        has_it = c.fetchone()[0] > 0
        conn.close()
        return has_it

    def get_quiz_count(self, student):
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM quiz_submissions WHERE student=?", (student,))
        count = c.fetchone()[0]
        conn.close()
        return count

    def is_early_submission(self, student, reason):
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        assignment_title = reason.split("'")[1]
        c.execute("SELECT due_date FROM assignments WHERE student=? AND description LIKE ? AND grade IS NULL ORDER BY due_date DESC LIMIT 1",
                 (student, f"%{assignment_title}%"))
        due_date = c.fetchone()
        conn.close()
        if due_date:
            due = datetime.strptime(due_date[0], "%Y-%m-%d").date()
            today = datetime.now().date()
            return (due - today).days >= 3
        return False

    def get_early_submission_count(self, student):
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM points WHERE student=? AND reason LIKE 'Submitted assignment%' AND EXISTS (SELECT 1 FROM assignments a WHERE a.student=? AND a.description LIKE '%' || SUBSTR(points.reason, 18, LENGTH(points.reason)-18) || '%' AND DATE(a.due_date) >= DATE('now', '+3 days'))",
                 (student, student))
        count = c.fetchone()[0]
        conn.close()
        return count

    def get_badges(self, student):
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT badge_name FROM badges WHERE student=?", (student,))
        badges = [row[0] for row in c.fetchall()]
        conn.close()
        return badges

    def get_leaderboard(self):
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT student, SUM(points) as total_points FROM points GROUP BY student ORDER BY total_points DESC LIMIT 5")
        leaderboard = c.fetchall()
        conn.close()
        return leaderboard

    def get_next_due_date(self):
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT due_date FROM assignments WHERE student=? AND grade IS NULL ORDER BY due_date LIMIT 1", 
                 (self.username,))
        assignment_date = c.fetchone()
        c.execute("SELECT due_date FROM quizzes WHERE course_id IN (SELECT course_id FROM enrollments WHERE student=?) AND quiz_id NOT IN (SELECT quiz_id FROM quiz_submissions WHERE student=?) ORDER BY due_date LIMIT 1",
                 (self.username, self.username))
        quiz_date = c.fetchone()
        conn.close()
        dates = [d[0] for d in [assignment_date, quiz_date] if d]
        return min(dates) if dates else None

    def check_due_dates(self):
        if self.role != "student":
            return
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT course_id, due_date, description FROM assignments WHERE student=? AND grade IS NULL", 
                 (self.username,))
        assignments = c.fetchall()
        c.execute("SELECT course_id, due_date, title FROM quizzes WHERE quiz_id NOT IN (SELECT quiz_id FROM quiz_submissions WHERE student=?)",
                 (self.username,))
        quizzes = c.fetchall()
        today = datetime.now().date()
        for course_id, due_date, desc in assignments + [(q[0], q[1], q[2]) for q in quizzes]:
            due = datetime.strptime(due_date, "%Y-%m-%d").date()
            days_left = (due - today).days
            if 0 <= days_left <= 3:
                msg = f"Due Soon: '{desc}' on {due_date}"
                c.execute("SELECT COUNT(*) FROM notifications WHERE username=? AND message=?", (self.username, msg))
                if c.fetchone()[0] == 0:
                    c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)", (self.username, msg))
        conn.commit()
        conn.close()
        self.refresh_notif_list()

    def setup_dashboard(self):
        if self.role == "student":
            self.student_dashboard()
        elif self.role == "teacher":
            self.teacher_dashboard()
        elif self.role == "admin":
            self.admin_dashboard()

    # Student Dashboard
    def student_dashboard(self):
        home_tab = QWidget()
        home_layout = QVBoxLayout()
        home_label = QLabel("Dashboard")
        home_label.setFont(QFont("Arial", 16, QFont.Bold))
        home_layout.addWidget(home_label)

        points = self.get_total_points(self.username)
        badges = len(self.get_badges(self.username))
        pie_series = QPieSeries()
        pie_series.append("Points", points)
        pie_series.append("Badges", badges)
        pie_chart = QChart()
        pie_chart.addSeries(pie_series)
        pie_chart.setTitle("Achievements")
        pie_chart.setTitleFont(QFont("Arial", 14, QFont.Bold))
        pie_chart_view = QChartView(pie_chart)
        pie_chart_view.setMinimumSize(300, 300)
        home_layout.addWidget(pie_chart_view)

        due_date = self.get_next_due_date()
        due_label = QLabel(f"Next Due: {due_date or 'None'}")
        due_label.setFont(QFont("Arial", 14))
        home_layout.addWidget(due_label)
        home_layout.addStretch()
        home_tab.setLayout(home_layout)
        self.tabs.addTab(home_tab, "Home")

        courses_tab = QWidget()
        courses_layout = QVBoxLayout()
        courses_layout.addWidget(QLabel("Courses", font=QFont("Arial", 16, QFont.Bold)))
        self.course_list = QListWidget()
        self.course_list.setFont(QFont("Arial", 12))
        self.refresh_course_list()
        courses_layout.addWidget(self.course_list)
        btn_layout = QHBoxLayout()
        enroll_button = QPushButton("Enroll", self)
        enroll_button.setFont(QFont("Arial", 14, QFont.Bold))
        enroll_button.clicked.connect(self.enroll_in_course)
        btn_layout.addWidget(enroll_button)
        submit_button = QPushButton("Submit", self)
        submit_button.setFont(QFont("Arial", 14, QFont.Bold))
        submit_button.clicked.connect(self.submit_assignment)
        btn_layout.addWidget(submit_button)
        quiz_button = QPushButton("Quiz", self)
        quiz_button.setFont(QFont("Arial", 14, QFont.Bold))
        quiz_button.clicked.connect(self.take_quiz)
        btn_layout.addWidget(quiz_button)
        courses_layout.addLayout(btn_layout)
        courses_tab.setLayout(courses_layout)
        self.tabs.addTab(courses_tab, "Courses")

        grades_tab = QWidget()
        grades_layout = QVBoxLayout()
        grades_layout.addWidget(QLabel("Grades", font=QFont("Arial", 16, QFont.Bold)))
        self.grade_chart = QChartView(self.create_grade_chart())
        self.grade_chart.setMinimumSize(400, 300)
        grades_layout.addWidget(self.grade_chart)
        stats_button = QPushButton("Stats", self)
        stats_button.setFont(QFont("Arial", 14, QFont.Bold))
        stats_button.clicked.connect(self.show_grade_stats)
        grades_layout.addWidget(stats_button)
        grades_tab.setLayout(grades_layout)
        self.tabs.addTab(grades_tab, "Grades")

        progress_tab = QWidget()
        progress_layout = QVBoxLayout()
        progress_layout.addWidget(QLabel("Progress", font=QFont("Arial", 16, QFont.Bold)))
        self.progress_chart = QChartView(self.create_progress_chart())
        self.progress_chart.setMinimumSize(400, 300)
        progress_layout.addWidget(self.progress_chart)
        progress_tab.setLayout(progress_layout)
        self.tabs.addTab(progress_tab, "Progress")

        leaderboard_tab = QWidget()
        leaderboard_layout = QVBoxLayout()
        leaderboard_layout.addWidget(QLabel("Leaderboard", font=QFont("Arial", 16, QFont.Bold)))
        self.leaderboard_list = QListWidget()
        self.leaderboard_list.setFont(QFont("Arial", 12))
        self.refresh_leaderboard()
        leaderboard_layout.addWidget(self.leaderboard_list)
        leaderboard_tab.setLayout(leaderboard_layout)
        self.tabs.addTab(leaderboard_tab, "Leaderboard")

        notif_tab = QWidget()
        notif_layout = QVBoxLayout()
        notif_layout.addWidget(QLabel("Notifications", font=QFont("Arial", 16, QFont.Bold)))
        self.notif_list = QListWidget()
        self.notif_list.setFont(QFont("Arial", 12))
        self.refresh_notif_list()
        notif_layout.addWidget(self.notif_list)
        mark_read_button = QPushButton("Mark Read", self)
        mark_read_button.setFont(QFont("Arial", 14, QFont.Bold))
        mark_read_button.clicked.connect(self.mark_notif_read)
        notif_layout.addWidget(mark_read_button)
        notif_tab.setLayout(notif_layout)
        self.tabs.addTab(notif_tab, "Notifs")

        messages_tab = QWidget()
        messages_layout = QVBoxLayout()
        messages_layout.addWidget(QLabel("Messages", font=QFont("Arial", 16, QFont.Bold)))
        self.message_list = QListWidget()
        self.message_list.setFont(QFont("Arial", 12))
        self.refresh_message_list()
        messages_layout.addWidget(self.message_list)
        send_message_button = QPushButton("Send", self)
        send_message_button.setFont(QFont("Arial", 14, QFont.Bold))
        send_message_button.clicked.connect(self.send_message)
        messages_layout.addWidget(send_message_button)
        messages_tab.setLayout(messages_layout)
        self.tabs.addTab(messages_tab, "Msgs")

        chat_tab = QWidget()
        chat_layout = QVBoxLayout()
        chat_layout.addWidget(QLabel("Chat", font=QFont("Arial", 16, QFont.Bold)))
        self.chat_list = QListWidget()
        self.chat_list.setFont(QFont("Arial", 12))
        self.refresh_chat_list()
        chat_layout.addWidget(self.chat_list)
        self.chat_input = QTextEdit()
        self.chat_input.setFont(QFont("Arial", 12))
        self.chat_input.setFixedHeight(50)
        chat_layout.addWidget(self.chat_input)
        send_chat_button = QPushButton("Send", self)
        send_chat_button.setFont(QFont("Arial", 14, QFont.Bold))
        send_chat_button.clicked.connect(self.send_chat_message)
        chat_layout.addWidget(send_chat_button)
        chat_tab.setLayout(chat_layout)
        self.tabs.addTab(chat_tab, "Chat")

        calendar_tab = QWidget()
        calendar_layout = QVBoxLayout()
        calendar_layout.addWidget(QLabel("Calendar", font=QFont("Arial", 16, QFont.Bold)))
        self.calendar = QCalendarWidget()
        self.calendar.setFont(QFont("Arial", 12))
        self.calendar.clicked.connect(self.show_calendar_events)
        self.update_calendar()
        calendar_layout.addWidget(self.calendar)
        self.calendar_events = QLabel("Select a date")
        self.calendar_events.setFont(QFont("Arial", 12))
        calendar_layout.addWidget(self.calendar_events)
        calendar_tab.setLayout(calendar_layout)
        self.tabs.addTab(calendar_tab, "Cal")

    def create_grade_chart(self):
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT course_id, grade FROM assignments WHERE student=? AND grade IS NOT NULL", (self.username,))
        assignments = c.fetchall()
        c.execute("SELECT q.course_id, qs.score FROM quiz_submissions qs JOIN quizzes q ON qs.quiz_id = q.quiz_id WHERE qs.student=?", (self.username,))
        quizzes = c.fetchall()
        conn.close()

        bar_series = QBarSeries()
        grades_set = QBarSet("Grades")
        courses = {}
        for course_id, grade in assignments:
            try:
                score = int(grade) if grade.isdigit() else 0
                courses[course_id] = courses.get(course_id, 0) + score
            except ValueError:
                continue
        for course_id, score in quizzes:
            courses[course_id] = courses.get(course_id, 0) + score * 100

        course_names = []
        for course_id in courses:
            conn = sqlite3.connect("resources/school_lms.db")
            c = conn.cursor()
            c.execute("SELECT course_name FROM courses WHERE course_id=?", (course_id,))
            name = c.fetchone()[0]
            conn.close()
            course_names.append(name)
            grades_set.append(courses[course_id])

        bar_series.append(grades_set)
        chart = QChart()
        chart.addSeries(bar_series)
        chart.setTitle("Grades by Course")
        chart.setTitleFont(QFont("Arial", 14, QFont.Bold))

        axis_x = QBarCategoryAxis()
        axis_x.append(course_names)
        axis_x.setTitleText("Courses")
        axis_x.setTitleFont(QFont("Arial", 12))
        chart.addAxis(axis_x, Qt.AlignBottom)
        bar_series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setRange(0, max(courses.values(), default=100))
        axis_y.setTitleText("Scores")
        axis_y.setTitleFont(QFont("Arial", 12))
        chart.addAxis(axis_y, Qt.AlignLeft)
        bar_series.attachAxis(axis_y)

        return chart

    def create_progress_chart(self):
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT course_id FROM enrollments WHERE student=?", (self.username,))
        courses = c.fetchall()
        bar_series = QBarSeries()
        completed_set = QBarSet("Completed")
        total_set = QBarSet("Total")
        course_names = []

        for course_id_tuple in courses:
            course_id = course_id_tuple[0]
            c.execute("SELECT course_name FROM courses WHERE course_id=?", (course_id,))
            course_name = c.fetchone()[0]
            course_names.append(course_name[:10])
            c.execute("SELECT COUNT(*) FROM assignment_definitions WHERE course_id=?", (course_id,))
            total_assignments = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM assignments WHERE course_id=? AND student=?", (course_id, self.username))
            submitted_assignments = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM quizzes WHERE course_id=?", (course_id,))
            total_quizzes = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM quiz_submissions WHERE quiz_id IN (SELECT quiz_id FROM quizzes WHERE course_id=?) AND student=?", 
                     (course_id, self.username))
            submitted_quizzes = c.fetchone()[0]
            total = total_assignments + total_quizzes
            completed = submitted_assignments + submitted_quizzes
            completed_set.append(completed)
            total_set.append(total)

        bar_series.append(completed_set)
        bar_series.append(total_set)
        chart = QChart()
        chart.addSeries(bar_series)
        chart.setTitle("Progress by Course")
        chart.setTitleFont(QFont("Arial", 14, QFont.Bold))

        axis_x = QBarCategoryAxis()
        axis_x.append(course_names)
        axis_x.setTitleText("Courses")
        axis_x.setTitleFont(QFont("Arial", 12))
        chart.addAxis(axis_x, Qt.AlignBottom)
        bar_series.attachAxis(axis_x)

        # Fix: Extract values from total_set manually
        total_values = [total_set.at(i) for i in range(total_set.count())]
        max_value = max(total_values) if total_values else 1  # Default to 1 if no values
        axis_y = QValueAxis()
        axis_y.setRange(0, max_value)
        axis_y.setTitleText("Tasks")
        axis_y.setTitleFont(QFont("Arial", 12))
        chart.addAxis(axis_y, Qt.AlignLeft)
        bar_series.attachAxis(axis_y)

        return chart

    def refresh_leaderboard(self):
        self.leaderboard_list.clear()
        leaderboard = self.get_leaderboard()
        for rank, (student, points) in enumerate(leaderboard, 1):
            item = QListWidgetItem(f"{rank}. {student} - {points}")
            if student == self.username:
                item.setData(Qt.UserRole, "user")
            self.leaderboard_list.addItem(item)

        opacity_effect = QGraphicsOpacityEffect(self.leaderboard_list)
        self.leaderboard_list.setGraphicsEffect(opacity_effect)
        animation = QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(500)
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()

    def refresh_course_list(self):
        self.course_list.clear()
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT c.course_id, c.course_name FROM courses c JOIN enrollments e ON c.course_id = e.course_id WHERE e.student=?", 
                 (self.username,))
        courses = c.fetchall()
        for course_id, course_name in courses:
            self.course_list.addItem(f"{course_name} (ID: {course_id})")
        conn.close()

    def refresh_grade_list(self):
        self.grade_chart.setChart(self.create_grade_chart())

    def refresh_progress_list(self):
        self.progress_chart.setChart(self.create_progress_chart())

    def refresh_notif_list(self):
        self.notif_list.clear()
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT notif_id, message, is_read FROM notifications WHERE username=?", (self.username,))
        notifications = c.fetchall()
        unread_count = sum(1 for _, _, is_read in notifications if is_read == 0)
        for notif_id, message, is_read in notifications:
            item = QListWidgetItem(f"{message}")
            if is_read == 0:
                item.setData(Qt.UserRole, "unread")
            self.notif_list.addItem(item)
        conn.close()
        self.status_bar.showMessage(f"{unread_count} unread")

    def mark_notif_read(self):
        selected = self.notif_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a notification!")
            return
        notif_id = int(selected.text().split("ID: ")[1].rstrip(")")) if "ID: " in selected.text() else None
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("UPDATE notifications SET is_read=1 WHERE notif_id=?", (notif_id,))
        conn.commit()
        conn.close()
        self.refresh_notif_list()

    def refresh_message_list(self):
        self.message_list.clear()
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT sender, message, timestamp FROM messages WHERE receiver=?", (self.username,))
        messages = c.fetchall()
        for sender, message, timestamp in messages:
            self.message_list.addItem(f"{timestamp} {sender}: {message}")
        if self.role == "teacher":
            c.execute("SELECT receiver, message, timestamp FROM messages WHERE sender=?", (self.username,))
            sent_messages = c.fetchall()
            for receiver, message, timestamp in sent_messages:
                self.message_list.addItem(f"{timestamp} To {receiver}: {message}")
        conn.close()

    def refresh_chat_list(self):
        self.chat_list.clear()
        selected = self.course_list.currentItem()
        if not selected:
            self.chat_list.addItem("Select a course")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT sender, message, timestamp FROM chat_messages WHERE course_id=? ORDER BY timestamp", 
                 (course_id,))
        messages = c.fetchall()
        for sender, message, timestamp in messages:
            self.chat_list.addItem(f"{timestamp} {sender}: {message}")
        conn.close()
        self.chat_list.scrollToBottom()

    def send_chat_message(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        message = self.chat_input.toPlainText().strip()
        if message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = sqlite3.connect("resources/school_lms.db")
            c = conn.cursor()
            c.execute("INSERT INTO chat_messages (course_id, sender, message, timestamp) VALUES (?, ?, ?, ?)",
                     (course_id, self.username, message, timestamp))
            conn.commit()
            conn.close()
            self.chat_input.clear()
            self.refresh_chat_list()
            if self.success_sound:
                self.success_sound.play()

    def update_calendar(self):
        if self.calendar_cache.get(self.username):
            dates = self.calendar_cache[self.username]
        else:
            conn = sqlite3.connect("resources/school_lms.db")
            c = conn.cursor()
            c.execute("SELECT due_date FROM assignments WHERE student=?", (self.username,))
            assignment_dates = [datetime.strptime(row[0], "%Y-%m-%d").date() for row in c.fetchall()]
            c.execute("SELECT due_date FROM quizzes WHERE course_id IN (SELECT course_id FROM enrollments WHERE student=?) AND quiz_id NOT IN (SELECT quiz_id FROM quiz_submissions WHERE student=?)",
                     (self.username, self.username))
            quiz_dates = [datetime.strptime(row[0], "%Y-%m-%d").date() for row in c.fetchall()]
            dates = assignment_dates + quiz_dates
            self.calendar_cache[self.username] = dates
            conn.close()
        for date in dates:
            format = QTextCharFormat()
            format.setBackground(Qt.yellow)
            self.calendar.setDateTextFormat(date, format)

    def show_calendar_events(self, date):
        date_str = date.toString("yyyy-MM-dd")
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT course_id, description FROM assignments WHERE student=? AND due_date=?", 
                 (self.username, date_str))
        assignments = c.fetchall()
        c.execute("SELECT course_id, title FROM quizzes WHERE course_id IN (SELECT course_id FROM enrollments WHERE student=?) AND due_date=? AND quiz_id NOT IN (SELECT quiz_id FROM quiz_submissions WHERE student=?)",
                 (self.username, date_str, self.username))
        quizzes = c.fetchall()
        events = []
        for course_id, desc in assignments:
            c.execute("SELECT course_name FROM courses WHERE course_id=?", (course_id,))
            course_name = c.fetchone()[0]
            events.append(f"{course_name}: {desc}")
        for course_id, title in quizzes:
            c.execute("SELECT course_name FROM courses WHERE course_id=?", (course_id,))
            course_name = c.fetchone()[0]
            events.append(f"{course_name}: {title}")
        conn.close()
        self.calendar_events.setText("\n".join(events) if events else "No events")

    def show_grade_stats(self):
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT grade FROM assignments WHERE student=? AND grade IS NOT NULL", (self.username,))
        assignment_grades = c.fetchall()
        c.execute("SELECT score FROM quiz_submissions WHERE student=?", (self.username,))
        quiz_scores = c.fetchall()
        conn.close()
        grades = [int(g[0]) for g in assignment_grades if g[0].isdigit()] + [s[0] * 100 for s in quiz_scores]
        if not grades:
            QMessageBox.information(self, "Stats", "No grades yet.", QMessageBox.Ok, QMessageBox.Ok)
            return
        avg_grade = sum(grades) / len(grades)
        stats = f"Grades: {len(grades)}\nAvg: {avg_grade:.1f}"
        QMessageBox.information(self, "Stats", stats, QMessageBox.Ok, QMessageBox.Ok)

    def enroll_in_course(self):
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT course_id, course_name FROM courses WHERE course_id NOT IN (SELECT course_id FROM enrollments WHERE student=?)", 
                 (self.username,))
        available_courses = c.fetchall()
        if not available_courses:
            QMessageBox.information(self, "Info", "No courses available.")
            conn.close()
            return
        course_names = [f"{course[1]}" for course in available_courses]
        course_name, ok = QInputDialog.getItem(self, "Enroll", "Select Course:", course_names, 0, False)
        if ok and course_name:
            course_id = next(c[0] for c in available_courses if c[1] == course_name)
            c.execute("INSERT INTO enrollments (course_id, student) VALUES (?, ?)", (course_id, self.username))
            c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)", (self.username, f"Enrolled in {course_name}"))
            self.award_points(self.username, 10, f"Enrolled in {course_name}")
            conn.commit()
            self.refresh_course_list()
            self.refresh_notif_list()
            self.refresh_progress_list()
            self.update_calendar()
            if self.success_sound:
                self.success_sound.play()
            QMessageBox.information(self, "Success", "Enrolled!")
        conn.close()

    def submit_assignment(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT def_id, title, due_date FROM assignment_definitions WHERE course_id=?", (course_id,))
        assignments = c.fetchall()
        if not assignments:
            QMessageBox.information(self, "Info", "No assignments.")
            conn.close()
            return
        assignment_titles = [f"{a[1]}" for a in assignments]
        assignment_title, ok = QInputDialog.getItem(self, "Submit", "Select Assignment:", assignment_titles, 0, False)
        if ok and assignment_title:
            def_id = next(a[0] for a in assignments if a[1] == assignment_title)
            file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
            if file_path:
                due_date = next(a[2] for a in assignments if a[0] == def_id)
                new_path = os.path.join("assignments", f"{self.username}_{course_id}_{def_id}_{os.path.basename(file_path)}")
                shutil.copy(file_path, new_path)
                c.execute("INSERT INTO assignments (course_id, student, file_path, due_date, description) VALUES (?, ?, ?, ?, ?)",
                         (course_id, self.username, new_path, due_date, assignment_title))
                c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)", (self.username, f"Submitted {assignment_title}"))
                self.award_points(self.username, 20, f"Submitted assignment '{assignment_title}'")
                conn.commit()
                conn.close()
                self.refresh_grade_list()
                self.refresh_progress_list()
                self.refresh_notif_list()
                self.refresh_leaderboard()
                self.update_calendar()
                if self.success_sound:
                    self.success_sound.play()
                QMessageBox.information(self, "Success", "Submitted!")

    def take_quiz(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT quiz_id, title, question, options, correct_answer FROM quizzes WHERE course_id=? AND quiz_id NOT IN (SELECT quiz_id FROM quiz_submissions WHERE student=?)",
                 (course_id, self.username))
        quizzes = c.fetchall()
        if not quizzes:
            QMessageBox.information(self, "Info", "No quizzes.")
            conn.close()
            return
        quiz_titles = [q[1] for q in quizzes]
        quiz_title, ok = QInputDialog.getItem(self, "Quiz", "Select Quiz:", quiz_titles, 0, False)
        if ok and quiz_title:
            quiz = next(q for q in quizzes if q[1] == quiz_title)
            quiz_id, _, question, options_str, correct_answer = quiz
            options = options_str.split("|")
            answer, ok = QInputDialog.getItem(self, f"{quiz_title}", question, options, 0, False)
            if ok and answer:
                score = 1 if options.index(answer) == correct_answer else 0
                c.execute("INSERT INTO quiz_submissions (quiz_id, student, answer, score) VALUES (?, ?, ?, ?)",
                         (quiz_id, self.username, options.index(answer), score))
                c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)", (self.username, f"Quiz '{quiz_title}': {score}/1"))
                self.award_points(self.username, 15, f"Completed quiz '{quiz_title}'")
                conn.commit()
                conn.close()
                self.refresh_grade_list()
                self.refresh_progress_list()
                self.refresh_notif_list()
                self.refresh_leaderboard()
                self.update_calendar()
                if self.success_sound:
                    self.success_sound.play()
                QMessageBox.information(self, "Success", f"Score: {score}/1")

    def send_message(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT teacher FROM courses WHERE course_id=?", (course_id,))
        teacher = c.fetchone()[0]
        message, ok = QInputDialog.getText(self, "Message", f"To {teacher}:")
        if ok and message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO messages (sender, receiver, course_id, message, timestamp) VALUES (?, ?, ?, ?, ?)",
                     (self.username, teacher, course_id, message, timestamp))
            c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)", (teacher, f"New message from {self.username}"))
            conn.commit()
            conn.close()
            self.refresh_message_list()
            if self.success_sound:
                self.success_sound.play()
            QMessageBox.information(self, "Success", "Sent!")

    # Teacher Dashboard
    def teacher_dashboard(self):
        courses_tab = QWidget()
        courses_layout = QVBoxLayout()
        courses_layout.addWidget(QLabel("Courses", font=QFont("Arial", 16, QFont.Bold)))
        self.course_list = QListWidget()
        self.course_list.setFont(QFont("Arial", 12))
        self.refresh_course_list_teacher()
        courses_layout.addWidget(self.course_list)
        btn_layout = QHBoxLayout()
        add_course_button = QPushButton("Add Course", self)
        add_course_button.setFont(QFont("Arial", 14, QFont.Bold))
        add_course_button.clicked.connect(self.add_course)
        btn_layout.addWidget(add_course_button)
        edit_course_button = QPushButton("Edit", self)
        edit_course_button.setFont(QFont("Arial", 14, QFont.Bold))
        edit_course_button.clicked.connect(self.edit_course)
        btn_layout.addWidget(edit_course_button)
        add_assignment_button = QPushButton("Add Assign", self)
        add_assignment_button.setFont(QFont("Arial", 14, QFont.Bold))
        add_assignment_button.clicked.connect(self.create_assignment)
        btn_layout.addWidget(add_assignment_button)
        edit_assignment_button = QPushButton("Edit Assign", self)
        edit_assignment_button.setFont(QFont("Arial", 14, QFont.Bold))
        edit_assignment_button.clicked.connect(self.edit_assignment)
        btn_layout.addWidget(edit_assignment_button)
        add_quiz_button = QPushButton("Add Quiz", self)
        add_quiz_button.setFont(QFont("Arial", 14, QFont.Bold))
        add_quiz_button.clicked.connect(self.create_quiz)
        btn_layout.addWidget(add_quiz_button)
        courses_layout.addLayout(btn_layout)
        courses_tab.setLayout(courses_layout)
        self.tabs.addTab(courses_tab, "Courses")

        assignments_tab = QWidget()
        assignments_layout = QVBoxLayout()
        assignments_layout.addWidget(QLabel("Assignments", font=QFont("Arial", 16, QFont.Bold)))
        self.assignment_list = QListWidget()
        self.assignment_list.setFont(QFont("Arial", 12))
        self.refresh_assignment_list()
        assignments_layout.addWidget(self.assignment_list)
        btn_layout = QHBoxLayout()
        view_button = QPushButton("Refresh", self)
        view_button.setFont(QFont("Arial", 14, QFont.Bold))
        view_button.clicked.connect(self.refresh_assignment_list)
        btn_layout.addWidget(view_button)
        grade_button = QPushButton("Grade", self)
        grade_button.setFont(QFont("Arial", 14, QFont.Bold))
        grade_button.clicked.connect(self.grade_assignment)
        btn_layout.addWidget(grade_button)
        preview_button = QPushButton("Preview", self)
        preview_button.setFont(QFont("Arial", 14, QFont.Bold))
        preview_button.clicked.connect(self.preview_assignment)
        btn_layout.addWidget(preview_button)
        download_button = QPushButton("Download", self)
        download_button.setFont(QFont("Arial", 14, QFont.Bold))
        download_button.clicked.connect(self.download_assignment)
        btn_layout.addWidget(download_button)
        assignments_layout.addLayout(btn_layout)
        assignments_tab.setLayout(assignments_layout)
        self.tabs.addTab(assignments_tab, "Assigns")

        messages_tab = QWidget()
        messages_layout = QVBoxLayout()
        messages_layout.addWidget(QLabel("Messages", font=QFont("Arial", 16, QFont.Bold)))
        self.message_list = QListWidget()
        self.message_list.setFont(QFont("Arial", 12))
        self.refresh_message_list()
        messages_layout.addWidget(self.message_list)
        messages_tab.setLayout(messages_layout)
        self.tabs.addTab(messages_tab, "Msgs")

        chat_tab = QWidget()
        chat_layout = QVBoxLayout()
        chat_layout.addWidget(QLabel("Chat", font=QFont("Arial", 16, QFont.Bold)))
        self.chat_list = QListWidget()
        self.chat_list.setFont(QFont("Arial", 12))
        self.refresh_chat_list()
        chat_layout.addWidget(self.chat_list)
        self.chat_input = QTextEdit()
        self.chat_input.setFont(QFont("Arial", 12))
        self.chat_input.setFixedHeight(50)
        chat_layout.addWidget(self.chat_input)
        send_chat_button = QPushButton("Send", self)
        send_chat_button.setFont(QFont("Arial", 14, QFont.Bold))
        send_chat_button.clicked.connect(self.send_chat_message)
        chat_layout.addWidget(send_chat_button)
        chat_tab.setLayout(chat_layout)
        self.tabs.addTab(chat_tab, "Chat")

    def refresh_course_list_teacher(self):
        self.course_list.clear()
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT course_id, course_name FROM courses WHERE teacher=?", (self.username,))
        courses = c.fetchall()
        for course_id, course_name in courses:
            self.course_list.addItem(f"{course_name} (ID: {course_id})")
        conn.close()

    def refresh_assignment_list(self):
        self.assignment_list.clear()
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT assignment_id, student, file_path, grade FROM assignments WHERE course_id IN (SELECT course_id FROM courses WHERE teacher=?)", 
                 (self.username,))
        self.assignments = c.fetchall()
        for assignment_id, student, file_path, grade in self.assignments:
            self.assignment_list.addItem(f"{student}: {os.path.basename(file_path)} - {grade or 'Ungraded'}")
        conn.close()

    def add_course(self):
        course_name, ok1 = QInputDialog.getText(self, "Add Course", "Course Name:")
        if ok1 and course_name:
            conn = sqlite3.connect("resources/school_lms.db")
            c = conn.cursor()
            c.execute("INSERT INTO courses (course_name, teacher) VALUES (?, ?)", (course_name, self.username))
            conn.commit()
            self.refresh_course_list_teacher()
            conn.close()
            if self.success_sound:
                self.success_sound.play()
            QMessageBox.information(self, "Success", "Course added!")

    def edit_course(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        description, ok = QInputDialog.getText(self, "Edit", "New Description:")
        if ok:
            conn = sqlite3.connect("resources/school_lms.db")
            c = conn.cursor()
            c.execute("UPDATE courses SET description=? WHERE course_id=?", (description, course_id))
            conn.commit()
            conn.close()
            self.refresh_course_list_teacher()
            if self.success_sound:
                self.success_sound.play()
            QMessageBox.information(self, "Success", "Updated!")

    def create_assignment(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        title, ok1 = QInputDialog.getText(self, "Add Assign", "Title:")
        due_date, ok2 = QInputDialog.getText(self, "Add Assign", "Due (YYYY-MM-DD):")
        if ok1 and ok2 and title and due_date:
            if not self.validate_due_date(due_date):
                QMessageBox.warning(self, "Error", "Invalid date!")
                return
            conn = sqlite3.connect("resources/school_lms.db")
            c = conn.cursor()
            c.execute("INSERT INTO assignment_definitions (course_id, title, due_date) VALUES (?, ?, ?)",
                     (course_id, title, due_date))
            c.execute("SELECT student FROM enrollments WHERE course_id=?", (course_id,))
            students = c.fetchall()
            for student_tuple in students:
                student = student_tuple[0]
                c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)",
                         (student, f"New assignment '{title}' due {due_date}"))
            conn.commit()
            conn.close()
            if self.success_sound:
                self.success_sound.play()
            QMessageBox.information(self, "Success", "Assignment added!")

    def edit_assignment(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT def_id, title, due_date FROM assignment_definitions WHERE course_id=?", (course_id,))
        assignments = c.fetchall()
        if not assignments:
            QMessageBox.information(self, "Info", "No assignments.")
            conn.close()
            return
        assignment_titles = [f"{a[1]}" for a in assignments]
        assignment_title, ok = QInputDialog.getItem(self, "Edit Assign", "Select:", assignment_titles, 0, False)
        if ok and assignment_title:
            def_id = next(a[0] for a in assignments if a[1] == assignment_title)
            new_title, ok1 = QInputDialog.getText(self, "Edit", "New Title:", text=assignment_title)
            new_due_date, ok2 = QInputDialog.getText(self, "Edit", "New Due (YYYY-MM-DD):", text=assignments[assignment_titles.index(assignment_title)][2])
            if ok1 and ok2:
                if not self.validate_due_date(new_due_date):
                    QMessageBox.warning(self, "Error", "Invalid date!")
                    conn.close()
                    return
                c.execute("UPDATE assignment_definitions SET title=?, due_date=? WHERE def_id=?", 
                         (new_title, new_due_date, def_id))
                c.execute("SELECT student FROM enrollments WHERE course_id=?", (course_id,))
                students = c.fetchall()
                for student_tuple in students:
                    student = student_tuple[0]
                    c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)",
                             (student, f"Assignment '{new_title}' updated: due {new_due_date}"))
                conn.commit()
                conn.close()
                if self.success_sound:
                    self.success_sound.play()
                QMessageBox.information(self, "Success", "Updated!")

    def create_quiz(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        title, ok1 = QInputDialog.getText(self, "Add Quiz", "Title:")
        due_date, ok2 = QInputDialog.getText(self, "Add Quiz", "Due (YYYY-MM-DD):")
        question, ok3 = QInputDialog.getText(self, "Add Quiz", "Question:")
        options_str, ok4 = QInputDialog.getText(self, "Add Quiz", "Options (A|B|C|D):")
        correct_answer, ok5 = QInputDialog.getInt(self, "Add Quiz", "Correct (0-3):", 0, 0, 3)
        if ok1 and ok2 and ok3 and ok4 and ok5 and title and due_date and question and options_str:
            if not self.validate_due_date(due_date):
                QMessageBox.warning(self, "Error", "Invalid date!")
                return
            options = options_str.split("|")
            if len(options) != 4:
                QMessageBox.warning(self, "Error", "Need 4 options!")
                return
            conn = sqlite3.connect("resources/school_lms.db")
            c = conn.cursor()
            c.execute("INSERT INTO quizzes (course_id, title, due_date, question, options, correct_answer) VALUES (?, ?, ?, ?, ?, ?)",
                     (course_id, title, due_date, question, options_str, correct_answer))
            c.execute("SELECT student FROM enrollments WHERE course_id=?", (course_id,))
            students = c.fetchall()
            for student_tuple in students:
                student = student_tuple[0]
                c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)",
                         (student, f"New quiz '{title}' due {due_date}"))
            conn.commit()
            conn.close()
            if self.success_sound:
                self.success_sound.play()
            QMessageBox.information(self, "Success", "Quiz added!")

    def grade_assignment(self):
        selected = self.assignment_list.currentItem()
        if not selected or not hasattr(self, 'assignments'):
            QMessageBox.warning(self, "Error", "Select an assignment!")
            return
        index = self.assignment_list.row(selected)
        assignment_id = self.assignments[index][0]
        grade, ok1 = QInputDialog.getText(self, "Grade", "Grade (e.g., A, 100):")
        if ok1 and grade:
            conn = sqlite3.connect("resources/school_lms.db")
            c = conn.cursor()
            c.execute("UPDATE assignments SET grade=? WHERE assignment_id=?", (grade, assignment_id))
            c.execute("SELECT student FROM assignments WHERE assignment_id=?", (assignment_id,))
            student = c.fetchone()[0]
            c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)",
                     (student, f"Assignment graded: {grade}"))
            conn.commit()
            conn.close()
            self.refresh_assignment_list()
            if self.success_sound:
                self.success_sound.play()
            QMessageBox.information(self, "Success", "Graded!")

    def preview_assignment(self):
        selected = self.assignment_list.currentItem()
        if not selected or not hasattr(self, 'assignments'):
            QMessageBox.warning(self, "Error", "Select an assignment!")
            return
        index = self.assignment_list.row(selected)
        file_path = self.assignments[index][2]
        if file_path.endswith((".pdf", ".txt")):
            try:
                with open(file_path, "r" if file_path.endswith(".txt") else "rb") as f:
                    content = f.read().decode("utf-8") if file_path.endswith(".txt") else "PDF Preview"
                preview = QTextEdit()
                preview.setFont(QFont("Arial", 12))
                preview.setReadOnly(True)
                preview.setText(content)
                dialog = QMessageBox(self)
                dialog.setWindowTitle("Preview")
                dialog.setText(os.path.basename(file_path))
                dialog.layout().addWidget(preview)
                dialog.exec_()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Preview failed: {str(e)}")
        elif file_path.endswith((".png", ".jpg", ".jpeg")):
            try:
                img = Image.open(file_path)
                img.thumbnail((400, 400))
                byte_arr = io.BytesIO()
                img.save(byte_arr, format=img.format)
                pixmap = QPixmap()
                pixmap.loadFromData(byte_arr.getvalue())
                dialog = QMessageBox(self)
                dialog.setWindowTitle("Preview")
                dialog.setText(os.path.basename(file_path))
                label = QLabel()
                label.setPixmap(pixmap)
                dialog.layout().addWidget(label)
                dialog.exec_()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Preview failed: {str(e)}")
        else:
            QMessageBox.information(self, "Preview", "Only PDF, TXT, PNG, JPG supported.")

    def download_assignment(self):
        selected = self.assignment_list.currentItem()
        if not selected or not hasattr(self, 'assignments'):
            QMessageBox.warning(self, "Error", "Select an assignment!")
            return
        index = self.assignment_list.row(selected)
        file_path = self.assignments[index][2]
        dest_path, _ = QFileDialog.getSaveFileName(self, "Save File", os.path.basename(file_path))
        if dest_path:
            shutil.copy(file_path, dest_path)
            if self.success_sound:
                self.success_sound.play()
            QMessageBox.information(self, "Success", "Downloaded!")

    # Admin Dashboard
    def admin_dashboard(self):
        users_tab = QWidget()
        users_layout = QVBoxLayout()
        users_layout.addWidget(QLabel("Users", font=QFont("Arial", 16, QFont.Bold)))
        self.user_list = QListWidget()
        self.user_list.setFont(QFont("Arial", 12))
        self.refresh_user_list()
        users_layout.addWidget(self.user_list)
        btn_layout = QHBoxLayout()
        add_user_button = QPushButton("Add User", self)
        add_user_button.setFont(QFont("Arial", 14, QFont.Bold))
        add_user_button.clicked.connect(self.add_user)
        btn_layout.addWidget(add_user_button)
        remove_user_button = QPushButton("Remove", self)
        remove_user_button.setFont(QFont("Arial", 14, QFont.Bold))
        remove_user_button.clicked.connect(self.remove_user)
        btn_layout.addWidget(remove_user_button)
        users_layout.addLayout(btn_layout)
        users_tab.setLayout(users_layout)
        self.tabs.addTab(users_tab, "Users")

    def refresh_user_list(self):
        self.user_list.clear()
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT username, role FROM users")
        users = c.fetchall()
        for user in users:
            self.user_list.addItem(f"{user[0]} ({user[1]})")
        conn.close()

    def add_user(self):
        from database import hash_password
        username, ok1 = QInputDialog.getText(self, "Add User", "Username:")
        password, ok2 = QInputDialog.getText(self, "Add User", "Password:", QLineEdit.Password)
        role, ok3 = QInputDialog.getText(self, "Add User", "Role (student/teacher/admin):")
        if ok1 and ok2 and ok3 and username and password and role:
            conn = sqlite3.connect("resources/school_lms.db")
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                     (username, hash_password(password), role))
            conn.commit()
            conn.close()
            self.refresh_user_list()
            if self.success_sound:
                self.success_sound.play()
            QMessageBox.information(self, "Success", "User added!")

    def remove_user(self):
        selected = self.user_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a user!")
            return
        username = selected.text().split(" (")[0]
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit()
        conn.close()
        self.refresh_user_list()
        if self.success_sound:
            self.success_sound.play()
        QMessageBox.information(self, "Success", "User removed!")

    def logout(self):
        from login import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()
