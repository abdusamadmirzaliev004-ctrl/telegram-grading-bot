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
    
    # Check if demo1 exists, if not seed demo1, demo2, demo3
    cursor.execute("SELECT COUNT(*) FROM groups WHERE name LIKE 'demo%'")
    if cursor.fetchone()[0] < 3:
        # Clear existing sample data for clean demo environment
        cursor.execute("DELETE FROM grades")
        cursor.execute("DELETE FROM lessons")
        cursor.execute("DELETE FROM students")
        cursor.execute("DELETE FROM groups")
        
        all_days = json.dumps(["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"])
        
        # Create demo1, demo2, demo3
        cursor.execute("INSERT INTO groups (id, name, schedule_days, lesson_time) VALUES (1, 'demo1', ?, '14:00')", (all_days,))
        cursor.execute("INSERT INTO groups (id, name, schedule_days, lesson_time) VALUES (2, 'demo2', ?, '16:00')", (all_days,))
        cursor.execute("INSERT INTO groups (id, name, schedule_days, lesson_time) VALUES (3, 'demo3', ?, '18:00')", (all_days,))
        
        demo1_students = [
            "Alexander Pierce", "Elena Rostova", "Marcus Vance", "Sofia Chen", "Liam O'Connor",
            "Victoria Sterling", "Daniel Kim", "Maya Patel", "Lucas Dubois", "Chloe Bennett",
            "Ethan Wright", "Olivia Martinez", "Noah Thorne"
        ]
        for s in demo1_students:
            cursor.execute("INSERT INTO students (group_id, full_name) VALUES (1, ?)", (s,))
            
        demo2_students = [
            "Dmitry Volkov", "Sarah Jenkins", "Hiroshi Tanaka", "Amina Said", "Gabriel Silva",
            "Hanna Schmidt", "Ryan Cooper", "Isabella Rossi", "Kevin Zhang", "Amelia Hughes",
            "Oscar Lindqvist", "Fatima Al-Mansoor", "Julian Mercer"
        ]
        for s in demo2_students:
            cursor.execute("INSERT INTO students (group_id, full_name) VALUES (2, ?)", (s,))
            
        demo3_students = [
            "Benjamin Hayes", "Zoe Kravitz", "David Miller", "Grace Taylor", "Nathan Reed",
            "Emma Watson", "Samuel Jackson", "Hannah Montana", "Arthur Pendelton", "Mia Khalifa",
            "Oliver Queen", "Charlotte York", "William Shakespeare"
        ]
        for s in demo3_students:
            cursor.execute("INSERT INTO students (group_id, full_name) VALUES (3, ?)", (s,))
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized with demo1, demo2, demo3 and 13 students each.")
