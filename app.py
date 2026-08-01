"""
Sistema CINA - Record Automatizado
Aplicación Flask para gestión de procedimientos clínicos odontológicos
"""
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
from werkzeug.utils import secure_filename
from datetime import datetime, date
import os
import uuid
import json
import random

from config import Config
from models import db, Usuario, Turno, TurnoEstudiante, TutorEstudiante, Procedimiento, NotaEstudiante, Asistencia, CodigoAcceso, LogActividad
from utils.excel_export import exportar_record_excel

app = Flask(__name__)
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicie sesión para acceder a esta página.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# ============================================================
# DECORADORES DE PERMISOS
# ============================================================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso denegado. Se requieren privilegios de administrador.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def docente_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol not in ['admin', 'docente_responsable']:
            flash('Acceso denegado. Se requieren privilegios de docente responsable.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def tutor_or_docente_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol not in ['admin', 'docente_responsable', 'tutor']:
            flash('Acceso denegado.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def generar_codigo_unico(rol):
    prefix = {'admin': 'ADM', 'docente_responsable': 'DOC', 'tutor': 'TUT', 'estudiante': 'EST'}
    return f"{prefix.get(rol, 'USR')}-{uuid.uuid4().hex[:8].upper()}"

def registrar_log(accion, detalle=None):
    log = LogActividad(
        usuario_id=current_user.id if current_user.is_authenticated else None,
        accion=accion,
        detalle=detalle,
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()

def calcular_estadisticas_estudiante(estudiante_id):
    """Calcula estadísticas completas de un estudiante"""
    proc_validados = Procedimiento.query.filter_by(
        estudiante_id=estudiante_id, estado='validado'
    ).all()

    proc_pendientes = Procedimiento.query.filter_by(
        estudiante_id=estudiante_id, estado='pendiente'
    ).count()

    proc_rechazados = Procedimiento.query.filter_by(
        estudiante_id=estudiante_id, estado='rechazado'
    ).count()

    notas = NotaEstudiante.query.filter_by(estudiante_id=estudiante_id).first()

    return {
        'procedimientos_validados': len(proc_validados),
        'procedimientos_pendientes': proc_pendientes,
        'procedimientos_rechazados': proc_rechazados,
        'nota_clinica': round(notas.nota_clinica, 2) if notas else 0,
        'nota_final': round(notas.nota_final, 2) if notas else 0
    }

# ============================================================
# RUTAS DE AUTENTICACIÓN
# ============================================================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        codigo = request.form.get('codigo', '').strip().upper()
        password = request.form.get('password', '')

        usuario = Usuario.query.filter_by(codigo_acceso=codigo, activo=True).first()

        if usuario and usuario.check_password(password):
            login_user(usuario, remember=True)
            registrar_log('Inicio de sesión', f'Usuario: {usuario.nombre_completo}')
            flash(f'Bienvenido, {usuario.nombre_completo}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Código o contraseña incorrectos.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    registrar_log('Cierre de sesión')
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        codigo_acceso = request.form.get('codigo_acceso', '').strip().upper()
        nombres = request.form.get('nombres', '').strip()
        apellidos = request.form.get('apellidos', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        # Validar código de acceso
        codigo = CodigoAcceso.query.filter_by(codigo=codigo_acceso, usado=False).first()
        if not codigo:
            flash('Código de acceso inválido o ya utilizado.', 'danger')
            return render_template('registro.html')

        if password != password_confirm:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('registro.html')

        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template('registro.html')

        # Verificar que no exista el usuario
        if Usuario.query.filter_by(codigo_acceso=codigo_acceso).first():
            flash('Ya existe un usuario con este código.', 'danger')
            return render_template('registro.html')

        # Crear usuario
        usuario = Usuario(
            codigo_acceso=codigo_acceso,
            nombres=nombres,
            apellidos=apellidos,
            email=email,
            rol=codigo.rol
        )
        usuario.set_password(password)

        db.session.add(usuario)

        # Marcar código como usado
        codigo.usado = True
        codigo.fecha_uso = datetime.utcnow()
        codigo.usado_por = usuario.id

        db.session.commit()

        registrar_log('Registro de usuario', f'Nuevo {codigo.rol}: {usuario.nombre_completo}')
        flash('Registro exitoso. Ahora puede iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('registro.html')


# ============================================================
# PERFIL DEL USUARIO (todos los roles)
# ============================================================

@app.route('/mi-perfil', methods=['GET', 'POST'])
@login_required
def mi_perfil():
    if request.method == 'POST':
        nombres = request.form.get('nombres', '').strip()
        apellidos = request.form.get('apellidos', '').strip()
        email = request.form.get('email', '').strip()
        telefono = request.form.get('telefono', '').strip()
        password_actual = request.form.get('password_actual', '')
        password_nueva = request.form.get('password_nueva', '')
        password_confirmar = request.form.get('password_confirmar', '')

        if not nombres or not apellidos:
            flash('Nombres y apellidos son obligatorios.', 'danger')
            return redirect(url_for('mi_perfil'))

        # Verificar que el email no esté en uso por otro usuario
        if email:
            existente = Usuario.query.filter(Usuario.email == email, Usuario.id != current_user.id).first()
            if existente:
                flash('Ese email ya está en uso por otro usuario.', 'danger')
                return redirect(url_for('mi_perfil'))

        current_user.nombres = nombres
        current_user.apellidos = apellidos
        current_user.email = email or None
        current_user.telefono = telefono or None

        cambio_password = password_actual or password_nueva or password_confirmar
        if cambio_password:
            if not current_user.check_password(password_actual):
                flash('La contraseña actual es incorrecta.', 'danger')
                return redirect(url_for('mi_perfil'))
            if len(password_nueva) < 6:
                flash('La nueva contraseña debe tener al menos 6 caracteres.', 'danger')
                return redirect(url_for('mi_perfil'))
            if password_nueva != password_confirmar:
                flash('Las contraseñas nuevas no coinciden.', 'danger')
                return redirect(url_for('mi_perfil'))
            current_user.set_password(password_nueva)
            registrar_log('Cambio de contraseña', f'Usuario: {current_user.nombre_completo}')

        db.session.commit()
        registrar_log('Actualización de perfil', f'Usuario: {current_user.nombre_completo}')
        flash('Perfil actualizado correctamente.', 'success')
        return redirect(url_for('mi_perfil'))

    return render_template('perfil.html')


# ============================================================
# DASHBOARD PRINCIPAL
# ============================================================

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.rol == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.rol == 'docente_responsable':
        return redirect(url_for('docente_dashboard'))
    elif current_user.rol == 'tutor':
        return redirect(url_for('tutor_dashboard'))
    elif current_user.rol == 'estudiante':
        return redirect(url_for('estudiante_dashboard'))
    return redirect(url_for('login'))

# ============================================================
# RUTAS DE ADMINISTRADOR
# ============================================================

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    stats = {
        'total_estudiantes': Usuario.query.filter_by(rol='estudiante').count(),
        'total_tutores': Usuario.query.filter_by(rol='tutor').count(),
        'total_docentes': Usuario.query.filter_by(rol='docente_responsable').count(),
        'total_procedimientos': Procedimiento.query.count(),
        'proc_pendientes': Procedimiento.query.filter_by(estado='pendiente').count(),
        'proc_validados': Procedimiento.query.filter_by(estado='validado').count(),
        'codigos_disponibles': CodigoAcceso.query.filter_by(usado=False).count(),
        'codigos_usados': CodigoAcceso.query.filter_by(usado=True).count(),
    }

    ultimos_procedimientos = Procedimiento.query.order_by(Procedimiento.fecha_registro.desc()).limit(10).all()
    ultimos_logs = LogActividad.query.order_by(LogActividad.fecha.desc()).limit(20).all()

    return render_template('admin_dashboard.html', stats=stats, 
                          ultimos_procedimientos=ultimos_procedimientos,
                          ultimos_logs=ultimos_logs)

@app.route('/admin/codigos', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_codigos():
    if request.method == 'POST':
        rol = request.form.get('rol')
        cantidad = int(request.form.get('cantidad', 1))
        descripcion = request.form.get('descripcion', '')

        codigos_generados = []
        for _ in range(cantidad):
            codigo_str = generar_codigo_unico(rol)
            codigo = CodigoAcceso(codigo=codigo_str, rol=rol, descripcion=descripcion)
            db.session.add(codigo)
            codigos_generados.append(codigo_str)

        db.session.commit()
        registrar_log('Generación de códigos', f'Rol: {rol}, Cantidad: {cantidad}')
        flash(f'Se generaron {cantidad} códigos de acceso para {rol}.', 'success')

        return render_template('codigos_generados.html', codigos=codigos_generados, rol=rol)

    codigos = CodigoAcceso.query.order_by(CodigoAcceso.fecha_creacion.desc()).all()
    return render_template('admin_codigos.html', codigos=codigos)


# Lista de estudiantes para importación masiva (edítala según tu clase real)
ESTUDIANTES_IMPORTAR = [
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


def generar_password_temporal():
    alfabeto = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sin 0/O/1/l ambiguos
    return ''.join(random.choice(alfabeto) for _ in range(8))


@app.route('/admin/importar-estudiantes', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_importar_estudiantes():
    if request.method == 'POST':
        try:
            # Precarga en 2 consultas (en vez de ~90) para que sea rápido incluso en hosting gratuito
            existentes = {
                u.apellidos for u in
                Usuario.query.filter_by(rol='estudiante')
                .filter(Usuario.apellidos.in_(ESTUDIANTES_IMPORTAR)).all()
            }
            codigos_en_uso = {c for (c,) in Usuario.query.with_entities(Usuario.codigo_acceso).all()}

            creados = []
            omitidos = []
            for apellidos in ESTUDIANTES_IMPORTAR:
                apellidos = apellidos.strip()
                if apellidos in existentes:
                    omitidos.append(apellidos)
                    continue

                codigo = generar_codigo_unico('estudiante')
                while codigo in codigos_en_uso:
                    codigo = generar_codigo_unico('estudiante')
                codigos_en_uso.add(codigo)
                password = generar_password_temporal()

                estudiante = Usuario(
                    codigo_acceso=codigo, nombres='', apellidos=apellidos,
                    rol='estudiante', activo=True,
                )
                estudiante.set_password(password, method='pbkdf2:sha256:20000')
                db.session.add(estudiante)
                creados.append({'apellidos': apellidos, 'codigo': codigo, 'password': password})

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al importar: {e}', 'danger')
            return redirect(url_for('admin_importar_estudiantes'))
        registrar_log('Importación masiva de estudiantes', f'Creados: {len(creados)}, Omitidos: {len(omitidos)}')
        if creados:
            flash(f'Se crearon {len(creados)} cuenta(s) de estudiante. Copia las credenciales antes de salir de esta página.', 'success')
        if omitidos:
            flash(f'{len(omitidos)} ya existían y se omitieron: {", ".join(omitidos)}', 'warning')
        return render_template('admin_importar_resultado.html', creados=creados)

    total_en_lista = len(ESTUDIANTES_IMPORTAR)
    ya_existentes = Usuario.query.filter(
        Usuario.rol == 'estudiante', Usuario.apellidos.in_(ESTUDIANTES_IMPORTAR)
    ).count()
    return render_template('admin_importar_estudiantes.html',
                            total_en_lista=total_en_lista, ya_existentes=ya_existentes,
                            lista=ESTUDIANTES_IMPORTAR)

@app.route('/admin/usuarios')
@login_required
@admin_required
def admin_usuarios():
    rol_filtro = request.args.get('rol', '')
    query = Usuario.query
    if rol_filtro:
        query = query.filter_by(rol=rol_filtro)
    usuarios = query.order_by(Usuario.apellidos).all()
    return render_template('admin_usuarios.html', usuarios=usuarios, rol_filtro=rol_filtro)

@app.route('/admin/usuario/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def admin_toggle_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    if usuario.id == current_user.id:
        flash('No puede desactivar su propia cuenta.', 'danger')
        return redirect(url_for('admin_usuarios'))

    usuario.activo = not usuario.activo
    db.session.commit()
    estado = 'activado' if usuario.activo else 'desactivado'
    registrar_log('Cambio estado usuario', f'{usuario.nombre_completo} {estado}')
    flash(f'Usuario {estado} correctamente.', 'success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/asignar-turnos', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_asignar_turnos():
    turnos = Turno.query.all()
    estudiantes_sin_turno = Usuario.query.filter_by(rol='estudiante').outerjoin(
        TurnoEstudiante, Usuario.id == TurnoEstudiante.estudiante_id
    ).filter(TurnoEstudiante.id == None).all()

    if request.method == 'POST':
        estudiante_id = request.form.get('estudiante_id')
        turno_id = request.form.get('turno_id')

        # Verificar si ya tiene turno
        existente = TurnoEstudiante.query.filter_by(estudiante_id=estudiante_id).first()
        if existente:
            existente.turno_id = turno_id
        else:
            asignacion = TurnoEstudiante(estudiante_id=estudiante_id, turno_id=turno_id)
            db.session.add(asignacion)

        db.session.commit()
        flash('Turno asignado correctamente.', 'success')
        return redirect(url_for('admin_asignar_turnos'))

    asignaciones = TurnoEstudiante.query.all()
    return render_template('admin_turnos.html', turnos=turnos, 
                          estudiantes=estudiantes_sin_turno,
                          asignaciones=asignaciones)

@app.route('/admin/asignar-tutores', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_asignar_tutores():
    tutores = Usuario.query.filter_by(rol='tutor').all()
    estudiantes_sin_tutor = Usuario.query.filter_by(rol='estudiante').outerjoin(
        TutorEstudiante, Usuario.id == TutorEstudiante.estudiante_id
    ).filter(TutorEstudiante.id == None).all()

    if request.method == 'POST':
        tutor_id = request.form.get('tutor_id')
        estudiante_id = request.form.get('estudiante_id')

        existente = TutorEstudiante.query.filter_by(estudiante_id=estudiante_id).first()
        if existente:
            existente.tutor_id = tutor_id
        else:
            asignacion = TutorEstudiante(tutor_id=tutor_id, estudiante_id=estudiante_id)
            db.session.add(asignacion)

        db.session.commit()
        flash('Tutor asignado correctamente.', 'success')
        return redirect(url_for('admin_asignar_tutores'))

    asignaciones = TutorEstudiante.query.all()
    return render_template('admin_tutores.html', tutores=tutores,
                          estudiantes=estudiantes_sin_tutor,
                          asignaciones=asignaciones)


# ============================================================
# RUTAS DE DOCENTE RESPONSABLE
# ============================================================

@app.route('/docente')
@login_required
@docente_required
def docente_dashboard():
    stats = {
        'total_estudiantes': Usuario.query.filter_by(rol='estudiante').count(),
        'total_procedimientos': Procedimiento.query.count(),
        'proc_pendientes': Procedimiento.query.filter_by(estado='pendiente').count(),
        'proc_validados': Procedimiento.query.filter_by(estado='validado').count(),
    }

    # Estudiantes con notas pendientes de ingresar
    estudiantes = Usuario.query.filter_by(rol='estudiante').order_by(Usuario.apellidos).all()
    estudiantes_data = []
    for est in estudiantes:
        stats_est = calcular_estadisticas_estudiante(est.id)
        notas = NotaEstudiante.query.filter_by(estudiante_id=est.id).first()
        estudiantes_data.append({
            'usuario': est,
            'stats': stats_est,
            'notas': notas
        })

    return render_template('docente_dashboard.html', stats=stats, estudiantes=estudiantes_data)

@app.route('/docente/notas', methods=['GET', 'POST'])
@login_required
@docente_required
def docente_notas():
    if request.method == 'POST':
        estudiante_id = request.form.get('estudiante_id')
        nota_caso = request.form.get('nota_caso_clinico', type=float)
        nota_actitud = request.form.get('nota_actitudinal', type=float)
        nota_trabajo = request.form.get('nota_trabajo_academico', type=float)

        notas = NotaEstudiante.query.filter_by(estudiante_id=estudiante_id).first()
        if not notas:
            notas = NotaEstudiante(estudiante_id=estudiante_id)
            db.session.add(notas)

        # Actualizar notas
        if nota_caso is not None:
            notas.nota_caso_clinico = min(max(nota_caso, 0), 20)
        if nota_actitud is not None:
            notas.nota_actitudinal = min(max(nota_actitud, 0), 20)
        if nota_trabajo is not None:
            notas.nota_trabajo_academico = min(max(nota_trabajo, 0), 20)

        notas.actualizado_por = current_user.id
        notas.fecha_actualizacion = datetime.utcnow()

        # Recalcular nota clínica y final
        proc_validados = Procedimiento.query.filter_by(estudiante_id=estudiante_id, estado='validado').all()
        notas.calcular_nota_clinica(proc_validados)

        db.session.commit()
        registrar_log('Actualización de notas', f'Estudiante ID: {estudiante_id}')
        flash('Notas actualizadas correctamente.', 'success')
        return redirect(url_for('docente_notas'))

    estudiantes = Usuario.query.filter_by(rol='estudiante').order_by(Usuario.apellidos).all()
    return render_template('docente_notas.html', estudiantes=estudiantes)

@app.route('/docente/exportar-excel')
@login_required
@docente_required
def docente_exportar_excel():
    filepath = exportar_record_excel()
    registrar_log('Exportación Excel', f'Archivo: {filepath}')
    return send_file(filepath, as_attachment=True, download_name='CINA_2026_I_RECORD_AUTOMATIZADO.xlsx')

# ============================================================
# RUTAS DE TUTOR
# ============================================================

@app.route('/tutor')
@login_required
def tutor_dashboard():
    if current_user.rol not in ['tutor', 'admin', 'docente_responsable']:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    # Obtener estudiantes asignados al tutor
    asignaciones = TutorEstudiante.query.filter_by(tutor_id=current_user.id).all()
    estudiantes_ids = [a.estudiante_id for a in asignaciones]

    estudiantes_data = []
    for est_id in estudiantes_ids:
        est = Usuario.query.get(est_id)
        if est:
            stats = calcular_estadisticas_estudiante(est_id)
            estudiantes_data.append({'usuario': est, 'stats': stats})

    # Procedimientos pendientes de sus estudiantes
    proc_pendientes = Procedimiento.query.filter(
        Procedimiento.estudiante_id.in_(estudiantes_ids),
        Procedimiento.estado == 'pendiente'
    ).order_by(Procedimiento.fecha_registro.desc()).all()

    return render_template('tutor_dashboard.html', 
                          estudiantes=estudiantes_data,
                          proc_pendientes=proc_pendientes)

@app.route('/tutor/validar-procedimientos', methods=['GET', 'POST'])
@login_required
def tutor_validar():
    if current_user.rol not in ['tutor', 'admin', 'docente_responsable']:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    # Obtener IDs de estudiantes asignados
    if current_user.rol == 'tutor':
        asignaciones = TutorEstudiante.query.filter_by(tutor_id=current_user.id).all()
        estudiantes_ids = [a.estudiante_id for a in asignaciones]
    else:
        estudiantes_ids = [e.id for e in Usuario.query.filter_by(rol='estudiante').all()]

    if request.method == 'POST':
        procedimiento_id = request.form.get('procedimiento_id')
        accion = request.form.get('accion')  # validar o rechazar
        comentario = request.form.get('comentario', '')

        proc = Procedimiento.query.get_or_404(procedimiento_id)

        if proc.estudiante_id not in estudiantes_ids and current_user.rol == 'tutor':
            flash('No tiene permiso para validar este procedimiento.', 'danger')
            return redirect(url_for('tutor_validar'))

        if accion == 'validar':
            proc.estado = 'validado'
            proc.validado_por = current_user.id
            proc.fecha_validacion = datetime.utcnow()
            proc.comentario_docente = comentario
            flash('Procedimiento validado correctamente.', 'success')
        elif accion == 'rechazar':
            proc.estado = 'rechazado'
            proc.validado_por = current_user.id
            proc.fecha_validacion = datetime.utcnow()
            proc.comentario_docente = comentario
            flash('Procedimiento rechazado.', 'warning')

        # Recalcular nota clínica del estudiante
        notas = NotaEstudiante.query.filter_by(estudiante_id=proc.estudiante_id).first()
        if not notas:
            notas = NotaEstudiante(estudiante_id=proc.estudiante_id)
            db.session.add(notas)

        proc_validados = Procedimiento.query.filter_by(estudiante_id=proc.estudiante_id, estado='validado').all()
        notas.calcular_nota_clinica(proc_validados)

        db.session.commit()
        registrar_log(f'Procedimiento {accion}', f'ID: {procedimiento_id}')
        return redirect(url_for('tutor_validar'))

    procedimientos = Procedimiento.query.filter(
        Procedimiento.estudiante_id.in_(estudiantes_ids)
    ).order_by(Procedimiento.fecha_registro.desc()).all()

    return render_template('tutor_validar.html', procedimientos=procedimientos)

# ============================================================
# RUTAS DE ESTUDIANTE
# ============================================================

@app.route('/estudiante')
@login_required
def estudiante_dashboard():
    if current_user.rol != 'estudiante':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    stats = calcular_estadisticas_estudiante(current_user.id)

    # Obtener turno asignado
    turno_asignado = TurnoEstudiante.query.filter_by(estudiante_id=current_user.id).first()

    # Últimos procedimientos
    ultimos_procedimientos = Procedimiento.query.filter_by(
        estudiante_id=current_user.id
    ).order_by(Procedimiento.fecha_registro.desc()).limit(10).all()

    # Notas
    notas = NotaEstudiante.query.filter_by(estudiante_id=current_user.id).first()

    # Conteo por tratamiento
    conteo_tratamientos = {}
    for t in Config.TRATAMIENTOS:
        validados = Procedimiento.query.filter_by(
            estudiante_id=current_user.id,
            tratamiento_codigo=t['codigo'],
            estado='validado'
        ).count()
        conteo_tratamientos[t['codigo']] = {
            'validados': validados,
            'requerido': t['requerido'],
            'puntos': min(validados, t['requerido']) * t['puntos_por_proc']
        }

    return render_template('estudiante_dashboard.html',
                          stats=stats,
                          turno=turno_asignado,
                          ultimos_procedimientos=ultimos_procedimientos,
                          notas=notas,
                          conteo_tratamientos=conteo_tratamientos,
                          tratamientos=Config.TRATAMIENTOS)

@app.route('/estudiante/registrar-procedimiento', methods=['GET', 'POST'])
@login_required
def estudiante_registrar_proc():
    if current_user.rol != 'estudiante':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    turno_asignado = TurnoEstudiante.query.filter_by(estudiante_id=current_user.id).first()

    if request.method == 'POST':
        tratamiento_codigo = request.form.get('tratamiento_codigo')
        fecha_realizacion = request.form.get('fecha_realizacion')
        paciente_nombre = request.form.get('paciente_nombre', '')
        paciente_edad = request.form.get('paciente_edad', type=int)
        diente_numero = request.form.get('diente_numero', '')
        descripcion = request.form.get('descripcion', '')

        # Validar fecha de realización contra turno
        fecha_proc = datetime.strptime(fecha_realizacion, '%Y-%m-%d').date()
        dia_semana = fecha_proc.weekday()  # 0=Lunes, 1=Martes, etc.

        if turno_asignado:
            turno = turno_asignado.turno
            if turno.tipo == 'martes_jueves' and dia_semana not in [1, 3]:  # Martes=1, Jueves=3
                flash('La fecha no corresponde a su turno asignado (Martes/Jueves).', 'danger')
                return redirect(url_for('estudiante_registrar_proc'))
            elif turno.tipo == 'sabado' and dia_semana != 5:  # Sábado=5
                flash('La fecha no corresponde a su turno asignado (Sábado).', 'danger')
                return redirect(url_for('estudiante_registrar_proc'))

        # Manejar archivo de evidencia
        evidencia_path = None
        evidencia_filename = None
        if 'evidencia' in request.files:
            file = request.files['evidencia']
            if file and file.filename and allowed_file(file.filename):
                evidencia_filename = secure_filename(file.filename)
                unique_name = f"{uuid.uuid4().hex}_{evidencia_filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                file.save(filepath)
                evidencia_path = filepath
                evidencia_filename = unique_name

        proc = Procedimiento(
            estudiante_id=current_user.id,
            tratamiento_codigo=tratamiento_codigo,
            fecha_realizacion=fecha_proc,
            paciente_nombre=paciente_nombre,
            paciente_edad=paciente_edad,
            diente_numero=diente_numero,
            descripcion=descripcion,
            evidencia_filename=evidencia_filename,
            evidencia_path=evidencia_path,
            estado='pendiente',
            turno_id=turno_asignado.turno_id if turno_asignado else None
        )

        db.session.add(proc)
        db.session.commit()

        registrar_log('Registro de procedimiento', f'Tratamiento: {tratamiento_codigo}')
        flash('Procedimiento registrado correctamente. Pendiente de validación.', 'success')
        return redirect(url_for('estudiante_dashboard'))

    return render_template('estudiante_registrar.html', 
                          tratamientos=Config.TRATAMIENTOS,
                          turno=turno_asignado)


# ============================================================
# RUTAS DE ASISTENCIAS
# ============================================================

@app.route('/asistencias', methods=['GET', 'POST'])
@login_required
def asistencias():
    if current_user.rol not in ['admin', 'docente_responsable', 'tutor']:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    turnos = Turno.query.all()
    fecha_hoy = date.today().isoformat()

    if request.method == 'POST':
        turno_id = request.form.get('turno_id')
        fecha_str = request.form.get('fecha')
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()

        # Obtener estudiantes del turno
        if current_user.rol == 'tutor':
            # Solo estudiantes asignados al tutor
            asignaciones_tutor = TutorEstudiante.query.filter_by(tutor_id=current_user.id).all()
            estudiantes_ids = [a.estudiante_id for a in asignaciones_tutor]
            turno_estudiantes = TurnoEstudiante.query.filter_by(turno_id=turno_id).filter(
                TurnoEstudiante.estudiante_id.in_(estudiantes_ids)
            ).all()
        else:
            turno_estudiantes = TurnoEstudiante.query.filter_by(turno_id=turno_id).all()

        for te in turno_estudiantes:
            estado = request.form.get(f'estado_{te.estudiante_id}', 'presente')
            observacion = request.form.get(f'observacion_{te.estudiante_id}', '')

            # Buscar o crear asistencia
            asistencia = Asistencia.query.filter_by(
                estudiante_id=te.estudiante_id,
                turno_id=turno_id,
                fecha=fecha
            ).first()

            if asistencia:
                asistencia.estado = estado
                asistencia.observacion = observacion
                asistencia.registrado_por = current_user.id
            else:
                asistencia = Asistencia(
                    estudiante_id=te.estudiante_id,
                    turno_id=turno_id,
                    fecha=fecha,
                    estado=estado,
                    observacion=observacion,
                    registrado_por=current_user.id
                )
                db.session.add(asistencia)

        db.session.commit()
        registrar_log('Registro de asistencias', f'Turno: {turno_id}, Fecha: {fecha}')
        flash('Asistencias registradas correctamente.', 'success')
        return redirect(url_for('asistencias'))

    # Obtener asistencias del día
    turno_id = request.args.get('turno_id', type=int)
    fecha_filtro = request.args.get('fecha', fecha_hoy)
    fecha_obj = datetime.strptime(fecha_filtro, '%Y-%m-%d').date()

    asistencias_data = []
    if turno_id:
        if current_user.rol == 'tutor':
            asignaciones_tutor = TutorEstudiante.query.filter_by(tutor_id=current_user.id).all()
            estudiantes_ids = [a.estudiante_id for a in asignaciones_tutor]
            turno_estudiantes = TurnoEstudiante.query.filter_by(turno_id=turno_id).filter(
                TurnoEstudiante.estudiante_id.in_(estudiantes_ids)
            ).all()
        else:
            turno_estudiantes = TurnoEstudiante.query.filter_by(turno_id=turno_id).all()

        for te in turno_estudiantes:
            asistencia = Asistencia.query.filter_by(
                estudiante_id=te.estudiante_id,
                turno_id=turno_id,
                fecha=fecha_obj
            ).first()

            total_asistencias = Asistencia.query.filter_by(
                estudiante_id=te.estudiante_id, estado='presente'
            ).count()
            total_faltas = Asistencia.query.filter_by(
                estudiante_id=te.estudiante_id, estado='ausente'
            ).count()

            asistencias_data.append({
                'estudiante': te.estudiante,
                'asistencia': asistencia,
                'total_presente': total_asistencias,
                'total_ausente': total_faltas
            })

    return render_template('asistencias.html', turnos=turnos, 
                          asistencias=asistencias_data,
                          turno_id=turno_id, fecha_filtro=fecha_filtro)

@app.route('/estudiante/mis-asistencias')
@login_required
def estudiante_asistencias():
    if current_user.rol != 'estudiante':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    asistencias = Asistencia.query.filter_by(estudiante_id=current_user.id).order_by(Asistencia.fecha.desc()).all()

    total_presente = sum(1 for a in asistencias if a.estado == 'presente')
    total_ausente = sum(1 for a in asistencias if a.estado == 'ausente')
    total_tardanza = sum(1 for a in asistencias if a.estado == 'tardanza')

    return render_template('estudiante_asistencias.html',
                          asistencias=asistencias,
                          total_presente=total_presente,
                          total_ausente=total_ausente,
                          total_tardanza=total_tardanza)

# ============================================================
# APIS JSON
# ============================================================

@app.route('/api/estudiante/<int:id>/procedimientos')
@login_required
def api_procedimientos_estudiante(id):
    if current_user.rol not in ['admin', 'docente_responsable', 'tutor']:
        if current_user.id != id:
            return jsonify({'error': 'Acceso denegado'}), 403

    # Si es tutor, verificar que el estudiante esté asignado
    if current_user.rol == 'tutor':
        asignacion = TutorEstudiante.query.filter_by(tutor_id=current_user.id, estudiante_id=id).first()
        if not asignacion:
            return jsonify({'error': 'No tiene acceso a este estudiante'}), 403

    procedimientos = Procedimiento.query.filter_by(estudiante_id=id).order_by(Procedimiento.fecha_registro.desc()).all()

    return jsonify([{
        'id': p.id,
        'tratamiento': p.tratamiento_codigo,
        'fecha': p.fecha_realizacion.isoformat(),
        'paciente': p.paciente_nombre,
        'estado': p.estado,
        'comentario': p.comentario_docente,
        'fecha_registro': p.fecha_registro.isoformat()
    } for p in procedimientos])

@app.route('/api/estudiante/<int:id>/notas')
@login_required
def api_notas_estudiante(id):
    if current_user.rol not in ['admin', 'docente_responsable', 'tutor']:
        if current_user.id != id:
            return jsonify({'error': 'Acceso denegado'}), 403

    notas = NotaEstudiante.query.filter_by(estudiante_id=id).first()
    if not notas:
        return jsonify({
            'nota_clinica': 0,
            'nota_caso_clinico': None,
            'nota_actitudinal': None,
            'nota_trabajo_academico': None,
            'nota_final': 0
        })

    return jsonify({
        'nota_clinica': round(notas.nota_clinica, 2),
        'nota_caso_clinico': notas.nota_caso_clinico,
        'nota_actitudinal': notas.nota_actitudinal,
        'nota_trabajo_academico': notas.nota_trabajo_academico,
        'nota_final': round(notas.nota_final, 2)
    })

# ============================================================
# INICIALIZACIÓN
# ============================================================

def init_db():
    with app.app_context():
        db.create_all()

        # Crear turnos si no existen
        if Turno.query.count() == 0:
            turnos_data = [
                ('martes_jueves', 'mañana', 'Martes y Jueves - Mañana'),
                ('martes_jueves', 'tarde', 'Martes y Jueves - Tarde'),
                ('sabado', 'mañana', 'Sábado - Mañana'),
                ('sabado', 'tarde', 'Sábado - Tarde'),
            ]
            for tipo, horario, nombre in turnos_data:
                db.session.add(Turno(tipo=tipo, horario=horario, nombre=nombre))
            db.session.commit()
            print("✅ Turnos creados")

        # Crear admin por defecto si no existe
        if not Usuario.query.filter_by(rol='admin').first():
            admin = Usuario(
                codigo_acceso='ADMIN-2026',
                nombres='Administrador',
                apellidos='Sistema',
                email='admin@cina.edu',
                rol='admin'
            )
            admin.set_password('admin2026')
            db.session.add(admin)
            db.session.commit()
            print("✅ Usuario admin creado: ADMIN-2026 / admin2026")

# Se ejecuta siempre al importar este módulo (idempotente: solo crea lo que falte).
# Es necesario aquí, y no solo dentro de __main__, porque servidores WSGI como
# Passenger (cPanel) o gunicorn importan la app sin ejecutar el bloque __main__.
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
