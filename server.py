import sqlite3
import json
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Telegram Grading Mini App API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")
DB_FILE = "grading_bot.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

class GradeSubmission(BaseModel):
    group_id: int
    grades: dict  # student_id -> score or 'absent'

@app.get("/ping")
async def ping():
    return {"status": "alive", "timestamp": datetime.now().isoformat()}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/groups/today")
async def get_today_groups():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, schedule_days, lesson_time FROM groups")
    groups = cursor.fetchall()
    conn.close()
    
    # Return all groups for demo purposes
    return [{"id": g["id"], "name": g["name"], "lesson_time": g["lesson_time"]} for g in groups]

@app.get("/api/roster/{group_id}")
async def get_roster(group_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, full_name FROM students WHERE group_id = ?", (group_id,))
    students = cursor.fetchall()
    conn.close()
    return [{"id": s["id"], "full_name": s["full_name"]} for s in students]

@app.post("/api/grades/submit")
async def submit_grades(payload: GradeSubmission):
    conn = get_db()
    cursor = conn.cursor()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Create or fetch today's lesson
    cursor.execute("SELECT id FROM lessons WHERE group_id = ? AND date = ?", (payload.group_id, today_str))
    lesson = cursor.fetchone()
    
    if not lesson:
        cursor.execute("INSERT INTO lessons (group_id, date, is_graded) VALUES (?, ?, 1)", (payload.group_id, today_str))
        lesson_id = cursor.lastrowid
    else:
        lesson_id = lesson["id"]
        cursor.execute("UPDATE lessons SET is_graded = 1 WHERE id = ?", (lesson_id,))
        
    for student_id_str, val in payload.grades.items():
        student_id = int(student_id_str)
        status = "ABSENT" if val == "absent" else "PRESENT"
        score = None if val == "absent" else int(val)
        
        cursor.execute('''
            INSERT INTO grades (lesson_id, student_id, score, status) 
            VALUES (?, ?, ?, ?)
        ''', (lesson_id, student_id, score, status))
        
    conn.commit()
    conn.close()
    return {"success": True, "count": len(payload.grades)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
