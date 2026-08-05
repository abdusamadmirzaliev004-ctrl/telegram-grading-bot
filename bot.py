import os
import sqlite3
import logging
import io
import csv
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_FILE = "grading_bot.db"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    base_url = os.getenv("RENDER_EXTERNAL_URL", "https://telegram-grading-bot-c2fk.onrender.com")
    mini_app_url = f"{base_url}/"
    journal_url = f"{base_url}/journal"
    
    keyboard = [
        [InlineKeyboardButton("📊 Grade Lesson (Mini App)", web_app=WebAppInfo(url=mini_app_url))],
        [InlineKeyboardButton("📖 View Web Journal", web_app=WebAppInfo(url=journal_url)),
         InlineKeyboardButton("📈 Summary Reports", callback_data="run_reports")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Greetings, {user.first_name}.\n\n"
        "Welcome to the Student Grading Adjutant.\n"
        "Tap the buttons below to launch the grading matrix or view reports:\n"
        "• /reports - Generate structured group journal summaries\n"
        "• /editroster - Manage group rosters",
        reply_markup=reply_markup
    )

async def edit_roster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "⚠️ Usage format:\n"
            "`/editroster add <group_id> <student_full_name>`\n"
            "`/editroster remove <student_id>`\n\n"
            "Example: `/editroster add 1 John Doe`",
            parse_mode="Markdown"
        )
        return

    action = args[0].lower()
    conn = get_db()
    cursor = conn.cursor()

    if action == "add":
        group_id = int(args[1])
        full_name = " ".join(args[2:])
        cursor.execute("INSERT INTO students (group_id, full_name) VALUES (?, ?)", (group_id, full_name))
        conn.commit()
        await update.message.reply_text(f"✅ Added student '{full_name}' to Group #{group_id}.")
    elif action == "remove":
        student_id = int(args[1])
        cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        await update.message.reply_text(f"✅ Removed student #{student_id} from database.")
    else:
        await update.message.reply_text("Unknown action. Use `add` or `remove`.")

    conn.close()

async def send_csv_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

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

    csv_data = output.getvalue().encode('utf-8')
    csv_file = io.BytesIO(csv_data)
    csv_file.name = "academic_grade_journal.csv"

    target = update.message if update.message else query.message
    await target.reply_document(
        document=csv_file,
        caption="📄 *Academic Grade Journal (CSV / Excel Format)*",
        parse_mode="Markdown"
    )

async def reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        target = query.message
    else:
        target = update.message

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM groups")
    groups = cursor.fetchall()

    if not groups:
        await target.reply_text("No groups found in database.")
        conn.close()
        return

    base_url = os.getenv("RENDER_EXTERNAL_URL", "https://telegram-grading-bot-c2fk.onrender.com")
    journal_url = f"{base_url}/journal"

    msg = "📚 *ACADEMIC JOURNAL & PERFORMANCE SUMMARY*\n"
    msg += "═════════════════════════\n\n"

    for g in groups:
        group_id = g["id"]
        group_name = g["name"]
        
        cursor.execute('''
            SELECT s.full_name, AVG(gr.score) as avg_score, COUNT(gr.id) as lessons_graded
            FROM students s
            LEFT JOIN grades gr ON s.id = gr.student_id
            WHERE s.group_id = ?
            GROUP BY s.id
        ''', (group_id,))
        students = cursor.fetchall()
        
        scores = [round(s["avg_score"], 2) for s in students if s["avg_score"] is not None]
        group_avg = f"{sum(scores)/len(scores):.2f}" if scores else "N/A"
        
        msg += f"📁 *GROUP: {group_name.upper()}*\n"
        msg += f"• Total Students: `{len(students)}` | Group Avg: `{group_avg}`\n"
        
        # Show top 3 students summary
        if scores:
            graded_students = sorted([s for s in students if s["avg_score"] is not None], key=lambda x: x["avg_score"], reverse=True)
            msg += "• Top Roster:\n"
            for st in graded_students[:3]:
                msg += f"   - {st['full_name']}: `{st['avg_score']:.1f}`\n"
        else:
            msg += "• Status: _No graded sessions logged yet_\n"
        msg += "\n"

    conn.close()

    keyboard = [
        [InlineKeyboardButton("📥 Download Excel/CSV Journal", callback_data="export_csv")],
        [InlineKeyboardButton("📖 Open Web Journal Matrix", web_app=WebAppInfo(url=journal_url))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await target.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "export_csv":
        await send_csv_report(update, context)
    elif query.data == "run_reports":
        await reports(update, context)

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("BOT_TOKEN missing in .env file.")
        exit(1)
        
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("editroster", edit_roster))
    app.add_handler(CommandHandler("reports", reports))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("JARVIS Telegram Grading Bot listening...")
    app.run_polling()
