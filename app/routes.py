

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
import MySQLdb.cursors

bp_main = Blueprint('main', __name__)


# Ruta para mostrar el template de registro de partos
@bp_main.route('/registro/partos')
def registro_partos():
    return render_template('registro_partos.html')


# Ruta para mostrar el template de registro de carne
@bp_main.route('/registro/carne')
def registro_carne():
    return render_template('registro_carne.html')


# Ruta para mostrar el template de registro de leche
@bp_main.route('/registro/leche')
def registro_leche():
    return render_template('registro_leche.html')

from flask import render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
import MySQLdb.cursors

# Configuración MySQL

mysql = MySQL()



# Ruta para mostrar el template de registro de hembras
@bp_main.route('/registro/hembras')
def registro_hembras():
    return render_template('registro_hembras.html')


# Ruta para mostrar el template de registro de machos
@bp_main.route('/registro/machos')
def registro_machos():
    return render_template('registro_machos.html')


# Ruta para mostrar el template de registro de crías
@bp_main.route('/registro/crias')
def registro_crias():
    return render_template('registro_crias.html')

# Crear tabla de usuarios si no existe

# Dashboard protegido

@bp_main.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder.', 'warning')
        return redirect(url_for('main.login'))
    return render_template('dashboard.html', usuario=session['usuario'])


@bp_main.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM usuarios WHERE usuario = %s', (usuario,))
            user = cursor.fetchone()
            cursor.close()
            if not user:
                flash('Usuario no válido', 'danger')
            elif user['contrasena'] != contrasena:
                flash('Contraseña no válida', 'danger')
            else:
                session['usuario'] = usuario
                flash('Bienvenido, ' + usuario, 'success')
                return redirect(url_for('main.dashboard'))
        except Exception as e:
            flash('Error de conexión a la base de datos', 'danger')
    return render_template('login.html')

# Registro de usuarios con validaciones y mensajes 

@bp_main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
        # Validaciones
        if not usuario or not contrasena:
            flash('Todos los campos son obligatorios.', 'danger')
        elif len(usuario) < 4 or len(contrasena) < 6:
            flash('Usuario mínimo 4 caracteres y contraseña mínimo 6.', 'warning')
        elif not usuario.isalnum():
            flash('El usuario solo puede contener letras y números.', 'warning')
        else:
            try:
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute('SELECT * FROM usuarios WHERE usuario = %s', (usuario,))
                user = cursor.fetchone()
                if user:
                    flash('El usuario ya existe.', 'danger')
                else:
                    cursor.execute('INSERT INTO usuarios (usuario, contrasena) VALUES (%s, %s)', (usuario, contrasena))
                    mysql.connection.commit()
                    flash('Usuario registrado exitosamente. Ahora puedes iniciar sesión.', 'success')
                    cursor.close()
                    return redirect(url_for('main.login'))
                cursor.close()
            except Exception as e:
                flash('Error de conexión a la base de datos', 'danger')
    return render_template('register.html')
