from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from functools import wraps
from pathlib import Path
import io
import json
import logging
import os
import random
import re
import sqlite3
import threading

import bleach
import google.genai as genai
import markdown
import requests
from dotenv import load_dotenv
from flask import Flask, Response, flash, g, jsonify, redirect, render_template, request, session, url_for
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Helper to get current UTC time without deprecation warning
def get_utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

ALLOWED_MODES = {"explain", "summarize", "quiz", "flashcards"}
ALLOWED_DIFFICULTIES = {"Easy", "Medium", "Hard"}
ALLOWED_PROVIDERS = {"gemini", "openrouter"}
MAX_TOPIC_LENGTH = 2000
REQUEST_WINDOW_SECONDS = 60
REQUEST_HISTORY = defaultdict(deque)
REQUEST_LOCK = threading.Lock()
AVATARS = ["🧙", "🦸", "🧠", "🤖", "🐉", "🦊", "🐼", "👾"]
XP_RULES = {
    "explain": 8,
    "summarize": 10,
    "flashcards": 12,
    "quiz": 15,
    "pdf_bonus": 5,
    "quiz_submit_base": 20,
    "per_correct_answer": 5,
}
DEFAULT_OWNER_NAME = "Kishan Nishad"

MOTIVATION_QUOTES = [
    "Small progress every day beats big plans someday.",
    "You are one focused session away from a breakthrough.",
    "Discipline creates confidence—keep going.",
    "Learn deeply, not quickly. Depth wins.",
    "Consistency is your superpower.",
]

LEVELS = [
    (0, "Bronze", "🥉"),
    (150, "Silver", "🥈"),
    (400, "Gold", "🥇"),
    (800, "Platinum", "💠"),
    (1500, "Legend", "👑"),
]

PYQ_BANK = {
    "jee": [
        {
            "id": "jee_1",
            "topic": "Kinematics",
            "question": "A particle starts from rest with acceleration 2 m/s^2. Find displacement in 4s.",
            "options": ["8 m", "16 m", "24 m", "32 m"],
            "answer": "16 m",
            "solution": "Use s = ut + 1/2 at^2. Here u=0, a=2, t=4. So s = 0 + 1/2 * 2 * 16 = 16 m.",
        },
        {
            "id": "jee_2",
            "topic": "Quadratic Equations",
            "question": "For x^2 - 5x + 6 = 0, the roots are:",
            "options": ["1 and 6", "2 and 3", "-2 and -3", "0 and 6"],
            "answer": "2 and 3",
            "solution": "Factor: x^2 - 5x + 6 = (x-2)(x-3). So roots are x=2 and x=3.",
        },
    ],
    "neet": [
        {
            "id": "neet_1",
            "topic": "Human Physiology",
            "question": "Which chamber of heart pumps oxygenated blood to body?",
            "options": ["Right atrium", "Right ventricle", "Left atrium", "Left ventricle"],
            "answer": "Left ventricle",
            "solution": "Left ventricle contracts and sends oxygen-rich blood into aorta for systemic circulation.",
        },
        {
            "id": "neet_2",
            "topic": "Cell Biology",
            "question": "Powerhouse of the cell is:",
            "options": ["Golgi body", "Ribosome", "Mitochondria", "Lysosome"],
            "answer": "Mitochondria",
            "solution": "Mitochondria produce ATP through cellular respiration, so called powerhouse of the cell.",
        },
    ],
}

DEMO_TEST_BANK = [
    {"id": "d1", "topic": "Kinematics", "question": "Unit of acceleration?", "options": ["m/s", "m/s^2", "kg", "N"], "answer": "m/s^2"},
    {"id": "d2", "topic": "Algebra", "question": "If 2x+3=11, x=?", "options": ["2", "3", "4", "5"], "answer": "4"},
    {"id": "d3", "topic": "Biology", "question": "DNA full form?", "options": ["Deoxy...", "Dynamic...", "Double...", "None"], "answer": "Deoxy..."},
]

MOCK_TEST_BANK = [
    {"id": "m1", "topic": "Mechanics", "question": "Work formula?", "options": ["F.v", "F/s", "mgh", "P/t"], "answer": "F.v"},
    {"id": "m2", "topic": "Chemistry", "question": "pH of neutral water?", "options": ["0", "7", "14", "1"], "answer": "7"},
    {"id": "m3", "topic": "Trigonometry", "question": "sin 30 equals", "options": ["1", "1/2", "0", "sqrt(3)"], "answer": "1/2"},
    {"id": "m4", "topic": "Biology", "question": "Functional unit of kidney?", "options": ["Neuron", "Nephron", "Alveoli", "Axon"], "answer": "Nephron"},
]

CONTEST_BANK = [
    {"id": "c1", "topic": "Math", "question": "Derivative of x^2?", "options": ["x", "2x", "x^3", "2"], "answer": "2x"},
    {"id": "c2", "topic": "Physics", "question": "Unit of Force?", "options": ["Joule", "Watt", "Newton", "Pascal"], "answer": "Newton"},
    {"id": "c3", "topic": "Biology", "question": "Genetic material in most organisms?", "options": ["RNA", "DNA", "Protein", "Lipid"], "answer": "DNA"},
]

_gemini_client = None


def create_app() -> Flask:
    app = Flask(__name__)

    cors_origins = [
        origin.strip().rstrip("/")
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    frontend_origin = (os.getenv("FRONTEND_ORIGIN") or "").strip().rstrip("/")
    if frontend_origin and frontend_origin not in cors_origins:
        cors_origins.append(frontend_origin)
    cross_site = bool(cors_origins)

    app.config.update(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "change-me-in-production"),
        DATABASE_PATH=str(BASE_DIR / os.getenv("DATABASE_FILE", "database.db")),
        REQUEST_TIMEOUT=int(os.getenv("REQUEST_TIMEOUT", "25")),
        RATE_LIMIT_PER_MINUTE=int(os.getenv("RATE_LIMIT_PER_MINUTE", "45")),
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        JSON_SORT_KEYS=False,
        CORS_ALLOWED_ORIGINS=cors_origins,
        SESSION_COOKIE_SAMESITE="None" if cross_site else "Lax",
        SESSION_COOKIE_SECURE=(
            os.getenv("SESSION_COOKIE_SECURE", "true" if cross_site else "false").lower() == "true"
        ),
        SESSION_COOKIE_HTTPONLY=True,
    )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    init_db(app)
    register_hooks(app)
    register_routes(app)
    return app


def get_db_connection(app: Flask) -> sqlite3.Connection:
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    return conn


def init_db(app: Flask) -> None:
    conn = get_db_connection(app)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            avatar TEXT NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS quiz_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            topic TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            difficulty TEXT NOT NULL,
            provider TEXT,
            date TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS xp_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            points INTEGER NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS owner_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            owner_name TEXT NOT NULL,
            linkedin_url TEXT,
            linkedin_summary TEXT,
            owner_strengths TEXT,
            owner_achievements TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            role TEXT,
            bio TEXT,
            learning_goal TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notes_exports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            source_type TEXT NOT NULL,
            title TEXT NOT NULL,
            raw_content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pyq_attempt_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exam_type TEXT NOT NULL,
            question_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            attempt_no INTEGER NOT NULL,
            selected_answer TEXT,
            is_correct INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS test_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            test_type TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            weak_topics TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS study_hours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            minutes INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, date),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS weekly_contest_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week_key TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, week_key),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            reminder_type TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            is_done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "xp" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN xp INTEGER NOT NULL DEFAULT 0")

    score_columns = {row["name"] for row in conn.execute("PRAGMA table_info(quiz_scores)").fetchall()}
    if "provider" not in score_columns:
        cursor.execute("ALTER TABLE quiz_scores ADD COLUMN provider TEXT")
    if "user_id" not in score_columns:
        cursor.execute("ALTER TABLE quiz_scores ADD COLUMN user_id INTEGER")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_quiz_scores_date ON quiz_scores(date DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_quiz_scores_user_id ON quiz_scores(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_xp ON users(xp DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_owner_profiles_user_id ON owner_profiles(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pyq_attempt_user ON pyq_attempt_logs(user_id, exam_type, question_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_attempt_user ON test_attempts(user_id, test_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_study_hours_user ON study_hours(user_id, date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contest_week ON weekly_contest_scores(week_key, score DESC)")
    conn.commit()
    conn.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def get_current_user(app: Flask):
    user_id = session.get("user_id")
    if not user_id:
        return None

    conn = get_db_connection(app)
    user = conn.execute("SELECT id, username, avatar, xp FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def get_level_info(xp: int):
    current_name = "Bronze"
    current_icon = "🥉"
    next_threshold = None

    for threshold, name, icon in LEVELS:
        if xp >= threshold:
            current_name = name
            current_icon = icon
        elif next_threshold is None:
            next_threshold = threshold

    progress_to_next = 100
    if next_threshold is not None:
        previous_threshold = 0
        for threshold, _, _ in LEVELS:
            if threshold <= xp:
                previous_threshold = threshold
        span = max(next_threshold - previous_threshold, 1)
        progress_to_next = int(((xp - previous_threshold) / span) * 100)

    return {
        "name": current_name,
        "icon": current_icon,
        "next_threshold": next_threshold,
        "progress": max(0, min(progress_to_next, 100)),
    }


def add_xp(app: Flask, user_id: int, points: int, action: str) -> int:
    safe_points = max(int(points), 0)
    conn = get_db_connection(app)
    conn.execute("UPDATE users SET xp = xp + ? WHERE id = ?", (safe_points, user_id))
    conn.execute(
        "INSERT INTO xp_events (user_id, action, points, date) VALUES (?, ?, ?, ?)",
        (user_id, action, safe_points, get_utc_now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    current = conn.execute("SELECT xp FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.commit()
    conn.close()
    return int(current["xp"]) if current else 0


def get_user_xp_events(app: Flask, user_id: int, limit: int = 20):
    conn = get_db_connection(app)
    rows = conn.execute(
        """
        SELECT action, points, date
        FROM xp_events
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    conn.close()
    return rows


def get_leaderboard(app: Flask, limit: int = 20):
    conn = get_db_connection(app)
    users = conn.execute(
        "SELECT username, avatar, xp FROM users ORDER BY xp DESC, id ASC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()

    leaderboard = []
    rank = 0
    previous_xp = None
    for idx, row in enumerate(users, start=1):
        if previous_xp != row["xp"]:
            rank = idx
            previous_xp = row["xp"]
        leaderboard.append(
            {
                "rank": rank,
                "username": row["username"],
                "avatar": row["avatar"],
                "xp": int(row["xp"]),
                "level": get_level_info(int(row["xp"])),
            }
        )
    return leaderboard


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]*>", "", text or "")


def get_week_key() -> str:
    return get_utc_now().strftime("%Y-W%U")


def _draw_notebook_background(pdf: canvas.Canvas, width: float, height: float) -> None:
    pdf.setFillColor(colors.HexColor("#fff9e6"))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setStrokeColor(colors.HexColor("#c7d2fe"))
    for y in range(60, int(height), 24):
        pdf.line(40, y, width - 25, y)
    pdf.setStrokeColor(colors.HexColor("#fca5a5"))
    pdf.line(70, 40, 70, height - 40)


def _normalize_handwritten_lines(content: str) -> list[str]:
    cleaned = strip_html(content or "")
    cleaned = cleaned.replace("\r", "\n")
    raw_lines = [line.strip() for line in cleaned.splitlines() if line.strip()]

    normalized = []
    for line in raw_lines:
        # Remove markdown-style heading and list markers for cleaner human-like notes.
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*+•]+\s*", "", line)
        line = re.sub(r"^\d+[\.)]\s*", "", line)
        line = line.replace("**", "").replace("__", "").replace("`", "")
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            normalized.append(line)

    if not normalized:
        normalized = ["No generated content found."]

    return normalized


def build_handwritten_notes_pdf(title: str, content: str, student_name: str) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    pages = []
    lines = _normalize_handwritten_lines(content)

    chunk = []
    for line in lines:
        chunk.append(line)
        if len(chunk) >= 20:
            pages.append(chunk)
            chunk = []
    if chunk:
        pages.append(chunk)

    # Enhanced vibrant color palette for better visual appeal
    primary_palette = [
        colors.HexColor("#7c3aed"),      # Purple
        colors.HexColor("#0ea5e9"),      # Cyan
        colors.HexColor("#16a34a"),      # Green
        colors.HexColor("#ea580c"),      # Orange
        colors.HexColor("#db2777"),      # Pink
        colors.HexColor("#dc2626"),      # Red
        colors.HexColor("#2563eb"),      # Blue
        colors.HexColor("#a16207"),      # Brown
    ]
    
    secondary_palette = [
        colors.HexColor("#e7d4f5"),      # Light Purple bg
        colors.HexColor("#cffafe"),      # Light Cyan bg
        colors.HexColor("#dcfce7"),      # Light Green bg
        colors.HexColor("#fed7aa"),      # Light Orange bg
        colors.HexColor("#fce7f3"),      # Light Pink bg
    ]

    for page_idx, page_lines in enumerate(pages):
        _draw_notebook_background(pdf, width, height)

        # Rotating color header background for visual interest
        header_bg_color = secondary_palette[(page_idx) % len(secondary_palette)]
        header_text_color = primary_palette[(page_idx) % len(primary_palette)]
        
        # Draw header background rectangle
        pdf.setFillColor(header_bg_color)
        pdf.rect(80, height - 95, width - 120, 50, fill=1, stroke=0)

        # Watermark on spine
        pdf.saveState()
        pdf.translate(20, height / 2)
        pdf.rotate(90)
        pdf.setFillColor(colors.HexColor("#e0e7ff"))
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(0, 0, "AI Study Buddy")
        pdf.restoreState()

        # Title with enhanced styling
        pdf.setFillColor(header_text_color)
        pdf.setFont("Helvetica-Bold", 22)
        pdf.drawString(90, height - 55, title[:55])
        
        # Subtitle with student name
        pdf.setFont("Helvetica-Oblique", 11)
        pdf.setFillColor(colors.HexColor("#475569"))
        pdf.drawString(90, height - 78, f"📚 {student_name}")

        # Draw decorative line below header
        pdf.setStrokeColor(header_text_color)
        pdf.setLineWidth(2)
        pdf.line(85, height - 95, width - 40, height - 95)

        y = height - 120
        for i, line in enumerate(page_lines):
            # Alternate between primary and secondary colors for visual rhythm
            is_alt = i % 2
            color = primary_palette[i % len(primary_palette)]
            
            # Draw subtle alternating background
            if is_alt:
                pdf.setFillColor(colors.HexColor("#f8fafc"))
                pdf.rect(85, y - 14, width - 125, 18, fill=1, stroke=0)
            
            # Draw bullet point or number
            pdf.setFillColor(color)
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(88, y, "●")
            
            # Draw text
            pdf.setFillColor(color)
            pdf.setFont("Helvetica-Oblique", 12)
            safe_line = line[:90]
            pdf.drawString(100, y, safe_line)
            
            # Draw decorative separators every 5 lines
            if (i + 1) % 6 == 0:
                sep_color = secondary_palette[(i // 6) % len(secondary_palette)]
                pdf.setStrokeColor(sep_color)
                pdf.setLineWidth(1)
                pdf.line(85, y - 18, width - 40, y - 18)
            
            y -= 24

        # Footer with enhanced styling
        footer_y = 30
        pdf.setFillColor(colors.HexColor("#0f172a"))
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(40, footer_y, "✨ AI Study Buddy · Exam-Ready Notes")
        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(colors.HexColor("#64748b"))
        page_num = (page_idx + 1)
        total_pages = len(pages)
        pdf.drawString(width - 110, footer_y, f"Page {page_num} of {total_pages}")
        
        pdf.showPage()

    pdf.save()
    buffer.seek(0)
    return buffer.read()


def build_certificate_pdf(student_name: str, score: int, total: int) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = A4
    width, height = height, width

    pdf.setFillColor(colors.HexColor("#f1f5f9"))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setStrokeColor(colors.HexColor("#f59e0b"))
    pdf.setLineWidth(6)
    pdf.rect(24, 24, width - 48, height - 48, fill=0, stroke=1)

    pdf.setFillColor(colors.HexColor("#0f172a"))
    pdf.setFont("Helvetica-Bold", 34)
    pdf.drawCentredString(width / 2, height - 88, "AI Study Buddy")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.setFillColor(colors.HexColor("#0369a1"))
    pdf.drawCentredString(width / 2, height - 110, "Authorized Academic Excellence Certificate")

    pdf.setFont("Helvetica-Bold", 18)
    pdf.setFillColor(colors.HexColor("#7c3aed"))
    pdf.drawCentredString(width / 2, height - 145, "Certificate of Achievement")

    pdf.setFillColor(colors.HexColor("#1f2937"))
    pdf.setFont("Helvetica", 13)
    pdf.drawCentredString(width / 2, height - 185, "This certificate is formally awarded to")
    pdf.setFont("Helvetica-Bold", 26)
    pdf.drawCentredString(width / 2, height - 220, student_name[:40])

    percent = round((score / max(total, 1)) * 100, 2)
    pdf.setFont("Helvetica", 14)
    pdf.drawCentredString(width / 2, height - 255, f"Performance: {score}/{total} ({percent}%)")

    pdf.setFillColor(colors.HexColor("#1e293b"))
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(70, height - 302, "Academic Theory Highlights")
    pdf.setFont("Helvetica", 11)
    theory_lines = [
        "1. Consistent retrieval practice improves long-term memory consolidation.",
        "2. Spaced repetition and mixed-topic revision strengthen exam adaptability.",
        "3. Error analysis converts weak areas into high-scoring opportunities.",
    ]
    y = height - 322
    for line in theory_lines:
        pdf.drawString(72, y, line)
        y -= 18

    pdf.setFillColor(colors.HexColor("#334155"))
    pdf.setFont("Helvetica", 10)
    doc_id = f"ASB-CERT-{get_utc_now().strftime('%Y%m%d%H%M%S')}"
    pdf.drawString(70, 88, f"Document ID: {doc_id}")
    pdf.drawString(70, 72, "Status: Digitally authorized for AI Study Buddy Academic Records")

    pdf.setStrokeColor(colors.HexColor("#94a3b8"))
    pdf.line(width - 260, 120, width - 70, 120)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.setFillColor(colors.HexColor("#0f172a"))
    pdf.drawString(width - 248, 102, "Kishan Nishad (Owner)")

    pdf.setStrokeColor(colors.HexColor("#0284c7"))
    pdf.circle(width - 92, 88, 24, stroke=1, fill=0)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawCentredString(width - 92, 90, "ASB")
    pdf.setFont("Helvetica", 7)
    pdf.drawCentredString(width - 92, 80, "AUTHORIZED")

    pdf.setFont("Helvetica-Bold", 10)
    pdf.setFillColor(colors.HexColor("#0f172a"))
    pdf.drawString(28, 24, "AI Study Buddy • Authorized Academic Certification")

    pdf.save()
    buffer.seek(0)
    return buffer.read()


def build_report_card_pdf(student_name: str, accuracy: float, tests: list, weak_topics: list[str]) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    pdf.setFillColor(colors.HexColor("#eef2ff"))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setStrokeColor(colors.HexColor("#2563eb"))
    pdf.setLineWidth(5)
    pdf.rect(24, 24, width - 48, height - 48, fill=0, stroke=1)

    pdf.setFillColor(colors.HexColor("#0f172a"))
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(44, height - 58, "AI Study Buddy")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.setFillColor(colors.HexColor("#1d4ed8"))
    pdf.drawString(46, height - 80, "Authorized Performance Report Card")

    pdf.setFillColor(colors.HexColor("#111827"))
    pdf.setFont("Helvetica", 12)
    pdf.drawString(46, height - 110, f"Student Name: {student_name[:40]}")
    pdf.drawString(46, height - 128, f"Overall Accuracy: {accuracy}%")
    pdf.drawString(46, height - 146, f"Total Tests Evaluated: {len(tests)}")

    theory_lines = [
        "Learning Theory: frequent low-stakes tests improve retention and reduce exam anxiety.",
        "Revision Theory: topic interleaving increases concept transfer in mixed problem sets.",
        "Performance Theory: mistake logging and corrective review raise score consistency.",
    ]
    pdf.setFillColor(colors.HexColor("#1e293b"))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(46, height - 178, "Academic Theory Notes")
    pdf.setFont("Helvetica", 10)
    y = height - 196
    for line in theory_lines:
        pdf.drawString(48, y, line)
        y -= 16

    pdf.setFillColor(colors.HexColor("#7f1d1d"))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(46, height - 254, "Weak Topics")
    pdf.setFont("Helvetica", 10)
    weak = weak_topics[:8] if weak_topics else ["No major weak topic detected yet"]
    y = height - 272
    for topic in weak:
        pdf.drawString(48, y, f"- {topic}")
        y -= 14

    pdf.setFillColor(colors.HexColor("#0f172a"))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(width / 2 + 20, height - 178, "Recent Test Performance")
    pdf.setFont("Helvetica", 10)
    y = height - 196
    for row in tests[:10]:
        line = f"{row['created_at']}  |  {row['test_type'].upper()}  |  {row['score']}/{row['total']}"
        pdf.drawString(width / 2 + 20, y, line[:70])
        y -= 14
    if not tests:
        pdf.drawString(width / 2 + 20, y, "No recent tests available.")

    doc_id = f"ASB-RPT-{get_utc_now().strftime('%Y%m%d%H%M%S')}"
    pdf.setFillColor(colors.HexColor("#334155"))
    pdf.setFont("Helvetica", 10)
    pdf.drawString(46, 64, f"Document ID: {doc_id}")
    pdf.drawString(46, 48, "Status: Authorized and generated by AI Study Buddy evaluation engine")

    pdf.setStrokeColor(colors.HexColor("#94a3b8"))
    pdf.line(width - 260, 92, width - 70, 92)
    pdf.setFillColor(colors.HexColor("#0f172a"))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(width - 250, 74, "Kishan Nishad (Owner)")

    pdf.setStrokeColor(colors.HexColor("#2563eb"))
    pdf.circle(width - 92, 62, 24, stroke=1, fill=0)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawCentredString(width - 92, 64, "ASB")
    pdf.setFont("Helvetica", 7)
    pdf.drawCentredString(width - 92, 54, "AUTH")

    pdf.save()
    buffer.seek(0)
    return buffer.read()


def parse_weak_topics(topic_result_pairs: list[tuple[str, bool]]) -> list[str]:
    topic_wrong_counts: dict[str, int] = {}
    for topic, is_correct in topic_result_pairs:
        if not is_correct:
            topic_wrong_counts[topic] = topic_wrong_counts.get(topic, 0) + 1
    ordered = sorted(topic_wrong_counts.items(), key=lambda item: item[1], reverse=True)
    return [item[0] for item in ordered]


def get_streak_calendar(app: Flask, user_id: int, days: int = 120) -> list[dict]:
    conn = get_db_connection(app)
    rows = conn.execute(
        """
        SELECT date, minutes
        FROM study_hours
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT ?
        """,
        (user_id, days),
    ).fetchall()
    conn.close()
    return [{"date": row["date"], "minutes": int(row["minutes"])} for row in rows]


def compute_streak_count(calendar_rows: list[dict]) -> int:
    if not calendar_rows:
        return 0
    day_minutes = {row["date"]: row["minutes"] for row in calendar_rows}
    streak = 0
    cursor = get_utc_now().date()
    while True:
        day_key = cursor.strftime("%Y-%m-%d")
        if day_minutes.get(day_key, 0) >= 60:
            streak += 1
            cursor = cursor.fromordinal(cursor.toordinal() - 1)
        else:
            break
    return streak


def get_report_card_data(app: Flask, user_id: int) -> tuple[list, float, list[str]]:
    conn = get_db_connection(app)
    tests = conn.execute(
        """
        SELECT test_type, score, total, weak_topics, created_at
        FROM test_attempts
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 20
        """,
        (user_id,),
    ).fetchall()

    pyq_rows = conn.execute(
        """
        SELECT topic, is_correct
        FROM pyq_attempt_logs
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 100
        """,
        (user_id,),
    ).fetchall()
    conn.close()

    total_score = sum(int(row["score"]) for row in tests)
    total_questions = sum(int(row["total"]) for row in tests)
    accuracy = round((total_score / max(total_questions, 1)) * 100, 2)
    weak_topics = parse_weak_topics([(row["topic"], bool(row["is_correct"])) for row in pyq_rows])
    if not weak_topics:
        weak_topics = ["No major weak topic detected yet"]

    return tests, accuracy, weak_topics


def register_hooks(app: Flask) -> None:
    def maybe_add_cors_headers(response: Response) -> Response:
        origin = (request.headers.get("Origin") or "").rstrip("/")
        allowed = app.config.get("CORS_ALLOWED_ORIGINS", [])
        if origin and origin in allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Vary"] = "Origin"
        return response

    @app.before_request
    def load_logged_user():
        g.user = get_current_user(app)

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            return maybe_add_cors_headers(app.make_default_options_response())
        return None

    @app.before_request
    def basic_rate_limit():
        if request.method != "POST":
            return None

        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "local")
        now = get_utc_now().timestamp()
        limit = app.config["RATE_LIMIT_PER_MINUTE"]

        with REQUEST_LOCK:
            history = REQUEST_HISTORY[client_ip]
            while history and now - history[0] > REQUEST_WINDOW_SECONDS:
                history.popleft()

            if len(history) >= limit:
                return jsonify({"error": "Too many requests. Please retry shortly."}), 429

            history.append(now)

        return None

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store" if request.path.startswith("/api/") else "public, max-age=60"
        return maybe_add_cors_headers(response)

    @app.context_processor
    def inject_user_level():
        user = getattr(g, "user", None)
        level = get_level_info(int(user["xp"])) if user else None
        return {"current_level": level, "level_for_xp": get_level_info}


def get_gemini_client():
    global _gemini_client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Gemini API key missing")
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((requests.RequestException, RuntimeError)),
)
def ask_gemini(prompt: str) -> str:
    response = get_gemini_client().models.generate_content(
        model="models/gemini-flash-latest",
        contents=prompt,
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned empty response")
    return text


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((requests.RequestException, RuntimeError)),
)
def ask_openrouter(prompt: str, timeout: int) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OpenRouter API key missing")

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo"),
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not content:
        raise RuntimeError("OpenRouter returned empty response")
    return content


def build_prompt(topic: str, mode: str, difficulty: str) -> str:
    if mode == "quiz":
        return f"""
Generate 5 {difficulty} level MCQs.

Format STRICTLY:
Q1. Question
A) Option
B) Option
C) Option
D) Option
Answer: Correct option letter

Topic:
{topic}
""".strip()

    if mode == "summarize":
        return f"Summarize clearly with key points and concise examples:\n{topic}"

    if mode == "flashcards":
        return f"""
Generate 5 flashcards.
Format:
Q: Question
A: Answer
Topic:
{topic}
""".strip()

    return f"Explain clearly in structured, easy language:\n{topic}"


def sanitize_markdown(text: str) -> str:
    rendered = markdown.markdown(text)
    return bleach.clean(
        rendered,
        tags=["p", "strong", "em", "ul", "ol", "li", "code", "pre", "blockquote", "h1", "h2", "h3", "h4", "hr", "br"],
        attributes={},
        strip=True,
    )


def local_guidance_response(message: str) -> str:
    short = message.strip()[:120]
    return (
        "I’m here to help. Try this quick plan:\n"
        "1) Break your topic into 3 sub-parts.\n"
        "2) Study each sub-part for 10 minutes.\n"
        "3) Write 5 key points from memory.\n"
        "4) Test yourself with a short quiz.\n\n"
        f"Starting point for your message: '{short}'"
    )


def extract_linkedin_profile_text(url: str, timeout: int) -> str:
    normalized = (url or "").strip()
    if not normalized:
        raise ValueError("Please add your LinkedIn profile URL first.")
    if "linkedin.com" not in normalized.lower():
        raise ValueError("Please provide a valid LinkedIn URL.")

    no_scheme = re.sub(r"^https?://", "", normalized, flags=re.IGNORECASE)
    mirror_url = f"https://r.jina.ai/http://{no_scheme}"
    response = requests.get(mirror_url, timeout=timeout)
    response.raise_for_status()
    text = (response.text or "").strip()

    if len(text) < 60:
        raise ValueError("Could not extract enough LinkedIn data. You can paste profile details manually.")
    return text[:4000]


def get_owner_profile(app: Flask, user_id: int) -> dict:
    conn = get_db_connection(app)
    row = conn.execute(
        """
        SELECT owner_name, linkedin_url, linkedin_summary, owner_strengths, owner_achievements
        FROM owner_profiles
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    conn.close()

    if not row:
        return {
            "owner_name": DEFAULT_OWNER_NAME,
            "linkedin_url": "",
            "linkedin_summary": "",
            "owner_strengths": "focused, consistent, disciplined learner",
            "owner_achievements": "keeps improving every day",
        }

    return {
        "owner_name": DEFAULT_OWNER_NAME,
        "linkedin_url": (row["linkedin_url"] or "").strip()[:300],
        "linkedin_summary": (row["linkedin_summary"] or "").strip()[:4000],
        "owner_strengths": (row["owner_strengths"] or "").strip()[:400],
        "owner_achievements": (row["owner_achievements"] or "").strip()[:400],
    }


def get_user_profile_customization(app: Flask, user_id: int) -> dict:
    conn = get_db_connection(app)
    row = conn.execute(
        """
        SELECT role, bio, learning_goal
        FROM user_profiles
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    conn.close()

    if not row:
        return {
            "role": "",
            "bio": "",
            "learning_goal": "",
        }

    return {
        "role": (row["role"] or "").strip()[:80],
        "bio": (row["bio"] or "").strip()[:300],
        "learning_goal": (row["learning_goal"] or "").strip()[:300],
    }


def build_owner_praise(owner_profile: dict) -> tuple[str, str]:
    owner_name = (owner_profile.get("owner_name") or DEFAULT_OWNER_NAME).strip()[:80]
    strengths = (owner_profile.get("owner_strengths") or "").strip()
    achievements = (owner_profile.get("owner_achievements") or "").strip()
    linkedin_summary = strip_html(owner_profile.get("linkedin_summary") or "").strip()

    highlights = []
    if strengths:
        highlights.append(strengths)
    if achievements:
        highlights.append(achievements)
    if linkedin_summary:
        first_line = linkedin_summary.splitlines()[0].strip()[:140]
        if first_line:
            highlights.append(first_line)

    if not highlights:
        highlights.append("focused, consistent, growth-driven, and serious about learning")

    praise = "; ".join(highlights[:2])
    return owner_name, praise


def canned_assistant_response(message: str, username: str, owner_profile: dict) -> str:
    text = message.lower().strip()
    owner_name, praise = build_owner_praise(owner_profile)
    owner_keywords = [
        "kishan",
        "owner",
        "creator",
        "who made",
        "who built",
        "about you",
        "about owner",
        "about kishan",
        "linkedin",
    ]

    if any(keyword in text for keyword in owner_keywords):
        linkedin_url = (owner_profile.get("linkedin_url") or "").strip()
        owner_summary = strip_html(owner_profile.get("linkedin_summary") or "").strip()
        summary_line = owner_summary.splitlines()[0].strip() if owner_summary else ""
        answer = (
            f"{owner_name} is my owner. He is {praise}. "
            "He is growth-focused, consistent, and serious about quality work."
        )
        if summary_line:
            answer += f"\nProfile highlight: {summary_line[:180]}"
        if linkedin_url:
            answer += f"\nLinkedIn: {linkedin_url}"
        return answer

    faq_rules = [
        (
            ["hello", "hi", "hey"],
            f"Hi {username}! 👋 I’m your Study Buddy. Ask me about chat, XP, quiz, PDF, leaderboard, or profile settings.",
        ),
        (
            ["how to use", "how use", "start", "guide", "help"],
            (
                f"Sure {username}, quick guide:\n"
                "1) Open AI Chat and enter a prompt.\n"
                "2) Pick mode (Explain/Summarize/Quiz/Flashcards).\n"
                "3) Optionally upload PDF and click Analyze PDF.\n"
                "4) Use Dashboard for stats/history.\n"
                "5) Use XP Center to track progress and rules."
            ),
        ),
        (
            ["xp", "points", "level", "badge"],
            (
                f"{username}, XP is earned on tasks and quiz submits.\n"
                "- Explain +8\n- Summarize +10\n- Flashcards +12\n- Quiz generate +15\n"
                "- PDF bonus +5\n- Quiz submit base +20\n- +5 per correct answer"
            ),
        ),
        (
            ["leaderboard", "rank", "ranking"],
            f"{username}, open Leaderboard from sidebar to see XP ranking. Higher XP means better rank 🏆.",
        ),
        (
            ["quiz", "mcq", "test"],
            f"{username}, select Quiz mode in Chat, generate questions, then submit. You earn extra XP based on correct answers.",
        ),
        (
            ["pdf", "file", "upload"],
            f"{username}, in Chat use the file picker, then click Analyze PDF. You’ll also get PDF bonus XP ✨.",
        ),
        (
            ["theme", "dark", "light", "mode"],
            f"{username}, use the 🌓 Toggle Theme button in the sidebar to switch Dark/Light mode.",
        ),
        (
            ["profile", "password", "avatar"],
            f"{username}, open Profile page to change avatar and password settings.",
        ),
    ]

    for keywords, response in faq_rules:
        if any(keyword in text for keyword in keywords):
            return response

    return (
        f"{username}, I didn’t fully catch that, but I can still guide you.\n"
        "Try asking one of these:\n"
        "- how to use\n- how to gain xp\n- how quiz works\n- how to upload pdf\n- how leaderboard works"
    )


def run_with_timeout(callable_fn, timeout_seconds: float):
    result = {}
    error = {}

    def worker():
        try:
            result["value"] = callable_fn()
        except Exception as exc:
            error["error"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout_seconds)

    if thread.is_alive():
        raise TimeoutError("Operation timed out")
    if "error" in error:
        raise error["error"]
    return result.get("value")


def generate_ai_response(topic: str, mode: str, difficulty: str, provider: str, timeout: int):
    prompt = build_prompt(topic, mode, difficulty)
    selected_provider = provider if provider in ALLOWED_PROVIDERS else "gemini"
    warning = None

    def call_provider(engine: str):
        if engine == "openrouter":
            return ask_openrouter(prompt, timeout)
        return ask_gemini(prompt)

    try:
        raw_response = call_provider(selected_provider)
    except Exception:
        alternate = "openrouter" if selected_provider == "gemini" else "gemini"
        try:
            raw_response = call_provider(alternate)
            warning = f"⚠️ {selected_provider.title()} unavailable. Switched to {alternate.title()} backup."
            selected_provider = alternate
        except Exception:
            raw_response = local_guidance_response(topic)
            warning = "⚠️ Live AI providers are temporarily unavailable. Showing local study guidance response."
            selected_provider = "local"

    output = raw_response if mode == "quiz" else sanitize_markdown(raw_response)
    return output, selected_provider, warning, raw_response


def extract_pdf_text(pdf_file) -> str:
    if not pdf_file or not pdf_file.filename:
        return ""
    if not pdf_file.filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported")

    reader = PdfReader(pdf_file)
    chunks = []
    for page in reader.pages:
        chunks.append((page.extract_text() or "").strip())
    return "\n".join(part for part in chunks if part).strip()[:12000]


def build_dashboard_data(app: Flask, user_id: int, q: str):
    conn = get_db_connection(app)
    params = [user_id]
    sql_filter = "WHERE user_id = ?"
    if q:
        sql_filter += " AND topic LIKE ?"
        params.append(f"%{q}%")

    rows = conn.execute(
        f"""
        SELECT topic, score, total, difficulty, provider, date
        FROM quiz_scores
        {sql_filter}
        ORDER BY id DESC
        LIMIT 30
        """,
        tuple(params),
    ).fetchall()

    stats = conn.execute(
        """
        SELECT
            COUNT(*) as attempts,
            COALESCE(SUM(score), 0) as total_score,
            COALESCE(SUM(total), 0) as total_questions,
            COALESCE(AVG(CASE WHEN total > 0 THEN (score * 100.0 / total) END), 0) as avg_percent
        FROM quiz_scores
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    conn.close()

    return rows, {
        "attempts": int(stats["attempts"]),
        "total_score": int(stats["total_score"]),
        "total_questions": int(stats["total_questions"]),
        "average_percent": round(float(stats["avg_percent"]), 2),
    }


def register_routes(app: Flask) -> None:
    @app.get("/")
    def root():
        if g.user:
            return redirect(url_for("dashboard"))
        return render_template("index.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if g.user:
            return redirect(url_for("chat"))

        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            avatar = request.form.get("avatar") or AVATARS[0]

            if len(username) < 3:
                flash("Username must be at least 3 characters.", "error")
                return render_template("signup.html", avatars=AVATARS, selected_avatar=avatar)
            if len(password) < 6:
                flash("Password must be at least 6 characters.", "error")
                return render_template("signup.html", avatars=AVATARS, selected_avatar=avatar)
            if avatar not in AVATARS:
                avatar = AVATARS[0]

            conn = get_db_connection(app)
            try:
                conn.execute(
                    "INSERT INTO users (username, password_hash, avatar, xp, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        username,
                        generate_password_hash(password, method="pbkdf2:sha256"),
                        avatar,
                        0,
                        get_utc_now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                conn.commit()
                flash("Account created. Please log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Username already exists. Try another one.", "error")
            finally:
                conn.close()

        return render_template("signup.html", avatars=AVATARS, selected_avatar=AVATARS[0])

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if g.user:
            return redirect(url_for("chat"))

        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""

            conn = get_db_connection(app)
            user = conn.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            conn.close()

            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                flash(f"Welcome back, {user['username']}!", "success")
                return redirect(url_for("chat"))

            flash("Invalid username or password.", "error")

        return render_template("login.html")

    @app.get("/logout")
    @login_required
    def logout():
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("login"))

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        if request.method == "POST":
            action = request.form.get("action", "avatar")
            conn = get_db_connection(app)

            if action == "avatar":
                avatar = request.form.get("avatar") or AVATARS[0]
                if avatar not in AVATARS:
                    avatar = AVATARS[0]
                conn.execute("UPDATE users SET avatar = ? WHERE id = ?", (avatar, g.user["id"]))
                conn.commit()
                flash("Avatar updated successfully.", "success")

            elif action == "password":
                current_password = request.form.get("current_password") or ""
                new_password = request.form.get("new_password") or ""
                user = conn.execute(
                    "SELECT password_hash FROM users WHERE id = ?",
                    (g.user["id"],),
                ).fetchone()

                if not user or not check_password_hash(user["password_hash"], current_password):
                    flash("Current password is incorrect.", "error")
                elif len(new_password) < 6:
                    flash("New password must be at least 6 characters.", "error")
                else:
                    conn.execute(
                        "UPDATE users SET password_hash = ? WHERE id = ?",
                        (generate_password_hash(new_password, method="pbkdf2:sha256"), g.user["id"]),
                    )
                    conn.commit()
                    flash("Password updated successfully.", "success")

            elif action == "owner_ai":
                owner_name = DEFAULT_OWNER_NAME
                linkedin_url = (request.form.get("linkedin_url") or "").strip()[:300]
                owner_strengths = (request.form.get("owner_strengths") or "").strip()[:400]
                owner_achievements = (request.form.get("owner_achievements") or "").strip()[:400]
                linkedin_summary = (request.form.get("linkedin_summary") or "").strip()[:4000]

                if request.form.get("import_linkedin") == "1":
                    try:
                        linkedin_summary = extract_linkedin_profile_text(linkedin_url, app.config["REQUEST_TIMEOUT"])
                        flash("LinkedIn data imported for chatbot memory.", "success")
                    except Exception as err:
                        flash(str(err), "error")

                conn.execute(
                    """
                    INSERT INTO owner_profiles (
                        user_id, owner_name, linkedin_url, linkedin_summary, owner_strengths, owner_achievements, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        owner_name=excluded.owner_name,
                        linkedin_url=excluded.linkedin_url,
                        linkedin_summary=excluded.linkedin_summary,
                        owner_strengths=excluded.owner_strengths,
                        owner_achievements=excluded.owner_achievements,
                        updated_at=excluded.updated_at
                    """,
                    (
                        g.user["id"],
                        owner_name,
                        linkedin_url,
                        linkedin_summary,
                        owner_strengths,
                        owner_achievements,
                        get_utc_now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                conn.commit()
                flash("Owner chatbot memory updated.", "success")

            elif action == "personalize":
                role = (request.form.get("role") or "").strip()[:80]
                bio = (request.form.get("bio") or "").strip()[:300]
                learning_goal = (request.form.get("learning_goal") or "").strip()[:300]

                conn.execute(
                    """
                    INSERT INTO user_profiles (user_id, role, bio, learning_goal, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        role=excluded.role,
                        bio=excluded.bio,
                        learning_goal=excluded.learning_goal,
                        updated_at=excluded.updated_at
                    """,
                    (
                        g.user["id"],
                        role,
                        bio,
                        learning_goal,
                        get_utc_now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                conn.commit()
                flash("Profile personalization saved.", "success")

            conn.close()
            return redirect(url_for("profile"))

        refreshed_user = get_current_user(app)
        user_profile_custom = get_user_profile_customization(app, g.user["id"])
        return render_template(
            "profile.html",
            user=refreshed_user,
            avatars=AVATARS,
            user_profile_custom=user_profile_custom,
        )

    @app.route("/chat", methods=["GET", "POST"])
    @login_required
    def chat():
        response_text = ""
        raw_response = ""
        user_input = ""
        mode = "explain"
        difficulty = "Easy"
        provider = "gemini"
        api_warning = None

        if request.method == "POST":
            user_input = (request.form.get("topic") or "").strip()[:MAX_TOPIC_LENGTH]
            mode = request.form.get("mode", "explain")
            difficulty = request.form.get("difficulty", "Easy")
            provider = request.form.get("provider", "gemini")
            action = request.form.get("action", "generate")
            pdf_file = request.files.get("pdf_file")

            if mode not in ALLOWED_MODES:
                mode = "explain"
            if difficulty not in ALLOWED_DIFFICULTIES:
                difficulty = "Easy"
            if provider not in ALLOWED_PROVIDERS:
                provider = "gemini"

            try:
                pdf_text = extract_pdf_text(pdf_file) if action == "pdf" else ""
            except ValueError as err:
                flash(str(err), "error")
                pdf_text = ""

            if action == "pdf" and pdf_text:
                user_input = f"{user_input}\n\nPDF content:\n{pdf_text}".strip()

            if not user_input:
                flash("Please enter prompt text or upload a PDF to analyze.", "error")
            else:
                try:
                    response_text, provider, api_warning, raw_response = generate_ai_response(
                        topic=user_input,
                        mode=mode,
                        difficulty=difficulty,
                        provider=provider,
                        timeout=app.config["REQUEST_TIMEOUT"],
                    )
                    earned = XP_RULES.get(mode, 8) + (XP_RULES["pdf_bonus"] if action == "pdf" else 0)
                    current_xp = add_xp(app, g.user["id"], earned, f"chat_{mode}_{action}")
                    flash(f"+{earned} XP earned. Total XP: {current_xp}", "success")
                except Exception:
                    app.logger.exception("AI generation failed")
                    response_text = "⚠️ AI service temporarily unavailable. Please try again in a moment."

        if raw_response:
            session["last_response_text"] = raw_response
            session["last_response_mode"] = mode
            session["last_response_topic"] = user_input[:300]

        leaderboard = get_leaderboard(app, 10)
        return render_template(
            "chat.html",
            user=g.user,
            response=response_text,
            user_input=user_input,
            mode=mode,
            difficulty=difficulty,
            provider=provider,
            api_warning=api_warning,
            leaderboard=leaderboard,
            level_info=get_level_info(int(g.user["xp"])),
        )

    @app.get("/dashboard")
    @login_required
    def dashboard():
        query = (request.args.get("q") or "").strip()
        rows, stats = build_dashboard_data(app, g.user["id"], query)
        leaderboard = get_leaderboard(app, 20)
        return render_template(
            "dashboard.html",
            user=g.user,
            rows=rows,
            stats=stats,
            query=query,
            leaderboard=leaderboard,
            level_info=get_level_info(int(g.user["xp"])),
        )

    @app.get("/xp-center")
    @login_required
    def xp_center():
        level_info = get_level_info(int(g.user["xp"]))
        events = get_user_xp_events(app, g.user["id"], 25)
        leaderboard = get_leaderboard(app, 50)
        return render_template(
            "xp_center.html",
            user=g.user,
            level_info=level_info,
            xp_rules=XP_RULES,
            events=events,
            leaderboard=leaderboard,
        )

    @app.post("/save_score")
    @login_required
    def save_score():
        topic = (request.form.get("topic") or "").strip()[:300]
        difficulty = (request.form.get("difficulty") or "Easy").strip()
        provider = (request.form.get("provider") or "unknown").strip()

        if difficulty not in ALLOWED_DIFFICULTIES:
            return jsonify({"error": "Invalid difficulty"}), 400

        try:
            score = int(request.form.get("score", 0))
            total = int(request.form.get("total", 0))
        except ValueError:
            return jsonify({"error": "Score and total must be integers"}), 400

        if total <= 0 or score < 0 or score > total:
            return jsonify({"error": "Invalid score range"}), 400

        conn = get_db_connection(app)
        conn.execute(
            """
            INSERT INTO quiz_scores (user_id, topic, score, total, difficulty, provider, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                g.user["id"],
                topic or "Untitled topic",
                score,
                total,
                difficulty,
                provider,
                get_utc_now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        conn.close()

        gained = XP_RULES["quiz_submit_base"] + (score * XP_RULES["per_correct_answer"])
        current_xp = add_xp(app, g.user["id"], gained, "quiz_submit")
        return jsonify({"status": "saved", "xp_gained": gained, "total_xp": current_xp})

    @app.post("/api/assistant")
    @login_required
    def assistant_api():
        payload = request.get_json(silent=True) or {}
        message = (payload.get("message") or "").strip()[:1200]

        if not message:
            return jsonify({"error": "Message is required"}), 400

        username = g.user["username"] if g.user else "Student"
        owner_profile = get_owner_profile(app, g.user["id"])
        return jsonify(
            {
                "reply": canned_assistant_response(message, username, owner_profile),
                "provider": "local-faq",
                "warning": None,
                "quote": random.choice(MOTIVATION_QUOTES),
            }
        )

    @app.get("/api/history")
    @login_required
    def history():
        limit = min(max(int(request.args.get("limit", 10)), 1), 100)
        q = (request.args.get("q") or "").strip()

        params = [g.user["id"]]
        filter_clause = "WHERE user_id = ?"
        if q:
            filter_clause += " AND topic LIKE ?"
            params.append(f"%{q}%")

        conn = get_db_connection(app)
        rows = conn.execute(
            """
            SELECT topic, score, total, difficulty, provider, date
            FROM quiz_scores
            """
            + filter_clause
            +
            """
            ORDER BY id DESC
            LIMIT ?
            """,
            tuple(params + [limit]),
        ).fetchall()
        conn.close()

        return jsonify([
            {
                "topic": row["topic"],
                "score": row["score"],
                "total": row["total"],
                "difficulty": row["difficulty"],
                "provider": row["provider"],
                "date": row["date"],
            }
            for row in rows
        ])

    @app.get("/api/stats")
    @login_required
    def stats():
        rows, data = build_dashboard_data(app, g.user["id"], "")
        _ = rows
        data["xp"] = int(g.user["xp"])
        return jsonify(data)

    @app.get("/api/leaderboard")
    @login_required
    def leaderboard_api():
        return jsonify(get_leaderboard(app, 20))

    @app.route("/notes-lab", methods=["GET", "POST"])
    @login_required
    def notes_lab():
        source_text = ""
        explanation_html = ""
        teacher_mode = request.form.get("teacher_mode", "normal")
        provider = request.form.get("provider", "gemini")

        if request.method == "POST":
            action = request.form.get("action", "from_chat")
            title = (request.form.get("title") or "Handwritten Notes").strip()[:80]
            manual_summary = (request.form.get("book_summary") or "").strip()[:6000]
            uploaded_pdf = request.files.get("pdf_file")

            if action == "from_chat":
                source_text = session.get("last_response_text", "")
            elif action == "from_pdf":
                try:
                    source_text = extract_pdf_text(uploaded_pdf)
                except ValueError as err:
                    flash(str(err), "error")
            elif action == "from_summary":
                source_text = manual_summary

            if source_text:
                strictness_map = {
                    "normal": "Give clear but friendly notes.",
                    "strict": "Keep it concise, challenge-oriented, less hinting.",
                    "very_strict": "Exam-level concise and strict guidance.",
                }
                prompt = (
                    f"Convert this study content into clean colorful handwritten notes in plain natural sentences. "
                    "Do not use markdown symbols like #, *, -, bullets, numbering, or arrows. "
                    f"{strictness_map.get(teacher_mode, strictness_map['normal'])}\n\n{source_text[:9000]}"
                )
                try:
                    explanation_html, provider, warning, raw_response = generate_ai_response(
                        topic=prompt,
                        mode="summarize",
                        difficulty="Easy",
                        provider=provider,
                        timeout=app.config["REQUEST_TIMEOUT"],
                    )
                    if warning:
                        flash(warning, "error")
                    source_text = raw_response or source_text
                except Exception:
                    app.logger.exception("Notes generation failed")
                    explanation_html = sanitize_markdown(source_text)

                conn = get_db_connection(app)
                conn.execute(
                    """
                    INSERT INTO notes_exports (user_id, source_type, title, raw_content, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        g.user["id"],
                        action,
                        title,
                        source_text[:12000],
                        get_utc_now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                conn.commit()
                conn.close()

                pdf_bytes = build_handwritten_notes_pdf(title, source_text, g.user["username"])
                session["last_notes_text"] = source_text
                session["last_notes_title"] = title
                return Response(
                    pdf_bytes,
                    mimetype="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=handwritten_notes.pdf"},
                )
            flash("Please provide chat response, book summary, or PDF.", "error")

        return render_template(
            "notes_lab.html",
            user=g.user,
            explanation_html=explanation_html,
            level_info=get_level_info(int(g.user["xp"])),
        )

    @app.route("/topic-learning", methods=["GET", "POST"])
    @login_required
    def topic_learning():
        topic = ""
        explanation = ""
        notes_points = []
        practice_questions = []
        teacher_mode = "normal"
        provider = "gemini"

        if request.method == "POST":
            topic = (request.form.get("topic") or "").strip()[:400]
            teacher_mode = request.form.get("teacher_mode", "normal")
            provider = request.form.get("provider", "gemini")
            if topic:
                mode_prompt = {
                    "normal": "Teach with balanced explanation and hints.",
                    "strict": "Use strict exam style, fewer hints.",
                    "very_strict": "Use very strict exam-level guidance with challenge tasks.",
                }
                enriched_topic = (
                    f"Topic: {topic}\n"
                    f"Instruction: {mode_prompt.get(teacher_mode, mode_prompt['normal'])}\n"
                    "Return: explanation, notes bullets, diagram pointers, and 4 practice questions."
                )
                try:
                    explanation, provider, warning, raw_response = generate_ai_response(
                        topic=enriched_topic,
                        mode="explain",
                        difficulty="Medium",
                        provider=provider,
                        timeout=app.config["REQUEST_TIMEOUT"],
                    )
                    if warning:
                        flash(warning, "error")
                    text_blob = strip_html(raw_response or explanation)
                except Exception:
                    app.logger.exception("Topic learning generation failed")
                    text_blob = (
                        f"Topic overview for {topic}. Focus on concept, formulas, visual model, and exam strategy."
                    )
                    explanation = sanitize_markdown(text_blob)

                notes_points = [line.strip("- ").strip() for line in text_blob.splitlines() if line.strip()][:8]
                if not notes_points:
                    notes_points = [
                        f"Core definition of {topic}",
                        "Key formula and variable meaning",
                        "Common mistakes to avoid",
                        "Exam shortcut method",
                    ]
                practice_questions = [
                    f"Explain the fundamental principle of {topic} in your own words.",
                    f"Solve one medium-level numerical from {topic}.",
                    f"List two common mistakes in {topic} and corrections.",
                    f"Write one exam-focused short note on {topic}.",
                ]

        return render_template(
            "topic_learning.html",
            user=g.user,
            topic=topic,
            explanation=explanation,
            notes_points=notes_points,
            practice_questions=practice_questions,
            teacher_mode=teacher_mode,
            provider=provider,
            level_info=get_level_info(int(g.user["xp"])),
        )

    @app.get("/graphs")
    @login_required
    def graphs_page():
        return render_template("graphs.html", user=g.user, level_info=get_level_info(int(g.user["xp"])))

    @app.route("/pyq", methods=["GET", "POST"])
    @login_required
    def pyq_page():
        exam_type = (request.values.get("exam") or "jee").lower()
        if exam_type not in PYQ_BANK:
            exam_type = "jee"

        questions = PYQ_BANK[exam_type]
        selected_question = questions[0]
        question_id = request.values.get("question_id")
        if question_id:
            for item in questions:
                if item["id"] == question_id:
                    selected_question = item
                    break

        feedback = None
        show_solution = False
        attempts_left = 2

        conn = get_db_connection(app)
        attempts_count = conn.execute(
            """
            SELECT COUNT(*) as count
            FROM pyq_attempt_logs
            WHERE user_id = ? AND exam_type = ? AND question_id = ?
            """,
            (g.user["id"], exam_type, selected_question["id"]),
        ).fetchone()["count"]
        attempts_left = max(0, 2 - int(attempts_count))

        if request.method == "POST":
            answer = (request.form.get("answer") or "").strip()
            if attempts_count < 2:
                next_attempt = attempts_count + 1
                is_correct = int(answer == selected_question["answer"])
                conn.execute(
                    """
                    INSERT INTO pyq_attempt_logs (
                        user_id, exam_type, question_id, topic, attempt_no, selected_answer, is_correct, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        g.user["id"],
                        exam_type,
                        selected_question["id"],
                        selected_question["topic"],
                        next_attempt,
                        answer,
                        is_correct,
                        get_utc_now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                conn.commit()

                if is_correct:
                    feedback = "Correct answer. Great job!"
                    show_solution = True
                else:
                    feedback = "Incorrect answer."
                    show_solution = next_attempt >= 2
                attempts_left = max(0, 2 - next_attempt)
            else:
                feedback = "Attempt limit reached for this question."
                show_solution = True

        conn.close()

        if attempts_left == 0:
            show_solution = True

        return render_template(
            "pyq.html",
            user=g.user,
            exam_type=exam_type,
            questions=questions,
            selected_question=selected_question,
            feedback=feedback,
            attempts_left=attempts_left,
            show_solution=show_solution,
            level_info=get_level_info(int(g.user["xp"])),
        )

    @app.route("/demo-test", methods=["GET", "POST"])
    @login_required
    def demo_test():
        report = None
        if request.method == "POST":
            score = 0
            topic_results = []
            for q in DEMO_TEST_BANK:
                selected = request.form.get(f"q_{q['id']}", "")
                correct = selected == q["answer"]
                topic_results.append((q["topic"], correct))
                if correct:
                    score += 1

            weak_topics = parse_weak_topics(topic_results)
            conn = get_db_connection(app)
            conn.execute(
                """
                INSERT INTO test_attempts (user_id, test_type, score, total, weak_topics, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    g.user["id"],
                    "demo",
                    score,
                    len(DEMO_TEST_BANK),
                    json.dumps(weak_topics),
                    get_utc_now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
            conn.close()

            report = {
                "score": score,
                "total": len(DEMO_TEST_BANK),
                "accuracy": round((score / max(len(DEMO_TEST_BANK), 1)) * 100, 2),
                "weak_topics": weak_topics,
            }

        return render_template(
            "demo_test.html",
            user=g.user,
            questions=DEMO_TEST_BANK,
            report=report,
            level_info=get_level_info(int(g.user["xp"])),
        )

    @app.route("/mock-test", methods=["GET", "POST"])
    @login_required
    def mock_test():
        report = None
        if request.method == "POST":
            score = 0
            topic_results = []
            for q in MOCK_TEST_BANK:
                selected = request.form.get(f"q_{q['id']}", "")
                correct = selected == q["answer"]
                topic_results.append((q["topic"], correct))
                if correct:
                    score += 1

            weak_topics = parse_weak_topics(topic_results)
            conn = get_db_connection(app)
            conn.execute(
                """
                INSERT INTO test_attempts (user_id, test_type, score, total, weak_topics, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    g.user["id"],
                    "mock",
                    score,
                    len(MOCK_TEST_BANK),
                    json.dumps(weak_topics),
                    get_utc_now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
            conn.close()

            session["last_mock_score"] = score
            session["last_mock_total"] = len(MOCK_TEST_BANK)

            report = {
                "score": score,
                "total": len(MOCK_TEST_BANK),
                "accuracy": round((score / max(len(MOCK_TEST_BANK), 1)) * 100, 2),
                "weak_topics": weak_topics,
                "suggestions": [
                    "Revise weakest topic first with 25-minute blocks.",
                    "Solve 10 targeted MCQs daily.",
                    "Re-attempt mock after 48 hours.",
                ],
            }

        return render_template(
            "mock_test.html",
            user=g.user,
            questions=MOCK_TEST_BANK,
            report=report,
            level_info=get_level_info(int(g.user["xp"])),
        )

    @app.get("/certificate.pdf")
    @login_required
    def certificate_pdf():
        score = int(session.get("last_mock_score", 0))
        total = int(session.get("last_mock_total", len(MOCK_TEST_BANK)))
        pdf_data = build_certificate_pdf(g.user["username"], score, total)
        return Response(
            pdf_data,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment; filename=mock_certificate.pdf"},
        )

    @app.get("/streak")
    @login_required
    def streak_page():
        rows = get_streak_calendar(app, g.user["id"], 140)
        streak_count = compute_streak_count(rows)
        return render_template(
            "streak.html",
            user=g.user,
            rows=rows,
            streak_count=streak_count,
            level_info=get_level_info(int(g.user["xp"])),
        )

    @app.post("/api/streak/log-hour")
    @login_required
    def streak_log_hour():
        today = get_utc_now().strftime("%Y-%m-%d")
        conn = get_db_connection(app)
        conn.execute(
            """
            INSERT INTO study_hours (user_id, date, minutes, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET
                minutes = minutes + 60
            """,
            (g.user["id"], today, 60, get_utc_now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        conn.close()

        rows = get_streak_calendar(app, g.user["id"], 140)
        streak_count = compute_streak_count(rows)
        return jsonify(
            {
                "message": "Your 1-hour streak is complete!",
                "streak_count": streak_count,
            }
        )

    @app.route("/weekly-contest", methods=["GET", "POST"])
    @login_required
    def weekly_contest():
        week_key = get_week_key()
        your_score = None

        if request.method == "POST":
            score = 0
            for q in CONTEST_BANK:
                if request.form.get(f"q_{q['id']}", "") == q["answer"]:
                    score += 1

            conn = get_db_connection(app)
            conn.execute(
                """
                INSERT INTO weekly_contest_scores (user_id, week_key, score, total, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, week_key) DO UPDATE SET
                    score = MAX(score, excluded.score),
                    total = excluded.total,
                    created_at = excluded.created_at
                """,
                (
                    g.user["id"],
                    week_key,
                    score,
                    len(CONTEST_BANK),
                    get_utc_now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
            conn.close()
            your_score = score

        conn = get_db_connection(app)
        leaderboard_rows = conn.execute(
            """
            SELECT u.username, u.avatar, w.score, w.total
            FROM weekly_contest_scores w
            JOIN users u ON u.id = w.user_id
            WHERE w.week_key = ?
            ORDER BY w.score DESC, w.created_at ASC
            LIMIT 50
            """,
            (week_key,),
        ).fetchall()
        conn.close()

        return render_template(
            "weekly_contest.html",
            user=g.user,
            week_key=week_key,
            questions=CONTEST_BANK,
            leaderboard=leaderboard_rows,
            your_score=your_score,
            level_info=get_level_info(int(g.user["xp"])),
        )

    @app.route("/reminders", methods=["GET", "POST"])
    @login_required
    def reminders_page():
        if request.method == "POST":
            title = (request.form.get("title") or "").strip()[:160]
            reminder_type = (request.form.get("reminder_type") or "study").strip()[:40]
            remind_at = (request.form.get("remind_at") or "").strip()[:40]

            if title and remind_at:
                conn = get_db_connection(app)
                conn.execute(
                    """
                    INSERT INTO reminders (user_id, title, reminder_type, remind_at, is_done, created_at)
                    VALUES (?, ?, ?, ?, 0, ?)
                    """,
                    (
                        g.user["id"],
                        title,
                        reminder_type,
                        remind_at,
                        get_utc_now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                conn.commit()
                conn.close()
                flash("Reminder saved.", "success")
            else:
                flash("Reminder title and date-time are required.", "error")

        conn = get_db_connection(app)
        reminders = conn.execute(
            """
            SELECT id, title, reminder_type, remind_at, is_done
            FROM reminders
            WHERE user_id = ?
            ORDER BY remind_at ASC
            """,
            (g.user["id"],),
        ).fetchall()
        conn.close()

        return render_template(
            "reminders.html",
            user=g.user,
            reminders=reminders,
            level_info=get_level_info(int(g.user["xp"])),
        )

    @app.get("/report-card")
    @login_required
    def report_card():
        tests, accuracy, weak_topics = get_report_card_data(app, g.user["id"])

        return render_template(
            "report_card.html",
            user=g.user,
            tests=tests,
            accuracy=accuracy,
            weak_topics=weak_topics,
            level_info=get_level_info(int(g.user["xp"])),
        )

    @app.get("/report-card.pdf")
    @login_required
    def report_card_pdf():
        tests, accuracy, weak_topics = get_report_card_data(app, g.user["id"])
        pdf_data = build_report_card_pdf(g.user["username"], accuracy, tests, weak_topics)
        return Response(
            pdf_data,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment; filename=report_card.pdf"},
        )

    @app.get("/models-3d")
    @login_required
    def models_3d():
        return render_template("models_3d.html", user=g.user, level_info=get_level_info(int(g.user["xp"])))

    @app.get("/healthz")
    def healthz():
        db_status = "ok"
        try:
            conn = get_db_connection(app)
            conn.execute("SELECT 1")
            conn.close()
        except Exception:
            db_status = "error"

        return jsonify(
            {
                "status": "ok" if db_status == "ok" else "degraded",
                "database": db_status,
                "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
                "openrouter_configured": bool(os.getenv("OPENROUTER_API_KEY")),
                "authenticated": bool(g.user),
                "timestamp": get_utc_now().isoformat() + "Z",
            }
        )


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
