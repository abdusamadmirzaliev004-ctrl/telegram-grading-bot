import sqlite3
import json
import io
import csv
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import init_db

app = FastAPI(title="Telegram Grading Mini App API")
try:
    init_db()
except Exception as e:
    print("Database init warning:", e)

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
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/journal", response_class=HTMLResponse)
async def read_journal(request: Request):
    return templates.TemplateResponse(request=request, name="journal.html")

@app.get("/api/groups/today")
async def get_today_groups():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, schedule_days, lesson_time FROM groups")
    groups = cursor.fetchall()
    conn.close()
    return [{"id": g["id"], "name": g["name"], "lesson_time": g["lesson_time"]} for g in groups]

@app.get("/api/roster/{group_id}")
async def get_roster(group_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, full_name FROM students WHERE group_id = ?", (group_id,))
    students = cursor.fetchall()
    conn.close()
    return [{"id": s["id"], "full_name": s["full_name"]} for s in students]

@app.get("/api/reports/summary")
async def get_reports_summary():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM groups")
    groups = cursor.fetchall()
    
    result = {}
    for g in groups:
        group_id = g["id"]
        group_name = g["name"]
        
        cursor.execute('''
            SELECT s.id, s.full_name, AVG(gr.score) as avg_score, COUNT(gr.id) as lessons_graded
            FROM students s
            LEFT JOIN grades gr ON s.id = gr.student_id
            WHERE s.group_id = ?
            GROUP BY s.id
        ''', (group_id,))
        students = cursor.fetchall()
        
        student_list = []
        scores = []
        for s in students:
            avg_val = round(s["avg_score"], 2) if s["avg_score"] is not None else None
            if avg_val is not None:
                scores.append(avg_val)
            student_list.append({
                "id": s["id"],
                "name": s["full_name"],
                "avg": avg_val,
                "lessons_graded": s["lessons_graded"]
            })
            
        group_avg = round(sum(scores) / len(scores), 2) if scores else "N/A"
        result[group_name] = {
            "group_avg": group_avg,
            "students": student_list
        }
        
    conn.close()
    return result

@app.get("/api/reports/csv")
async def export_csv():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT g.name as group_name, s.full_name, COUNT(gr.id) as lessons_graded, 
               ROUND(AVG(gr.score), 2) as avg_score
        FROM students s
        JOIN groups g ON s.group_id = g.id
        LEFT JOIN grades gr ON s.id = gr.student_id
        GROUP BY s.id
        ORDER BY g.name, s.full_name
    ''')
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Group Name", "Student Name", "Lessons Graded", "Average Score", "Status"])

    for r in rows:
        avg = r["avg_score"] if r["avg_score"] is not None else "N/A"
        if avg == "N/A":
            status = "Pending"
        elif avg >= 4.5:
            status = "Excellent"
        elif avg >= 3.5:
            status = "Good"
        elif avg >= 2.5:
            status = "Satisfactory"
        else:
            status = "Needs Attention"
            
        writer.writerow([r["group_name"], r["full_name"], r["lessons_graded"], avg, status])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=academic_grade_journal.csv"}
    )

@app.post("/api/grades/submit")
async def submit_grades(payload: GradeSubmission):
    conn = get_db()
    cursor = conn.cursor()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
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
