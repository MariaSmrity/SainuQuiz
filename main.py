import os
import random
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room, leave_room

# --- 1. CONFIGURATION & IDENTITY ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'sainu_quiz_master_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sainuquiz.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Hardcoded Admin Data as requested
ADMIN_USER = "Sainu_214"
ADMIN_EMAIL = "sainu.quiz@gmail.com"

db = SQLAlchemy(app)
# Eventlet is the "secret sauce" for Railway to handle 80+ players smoothly
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- 2. DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    questions_json = db.Column(db.Text, nullable=False) # Stores Qs as JSON string
    creator_name = db.Column(db.String(50), default=ADMIN_USER)

# --- 3. GLOBAL GAME ENGINE ---
# Tracks active games: { "PIN": { "players": {sid: {name, score}}, "state": "lobby" } }
active_rooms = {}

# --- 4. WEB ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        if user == ADMIN_USER:
            session['username'] = ADMIN_USER
            session['email'] = ADMIN_EMAIL
            return redirect(url_for('discover'))
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/discover')
def discover():
    return render_template('discover.html')

@app.route('/play')
def play():
    return render_template('play.html')

@app.route('/gameplay', methods=['POST'])
def gameplay():
    # Pass data to the unified gameplay.html we built
    context = {
        'pin': request.form.get('pin'),
        'nickname': request.form.get('nickname'),
        'score': 0
    }
    return render_template('gameplay.html', data=context)

# --- CREATOR SUBFOLDER ROUTES ---
# These routes match your file tree (creator/view.html, etc.)
@app.route('/creator')
def creator_dashboard():
    return render_template('creator.html')

@app.route('/creator/create')
def create_quiz():
    return render_template('create.html')

@app.route('/creator/live')
def live_list():
    return render_template('live/live.html')

# --- 5. HOSTING & SOCKETS (The Spacebar logic) ---

@app.route('/host/<int:quiz_id>')
def host_game(quiz_id):
    # Generates a unique 6-digit PIN for one of the 67+ games
    game_pin = str(random.randint(100000, 999999))
    active_rooms[game_pin] = {
        'players': {},
        'state': 'lobby',
        'current_q': 0
    }
    return render_template('host.html', pin=game_pin)

@socketio.on('join')
def on_join(data):
    room = data['pin']
    name = data['nickname']
    if room in active_rooms:
        join_room(room)
        active_rooms[room]['players'][request.sid] = {'name': name, 'score': 0}
        # Update Host's lobby view
        emit('player_list_update', list(active_rooms[room]['players'].values()), room=room)

@socketio.on('next_step')
def on_spacebar(data):
    """ The logic triggered by the Spacebar on the Leaderboard/Host screen """
    room = data['pin']
    if room in active_rooms:
        game = active_rooms[room]
        
        if game['state'] == 'lobby':
            game['state'] = 'answering'
            emit('trigger_phase', {'phase': 'answering'}, room=room)
            
        elif game['state'] == 'answering':
            game['state'] = 'leaderboard'
            # Sort players by score for the Top 5
            leaderboard = sorted(game['players'].values(), key=lambda x: x['score'], reverse=True)[:5]
            emit('trigger_phase', {'phase': 'leaderboard', 'data': leaderboard}, room=room)
            
        elif game['state'] == 'leaderboard':
            game['state'] = 'answering'
            game['current_q'] += 1
            emit('trigger_phase', {'phase': 'answering', 'q_index': game['current_q']}, room=room)

@socketio.on('submit_answer')
def handle_answer(data):
    room = data['pin']
    if room in active_rooms and request.sid in active_rooms[room]['players']:
        # Logic: 1000 base points - (seconds taken * 50)
        time_penalty = data.get('time_taken', 0) * 50
        earned_points = max(100, 1000 - time_penalty)
        active_rooms[room]['players'][request.sid]['score'] += earned_points
        emit('answer_locked', {'points': earned_points}, room=request.sid)

# --- 6. RAILWAY PRODUCTION STARTUP ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Generates sainuquiz.db if missing
    
    # Railway binds to the PORT variable; default to 5000 locally
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)