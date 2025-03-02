# database.py
import sqlite3
import os
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db(force_reset=False):
    if force_reset and os.path.exists("resources/school_lms.db"):
        os.remove("resources/school_lms.db")
    
    conn = sqlite3.connect("resources/school_lms.db")
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS courses 
                 (course_id INTEGER PRIMARY KEY AUTOINCREMENT, course_name TEXT, teacher TEXT, description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS enrollments 
                 (enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, student TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS assignments 
                 (assignment_id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, 
                  student TEXT, file_path TEXT, grade TEXT, due_date TEXT, description TEXT, comment TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS assignment_definitions 
                 (def_id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, 
                  title TEXT, due_date TEXT, description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS notifications 
                 (notif_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, message TEXT, is_read INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (msg_id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, 
                  course_id INTEGER, message TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS quizzes 
                 (quiz_id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, 
                  title TEXT, due_date TEXT, question TEXT, options TEXT, correct_answer INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS quiz_submissions 
                 (submission_id INTEGER PRIMARY KEY AUTOINCREMENT, quiz_id INTEGER, 
                  student TEXT, answer INTEGER, score INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS points 
                 (point_id INTEGER PRIMARY KEY AUTOINCREMENT, student TEXT, points INTEGER, reason TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS badges 
                 (badge_id INTEGER PRIMARY KEY AUTOINCREMENT, student TEXT, badge_name TEXT, awarded_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_messages 
                 (chat_id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, 
                  sender TEXT, message TEXT, timestamp TEXT)''')
    
    # Add missing columns
    c.execute("PRAGMA table_info(assignments)")
    columns = [col[1] for col in c.fetchall()]
    if 'grade' not in columns:
        c.execute("ALTER TABLE assignments ADD COLUMN grade TEXT")
    if 'due_date' not in columns:
        c.execute("ALTER TABLE assignments ADD COLUMN due_date TEXT")
    if 'description' not in columns:
        c.execute("ALTER TABLE assignments ADD COLUMN description TEXT")
    if 'comment' not in columns:
        c.execute("ALTER TABLE assignments ADD COLUMN comment TEXT")
    
    c.execute("PRAGMA table_info(courses)")
    columns = [col[1] for col in c.fetchall()]
    if 'description' not in columns:
        c.execute("ALTER TABLE courses ADD COLUMN description TEXT")
    
    # Add indexes for performance
    c.execute("CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_assignments_student ON assignments(student)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_notifications_username ON notifications(username)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_quiz_submissions_student ON quiz_submissions(student)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_points_student ON points(student)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_chat_course ON chat_messages(course_id)")

    default_users = [
        ("student1", hash_password("pass123"), "student"),
        ("teacher1", hash_password("pass456"), "teacher"),
        ("admin1", hash_password("pass789"), "admin")
    ]
    c.executemany("INSERT OR IGNORE INTO users VALUES (?, ?, ?)", default_users)
    conn.commit()
    conn.close()

if not os.path.exists("assignments"):
    os.makedirs("assignments")
if not os.path.exists("resources"):
    os.makedirs("resources")
