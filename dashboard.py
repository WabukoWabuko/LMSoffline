# dashboard.py
import sqlite3
import os
import shutil
import re
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QListWidget, QFileDialog, QInputDialog, QMessageBox, 
                             QTabWidget, QStatusBar, QProgressBar, QTextEdit, QApplication,
                             QListWidgetItem, QCalendarWidget, QCheckBox, QDialog, QTextBrowser)
from PyQt5.QtGui import QIcon, QFont, QPixmap, QTextCharFormat
from PyQt5.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve
from PIL import Image
import io

class TutorialDialog(QDialog):
    def __init__(self, role, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Springfield LMS!")
        self.setGeometry(200, 200, 400, 300)
        self.setModal(True)  # Makes it a modal dialog, closable by clicking outside

        layout = QVBoxLayout()
        self.text_browser = QTextBrowser()
        if role == "student":
            self.text_browser.setHtml("""
                <h2>Welcome, Student!</h2>
                <p>Here's how to get started:</p>
                <ul>
                    <li><b>Courses</b>: Enroll in courses and submit assignments or take quizzes.</li>
                    <li><b>Grades</b>: Check your scores and teacher comments.</li>
                    <li><b>Progress</b>: Track your completion with progress bars and earn points!</li>
                    <li><b>Chat</b>: Message your teachers in real-time.</li>
                    <li><b>Calendar</b>: View due dates at a glance.</li>
                </ul>
                <p>Complete tasks to earn badges like 'Star Student'!</p>
            """)
        elif role == "teacher":
            self.text_browser.setHtml("""
                <h2>Welcome, Teacher!</h2>
                <p>Here's how to get started:</p>
                <ul>
                    <li><b>Courses</b>: Create courses, assignments, and quizzes.</li>
                    <li><b>Assignments</b>: Grade submissions and add comments.</li>
                    <li><b>Chat</b>: Communicate with students in real-time.</li>
                </ul>
                <p>Support your students’ success!</p>
            """)
        layout.addWidget(self.text_browser)

        ok_button = QPushButton("OK", self)
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)

        self.setLayout(layout)

class DashboardWindow(QMainWindow):
    def __init__(self, role, username):
        super().__init__()
        self.role = role
        self.username = username
        self.dark_mode = False
        self.calendar_cache = {}
        self.setWindowTitle(f"School LMS - {role.capitalize()} Dashboard")
        self.setGeometry(150, 150, 800, 600)
        self.update_stylesheet()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout()

        welcome_label = QLabel(f"Welcome, {self.username} ({role.capitalize()})!")
        welcome_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.layout.addWidget(welcome_label)
        self.tabs = QTabWidget()
        self.setup_dashboard()
        self.layout.addWidget(self.tabs)

        mode_toggle = QCheckBox("Dark Mode", self)
        mode_toggle.stateChanged.connect(self.toggle_dark_mode)
        self.layout.addWidget(mode_toggle)

        logout_button = QPushButton("Logout", self)
        logout_button.clicked.connect(self.logout)
        self.layout.addWidget(logout_button)

        central_widget.setLayout(self.layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_due_dates)
        self.timer.start(60000)

        self.animate_tabs()
        self.show_tutorial()

    def update_stylesheet(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow { background-color: #2d2d2d; color: #ffffff; }
                QTabWidget::pane { border: 1px solid #555; }
                QTabBar::tab { background: #424242; padding: 8px; color: #ffffff; }
                QTabBar::tab:selected { background: #1976d2; }
                QPushButton { background-color: #1976d2; color: white; padding: 5px; border-radius: 3px; }
                QPushButton:hover { background-color: #1565c0; }
                QLabel { font-family: Arial; color: #ffffff; }
                QListWidget { background-color: #333; color: #ffffff; }
                QListWidget::item[unread="true"] { background-color: #ff8f00; color: #ffffff; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow { background-color: #ffffff; color: #000000; }
                QTabWidget::pane { border: 1px solid #ccc; }
                QTabBar::tab { background: #e0e0e0; padding: 8px; }
                QTabBar::tab:selected { background: #90caf9; }
                QPushButton { background-color: #4CAF50; color: white; padding: 5px; border-radius: 3px; }
                QPushButton:hover { background-color: #45a049; }
                QLabel { font-family: Arial; }
                QListWidget { background-color: #ffffff; color: #000000; }
                QListWidget::item[unread="true"] { background-color: #fff3e0; }
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
        tutorial.exec_()  # Show as a modal dialog

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
                     (student, "Congratulations! You've earned the 'Star Student' badge!"))
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
                msg = f"Reminder: '{desc}' due on {due_date} (Course ID: {course_id})"
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
        courses_tab = QWidget()
        courses_layout = QVBoxLayout()
        courses_layout.addWidget(QLabel("Enrolled Courses:"))
        self.course_list = QListWidget()
        self.refresh_course_list()
        courses_layout.addWidget(self.course_list)

        enroll_button = QPushButton("Enroll in Course", self)
        enroll_button.setIcon(QIcon.fromTheme("list-add"))
        enroll_button.clicked.connect(self.enroll_in_course)
        courses_layout.addWidget(enroll_button)
        submit_button = QPushButton("Submit Assignment", self)
        submit_button.setIcon(QIcon.fromTheme("document-save"))
        submit_button.clicked.connect(self.submit_assignment)
        courses_layout.addWidget(submit_button)
        take_quiz_button = QPushButton("Take Quiz", self)
        take_quiz_button.setIcon(QIcon.fromTheme("question"))
        take_quiz_button.clicked.connect(self.take_quiz)
        courses_layout.addWidget(take_quiz_button)
        courses_tab.setLayout(courses_layout)
        self.tabs.addTab(courses_tab, "Courses")

        grades_tab = QWidget()
        grades_layout = QVBoxLayout()
        grades_layout.addWidget(QLabel("Your Grades:"))
        self.grade_list = QListWidget()
        self.refresh_grade_list()
        grades_layout.addWidget(self.grade_list)
        stats_button = QPushButton("View Grade Statistics", self)
        stats_button.clicked.connect(self.show_grade_stats)
        grades_layout.addWidget(stats_button)
        grades_tab.setLayout(grades_layout)
        self.tabs.addTab(grades_tab, "Grades")

        progress_tab = QWidget()
        progress_layout = QVBoxLayout()
        progress_layout.addWidget(QLabel("Course Progress:"))
        self.progress_list = QListWidget()
        self.refresh_progress_list()
        progress_layout.addWidget(self.progress_list)
        points_label = QLabel(f"Total Points: {self.get_total_points(self.username)}")
        progress_layout.addWidget(points_label)
        badges_label = QLabel("Badges: " + ", ".join(self.get_badges(self.username)) or "No badges yet")
        progress_layout.addWidget(badges_label)
        progress_tab.setLayout(progress_layout)
        self.tabs.addTab(progress_tab, "Progress")

        notif_tab = QWidget()
        notif_layout = QVBoxLayout()
        notif_layout.addWidget(QLabel("Notifications:"))
        self.notif_list = QListWidget()
        self.refresh_notif_list()
        notif_layout.addWidget(self.notif_list)
        mark_read_button = QPushButton("Mark Selected as Read", self)
        mark_read_button.clicked.connect(self.mark_notif_read)
        notif_layout.addWidget(mark_read_button)
        notif_tab.setLayout(notif_layout)
        self.tabs.addTab(notif_tab, "Notifications")

        messages_tab = QWidget()
        messages_layout = QVBoxLayout()
        messages_layout.addWidget(QLabel("Messages:"))
        self.message_list = QListWidget()
        self.refresh_message_list()
        messages_layout.addWidget(self.message_list)
        send_message_button = QPushButton("Send Message to Teacher", self)
        send_message_button.clicked.connect(self.send_message)
        messages_layout.addWidget(send_message_button)
        messages_tab.setLayout(messages_layout)
        self.tabs.addTab(messages_tab, "Messages")

        chat_tab = QWidget()
        chat_layout = QVBoxLayout()
        chat_layout.addWidget(QLabel("Live Chat:"))
        self.chat_list = QListWidget()
        self.refresh_chat_list()
        chat_layout.addWidget(self.chat_list)
        self.chat_input = QTextEdit()
        self.chat_input.setFixedHeight(50)
        chat_layout.addWidget(self.chat_input)
        send_chat_button = QPushButton("Send", self)
        send_chat_button.clicked.connect(self.send_chat_message)
        chat_layout.addWidget(send_chat_button)
        chat_tab.setLayout(chat_layout)
        self.tabs.addTab(chat_tab, "Chat")

        calendar_tab = QWidget()
        calendar_layout = QVBoxLayout()
        calendar_layout.addWidget(QLabel("Due Dates Calendar:"))
        self.calendar = QCalendarWidget()
        self.calendar.clicked.connect(self.show_calendar_events)
        self.update_calendar()
        calendar_layout.addWidget(self.calendar)
        self.calendar_events = QLabel("Select a date to view events.")
        calendar_layout.addWidget(self.calendar_events)
        calendar_tab.setLayout(calendar_layout)
        self.tabs.addTab(calendar_tab, "Calendar")

    def refresh_course_list(self):
        self.course_list.clear()
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT c.course_id, c.course_name, c.description FROM courses c JOIN enrollments e ON c.course_id = e.course_id WHERE e.student=?", 
                 (self.username,))
        courses = c.fetchall()
        for course_id, course_name, desc in courses:
            self.course_list.addItem(f"{course_name} (ID: {course_id}) - {desc or 'No description'}")
        conn.close()

    def refresh_grade_list(self):
        self.grade_list.clear()
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT course_id, file_path, grade, due_date, description, comment FROM assignments WHERE student=?", 
                 (self.username,))
        assignments = c.fetchall()
        c.execute("SELECT q.course_id, q.title, qs.score, q.due_date FROM quiz_submissions qs JOIN quizzes q ON qs.quiz_id = q.quiz_id WHERE qs.student=?", 
                 (self.username,))
        quizzes = c.fetchall()
        for course_id, file_path, grade, due_date, description, comment in assignments:
            c.execute("SELECT course_name FROM courses WHERE course_id=?", (course_id,))
            course_name = c.fetchone()[0]
            comment_text = f" - Comment: {comment}" if comment else ""
            self.grade_list.addItem(f"{course_name}: {os.path.basename(file_path)} - Grade: {grade or 'Not graded'} - Due: {due_date or 'N/A'}{comment_text}")
        for course_id, title, score, due_date in quizzes:
            c.execute("SELECT course_name FROM courses WHERE course_id=?", (course_id,))
            course_name = c.fetchone()[0]
            self.grade_list.addItem(f"{course_name}: Quiz '{title}' - Score: {score}/1 - Due: {due_date}")
        conn.close()

    def refresh_progress_list(self):
        self.progress_list.clear()
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT course_id FROM enrollments WHERE student=?", (self.username,))
        courses = c.fetchall()
        for course_id_tuple in courses:
            course_id = course_id_tuple[0]
            c.execute("SELECT course_name FROM courses WHERE course_id=?", (course_id,))
            course_name = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM assignment_definitions WHERE course_id=?", (course_id,))
            total_assignments = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM assignments WHERE course_id=? AND student=?", 
                     (course_id, self.username))
            submitted_assignments = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM quizzes WHERE course_id=?", (course_id,))
            total_quizzes = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM quiz_submissions WHERE quiz_id IN (SELECT quiz_id FROM quizzes WHERE course_id=?) AND student=?", 
                     (course_id, self.username))
            submitted_quizzes = c.fetchone()[0]
            total = total_assignments + total_quizzes
            submitted = submitted_assignments + submitted_quizzes
            progress_bar = QProgressBar()
            progress_bar.setMaximum(total if total > 0 else 1)
            progress_bar.setValue(submitted)
            progress_bar.setFormat(f"{course_name}: {submitted}/{total} ({submitted/total*100:.0f}%)")
            item = QListWidgetItem()
            self.progress_list.addItem(item)
            self.progress_list.setItemWidget(item, progress_bar)
        conn.close()

    def get_badges(self, student):
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT badge_name FROM badges WHERE student=?", (student,))
        badges = [row[0] for row in c.fetchall()]
        conn.close()
        return badges

    def refresh_notif_list(self):
        self.notif_list.clear()
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT notif_id, message, is_read FROM notifications WHERE username=?", (self.username,))
        notifications = c.fetchall()
        unread_count = sum(1 for _, _, is_read in notifications if is_read == 0)
        for notif_id, message, is_read in notifications:
            item = QListWidgetItem(f"[{ 'Unread' if is_read == 0 else 'Read' }] {message} (ID: {notif_id})")
            if is_read == 0:
                item.setData(Qt.UserRole, "unread")
            self.notif_list.addItem(item)
        conn.close()
        self.status_bar.showMessage(f"{unread_count} unread notifications")

    def mark_notif_read(self):
        selected = self.notif_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a notification first!")
            return
        notif_id = int(selected.text().split("ID: ")[1].rstrip(")"))
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
        c.execute("SELECT msg_id, sender, course_id, message, timestamp FROM messages WHERE receiver=?", 
                 (self.username,))
        messages = c.fetchall()
        for msg_id, sender, course_id, message, timestamp in messages:
            c.execute("SELECT course_name FROM courses WHERE course_id=?", (course_id,))
            course_name = c.fetchone()[0] if course_id else "General"
            self.message_list.addItem(f"[{timestamp}] From {sender} ({course_name}): {message} (ID: {msg_id})")
        if self.role == "teacher":
            c.execute("SELECT msg_id, receiver, course_id, message, timestamp FROM messages WHERE sender=?", 
                     (self.username,))
            sent_messages = c.fetchall()
            for msg_id, receiver, course_id, message, timestamp in sent_messages:
                c.execute("SELECT course_name FROM courses WHERE course_id=?", (course_id,))
                course_name = c.fetchone()[0] if course_id else "General"
                self.message_list.addItem(f"[{timestamp}] To {receiver} ({course_name}): {message} (ID: {msg_id})")
        conn.close()

    def refresh_chat_list(self):
        self.chat_list.clear()
        selected = self.course_list.currentItem()
        if not selected:
            self.chat_list.addItem("Select a course to view chat.")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT sender, message, timestamp FROM chat_messages WHERE course_id=? ORDER BY timestamp", 
                 (course_id,))
        messages = c.fetchall()
        for sender, message, timestamp in messages:
            self.chat_list.addItem(f"[{timestamp}] {sender}: {message}")
        conn.close()
        self.chat_list.scrollToBottom()

    def send_chat_message(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course first!")
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
            events.append(f"{course_name}: Assignment '{desc}'")
        for course_id, title in quizzes:
            c.execute("SELECT course_name FROM courses WHERE course_id=?", (course_id,))
            course_name = c.fetchone()[0]
            events.append(f"{course_name}: Quiz '{title}'")
        conn.close()
        self.calendar_events.setText(f"Events on {date_str}:\n" + "\n".join(events) if events else "No events on this date.")

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
            QMessageBox.information(self, "Grade Statistics", "No grades available yet.")
            return
        avg_grade = sum(grades) / len(grades)
        stats = f"Total Graded: {len(grades)}\nAverage Score: {avg_grade:.1f}"
        QMessageBox.information(self, "Grade Statistics", stats)

    def enroll_in_course(self):
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT course_id, course_name FROM courses WHERE course_id NOT IN (SELECT course_id FROM enrollments WHERE student=?)", 
                 (self.username,))
        available_courses = c.fetchall()
        if not available_courses:
            QMessageBox.information(self, "Info", "No courses available to enroll in.")
            conn.close()
            return
        course_names = [f"{course[1]} (ID: {course[0]})" for course in available_courses]
        course_name, ok = QInputDialog.getItem(self, "Enroll", "Select a course:", course_names, 0, False)
        if ok and course_name:
            course_id = int(course_name.split("ID: ")[1].rstrip(")"))
            c.execute("INSERT INTO enrollments (course_id, student) VALUES (?, ?)", 
                     (course_id, self.username))
            c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)",
                     (self.username, f"Enrolled in {course_name}"))
            self.award_points(self.username, 10, f"Enrolled in {course_name}")
            conn.commit()
            self.refresh_course_list()
            self.refresh_notif_list()
            self.refresh_progress_list()
            self.update_calendar()
            QMessageBox.information(self, "Success", "Enrolled in course!")
        conn.close()

    def submit_assignment(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course first!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT def_id, title, due_date, description FROM assignment_definitions WHERE course_id=?", 
                 (course_id,))
        assignments = c.fetchall()
        if not assignments:
            QMessageBox.information(self, "Info", "No assignments defined for this course.")
            conn.close()
            return
        assignment_titles = [f"{a[1]} (Due: {a[2]})" for a in assignments]
        assignment_title, ok = QInputDialog.getItem(self, "Submit Assignment", "Select an assignment:", assignment_titles, 0, False)
        if ok and assignment_title:
            def_id = next(a[0] for a in assignments if f"{a[1]} (Due: {a[2]})" == assignment_title)
            file_path, _ = QFileDialog.getOpenFileName(self, "Select Assignment File")
            if file_path:
                due_date = next(a[2] for a in assignments if a[0] == def_id)
                description = next(a[3] for a in assignments if a[0] == def_id)
                new_path = os.path.join("assignments", f"{self.username}_{course_id}_{def_id}_{os.path.basename(file_path)}")
                shutil.copy(file_path, new_path)
                c.execute("INSERT INTO assignments (course_id, student, file_path, due_date, description) VALUES (?, ?, ?, ?, ?)",
                         (course_id, self.username, new_path, due_date, description))
                c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)",
                         (self.username, f"Submitted {assignment_title} for course ID {course_id}"))
                self.award_points(self.username, 20, f"Submitted assignment '{assignment_title}'")
                conn.commit()
                conn.close()
                self.refresh_grade_list()
                self.refresh_progress_list()
                self.refresh_notif_list()
                self.update_calendar()
                QMessageBox.information(self, "Success", "Assignment submitted!")

    def take_quiz(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course first!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT quiz_id, title, question, options, correct_answer FROM quizzes WHERE course_id=? AND quiz_id NOT IN (SELECT quiz_id FROM quiz_submissions WHERE student=?)",
                 (course_id, self.username))
        quizzes = c.fetchall()
        if not quizzes:
            QMessageBox.information(self, "Info", "No quizzes available for this course.")
            conn.close()
            return
        quiz_titles = [q[1] for q in quizzes]
        quiz_title, ok = QInputDialog.getItem(self, "Take Quiz", "Select a quiz:", quiz_titles, 0, False)
        if ok and quiz_title:
            quiz = next(q for q in quizzes if q[1] == quiz_title)
            quiz_id, _, question, options_str, correct_answer = quiz
            options = options_str.split("|")
            answer, ok = QInputDialog.getItem(self, f"Quiz: {quiz_title}", question, options, 0, False)
            if ok and answer:
                score = 1 if options.index(answer) == correct_answer else 0
                c.execute("INSERT INTO quiz_submissions (quiz_id, student, answer, score) VALUES (?, ?, ?, ?)",
                         (quiz_id, self.username, options.index(answer), score))
                c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)",
                         (self.username, f"Completed quiz '{quiz_title}' with score {score}/1"))
                self.award_points(self.username, 15, f"Completed quiz '{quiz_title}'")
                conn.commit()
                conn.close()
                self.refresh_grade_list()
                self.refresh_progress_list()
                self.refresh_notif_list()
                self.update_calendar()
                QMessageBox.information(self, "Success", f"Quiz submitted! Score: {score}/1")

    def send_message(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course first!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT teacher FROM courses WHERE course_id=?", (course_id,))
        teacher = c.fetchone()[0]
        message, ok = QInputDialog.getText(self, "Send Message", f"Message to {teacher}:")
        if ok and message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO messages (sender, receiver, course_id, message, timestamp) VALUES (?, ?, ?, ?, ?)",
                     (self.username, teacher, course_id, message, timestamp))
            c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)",
                     (teacher, f"New message from {self.username} in course ID {course_id}"))
            conn.commit()
            conn.close()
            self.refresh_message_list()
            QMessageBox.information(self, "Success", "Message sent!")

    # Teacher Dashboard
    def teacher_dashboard(self):
        courses_tab = QWidget()
        courses_layout = QVBoxLayout()
        courses_layout.addWidget(QLabel("Your Courses:"))
        self.course_list = QListWidget()
        self.refresh_course_list_teacher()
        courses_layout.addWidget(self.course_list)

        add_course_button = QPushButton("Add New Course", self)
        add_course_button.setIcon(QIcon.fromTheme("list-add"))
        add_course_button.clicked.connect(self.add_course)
        courses_layout.addWidget(add_course_button)
        edit_course_button = QPushButton("Edit Course Description", self)
        edit_course_button.clicked.connect(self.edit_course)
        courses_layout.addWidget(edit_course_button)
        add_assignment_button = QPushButton("Create Assignment", self)
        add_assignment_button.setIcon(QIcon.fromTheme("document-new"))
        add_assignment_button.clicked.connect(self.create_assignment)
        courses_layout.addWidget(add_assignment_button)
        edit_assignment_button = QPushButton("Edit Assignment", self)
        edit_assignment_button.clicked.connect(self.edit_assignment)
        courses_layout.addWidget(edit_assignment_button)
        add_quiz_button = QPushButton("Create Quiz", self)
        add_quiz_button.setIcon(QIcon.fromTheme("question"))
        add_quiz_button.clicked.connect(self.create_quiz)
        courses_layout.addWidget(add_quiz_button)
        courses_tab.setLayout(courses_layout)
        self.tabs.addTab(courses_tab, "Courses")

        assignments_tab = QWidget()
        assignments_layout = QVBoxLayout()
        assignments_layout.addWidget(QLabel("Submitted Assignments:"))
        self.assignment_list = QListWidget()
        self.refresh_assignment_list()
        assignments_layout.addWidget(self.assignment_list)
        view_button = QPushButton("Refresh Assignments", self)
        view_button.clicked.connect(self.refresh_assignment_list)
        grade_button = QPushButton("Grade Selected Assignment", self)
        grade_button.clicked.connect(self.grade_assignment)
        preview_button = QPushButton("Preview Selected Assignment", self)
        preview_button.clicked.connect(self.preview_assignment)
        download_button = QPushButton("Download Selected Assignment", self)
        download_button.clicked.connect(self.download_assignment)
        assignments_layout.addWidget(view_button)
        assignments_layout.addWidget(grade_button)
        assignments_layout.addWidget(preview_button)
        assignments_layout.addWidget(download_button)
        assignments_tab.setLayout(assignments_layout)
        self.tabs.addTab(assignments_tab, "Assignments")

        messages_tab = QWidget()
        messages_layout = QVBoxLayout()
        messages_layout.addWidget(QLabel("Messages:"))
        self.message_list = QListWidget()
        self.refresh_message_list()
        messages_layout.addWidget(self.message_list)
        messages_tab.setLayout(messages_layout)
        self.tabs.addTab(messages_tab, "Messages")

        chat_tab = QWidget()
        chat_layout = QVBoxLayout()
        chat_layout.addWidget(QLabel("Live Chat:"))
        self.chat_list = QListWidget()
        self.refresh_chat_list()
        chat_layout.addWidget(self.chat_list)
        self.chat_input = QTextEdit()
        self.chat_input.setFixedHeight(50)
        chat_layout.addWidget(self.chat_input)
        send_chat_button = QPushButton("Send", self)
        send_chat_button.clicked.connect(self.send_chat_message)
        chat_layout.addWidget(send_chat_button)
        chat_tab.setLayout(chat_layout)
        self.tabs.addTab(chat_tab, "Chat")

    def refresh_course_list_teacher(self):
        self.course_list.clear()
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT course_id, course_name, description FROM courses WHERE teacher=?", (self.username,))
        courses = c.fetchall()
        for course_id, course_name, desc in courses:
            self.course_list.addItem(f"{course_name} (ID: {course_id}) - {desc or 'No description'}")
        conn.close()

    def refresh_assignment_list(self):
        self.assignment_list.clear()
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT assignment_id, student, file_path, grade, due_date, description, comment FROM assignments WHERE course_id IN (SELECT course_id FROM courses WHERE teacher=?)", 
                 (self.username,))
        self.assignments = c.fetchall()
        for assignment_id, student, file_path, grade, due_date, description, comment in self.assignments:
            comment_text = f" - Comment: {comment}" if comment else ""
            self.assignment_list.addItem(f"Student: {student} - File: {os.path.basename(file_path)} - Grade: {grade or 'Not graded'} - Due: {due_date or 'N/A'} - {description or 'No desc'}{comment_text}")
        conn.close()

    def add_course(self):
        course_name, ok1 = QInputDialog.getText(self, "Add Course", "Enter course name:")
        description, ok2 = QInputDialog.getText(self, "Add Course", "Enter course description (optional):")
        if ok1 and course_name:
            conn = sqlite3.connect("resources/school_lms.db")
            c = conn.cursor()
            c.execute("INSERT INTO courses (course_name, teacher, description) VALUES (?, ?, ?)", 
                     (course_name, self.username, description if ok2 and description else None))
            conn.commit()
            self.refresh_course_list_teacher()
            conn.close()
            QMessageBox.information(self, "Success", "Course added!")

    def edit_course(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course first!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        description, ok = QInputDialog.getText(self, "Edit Course", "Enter new description:")
        if ok:
            conn = sqlite3.connect("resources/school_lms.db")
            c = conn.cursor()
            c.execute("UPDATE courses SET description=? WHERE course_id=?", (description, course_id))
            conn.commit()
            conn.close()
            self.refresh_course_list_teacher()
            QMessageBox.information(self, "Success", "Course description updated!")

    def create_assignment(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course first!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        title, ok1 = QInputDialog.getText(self, "Create Assignment", "Enter assignment title:")
        due_date, ok2 = QInputDialog.getText(self, "Create Assignment", "Enter due date (YYYY-MM-DD):")
        description, ok3 = QInputDialog.getText(self, "Create Assignment", "Enter description:")
        if ok1 and ok2 and ok3 and title and due_date and description:
            if not self.validate_due_date(due_date):
                QMessageBox.warning(self, "Error", "Due date must be in YYYY-MM-DD format!")
                return
            conn = sqlite3.connect("resources/school_lms.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM assignment_definitions WHERE course_id=? AND title=?", 
                     (course_id, title))
            if c.fetchone()[0] > 0:
                QMessageBox.warning(self, "Error", "Assignment title already exists in this course!")
                conn.close()
                return
            c.execute("INSERT INTO assignment_definitions (course_id, title, due_date, description) VALUES (?, ?, ?, ?)",
                     (course_id, title, due_date, description))
            c.execute("SELECT student FROM enrollments WHERE course_id=?", (course_id,))
            students = c.fetchall()
            for student_tuple in students:
                student = student_tuple[0]
                c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)",
                         (student, f"New assignment '{title}' due {due_date} in course ID {course_id}"))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Assignment created and students notified!")

    def edit_assignment(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course first!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("SELECT def_id, title, due_date, description FROM assignment_definitions WHERE course_id=?", 
                 (course_id,))
        assignments = c.fetchall()
        if not assignments:
            QMessageBox.information(self, "Info", "No assignments to edit in this course.")
            conn.close()
            return
        assignment_titles = [f"{a[1]} (Due: {a[2]})" for a in assignments]
        assignment_title, ok = QInputDialog.getItem(self, "Edit Assignment", "Select an assignment:", assignment_titles, 0, False)
        if ok and assignment_title:
            def_id = next(a[0] for a in assignments if f"{a[1]} (Due: {a[2]})" == assignment_title)
            new_title, ok1 = QInputDialog.getText(self, "Edit Assignment", "Enter new title:", text=assignments[assignment_titles.index(assignment_title)][1])
            new_due_date, ok2 = QInputDialog.getText(self, "Edit Assignment", "Enter new due date (YYYY-MM-DD):", text=assignments[assignment_titles.index(assignment_title)][2])
            new_description, ok3 = QInputDialog.getText(self, "Edit Assignment", "Enter new description:", text=assignments[assignment_titles.index(assignment_title)][3])
            if ok1 and ok2 and ok3:
                if not self.validate_due_date(new_due_date):
                    QMessageBox.warning(self, "Error", "Due date must be in YYYY-MM-DD format!")
                    conn.close()
                    return
                c.execute("UPDATE assignment_definitions SET title=?, due_date=?, description=? WHERE def_id=?", 
                         (new_title, new_due_date, new_description, def_id))
                c.execute("SELECT student FROM enrollments WHERE course_id=?", (course_id,))
                students = c.fetchall()
                for student_tuple in students:
                    student = student_tuple[0]
                    c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)",
                             (student, f"Assignment '{new_title}' updated: due {new_due_date} in course ID {course_id}"))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Success", "Assignment updated and students notified!")

    def create_quiz(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course first!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        title, ok1 = QInputDialog.getText(self, "Create Quiz", "Enter quiz title:")
        due_date, ok2 = QInputDialog.getText(self, "Create Quiz", "Enter due date (YYYY-MM-DD):")
        question, ok3 = QInputDialog.getText(self, "Create Quiz", "Enter question:")
        options_str, ok4 = QInputDialog.getText(self, "Create Quiz", "Enter options (separate with '|', e.g., A|B|C|D):")
        correct_answer, ok5 = QInputDialog.getInt(self, "Create Quiz", "Enter correct answer index (0-based):", 0, 0, 3)
        if ok1 and ok2 and ok3 and ok4 and ok5 and title and due_date and question and options_str:
            if not self.validate_due_date(due_date):
                QMessageBox.warning(self, "Error", "Due date must be in YYYY-MM-DD format!")
                return
            options = options_str.split("|")
            if len(options) != 4:
                QMessageBox.warning(self, "Error", "Exactly 4 options required!")
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
                         (student, f"New quiz '{title}' due {due_date} in course ID {course_id}"))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Quiz created and students notified!")

    def grade_assignment(self):
        selected = self.assignment_list.currentItem()
        if not selected or not hasattr(self, 'assignments'):
            QMessageBox.warning(self, "Error", "Refresh assignments and select one first!")
            return
        index = self.assignment_list.row(selected)
        assignment_id = self.assignments[index][0]
        grade, ok1 = QInputDialog.getText(self, "Grade Assignment", "Enter grade (e.g., A, B, 100):")
        comment, ok2 = QInputDialog.getText(self, "Grade Assignment", "Enter comment (optional):")
        if ok1 and grade:
            conn = sqlite3.connect("resources/school_lms.db")
            c = conn.cursor()
            c.execute("UPDATE assignments SET grade=?, comment=? WHERE assignment_id=?", (grade, comment if ok2 and comment else None, assignment_id))
            c.execute("SELECT student, description FROM assignments WHERE assignment_id=?", (assignment_id,))
            student, desc = c.fetchone()
            comment_text = f" with comment: {comment}" if comment else ""
            c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)",
                     (student, f"Your assignment '{desc}' has been graded: {grade}{comment_text}"))
            conn.commit()
            conn.close()
            self.refresh_assignment_list()
            QMessageBox.information(self, "Success", "Grade assigned!")

    def preview_assignment(self):
        selected = self.assignment_list.currentItem()
        if not selected or not hasattr(self, 'assignments'):
            QMessageBox.warning(self, "Error", "Refresh assignments and select one first!")
            return
        index = self.assignment_list.row(selected)
        file_path = self.assignments[index][2]
        if file_path.endswith((".pdf", ".txt")):
            try:
                with open(file_path, "r" if file_path.endswith(".txt") else "rb") as f:
                    content = f.read().decode("utf-8") if file_path.endswith(".txt") else "PDF Preview (Binary content not displayed)"
                preview = QTextEdit()
                preview.setReadOnly(True)
                preview.setText(content)
                dialog = QMessageBox(self)
                dialog.setWindowTitle("File Preview")
                dialog.setText("Preview of " + os.path.basename(file_path))
                dialog.layout().addWidget(preview)
                dialog.exec_()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not preview file: {str(e)}")
        elif file_path.endswith((".png", ".jpg", ".jpeg")):
            try:
                img = Image.open(file_path)
                img.thumbnail((400, 400))
                byte_arr = io.BytesIO()
                img.save(byte_arr, format=img.format)
                pixmap = QPixmap()
                pixmap.loadFromData(byte_arr.getvalue())
                dialog = QMessageBox(self)
                dialog.setWindowTitle("File Preview")
                dialog.setText("Preview of " + os.path.basename(file_path))
                label = QLabel()
                label.setPixmap(pixmap)
                dialog.layout().addWidget(label)
                dialog.exec_()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not preview image: {str(e)}")
        else:
            QMessageBox.information(self, "Preview", "Preview supported for PDF, TXT, PNG, JPG, JPEG files only.")

    def download_assignment(self):
        selected = self.assignment_list.currentItem()
        if not selected or not hasattr(self, 'assignments'):
            QMessageBox.warning(self, "Error", "Refresh assignments and select one first!")
            return
        index = self.assignment_list.row(selected)
        file_path = self.assignments[index][2]
        dest_path, _ = QFileDialog.getSaveFileName(self, "Save Assignment File", os.path.basename(file_path))
        if dest_path:
            shutil.copy(file_path, dest_path)
            QMessageBox.information(self, "Success", "File downloaded!")

    # Admin Dashboard
    def admin_dashboard(self):
        users_tab = QWidget()
        users_layout = QVBoxLayout()
        users_layout.addWidget(QLabel("Manage Users:"))
        self.user_list = QListWidget()
        self.refresh_user_list()
        users_layout.addWidget(self.user_list)

        add_user_button = QPushButton("Add User", self)
        add_user_button.clicked.connect(self.add_user)
        remove_user_button = QPushButton("Remove User", self)
        remove_user_button.clicked.connect(self.remove_user)
        users_layout.addWidget(add_user_button)
        users_layout.addWidget(remove_user_button)
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
        username, ok1 = QInputDialog.getText(self, "Add User", "Enter username:")
        password, ok2 = QInputDialog.getText(self, "Add User", "Enter password:", QLineEdit.Password)
        role, ok3 = QInputDialog.getText(self, "Add User", "Enter role (student/teacher/admin):")
        if ok1 and ok2 and ok3 and username and password and role:
            conn = sqlite3.connect("resources/school_lms.db")
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                     (username, hash_password(password), role))
            conn.commit()
            conn.close()
            self.refresh_user_list()
            QMessageBox.information(self, "Success", "User added!")

    def remove_user(self):
        selected = self.user_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a user first!")
            return
        username = selected.text().split(" (")[0]
        conn = sqlite3.connect("resources/school_lms.db")
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit()
        conn.close()
        self.refresh_user_list()
        QMessageBox.information(self, "Success", "User removed!")

    def logout(self):
        from login import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()
