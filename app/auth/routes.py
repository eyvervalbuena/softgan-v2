from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import MySQLdb.cursors
from .. import mysql

bp = Blueprint('auth', __name__)

@bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        except Exception:
            cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE usuario = %s', (usuario,))
        user = cursor.fetchone()
        cursor.close()
        if not user:
            flash('Usuario no válido', 'danger')
        elif user.get('contrasena') if isinstance(user, dict) else user[2] != contrasena:
            flash('Contraseña no válida', 'danger')
        else:
            session['usuario'] = usuario
            flash('Bienvenido, ' + usuario, 'success')
            return redirect(url_for('main.dashboard'))
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
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
            try:
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            except Exception:
                cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM usuarios WHERE usuario = %s', (usuario,))
            user = cursor.fetchone()
            if user:
                flash('El usuario ya existe.', 'danger')
            else:
                cursor.execute('INSERT INTO usuarios (usuario, contrasena) VALUES (%s, %s)', (usuario, contrasena))
                mysql.connection.commit()
                flash('Usuario registrado exitosamente. Ahora puedes iniciar sesión.', 'success')
                cursor.close()
                return redirect(url_for('auth.login'))
            cursor.close()
    return render_template('register.html')

@bp.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Sesión finalizada.', 'info')
    return redirect(url_for('auth.login'))

