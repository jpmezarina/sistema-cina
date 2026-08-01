"""
Script de carga masiva de estudiantes - Sistema CINA
=======================================================
Crea directamente una cuenta (usuario + clave) para cada estudiante
de la lista, sin pasar por el flujo de "generar código -> auto-registro".

CÓMO USARLO
-----------
1. Copia este archivo en la raíz del proyecto (junto a app.py).
2. Revisa/edita la lista ESTUDIANTES más abajo si hace falta.
3. Ejecuta UNA sola vez:

       python seed_estudiantes.py

4. Al terminar, se genera el archivo `credenciales_estudiantes.csv`
   con el usuario y clave de cada estudiante, listo para imprimir
   o compartir. GUÁRDALO EN UN LUGAR SEGURO Y BÓRRALO DEL SERVIDOR
   después de entregar las credenciales (contiene claves en texto
   plano solo para esta única entrega inicial).

Es seguro volver a ejecutarlo: si un estudiante ya existe (mismo
apellido), lo salta y no crea duplicados ni le cambia la clave.

Cada estudiante entra a la app con su "Código de Acceso" (usuario)
y su clave, y luego puede completar su nombre y cambiar su clave
desde "Mi Perfil".
"""
import csv
import random
import string
import uuid

from app import app, db
from models import Usuario

# ------------------------------------------------------------------
# Lista de estudiantes (apellidos tomados del Excel subido).
# Puedes editar/agregar/quitar nombres aquí libremente.
# ------------------------------------------------------------------
ESTUDIANTES = [
    "AGUIRRE ARROYO", "ANCALLA TARQUI", "ARIZA SOLIS", "AROCUTIPA CHOQUEHUANCA",
    "ATOCHE ANICAMA", "BERROCAL SALVATIERRA", "BRAVO SAMAME", "CABALLERO HUAMANTALLA",
    "CABRERA VELA", "CADILLO LAURA", "CALLALLI FLORES", "CANALES LOYOLA",
    "CARRILLO PAULINO", "CHAFLOQUE OSORIO", "CHAPOÑAN ARROYO", "CHICANA BECERRA",
    "CHICO ORMEÑO", "CHOQUEHUANCA OBREGON", "CIPRIAN MENESES", "ESPINOZA PAISIG",
    "EVANGELISTA PARRA", "GAMA CCAPA", "GOMEZ RAMIREZ", "HERNÁNDEZ FARFÁN",
    "LAVADO BASILIO", "LEYVA MARIÑO", "MATTA CARRANZA", "MEDINA GARCIA",
    "MINAYA CADILLO", "ORTEGA TORRES", "OSORIO ALEGRIA", "PALOMINO CARRILLO",
    "PAUCAR PEÑA", "PEREZ CONDOR", "PUMACHAGUA LUQUE", "RAMOS AREVALO",
    "ROMERO ACOSTA", "SALVADOR SANTILLANA", "SANABRIA HUERTA", "SUÁREZ QUISPE",
    "TERREL JUAN DE DIOS", "TOCTO FACUNDO", "TORRES AGUIRRE", "USCUVILCA CABRERA",
    "VILCHEZ ARTEAGA", "VILLANO ÑUFLO", "ZAMORA DEL CARPIO",
]


def generar_codigo():
    return f"EST-{uuid.uuid4().hex[:8].upper()}"


def generar_password():
    """Clave de 8 caracteres, fácil de leer/transcribir (sin 0/O/1/l ambiguos)."""
    alfabeto = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return ''.join(random.choice(alfabeto) for _ in range(8))


def main():
    creados = []
    with app.app_context():
        for apellidos in ESTUDIANTES:
            apellidos = apellidos.strip()

            # Evita duplicados si el script se corre más de una vez
            existente = Usuario.query.filter_by(apellidos=apellidos, rol='estudiante').first()
            if existente:
                print(f"–  Ya existe: {apellidos} ({existente.codigo_acceso}) — se omite")
                continue

            codigo = generar_codigo()
            # Aseguro que el código no choque con uno ya usado (muy improbable, pero por si acaso)
            while Usuario.query.filter_by(codigo_acceso=codigo).first():
                codigo = generar_codigo()

            password = generar_password()

            estudiante = Usuario(
                codigo_acceso=codigo,
                nombres='',                # el estudiante lo completa en "Mi Perfil"
                apellidos=apellidos,
                rol='estudiante',
                activo=True,
            )
            estudiante.set_password(password)
            db.session.add(estudiante)
            db.session.commit()

            creados.append({'apellidos': apellidos, 'codigo': codigo, 'password': password})
            print(f"✅ Creado: {apellidos:<30} usuario={codigo}  clave={password}")

        # Guarda el detalle en un CSV para imprimir/repartir
        if creados:
            with open('credenciales_estudiantes.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['apellidos', 'codigo', 'password'])
                writer.writeheader()
                writer.writerows(creados)
            print(f"\n📄 Guardado: credenciales_estudiantes.csv ({len(creados)} estudiante(s))")
        else:
            print("\nNo se creó ningún estudiante nuevo (todos ya existían).")


if __name__ == '__main__':
    main()
