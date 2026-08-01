"""
Punto de entrada WSGI para cPanel (Python App / Passenger).

cPanel genera automáticamente un passenger_wsgi.py "stub" al crear la
Python App. Este archivo debe REEMPLAZAR ese stub: Passenger busca en
este archivo una variable llamada `application`, que aquí apunta al
objeto Flask definido en app.py (la variable `app`).
"""
import sys
import os

# Asegura que el directorio del proyecto esté en el path de Python
sys.path.insert(0, os.path.dirname(__file__))

from app import app as application
