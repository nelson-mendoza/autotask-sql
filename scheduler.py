import threading
import time
import smtplib
import ssl
import os
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from db import get_connection, actualizar

SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASS = os.environ.get('SMTP_PASS')
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))

def is_valid_email(email):
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def send_email(to_email, subject, body):
    if not SMTP_USER or not SMTP_PASS:
        print("⚠️ SMTP no configurado. Agrega variables de entorno para activar notificaciones.")
        return False
    
    if not is_valid_email(to_email):
        return False
    
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception:
        return False

def check_and_notify():
    if not SMTP_USER or not SMTP_PASS:
        print("⚠️ SMTP no configurado. Agrega variables de entorno para activar notificaciones.")
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute(
        "SELECT id, title, due_date, owner_email FROM tasks WHERE date(due_date) = ? AND status = 'pendiente'",
        (today,)
    )
    tasks = cursor.fetchall()
    
    for task in tasks:
        task_id = task['id']
        title = task['title']
        owner_email = task['owner_email']
        
        subject = f'Recordatorio de tarea: {title}'
        body = f'La tarea "{title}" vence hoy ({today}). Por favor revisa tu lista de tareas.'
        
        if send_email(owner_email, subject, body):
            actualizar(task_id, status='notificado')
    
    conn.close()

def scheduler_loop():
    while True:
        try:
            check_and_notify()
        except Exception:
            pass
        time.sleep(900)

def start_scheduler():
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()

if __name__ == '__main__':
    start_scheduler()
    while True:
        time.sleep(1)
