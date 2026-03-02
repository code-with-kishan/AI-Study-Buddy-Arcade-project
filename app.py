from collections import defaultdict, deque
from datetime import datetime
from functools import wraps
from pathlib import Path
import io
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
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
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

_gemini_client = None


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "change-me-in-production"),
        DATABASE_PATH=str(BASE_DIR / os.getenv("DATABASE_FILE", "database.db")),
        REQUEST_TIMEOUT=int(os.getenv("REQUEST_TIMEOUT", "25")),
        RATE_LIMIT_PER_MINUTE=int(os.getenv("RATE_LIMIT_PER_MINUTE", "45")),
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        JSON_SORT_KEYS=False,
    )

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
        (user_id, action, safe_points, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
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


def generate_pdf(title: str, lines: list[str]) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, title)
    y -= 28
    pdf.setFont("Helvetica", 10)

    for raw_line in lines:
        line = raw_line or ""
        chunks = [line[i:i + 100] for i in range(0, len(line), 100)] or [""]
        for chunk in chunks:
            if y < 50:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = height - 50
            pdf.drawString(40, y, chunk)
            y -= 14

    pdf.save()
    buffer.seek(0)
    return buffer.read()


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]*>", "", text or "")


def register_hooks(app: Flask) -> None:
    @app.before_request
    def load_logged_user():
        g.user = get_current_user(app)

    @app.before_request
    def basic_rate_limit():
        if request.method != "POST":
            return None

        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "local")
        now = datetime.utcnow().timestamp()
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
        return response

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
        "owner_name": (row["owner_name"] or DEFAULT_OWNER_NAME).strip()[:80],
        "linkedin_url": (row["linkedin_url"] or "").strip()[:300],
        "linkedin_summary": (row["linkedin_summary"] or "").strip()[:4000],
        "owner_strengths": (row["owner_strengths"] or "").strip()[:400],
        "owner_achievements": (row["owner_achievements"] or "").strip()[:400],
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
        raw_response = call_provider(alternate)
        warning = f"⚠️ {selected_provider.title()} unavailable. Switched to {alternate.title()} backup."
        selected_provider = alternate

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
            return redirect(url_for("chat"))
        return redirect(url_for("login"))

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
                        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
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
                owner_name = (request.form.get("owner_name") or DEFAULT_OWNER_NAME).strip()[:80] or DEFAULT_OWNER_NAME
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
                        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                conn.commit()
                flash("Owner chatbot memory updated.", "success")

            conn.close()
            return redirect(url_for("profile"))

        refreshed_user = get_current_user(app)
        owner_profile = get_owner_profile(app, g.user["id"])
        return render_template("profile.html", user=refreshed_user, avatars=AVATARS, owner_profile=owner_profile)

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

    @app.get("/leaderboard")
    @login_required
    def leaderboard_page():
        leaderboard = get_leaderboard(app, 50)
        return render_template("leaderboard.html", user=g.user, leaderboard=leaderboard, level_info=get_level_info(int(g.user["xp"])))

    @app.get("/xp-center")
    @login_required
    def xp_center():
        level_info = get_level_info(int(g.user["xp"]))
        events = get_user_xp_events(app, g.user["id"], 25)
        leaderboard = get_leaderboard(app, 10)
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
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
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

    @app.get("/export_scores.pdf")
    @login_required
    def export_scores_pdf():
        conn = get_db_connection(app)
        rows = conn.execute(
            """
            SELECT topic, score, total, difficulty, provider, date
            FROM quiz_scores
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (g.user["id"],),
        ).fetchall()
        conn.close()

        lines = [f"User: {g.user['username']} ({g.user['avatar']})", f"XP: {g.user['xp']}", ""]
        if not rows:
            lines.append("No score entries found.")
        else:
            for row in rows:
                lines.append(
                    f"{row['date']} | {row['topic']} | Score {row['score']}/{row['total']} | {row['difficulty']} | {row['provider'] or '-'}"
                )

        data = generate_pdf("AI Study Buddy Score Report", lines)
        return Response(
            data,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment; filename=quiz_scores.pdf"},
        )

    @app.get("/export_response.pdf")
    @login_required
    def export_response_pdf():
        response_text = session.get("last_response_text", "")
        mode = session.get("last_response_mode", "unknown")
        topic = session.get("last_response_topic", "")
        if not response_text:
            flash("No generated response available yet. Use Chat first.", "error")
            return redirect(url_for("chat"))

        lines = [f"Mode: {mode}", f"Prompt: {topic}", "", *strip_html(response_text).splitlines()]
        data = generate_pdf("AI Study Buddy Generated Response", lines)
        return Response(
            data,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment; filename=study_response.pdf"},
        )

    @app.get("/health")
    def health_page():
        payload = healthz().get_json()
        return render_template("health.html", user=g.user, health=payload)

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
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
