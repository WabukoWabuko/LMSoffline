# database.py
import sqlite3
import os
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db(force_reset=False):
    if force_reset and os.path.exists("school_lms.db"):
        os.remove("school_lms.db")
    
    conn = sqlite3.connect("school_lms.db")
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS courses 
                 (course_id INTEGER PRIMARY KEY AUTOINCREMENT, course_name TEXT, teacher TEXT, description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS enrollments 
                 (enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, student TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS assignments 
                 (assignment_id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, 
                  student TEXT, file_path TEXT, grade TEXT, due_date TEXT, description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS assignment_definitions 
                 (def_id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, 
                  title TEXT, due_date TEXT, description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS notifications 
                 (notif_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, message TEXT, is_read INTEGER DEFAULT 0)''')
    
    c.execute("PRAGMA table_info(assignments)")
    columns = [col[1] for col in c.fetchall()]
    if 'grade' not in columns:
        c.execute("ALTER TABLE assignments ADD COLUMN grade TEXT")
    if 'due_date' not in columns:
        c.execute("ALTER TABLE assignments ADD COLUMN due_date TEXT")
    if 'description' not in columns:
        c.execute("ALTER TABLE assignments ADD COLUMN description TEXT")
    
    c.execute("PRAGMA table_info(courses)")
    columns = [col[1] for col in c.fetchall()]
    if 'description' not in columns:
        c.execute("ALTER TABLE courses ADD COLUMN description TEXT")
    
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
