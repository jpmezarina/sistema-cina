"""
Genera fichas imprimibles de credenciales - Sistema CINA
===========================================================
Lee credenciales_estudiantes.csv (generado por seed_estudiantes.py)
y produce un archivo HTML con una "ficha" recortable por estudiante,
lista para imprimir y entregar en mano.

USO
---
    python generar_fichas_credenciales.py

Genera: fichas_credenciales.html
Ábrelo en el navegador y usa Archivo -> Imprimir (o "Guardar como PDF").
Cada ficha trae líneas punteadas para recortar.
"""
import csv
import os
import sys

CSV_PATH = 'credenciales_estudiantes.csv'
OUT_PATH = 'fichas_credenciales.html'
URL_SISTEMA = 'http://TU-DOMINIO-O-IP-AQUI'  # <-- cambia esto por la URL real de tu sistema

HTML_HEAD = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Fichas de Acceso - CINA 2026</title>
<style>
  @page { size: A4; margin: 12mm; }
  body { font-family: Arial, Helvetica, sans-serif; margin: 0; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; }
  .ficha {
    border: 1px dashed #999;
    border-radius: 6px;
    padding: 10px 14px;
    page-break-inside: avoid;
  }
  .ficha h3 { margin: 0 0 6px 0; font-size: 13px; color: #1a2634; text-transform: uppercase; }
  .ficha .campo { font-size: 12px; margin: 3px 0; }
  .ficha .campo b { display: inline-block; width: 70px; color: #444; }
  .ficha .codigo { font-family: 'Courier New', monospace; font-size: 13px; background: #f0f4f8; padding: 2px 6px; border-radius: 3px; }
  .ficha .aviso { font-size: 10px; color: #b8860b; margin-top: 6px; }
  .ficha .url { font-size: 10px; color: #555; margin-top: 4px; word-break: break-all; }
</style>
</head>
<body>
<div class="grid">
"""

FICHA_TEMPLATE = """
  <div class="ficha">
    <h3>{apellidos}</h3>
    <div class="campo"><b>Usuario:</b> <span class="codigo">{codigo}</span></div>
    <div class="campo"><b>Clave:</b> <span class="codigo">{password}</span></div>
    <div class="url">Ingresa en: {url}</div>
    <div class="aviso">⚠️ Cambia tu clave en "Mi Perfil" al ingresar por primera vez.</div>
  </div>
"""

HTML_TAIL = """
</div>
</body>
</html>
"""


def main():
    if not os.path.exists(CSV_PATH):
        print(f"❌ No se encontró {CSV_PATH}. Corre primero seed_estudiantes.py")
        sys.exit(1)

    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        filas = list(csv.DictReader(f))

    if not filas:
        print("❌ El CSV está vacío.")
        sys.exit(1)

    with open(OUT_PATH, 'w', encoding='utf-8') as out:
        out.write(HTML_HEAD)
        for fila in filas:
            out.write(FICHA_TEMPLATE.format(
                apellidos=fila['apellidos'],
                codigo=fila['codigo'],
                password=fila['password'],
                url=URL_SISTEMA,
            ))
        out.write(HTML_TAIL)

    print(f"✅ Generado: {OUT_PATH} ({len(filas)} ficha(s))")
    print("   Ábrelo en tu navegador y usa Archivo > Imprimir (o Guardar como PDF).")


if __name__ == '__main__':
    main()
