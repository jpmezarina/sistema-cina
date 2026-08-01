# Sistema CINA - Record Automatizado

Aplicación Flask para la gestión del record clínico odontológico (procedimientos,
notas, asistencias, turnos y validaciones) de la Clínica Integral (CINA 2026).

## Instalación

```bash
python3 -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración (opcional)

Copia `.env.example` a `.env` y ajusta `SECRET_KEY` para producción.
Por defecto usa una base de datos SQLite local (`database.db`) y una
SECRET_KEY de desarrollo, así que también funciona sin `.env`.

## Ejecución

```bash
python app.py
```

La aplicación queda disponible en `http://localhost:5001`.

> **Nota (macOS):** se usa el puerto 5001 en vez de 5000 porque macOS
> (Monterey en adelante) reserva el 5000 para "AirPlay Receiver". Si
> quieres otro puerto, define la variable de entorno `PORT`, por ejemplo:
> `PORT=8000 python app.py`.
En el primer arranque se crean automáticamente:
- Los 4 turnos (Martes/Jueves y Sábado, mañana/tarde).
- Un usuario administrador por defecto: **código `ADMIN-2026`, contraseña `admin2026`**.

## Flujo de uso

1. Inicia sesión como admin (`ADMIN-2026` / `admin2026`).
2. Genera códigos de acceso para docente, tutor(es) y estudiante(s) en "Códigos de Acceso".
3. Cada usuario se registra en `/registro` usando su código y crea su propia contraseña.
4. Admin asigna turno y tutor a cada estudiante.
5. El estudiante registra procedimientos clínicos (con evidencia opcional).
6. El tutor valida o rechaza los procedimientos.
7. El docente responsable ingresa notas (caso clínico, actitudinal, trabajo académico);
   la nota clínica se calcula automáticamente según los procedimientos validados.
8. El docente puede exportar el record completo a Excel.

## Estructura del proyecto

```
app.py                 # Rutas y lógica de la aplicación
config.py               # Configuración y catálogo de tratamientos
models.py                # Modelos SQLAlchemy
requirements.txt
templates/                # Vistas Jinja2 (incluye base.html)
static/uploads/evidencias/  # Evidencias subidas por estudiantes
static/exports/              # Excel generados
utils/excel_export.py     # Generación del record en Excel
```
