from flask import Flask, render_template, request, send_file
import os
from dotenv import load_dotenv
import google.genai as genai
import requests
import sqlite3
from datetime import datetime
import markdown

load_dotenv()

app = Flask(__name__)

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ---------------- DATABASE ---------------- #

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            score INTEGER,
            total INTEGER,
            difficulty TEXT,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------- AI FUNCTIONS ---------------- #

def ask_gemini(prompt):
    response = gemini_client.models.generate_content(
        model="models/gemini-flash-latest",
        contents=prompt
    )
    return response.text


def ask_openrouter(prompt):
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    )

    return response.json()["choices"][0]["message"]["content"]


# ---------------- MAIN ROUTE ---------------- #

@app.route("/", methods=["GET", "POST"])
def index():
    response_text = ""
    user_input = ""
    mode = ""
    difficulty = "Easy"
    provider = "gemini"
    api_warning = None

    if request.method == "POST":
        user_input = request.form.get("topic")
        mode = request.form.get("mode")
        difficulty = request.form.get("difficulty")
        provider = request.form.get("provider")

        if user_input:
            try:

                if mode == "quiz":
                    prompt = f"""
                    Generate 5 {difficulty} level MCQs.

                    Format STRICTLY:

                    Q1. Question
                    A) Option
                    B) Option
                    C) Option
                    D) Option
                    Answer: Correct option letter

                    Topic:
                    {user_input}
                    """

                elif mode == "summarize":
                    prompt = f"Summarize clearly:\n{user_input}"

                elif mode == "flashcards":
                    prompt = f"""
                    Generate 5 flashcards.
                    Format:
                    Q: Question
                    A: Answer
                    Topic:
                    {user_input}
                    """

                else:
                    prompt = f"Explain clearly:\n{user_input}"

                # ---------------- SMART AI CALL ---------------- #

                try:
                    if provider == "openrouter":
                        ai_response = ask_openrouter(prompt)
                    else:
                        ai_response = ask_gemini(prompt)

                except Exception as e:
                    error_msg = str(e).lower()

                    # 🔥 If Gemini fails due to quota, auto fallback
                    if provider == "gemini" and ("quota" in error_msg or "429" in error_msg):
                        try:
                            ai_response = ask_openrouter(prompt)
                            provider = "openrouter"
                            api_warning = "⚠️ Gemini daily limit reached. Switched to OpenRouter Backup."
                        except:
                            response_text = """
                            ⚠️ Both AI engines are currently unavailable.
                            Please try again later.
                            """
                            return render_template(
                                "index.html",
                                response=response_text,
                                user_input=user_input,
                                mode=mode,
                                difficulty=difficulty,
                                provider=provider,
                                api_warning=None
                            )
                    else:
                        response_text = """
                        ⚠️ AI service temporarily unavailable.
                        Please switch AI Engine and try again.
                        """
                        return render_template(
                            "index.html",
                            response=response_text,
                            user_input=user_input,
                            mode=mode,
                            difficulty=difficulty,
                            provider=provider,
                            api_warning=None
                        )

                # Format response
                if mode == "quiz":
                    response_text = ai_response
                else:
                    response_text = markdown.markdown(ai_response)

            except Exception:
                response_text = """
                ⚠️ Something went wrong.
                Please try again or change AI engine.
                """

    return render_template(
        "index.html",
        response=response_text,
        user_input=user_input,
        mode=mode,
        difficulty=difficulty,
        provider=provider,
        api_warning=api_warning
    )


# ---------------- SAVE SCORE ---------------- #

@app.route("/save_score", methods=["POST"])
def save_score():
    topic = request.form.get("topic")
    score = request.form.get("score")
    total = request.form.get("total")
    difficulty = request.form.get("difficulty")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO quiz_scores (topic, score, total, difficulty, date)
        VALUES (?, ?, ?, ?, ?)
    """, (topic, score, total, difficulty,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    return "Saved"


if __name__ == "__main__":
    app.run(debug=True)
