import sqlite3
import os

DATABASE_PATH = os.environ.get('DATABASE_PATH', 'tasks.db')

def get_connection():
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.execute('PRAGMA foreign_keys = ON;')
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA busy_timeout=30000;')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            owner_email TEXT NOT NULL,
            last_active TIMESTAMP DEFAULT (datetime('now'))
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            priority TEXT DEFAULT 'media',
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'pendiente',
            owner_email TEXT NOT NULL,
            session_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

def crear_session(session_id, email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT session_id FROM sessions WHERE owner_email = ?',
        (email,)
    )
    existing = cursor.fetchone()
    if existing:
        old_session_id = existing['session_id']
        cursor.execute(
            'UPDATE tasks SET session_id = ? WHERE session_id = ?',
            (session_id, old_session_id)
        )
        cursor.execute(
            'DELETE FROM sessions WHERE owner_email = ?',
            (email,)
        )
        cursor.execute(
            'INSERT INTO sessions (session_id, owner_email, last_active) VALUES (?, ?, datetime(\'now\'))',
            (session_id, email)
        )
    else:
        cursor.execute(
            'INSERT INTO sessions (session_id, owner_email, last_active) VALUES (?, ?, datetime(\'now\'))',
            (session_id, email)
        )
    conn.commit()
    conn.close()

def update_session_activity(session_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE sessions SET last_active = datetime(\'now\') WHERE session_id = ?',
        (session_id,)
    )
    conn.commit()
    conn.close()

def cleanup_old_sessions(permanent_mode=False):
    conn = get_connection()
    cursor = conn.cursor()
    if permanent_mode:
        conn.close()
        return
    cursor.execute(
        "DELETE FROM sessions WHERE last_active < datetime('now', '-15 minutes')"
    )
    conn.commit()
    conn.close()

def is_session_valid(session_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT 1 FROM sessions WHERE session_id = ?',
        (session_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None

def crear(title, description, due_date, owner_email, session_id=None, category=None, priority='media'):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO tasks (title, description, category, priority, due_date, status, owner_email, session_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (title, description, category, priority, due_date, 'pendiente', owner_email, session_id)
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return {
        'id': task_id,
        'title': title,
        'description': description,
        'category': category,
        'priority': priority,
        'due_date': due_date,
        'status': 'pendiente',
        'owner_email': owner_email
    }

def leer_todos(session_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if session_id:
        cursor.execute('''
            SELECT t.* FROM tasks t
            JOIN sessions s ON t.session_id = s.session_id
            WHERE t.session_id = ? OR s.owner_email = (
                SELECT owner_email FROM sessions WHERE session_id = ?
            )
        ''', (session_id, session_id))
    else:
        cursor.execute('SELECT * FROM tasks')
    rows = cursor.fetchall()
    conn.close()
    tasks = []
    for row in rows:
        tasks.append({
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'category': row['category'],
            'priority': row['priority'],
            'due_date': row['due_date'],
            'status': row['status'],
            'owner_email': row['owner_email']
        })
    return tasks

def actualizar(task_id, title=None, description=None, due_date=None, status=None, owner_email=None, category=None, priority=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    current = cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    if not current:
        conn.close()
        return None
    
    new_title = title if title is not None else current['title']
    new_description = description if description is not None else current['description']
    new_category = category if category is not None else current['category']
    new_priority = priority if priority is not None else current['priority']
    new_due_date = due_date if due_date is not None else current['due_date']
    new_status = status if status is not None else current['status']
    new_owner_email = owner_email if owner_email is not None else current['owner_email']
    
    cursor.execute(
        'UPDATE tasks SET title = ?, description = ?, category = ?, priority = ?, due_date = ?, status = ?, owner_email = ? WHERE id = ?',
        (new_title, new_description, new_category, new_priority, new_due_date, new_status, new_owner_email, task_id)
    )
    conn.commit()
    conn.close()
    
    return {
        'id': task_id,
        'title': new_title,
        'description': new_description,
        'category': new_category,
        'priority': new_priority,
        'due_date': new_due_date,
        'status': new_status,
        'owner_email': new_owner_email
    }

def eliminar(task_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted
