import sqlite3
import json
from datetime import datetime

DB_FILE = "grading_bot.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Groups table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            schedule_days TEXT NOT NULL, -- JSON list e.g. ["MON", "WED", "FRI"]
            lesson_time TEXT NOT NULL    -- e.g. "16:00"
        )
    ''')
    
    # Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            parent_telegram_id TEXT,
            FOREIGN KEY (group_id) REFERENCES groups (id)
        )
    ''')
    
    # Lessons table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            is_graded INTEGER DEFAULT 0,
            FOREIGN KEY (group_id) REFERENCES groups (id)
        )
    ''')
    
    # Grades table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            score INTEGER, -- 1 to 5, NULL if absent
            status TEXT NOT NULL, -- PRESENT, ABSENT
            FOREIGN KEY (lesson_id) REFERENCES lessons (id),
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    ''')
    
    # Seed initial data if empty
    cursor.execute("SELECT COUNT(*) FROM groups")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO groups (name, schedule_days, lesson_time) VALUES (?, ?, ?)",
                       ("Group A - Mathematics", json.dumps(["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]), "16:00"))
        cursor.execute("INSERT INTO groups (name, schedule_days, lesson_time) VALUES (?, ?, ?)",
                       ("Group B - Physics", json.dumps(["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]), "18:00"))
        
        # Add sample students for Group 1
        students_a = ["Alexander Pierce", "Elena Rostova", "Marcus Vance", "Sofia Chen", "Liam O'Connor"]
        for s in students_a:
            cursor.execute("INSERT INTO students (group_id, full_name) VALUES (1, ?)", (s,))
            
        # Add sample students for Group 2
        students_b = ["Dmitry Volkov", "Sarah Jenkins", "Hiroshi Tanaka", "Amina Said"]
        for s in students_b:
            cursor.execute("INSERT INTO students (group_id, full_name) VALUES (2, ?)", (s,))
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
