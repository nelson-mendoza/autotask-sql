
# AutoTask

Gestor de tareas que te avisa por email cuando una tarea vence hoy. Simple, sin complicaciones.

<img style="display: block; margin: 0 auto; max-width: 100%; height: auto;" 
     width="350" 
     alt="autotask_api" 
     src="https://github.com/user-attachments/assets/1513119e-fead-4d52-ae3b-57fd5450e95d" />

## ¿Qué hace?

- Creas tareas con fecha límite
- El sistema verifica cada 15 minutos si hay tareas que vencen hoy
- Te envía un email de recordatorio automáticamente
- Todo se guarda en una base de datos SQLite

## ¿Para quién es?


Para cualquiera que necesite:
- Recordatorios de tareas importantes
- Un sistema simple sin frameworks complejos
- Notificaciones reales por email

## Empezar en 1 minuto

```bash
python app.py
```

Abre http://localhost:8000 y listo.

## Configurar notificaciones por email (opcional)

Si quieres recibir los recordatorios:

1. En tu cuenta de Google: Seguridad → Verificación en 2 pasos → Contraseñas de aplicaciones
2. Genera una contraseña para "Correo"
3. Copia los 16 caracteres
4. Crea un archivo `.env` o exporta las variables:

```bash
export SMTP_USER=tu_email@gmail.com
export SMTP_PASS=los_16_caracteres
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=465
```

## Cómo funciona

### Interfaz web

Entras a http://localhost:8000, te registras con tu email y puedes:

- **Crear tareas**: Título, descripción, categoría, prioridad, fecha límite y tu email
- **Ver todas tus tareas**: Con badges de color según estado y prioridad
- **Editar tareas**: Actualiza cualquier campo
- **Completar o eliminar**: Cuando ya no necesites una tarea

### Dos modos de sesión

- **Temporal (default)**: Los datos se borran después de 15 min de inactividad
- **Permanente**: Los datos persisten hasta que los borres manualmente

Puedes cambiar entre ellos desde la interfaz.

### API REST

Si prefieres usar la terminal:

```bash
# Login (guarda la cookie)
curl -c cookies.txt -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email":"tu@email.com"}'

# Crear tarea
curl -b cookies.txt -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Entregar proyecto",
    "description": "Finalizar módulo de Python",
    "category": "Trabajo",
    "priority": "alta",
    "due_date": "2025-12-31",
    "owner_email": "tu@email.com"
  }'

# Listar tareas
curl -b cookies.txt http://localhost:8000/tasks

# Editar tarea (ID: 1)
curl -b cookies.txt -X PUT http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "completado"}'

# Eliminar tarea
curl -b cookies.txt -X DELETE http://localhost:8000/tasks/1

# Probar envío de email
curl -b cookies.txt http://localhost:8000/test-email

# Cerrar sesión
curl -b cookies.txt -X POST http://localhost:8000/logout
```

## Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/login` | Formulario de login |
| POST | `/login` | Iniciar sesión (recibe cookie) |
| GET | `/` | Dashboard (requiere sesión) |
| GET | `/tasks` | Listar tareas de tu sesión |
| POST | `/tasks` | Crear nueva tarea |
| PUT | `/tasks/<id>` | Actualizar tarea |
| DELETE | `/tasks/<id>` | Eliminar tarea |
| GET | `/test-email` | Enviar email de prueba |
| POST | `/logout` | Cerrar sesión |

## Tecnologías

- **Python 3** (biblioteca estándar, sin frameworks)
- **SQLite** para la base de datos
- **HTML/CSS/JS** puro para el frontend
- **SMTP** para envío de emails

## ¿Dónde probarlo?

Disponible en: https://autotask-sql.onrender.com/login

---

Hecho por Nelson Abner Mendoza Pérez - Si algo falla o quieres mejorarlo, avísame: nelson.abner.mendoza.perez@outlook.com
