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

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    """Authenticate user and start a session."""
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
            flash('Bienvenido, ' + usuario, 'success')
            return redirect(url_for('main.dashboard'))
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user."""
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
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
                        'INSERT INTO usuarios (usuario, contrasena) VALUES (%s, %s)',
                        (usuario, hashed),
                    )
                    mysql.connection.commit()
                    flash('Usuario registrado exitosamente. Ahora puedes iniciar sesión.', 'success')
                    return redirect(url_for('auth.login'))
    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Sesión finalizada.', 'info')
    return redirect(url_for('auth.login'))
