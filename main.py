import os
import sqlite3
import uvicorn
from typing import List
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

# --- FILE PATH SETUP ---
# BASE_DIR helps Railway find your folders regardless of its internal setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Ensure static folder exists and mount it
static_path = os.path.join(BASE_DIR, "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# --- DATABASE SETUP ---
def init_db():
    # Path to the database file in the root directory
    db_path = os.path.join(BASE_DIR, 'sainuquiz.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Table for Quizzes
    cursor.execute('''CREATE TABLE IF NOT EXISTS questions 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         quiz_id INTEGER, 
         quiz_name TEXT, 
         question TEXT, 
         option1 TEXT, 
         option2 TEXT, 
         option3 TEXT, 
         option4 TEXT, 
         correct INTEGER)''')
    
    # Table for User Profile
    cursor.execute('''CREATE TABLE IF NOT EXISTS profile 
        (id INTEGER PRIMARY KEY, nickname TEXT, email TEXT)''')
    
    # Default entry for Sainu if table is empty
    cursor.execute("INSERT OR IGNORE INTO profile (id, nickname, email) VALUES (1, 'Sainu', 'saihan@example.com')")
    
    conn.commit()
    conn.close()

# Run database setup
init_db()

# --- DATA MODELS ---
class QuestionData(BaseModel):
    quiz_name: str
    question: str
    options: List[str]
    correct: int

class ProfileUpdate(BaseModel):
    nickname: str
    email: str

# --- PAGE ROUTES ---
# These match the .html files I see in your VS Code Explorer screenshot

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/my_quizzes", response_class=HTMLResponse)
async def my_quizzes_page(request: Request):
    db_path = os.path.join(BASE_DIR, 'sainuquiz.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT quiz_id, quiz_name FROM questions")
    quizzes = cursor.fetchall()
    conn.close()
    return templates.TemplateResponse("my_quizzes.html", {"request": request, "quizzes": quizzes})

@app.get("/discover", response_class=HTMLResponse)
async def discover_page(request: Request):
    return templates.TemplateResponse("discover.html", {"request": request})

@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    return templates.TemplateResponse("reports.html", {"request": request})

@app.get("/account", response_class=HTMLResponse)
async def account_page(request: Request):
    db_path = os.path.join(BASE_DIR, 'sainuquiz.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT nickname, email FROM profile WHERE id = 1")
    user = cursor.fetchone()
    conn.close()
    return templates.TemplateResponse("account.html", {
        "request": request, 
        "nickname": user[0] if user else "Sainu", 
        "email": user[1] if user else ""
    })

@app.get("/subscription", response_class=HTMLResponse)
async def subscription_page(request: Request):
    return templates.TemplateResponse("subscription.html", {"request": request})

@app.get("/create", response_class=HTMLResponse)
async def create_page(request: Request):
    return templates.TemplateResponse("create.html", {"request": request})

@app.get("/play", response_class=HTMLResponse)
async def play_page(request: Request):
    return templates.TemplateResponse("play.html", {"request": request})

@app.get("/gameplay", response_class=HTMLResponse)
async def gameplay_page(request: Request):
    return templates.TemplateResponse("gameplay.html", {"request": request})

@app.get("/host", response_class=HTMLResponse)
async def host_page(request: Request):
    return templates.TemplateResponse("host.html", {"request": request})

@app.get("/quiz", response_class=HTMLResponse)
async def quiz_page(request: Request):
    return templates.TemplateResponse("quiz.html", {"request": request})

# --- API ROUTES ---

@app.post("/save_question")
async def save_question(data: QuestionData):
    db_path = os.path.join(BASE_DIR, 'sainuquiz.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    quiz_id = abs(hash(data.quiz_name)) % 10000 
    cursor.execute('''INSERT INTO questions (quiz_id, quiz_name, question, option1, option2, option3, option4, correct) 
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                   (quiz_id, data.quiz_name, data.question, data.options[0], data.options[1], 
                    data.options[2], data.options[3], data.correct))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/update_profile")
async def update_profile(data: ProfileUpdate):
    db_path = os.path.join(BASE_DIR, 'sainuquiz.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE profile SET nickname = ?, email = ? WHERE id = 1", (data.nickname, data.email))
    conn.commit()
    conn.close()
    return {"status": "success"}


# --- PRODUCTION STARTUP ---
if __name__ == "__main__":
    # Railway provides the port via environment variables
    port = int(os.environ.get("PORT", 8000))
    # host must be 0.0.0.0 for the app to be public
    uvicorn.run(app, host="0.0.0.0", port=port)