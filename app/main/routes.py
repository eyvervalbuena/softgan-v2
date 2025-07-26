from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    request,
    jsonify,
)
import logging
import MySQLdb.cursors
from werkzeug.security import generate_password_hash
from .. import mysql

main_bp = Blueprint('main', __name__)

@main_bp.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder.', 'warning')
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html', usuario=session['usuario'])

@main_bp.route('/crear_finca')
def crear_finca():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder.', 'warning')
        return redirect(url_for('auth.login'))
    return render_template('crear_finca.html')


@main_bp.route('/api/finca', methods=['POST'])
def api_finca():
    """Registrar una nueva finca y el primer usuario administrador."""
    try:
        data = request.get_json() if request.is_json else request.form
        nombre = data.get('nombre')
        ubicacion = data.get('ubicacion')
        tamano = data.get('tamano')
        usuario = data.get('usuario')
        contrasena = data.get('contrasena')

        if not nombre or not usuario or not contrasena:
            return (
                jsonify(status='error', message='Datos obligatorios faltantes'),
                400,
            )

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute(
                'INSERT INTO finca (nombre, ubicacion, tamano) VALUES (%s, %s, %s)',
                (nombre, ubicacion, tamano),
            )
            finca_id = cursor.lastrowid

            cursor.execute('SELECT COUNT(*) AS cnt FROM usuarios')
            if cursor.fetchone()['cnt'] == 0:
                hashed = generate_password_hash(contrasena)
                cursor.execute(
                    'INSERT INTO usuarios (usuario, contrasena) VALUES (%s, %s)',
                    (usuario, hashed),
                )
                session['usuario'] = usuario

            mysql.connection.commit()

        return (
            jsonify(status='success', message='Registro guardado', redirect='/dashboard'),
            201,
        )
    except Exception as e:
        logging.exception('Error registrando finca')
        mysql.connection.rollback()
        return jsonify(status='error', message=str(e)), 500
