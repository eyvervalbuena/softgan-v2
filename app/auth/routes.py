from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    request,
)
import logging
from MySQLdb.cursors import DictCursor
from werkzeug.security import check_password_hash, generate_password_hash

from .. import mysql

def _finca_count(cursor_class=DictCursor):
    """Return the number of registered farms."""
    with mysql.connection.cursor(cursor_class) as cursor:
        cursor.execute("SELECT COUNT(*) AS c FROM fincas")
        row = cursor.fetchone()
        if isinstance(row, dict):
            return row.get("c", 0)
        return row[0] if row else 0

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    """Authenticate user and start a session."""
    if _finca_count() == 0:
        return redirect(url_for('setup.crear_finca_form'))
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
        logger.debug('Login POST data usuario=%s', usuario)

        if not usuario or not contrasena:
            flash('Usuario y contraseña son obligatorios.', 'warning')
            return render_template('login.html')

        with mysql.connection.cursor(DictCursor) as cursor:
            cursor.execute('SELECT * FROM usuarios WHERE usuario = %s', (usuario,))
            user = cursor.fetchone()
        logger.debug('User fetched from DB: %s', user)

        if not user or not check_password_hash(user['contrasena'], contrasena):
            flash('Usuario o contraseña no válidos', 'danger')
        else:
            session['usuario'] = usuario
            session['finca_id'] = user.get('finca_id')
            session['rol'] = user.get('rol')
            flash('Bienvenido, ' + usuario, 'success')
            return redirect(url_for('main.dashboard'))
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user."""
    if _finca_count() == 0:
        flash('Primero debe registrar la finca.', 'warning')
        return redirect(url_for('setup.crear_finca_form'))

    if 'usuario' not in session or session.get('rol') != 'admin':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        usuario = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
        rol = request.form.get('rol') or 'worker'
        if not usuario or not contrasena:
            flash('Todos los campos son obligatorios.', 'danger')
        elif len(usuario) < 4 or len(contrasena) < 6:
            flash('Usuario mínimo 4 caracteres y contraseña mínimo 6.', 'warning')
        elif not usuario.isalnum():
            flash('El usuario solo puede contener letras y números.', 'warning')
        else:
            with mysql.connection.cursor(DictCursor) as cursor:
                cursor.execute('SELECT id FROM usuarios WHERE usuario = %s', (usuario,))
                user = cursor.fetchone()
                if user:
                    flash('El usuario ya existe.', 'danger')
                else:
                    hashed = generate_password_hash(contrasena)
                    cursor.execute(
                        'INSERT INTO usuarios (finca_id, usuario, contrasena, rol) VALUES (%s, %s, %s, %s)',
                        (session.get('finca_id'), usuario, hashed, rol),
                    )
                    mysql.connection.commit()
                    flash('Usuario registrado exitosamente.', 'success')
                    return redirect(url_for('main.dashboard'))

    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Sesión finalizada.', 'info')
    return redirect(url_for('auth.login'))
