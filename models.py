"""
Modelos de Base de Datos - Sistema CINA
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    codigo_acceso = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    rol = db.Column(db.String(20), nullable=False)  # admin, docente_responsable, tutor, estudiante
    password_hash = db.Column(db.String(256), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Campos específicos por rol
    telefono = db.Column(db.String(20), nullable=True)

    # Relaciones
    estudiante_turno = db.relationship('TurnoEstudiante', backref='estudiante', uselist=False, cascade='all, delete-orphan')
    procedimientos = db.relationship('Procedimiento', backref='estudiante_obj', lazy='dynamic', foreign_keys='Procedimiento.estudiante_id')
    tutor_estudiantes = db.relationship('TutorEstudiante', backref='tutor', lazy='dynamic', foreign_keys='TutorEstudiante.tutor_id')
    asistencias = db.relationship('Asistencia', backref='estudiante_obj', lazy='dynamic', foreign_keys='Asistencia.estudiante_id')
    notas = db.relationship('NotaEstudiante', backref='estudiante_obj', uselist=False, cascade='all, delete-orphan', foreign_keys='NotaEstudiante.estudiante_id')

    def set_password(self, password, method='scrypt'):
        self.password_hash = generate_password_hash(password, method=method)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def nombre_completo(self):
        return f"{self.apellidos} {self.nombres}".strip()

    @property
    def is_active(self):
        return self.activo

    def __repr__(self):
        return f'<Usuario {self.nombre_completo} ({self.rol})>'


class Turno(db.Model):
    __tablename__ = 'turnos'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # martes_jueves, sabado
    horario = db.Column(db.String(20), nullable=False)  # mañana, tarde
    nombre = db.Column(db.String(50), nullable=False)
    activo = db.Column(db.Boolean, default=True)

    # Relaciones
    estudiantes = db.relationship('TurnoEstudiante', backref='turno', lazy='dynamic')
    asistencias = db.relationship('Asistencia', backref='turno', lazy='dynamic')

    def __repr__(self):
        return f'<Turno {self.nombre}>'


class TurnoEstudiante(db.Model):
    __tablename__ = 'turno_estudiantes'

    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, unique=True)
    turno_id = db.Column(db.Integer, db.ForeignKey('turnos.id'), nullable=False)
    fecha_asignacion = db.Column(db.DateTime, default=datetime.utcnow)


class TutorEstudiante(db.Model):
    __tablename__ = 'tutor_estudiantes'

    id = db.Column(db.Integer, primary_key=True)
    tutor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, unique=True)
    fecha_asignacion = db.Column(db.DateTime, default=datetime.utcnow)

    estudiante = db.relationship('Usuario', foreign_keys=[estudiante_id], backref='mi_tutor')


class Procedimiento(db.Model):
    __tablename__ = 'procedimientos'

    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    tratamiento_codigo = db.Column(db.String(20), nullable=False)  # RE, IHO, FLUOR, etc.

    # Datos del procedimiento
    fecha_realizacion = db.Column(db.Date, nullable=False)
    paciente_nombre = db.Column(db.String(100), nullable=True)
    paciente_edad = db.Column(db.Integer, nullable=True)
    diente_numero = db.Column(db.String(20), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)

    # Evidencia
    evidencia_filename = db.Column(db.String(255), nullable=True)
    evidencia_path = db.Column(db.String(500), nullable=True)

    # Estado y validación
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, validado, rechazado
    validado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    fecha_validacion = db.Column(db.DateTime, nullable=True)
    comentario_docente = db.Column(db.Text, nullable=True)

    # Metadatos
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    turno_id = db.Column(db.Integer, db.ForeignKey('turnos.id'), nullable=True)

    validador = db.relationship('Usuario', foreign_keys=[validado_por])
    turno = db.relationship('Turno')

    def __repr__(self):
        return f'<Procedimiento {self.tratamiento_codigo} - {self.estado}>'


class NotaEstudiante(db.Model):
    __tablename__ = 'notas_estudiantes'

    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, unique=True)

    # Notas ingresadas por el docente (0-20)
    nota_caso_clinico = db.Column(db.Float, nullable=True)
    nota_actitudinal = db.Column(db.Float, nullable=True)
    nota_trabajo_academico = db.Column(db.Float, nullable=True)

    # Nota clínica calculada automáticamente (máx 18)
    nota_clinica = db.Column(db.Float, default=0)

    # Nota final calculada
    nota_final = db.Column(db.Float, default=0)

    # Metadatos
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    actualizado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

    actualizador = db.relationship('Usuario', foreign_keys=[actualizado_por])

    def calcular_nota_clinica(self, procedimientos_validados):
        """Calcula la nota clínica basada en procedimientos validados"""
        from config import Config
        puntaje_total = 0

        for tratamiento in Config.TRATAMIENTOS:
            codigo = tratamiento['codigo']
            requerido = tratamiento['requerido']
            puntos_por_proc = tratamiento['puntos_por_proc']
            max_puntos = tratamiento['max_puntos']

            # Contar procedimientos validados de este tipo
            count = sum(1 for p in procedimientos_validados if p.tratamiento_codigo == codigo)
            puntaje = min(count, requerido) * puntos_por_proc
            puntaje_total += min(puntaje, max_puntos)

        self.nota_clinica = min(puntaje_total, 18)
        self.calcular_nota_final()
        return self.nota_clinica

    def calcular_nota_final(self):
        """Nota Final = Clínica×0.70 + Caso×0.10 + Actitud×0.10 + Trabajo×0.10"""
        caso = (self.nota_caso_clinico or 0) * 0.10
        actitud = (self.nota_actitudinal or 0) * 0.10
        trabajo = (self.nota_trabajo_academico or 0) * 0.10
        clinica = (self.nota_clinica or 0) * 0.70

        self.nota_final = round(clinica + caso + actitud + trabajo, 2)
        return self.nota_final


class Asistencia(db.Model):
    __tablename__ = 'asistencias'

    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    turno_id = db.Column(db.Integer, db.ForeignKey('turnos.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    estado = db.Column(db.String(20), default='presente')  # presente, ausente, tardanza, justificado
    observacion = db.Column(db.Text, nullable=True)
    registrado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    registrador = db.relationship('Usuario', foreign_keys=[registrado_por])

    __table_args__ = (db.UniqueConstraint('estudiante_id', 'turno_id', 'fecha', name='uix_asistencia'),)

    def __repr__(self):
        return f'<Asistencia {self.estudiante_id} - {self.fecha} - {self.estado}>'


class CodigoAcceso(db.Model):
    __tablename__ = 'codigos_acceso'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    rol = db.Column(db.String(20), nullable=False)
    descripcion = db.Column(db.String(200), nullable=True)
    usado = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_uso = db.Column(db.DateTime, nullable=True)
    usado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

    def __repr__(self):
        return f'<CodigoAcceso {self.codigo} ({self.rol}) - {"Usado" if self.usado else "Disponible"}>'


class LogActividad(db.Model):
    __tablename__ = 'log_actividades'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    accion = db.Column(db.String(100), nullable=False)
    detalle = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('Usuario')
