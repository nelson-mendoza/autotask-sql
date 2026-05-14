import json
import os
import signal
import sys
import threading
import time
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from db import init_db, crear_session, update_session_activity, cleanup_old_sessions, is_session_valid, crear, leer_todos, actualizar, eliminar

def signal_handler(sig, frame):
    print('\nServidor detenido correctamente')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

class TaskHandler(BaseHTTPRequestHandler):
    
    def send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def send_html_response(self, content):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))
    
    def get_session_id(self):
        cookie_header = self.headers.get('Cookie', '')
        if cookie_header:
            cookie = SimpleCookie()
            cookie.load(cookie_header)
            if 'session_id' in cookie:
                return cookie['session_id'].value
        return None
    
    def set_session_cookie(self, session_id):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Set-Cookie', f'session_id={session_id}; Path=/; SameSite=Lax')
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/healthcheck':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
            return
        
        session_id = self.get_session_id()
        
        if self.path == '/login':
            if session_id and is_session_valid(session_id):
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()
                return
            login_html = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - AutoTask API</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .login-container { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
        h1 { color: #333; margin-bottom: 10px; font-size: 24px; }
        p { color: #666; margin-bottom: 30px; font-size: 14px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #333; font-weight: 500; }
        input[type="email"] { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 16px; }
        input[type="email"]:focus { outline: none; border-color: #007bff; }
        button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .footer-note { margin-top: 20px; font-size: 12px; color: #999; text-align: center; }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>AutoTask API</h1>
        <p>Ingresa tu correo para acceder a tus tareas</p>
        <form id="loginForm">
            <div class="form-group">
                <label for="email">Correo electrónico *</label>
                <input type="email" id="email" name="email" required placeholder="tu@correo.com">
            </div>
            <button type="submit">Iniciar Sesión</button>
        </form>
        <div class="footer-note" id="login-footer-note">Sesión automática: se limpia tras 15 min de inactividad o al cerrar el navegador.</div>
    </div>
    <script>
        function getSessionMode() {
            return localStorage.getItem('sessionMode') || 'temporal';
        }
        function updateLoginFooterNote() {
            const mode = getSessionMode();
            const noteElement = document.getElementById('login-footer-note');
            if (mode === 'permanente') {
                noteElement.textContent = 'Modo Permanente: Los datos persisten hasta que los borres manualmente.';
            } else {
                noteElement.textContent = 'Sesión automática: se limpia tras 15 min de inactividad o al cerrar el navegador.';
            }
        }
        updateLoginFooterNote();
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            try {
                const res = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email })
                });
                if (res.ok) {
                    window.location.href = '/';
                } else {
                    alert('Error al iniciar sesión');
                }
            } catch (err) {
                alert('Error de conexión');
            }
        });
    </script>
</body>
</html>'''
            self.send_html_response(login_html)
            return
        
        if session_id and not is_session_valid(session_id):
            self.send_response(302)
            self.send_header('Location', '/login')
            self.send_header('Set-Cookie', 'session_id=; Path=/; Max-Age=0')
            self.end_headers()
            return
        
        if not session_id:
            self.send_response(302)
            self.send_header('Location', '/login')
            self.end_headers()
            return
        
        update_session_activity(session_id)
        
        if self.path == '/':
            try:
                with open('index.html', 'r', encoding='utf-8') as f:
                    html_content = f.read()
                self.send_html_response(html_content)
            except FileNotFoundError:
                self.send_json_response(404, {'error': 'Not found'})
        elif self.path == '/tasks':
            tasks = leer_todos(session_id)
            self.send_json_response(200, tasks)
        elif self.path == '/test-email':
            smtp_user = os.environ.get('SMTP_USER')
            smtp_pass = os.environ.get('SMTP_PASS')
            
            if not smtp_user or not smtp_pass:
                self.send_json_response(400, {'status': 'error', 'message': 'SMTP no configurado. Agrega las variables de entorno SMTP_USER y SMTP_PASS.'})
                return
            
            test_email = smtp_user
            subject = 'Test de correo - AutoTask API'
            body = 'Este es un correo de prueba enviado desde AutoTask API. La configuración SMTP es correcta.'
            
            if send_email(test_email, subject, body):
                self.send_json_response(200, {'status': 'enviado', 'message': f'Correo de prueba enviado a {test_email}'})
            else:
                self.send_json_response(500, {'status': 'error', 'message': 'Error al enviar el correo de prueba. Verifica las credenciales SMTP.'})
        else:
            self.send_json_response(404, {'error': 'Not found'})
    
    def do_POST(self):
        session_id = self.get_session_id()
        
        if self.path == '/login':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
                email = data.get('email')
                if not email:
                    self.send_json_response(400, {'error': 'Email requerido'})
                    return
                new_session_id = secrets.token_hex(16)
                crear_session(new_session_id, email)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Set-Cookie', f'session_id={new_session_id}; Path=/; SameSite=Lax')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response(400, {'error': 'JSON inválido'})
            return
        
        if session_id and not is_session_valid(session_id):
            self.send_response(302)
            self.send_header('Location', '/login')
            self.send_header('Set-Cookie', 'session_id=; Path=/; Max-Age=0')
            self.end_headers()
            return
        
        if session_id:
            update_session_activity(session_id)
        
        if self.path == '/tasks':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
                title = data.get('title')
                description = data.get('description', '')
                category = data.get('category', '')
                priority = data.get('priority', 'media')
                due_date = data.get('due_date')
                owner_email = data.get('owner_email')
                
                if not title or not due_date or not owner_email:
                    self.send_json_response(400, {'error': 'Missing required fields'})
                    return
                
                new_task = crear(title, description, due_date, owner_email, session_id, category, priority)
                self.send_json_response(201, new_task)
            except json.JSONDecodeError:
                self.send_json_response(400, {'error': 'Invalid JSON'})
        else:
            self.send_json_response(404, {'error': 'Not found'})
    
    def do_PUT(self):
        session_id = self.get_session_id()
        
        if session_id and not is_session_valid(session_id):
            self.send_response(302)
            self.send_header('Location', '/login')
            self.send_header('Set-Cookie', 'session_id=; Path=/; Max-Age=0')
            self.end_headers()
            return
        
        if session_id:
            update_session_activity(session_id)
        
        if self.path.startswith('/tasks/'):
            try:
                task_id = int(self.path.split('/')[-1])
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(body) if body else {}
                
                updated_task = actualizar(
                    task_id,
                    title=data.get('title'),
                    description=data.get('description'),
                    category=data.get('category'),
                    priority=data.get('priority'),
                    due_date=data.get('due_date'),
                    status=data.get('status'),
                    owner_email=data.get('owner_email')
                )
                
                if updated_task:
                    self.send_json_response(200, updated_task)
                else:
                    self.send_json_response(404, {'error': 'Task not found'})
            except (ValueError, json.JSONDecodeError):
                self.send_json_response(400, {'error': 'Invalid input'})
        else:
            self.send_json_response(404, {'error': 'Not found'})
    
    def do_DELETE(self):
        session_id = self.get_session_id()
        
        if session_id and not is_session_valid(session_id):
            self.send_response(302)
            self.send_header('Location', '/login')
            self.send_header('Set-Cookie', 'session_id=; Path=/; Max-Age=0')
            self.end_headers()
            return
        
        if session_id:
            update_session_activity(session_id)
        
        if self.path.startswith('/tasks/'):
            try:
                task_id = int(self.path.split('/')[-1])
                deleted = eliminar(task_id)
                if deleted:
                    self.send_json_response(200, {'message': 'Task deleted'})
                else:
                    self.send_json_response(404, {'error': 'Task not found'})
            except ValueError:
                self.send_json_response(400, {'error': 'Invalid task ID'})
        else:
            self.send_json_response(404, {'error': 'Not found'})
    
    def log_message(self, format, *args):
        pass

def cleanup_thread():
    while True:
        time.sleep(300)
        permanent_mode = os.environ.get('PERMANENT_MODE', 'false').lower() == 'true'
        cleanup_old_sessions(permanent_mode)

def run_server():
    init_db()
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('0.0.0.0', port), TaskHandler)
    print(f'Server running on port {port}')
    cleaner = threading.Thread(target=cleanup_thread, daemon=True)
    cleaner.start()
    server.serve_forever()

if __name__ == '__main__':
    run_server()
