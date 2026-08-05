import os
import sqlite3
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

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
    # Note: For actual Telegram WebApp testing, replace URL below with your public HTTPS server (e.g. ngrok / domain)
    mini_app_url = "http://localhost:8000"
    
    keyboard = [
        [InlineKeyboardButton("📊 Grade Lesson (Mini App)", web_app=WebAppInfo(url=mini_app_url))],
        [InlineKeyboardButton("✏️ Edit Roster (/editroster)", callback_data="editroster"),
         InlineKeyboardButton("📈 Weekly Reports (/reports)", callback_data="reports")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Greetings, {user.first_name}.\n\n"
        "Welcome to the Student Grading Adjutant.\n"
        "Tap the button below to launch the grading matrix or use CLI commands:\n"
        "• /editroster - Add or remove students\n"
        "• /reports - Generate weekly performance summaries",
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

async def reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.full_name, g.name as group_name, AVG(gr.score) as avg_score, COUNT(gr.id) as total_lessons
        FROM students s
        JOIN groups g ON s.group_id = g.id
        LEFT JOIN grades gr ON s.id = gr.student_id
        GROUP BY s.id
    ''')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("No grade entries recorded yet.")
        return

    msg = "📊 *Weekly Performance Summary*\n\n"
    for r in rows:
        avg = f"{r['avg_score']:.1f}" if r['avg_score'] else "N/A"
        msg += f"• *{r['full_name']}* ({r['group_name']}): Avg `{avg}` (Lessons: {r['total_lessons']})\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("BOT_TOKEN missing in .env file.")
        exit(1)
        
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("editroster", edit_roster))
    app.add_handler(CommandHandler("reports", reports))
    
    print("JARVIS Telegram Grading Bot listening...")
    app.run_polling()
