# dashboard.py
import sqlite3
import os
import shutil
import re
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QListWidget, QFileDialog, QInputDialog, QMessageBox, 
                             QTabWidget, QStatusBar, QProgressBar, QTextEdit, QApplication)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import QTimer, Qt

class DashboardWindow(QMainWindow):
    def __init__(self, role, username):
        super().__init__()
        self.role = role
        self.username = username
        self.setWindowTitle(f"School LMS - {role.capitalize()} Dashboard")
        self.setGeometry(150, 150, 700, 550)
        self.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ccc; }
            QTabBar::tab { background: #e0e0e0; padding: 8px; }
            QTabBar::tab:selected { background: #90caf9; }
            QPushButton { background-color: #4CAF50; color: white; padding: 5px; border-radius: 3px; }
            QPushButton:hover { background-color: #45a049; }
            QLabel { font-family: Arial; }
            QListWidget::item[unread="true"] { background-color: #fff3e0; }
        """)

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

        logout_button = QPushButton("Logout", self)
        logout_button.clicked.connect(self.logout)
        self.layout.addWidget(logout_button)

        central_widget.setLayout(self.layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_due_dates)
        self.timer.start(60000)

    def validate_due_date(self, due_date):
        pattern = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(pattern, due_date):
            return False
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def check_due_dates(self):
        if self.role != "student":
            return
        conn = sqlite3.connect("school_lms.db")
        c = conn.cursor()
        c.execute("SELECT course_id, due_date, description FROM assignments WHERE student=? AND grade IS NULL", 
                 (self.username,))
        assignments = c.fetchall()
        today = datetime.now().date()
        for course_id, due_date, description in assignments:
            due = datetime.strptime(due_date, "%Y-%m-%d").date()
            days_left = (due - today).days
            if 0 <= days_left <= 3:
                c.execute("SELECT COUNT(*) FROM notifications WHERE username=? AND message=?",
                         (self.username, f"Reminder: '{description}' due on {due_date} (Course ID: {course_id})"))
                if c.fetchone()[0] == 0:
                    c.execute("INSERT INTO notifications (username, message) VALUES (?, ?)",
                             (self.username, f"Reminder: '{description}' due on {due_date} (Course ID: {course_id})"))
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

    def refresh_course_list(self):
        self.course_list.clear()
        conn = sqlite3.connect("school_lms.db")
        c = conn.cursor()
        c.execute("SELECT c.course_id, c.course_name, c.description FROM courses c JOIN enrollments e ON c.course_id = e.course_id WHERE e.student=?", 
                 (self.username,))
        courses = c.fetchall()
        for course_id, course_name, desc in courses:
            self.course_list.addItem(f"{course_name} (ID: {course_id}) - {desc or 'No description'}")
        conn.close()

    def refresh_grade_list(self):
        self.grade_list.clear()
        conn = sqlite3.connect("school_lms.db")
        c = conn.cursor()
        c.execute("SELECT course_id, file_path, grade, due_date, description FROM assignments WHERE student=?", 
                 (self.username,))
        grades = c.fetchall()
        for course_id, file_path, grade, due_date, description in grades:
            c.execute("SELECT course_name FROM courses WHERE course_id=?", (course_id,))
            course_name = c.fetchone()[0]
            self.grade_list.addItem(f"{course_name}: {os.path.basename(file_path)} - Grade: {grade or 'Not graded'} - Due: {due_date or 'N/A'}")
        conn.close()

    def refresh_progress_list(self):
        self.progress_list.clear()
        conn = sqlite3.connect("school_lms.db")
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
            submitted = c.fetchone()[0]
            progress_bar = QProgressBar()
            progress_bar.setMaximum(total_assignments if total_assignments > 0 else 1)
            progress_bar.setValue(submitted)
            progress_bar.setFormat(f"{course_name}: {submitted}/{total_assignments} ({submitted/total_assignments*100:.0f}%)")
            item = QListWidgetItem()
            self.progress_list.addItem(item)
            self.progress_list.setItemWidget(item, progress_bar)
        conn.close()

    def refresh_notif_list(self):
        self.notif_list.clear()
        conn = sqlite3.connect("school_lms.db")
        c = conn.cursor()
        c.execute("SELECT notif_id, message, is_read FROM notifications WHERE username=?", (self.username,))
        notifications = c.fetchall()
        unread_count = sum(1 for _, _, is_read in notifications if is_read == 0)
        for notif_id, message, is_read in notifications:
            item = QListWidgetItem(f"[{ 'Unread' if is_read == 0 else 'Read' }] {message} (ID: {notif_id})")
            if is_read == 0:
                item.setData(Qt.UserRole, "unread")  # Custom data for styling
            self.notif_list.addItem(item)
        conn.close()
        self.status_bar.showMessage(f"{unread_count} unread notifications")

    def mark_notif_read(self):
        selected = self.notif_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a notification first!")
            return
        notif_id = int(selected.text().split("ID: ")[1].rstrip(")"))
        conn = sqlite3.connect("school_lms.db")
        c = conn.cursor()
        c.execute("UPDATE notifications SET is_read=1 WHERE notif_id=?", (notif_id,))
        conn.commit()
        conn.close()
        self.refresh_notif_list()

    def refresh_message_list(self):
        self.message_list.clear()
        conn = sqlite3.connect("school_lms.db")
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

    def show_grade_stats(self):
        conn = sqlite3.connect("school_lms.db")
        c = conn.cursor()
        c.execute("SELECT grade FROM assignments WHERE student=? AND grade IS NOT NULL", (self.username,))
        grades = c.fetchall()
        conn.close()
        if not grades:
            QMessageBox.information(self, "Grade Statistics", "No grades available yet.")
            return
        grades = [g[0] for g in grades if g[0].isdigit()]  # Only numeric grades for average
        if grades:
            avg_grade = sum(int(g) for g in grades) / len(grades)
            stats = f"Total Graded: {len(grades)}\nAverage Grade: {avg_grade:.1f}"
        else:
            stats = "Total Graded: 0\nAverage Grade: N/A (No numeric grades)"
        QMessageBox.information(self, "Grade Statistics", stats)

    def enroll_in_course(self):
        conn = sqlite3.connect("school_lms.db")
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
            conn.commit()
            self.refresh_course_list()
            self.refresh_notif_list()
            self.refresh_progress_list()
            QMessageBox.information(self, "Success", "Enrolled in course!")
        conn.close()

    def submit_assignment(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course first!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        
        conn = sqlite3.connect("school_lms.db")
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
                conn.commit()
                conn.close()
                self.refresh_grade_list()
                self.refresh_progress_list()
                self.refresh_notif_list()
                QMessageBox.information(self, "Success", "Assignment submitted!")

    def send_message(self):
        selected = self.course_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a course first!")
            return
        course_id = int(selected.text().split("ID: ")[1].split(")")[0])
        conn = sqlite3.connect("school_lms.db")
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

    def refresh_course_list_teacher(self):
        self.course_list.clear()
        conn = sqlite3.connect("school_lms.db")
        c = conn.cursor()
        c.execute("SELECT course_id, course_name, description FROM courses WHERE teacher=?", (self.username,))
        courses = c.fetchall()
        for course_id, course_name, desc in courses:
            self.course_list.addItem(f"{course_name} (ID: {course_id}) - {desc or 'No description'}")
        conn.close()

    def refresh_assignment_list(self):
        self.assignment_list.clear()
        conn = sqlite3.connect("school_lms.db")
        c = conn.cursor()
        c.execute("SELECT assignment_id, student, file_path, grade, due_date, description FROM assignments WHERE course_id IN (SELECT course_id FROM courses WHERE teacher=?)", 
                 (self.username,))
        self.assignments = c.fetchall()
        for assignment_id, student, file_path, grade, due_date, description in self.assignments:
            self.assignment_list.addItem(f"Student: {student} - File: {os.path.basename(file_path)} - Grade: {grade or 'Not graded'} - Due: {due_date or 'N/A'} - {description or 'No desc'}")
        conn.close()

    def add_course(self):
        course_name, ok1 = QInputDialog.getText(self, "Add Course", "Enter course name:")
        description, ok2 = QInputDialog.getText(self, "Add Course", "Enter course description (optional):")
        if ok1 and course_name:
            conn = sqlite3.connect("school_lms.db")
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
            conn = sqlite3.connect("school_lms.db")
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
