# 🎮 AI Study Buddy – Gamified AI Learning Platform

An intelligent, arcade-style AI-powered learning platform that combines 
explanations, quizzes, flashcards, gamification, and dual AI reliability 
into one unified system.

---

## 📌 Overview

AI Study Buddy is a next-generation EdTech platform designed to enhance student engagement through:

- 🧠 AI-powered topic explanation
- 📝 Smart note summarization
- ❓ Dynamic MCQ quiz generation
- 🃏 Flashcard creation
- 🎮 XP-based gamification system
- 🏆 Level-up progress tracking
- 🔁 AI engine auto-fallback system
- 🤖 Dual AI integration (Gemini + OpenRouter)
- 🎨 Arcade-style interactive UI

This platform solves real-world learning challenges by combining AI + Gamification + API Redundancy.

---

## 🚨 Problem Statement

Students face multiple learning challenges:

- Difficulty understanding complex topics  
- Lack of personalized explanation  
- No interactive revision tools  
- Limited practice MCQs  
- No gamified motivation system  
- Dependency on a single AI service  

Existing platforms do not combine:
- AI explanation  
- Quiz generation  
- Flashcards  
- Gamification  
- API redundancy  

---

## 💡 Proposed Solution

AI Study Buddy provides:

- Real-time AI explanations  
- Automatic quiz generation  
- Flashcard learning system  
- XP & level-based progression  
- Dual AI engine fallback mechanism  
- Reliable performance even during API downtime  

---

## 🛠️ Tech Stack

### 🔹 Backend
- Python
- Flask
- SQLite
- Google Gemini API
- OpenRouter API
- REST API handling

### 🔹 Frontend
- HTML5
- CSS3
- JavaScript
- Jinja2
- Gamified animations

### 🔹 AI Models
- Gemini Flash (Primary)
- OpenRouter GPT-3.5 (Backup)

---

## ⚙️ System Architecture Flow

1. User selects:
   - AI Engine
   - Mode (Explain / Quiz / Flashcards)
   - Difficulty level

2. Dynamic prompt generation

3. API Call:
   - If Gemini fails → Switch to OpenRouter
   - If both fail → Show fallback message

4. Quiz Parsing Algorithm:
   - Extract questions
   - Extract options
   - Store correct answers
   - Enforce single option selection

5. Score Calculation:
   - Compare answers
   - Highlight correct/wrong
   - Update XP bar
   - Trigger level-up animation

6. Save results in SQLite database

---

## 🚀 Features

✔ AI-based explanations  
✔ Dynamic MCQ generation  
✔ Flashcard creation  
✔ XP gamification system  
✔ AI auto-fallback system  
✔ SQLite result storage  
✔ Arcade-style interactive UI  
✔ Fast response time (~1–3 seconds)  

---

## 📂 Project Structure

AI-Study-Buddy/
│
├── app.py
├── database.db
├── requirements.txt
├── .env.example
├── static/
├── templates/index.html
└── README.md

---

## 🔧 Installation & Setup (copy and run this commands on terminal)

### 1️⃣ Clone Repository

git clone https://github.com/code-with-kishan/AI-Study-Buddy-Arcade-project.git
cd AI-Study-Buddy-Arcade-project


### 2️⃣ Create Virtual Environment

python3 -m venv venv
source venv/bin/activate


### 3️⃣ Install Dependencies

pip install -r requirements.txt


### 4️⃣ Setup Environment Variables 

cp .env.example .env

Add your API keys:

GEMINI_API_KEY=your_gemini_key_here
OPENROUTER_API_KEY=your_openrouter_key_here


### 5️⃣ Run Application

python app.py

click on: http://127.0.0.1:5000 (Open browser)


---

## 🌍 Deployment Options

- Local Flask Server
- Google Cloud Run
- Render
- Railway
- Streamlit (alternative)

---

## 📊 Results

The system successfully:

✔ Generates AI explanations  
✔ Generates dynamic quizzes  
✔ Prevents multi-option selection errors  
✔ Auto-switches AI during quota limits  
✔ Saves quiz results  
✔ Provides smooth arcade-style UI  

---

## 🔮 Future Scope

- User authentication system  
- Leaderboard & ranking  
- Persistent XP tracking  
- Advanced UI sound effects  
- AI explanation after wrong answers  
- Multi-language support  
- Full cloud deployment  
- Mobile application version  

---

## 📚 References

- Google Gemini API Documentation  
- OpenRouter API Documentation  
- Flask Documentation  
- Python Official Documentation  
- SQLite Documentation  

---

## 🔗 Project Links

GitHub Repository:  https://github.com/code-with-kishan/AI-Study-Buddy-Arcade-project.git

Deployment Link:  

---

## 🏆 Conclusion

AI Study Buddy demonstrates:

- Real-time AI learning integration  
- Smart API fallback mechanism  
- Gamification for engagement  
- Scalable backend architecture  
- Industry-ready implementation  

This project bridges the gap between AI-powered education and interactive gaming-based motivation.

---

⭐ If you like this project, consider giving it a star!
