from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import hashlib
import os
from werkzeug.security import generate_password_hash, check_password_hash
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Generate a random secret key

DATABASE = 'users.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            password_md5 TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def validate_username(username):
    if not username:
        return False, "Username cannot be empty"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    
    if len(username) > 15:
        return False, "Username must be no more than 15 characters long"
    
    if not re.match("^[a-zA-Z0-9_-]+$", username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"
    
    return True, ""

def validate_password(password):
    if not password:
        return False, "Password cannot be empty"
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    
    if len(password) > 128:
        return False, "Password is too long"
    
    return True, ""

def get_user_by_username(username):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(username, password):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        # MD5 for osu
        password_md5 = hashlib.md5(password.encode('utf-8')).hexdigest()
        
        cursor.execute('''
            INSERT INTO users (username, password_hash, password_md5) 
            VALUES (?, ?, ?)
        ''', (username, password_hash, password_md5))
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return True, user_id
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    except Exception as e:
        return False, f"Database error: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # inputs
        username_valid, username_error = validate_username(username)
        if not username_valid:
            flash(username_error, 'error')
            return render_template('register.html')
        
        password_valid, password_error = validate_password(password)
        if not password_valid:
            flash(password_error, 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if get_user_by_username(username):
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        success, result = create_user(username, password)
        if success:
            flash(f'Registration successful! Welcome, {username}!', 'success')
            session['user_id'] = result
            session['username'] = username
            return redirect(url_for('success'))
        else:
            flash(result, 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/success')
def success():
    if 'username' not in session:
        return redirect(url_for('index'))
    return render_template('success.html')

@app.route('/users')
def list_users():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, created_at FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    conn.close()
    return render_template('users.html', users=users)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='127.0.0.1', port=5000)