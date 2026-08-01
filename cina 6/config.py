"""
Configuración del Sistema CINA - Record Automatizado
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cina-2026-sistema-clinico-secreto'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(BASE_DIR, "database.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'evidencias')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx'}

    # Configuración de turnos
    TURNOS = {
        'martes_jueves': {
            'nombre': 'Martes y Jueves',
            'horarios': ['mañana', 'tarde']
        },
        'sabado': {
            'nombre': 'Sábado',
            'horarios': ['mañana', 'tarde']
        }
    }

    # Tratamientos del Excel (orden y configuración)
    TRATAMIENTOS = [
        {'codigo': 'RE', 'nombre': 'Restauración Estética', 'requerido': 6, 'puntos_por_proc': 0.25, 'max_puntos': 1.5},
        {'codigo': 'IHO', 'nombre': 'Instrucción de Higiene Oral', 'requerido': 6, 'puntos_por_proc': 0.25, 'max_puntos': 1.5},
        {'codigo': 'FLUOR', 'nombre': 'Aplicación de Flúor', 'requerido': 4, 'puntos_por_proc': 0.375, 'max_puntos': 1.5},
        {'codigo': 'SELLANTE', 'nombre': 'Sellantes', 'requerido': 8, 'puntos_por_proc': 0.1875, 'max_puntos': 1.5},
        {'codigo': 'IONOMERO', 'nombre': 'Ionomero de Vidrio', 'requerido': 3, 'puntos_por_proc': 0.5, 'max_puntos': 1.5},
        {'codigo': 'RESINA', 'nombre': 'Resina Compuesta', 'requerido': 3, 'puntos_por_proc': 0.5, 'max_puntos': 1.5},
        {'codigo': 'PULPO', 'nombre': 'Tratamiento de Pulpo', 'requerido': 1, 'puntos_por_proc': 1.5, 'max_puntos': 1.5},
        {'codigo': 'PULPEC', 'nombre': 'Pulpectomía', 'requerido': 1, 'puntos_por_proc': 1.5, 'max_puntos': 1.5},
        {'codigo': 'RPD_RPI', 'nombre': 'RPD/RPI', 'requerido': 1, 'puntos_por_proc': 1.5, 'max_puntos': 1.5},
        {'codigo': 'OTROS_PULP', 'nombre': 'Otros Tx Pulpares', 'requerido': 1, 'puntos_por_proc': 1.5, 'max_puntos': 1.5},
        {'codigo': 'EXO', 'nombre': 'Cirugías (Exodoncia)', 'requerido': 3, 'puntos_por_proc': 0.5, 'max_puntos': 1.5},
        {'codigo': 'RO', 'nombre': 'Rehabilitación Oral', 'requerido': 4, 'puntos_por_proc': 0.375, 'max_puntos': 1.5},
    ]
