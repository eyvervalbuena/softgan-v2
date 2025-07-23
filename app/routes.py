
from flask import render_template, request, redirect, url_for, flash, session
from app import app
from flask_mysqldb import MySQL
import MySQLdb.cursors

# Configuración MySQL
app.config.from_object('app.config')
app.secret_key = 'softgan_secret_key'  # Necesario para flash y sesiones
mysql = MySQL(app)


# Ruta para mostrar el template de registro de hembras
@app.route('/registro/hembras')
def registro_hembras():
    return render_template('registro_hembras.html')

# Ruta para mostrar el template de registro de machos
@app.route('/registro/machos')
def registro_machos():
    return render_template('registro_machos.html')

# Crear tabla de usuarios si no existe
with app.app_context():
    cursor = mysql.connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario VARCHAR(50) NOT NULL UNIQUE,
        contrasena VARCHAR(100) NOT NULL
    )''')
    mysql.connection.commit()
    cursor.close()


# Dashboard protegido
@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder.', 'warning')
        return redirect(url_for('login'))
    return render_template('dashboard.html', usuario=session['usuario'])

@app.route('/', methods=['GET', 'POST'])
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
                return redirect(url_for('dashboard'))
        except Exception as e:
            flash('Error de conexión a la base de datos', 'danger')
    return render_template('login.html')

# Registro de usuarios con validaciones y mensajes flash
@app.route('/register', methods=['GET', 'POST'])
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
                    return redirect(url_for('login'))
                cursor.close()
            except Exception as e:
                flash('Error de conexión a la base de datos', 'danger')
    return render_template('register.html')
