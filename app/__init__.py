from flask import Flask, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import os
from datetime import date

mysql = MySQL()


def crear_tablas():
    """Ensure required tables exist with the correct schema."""
    with mysql.connection.cursor() as cursor:
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS fincas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100),
                encargado VARCHAR(100),
                direccion VARCHAR(255),
                hectareas FLOAT,
                num_potreros INT,
                marca1 VARCHAR(50),
                marca2 VARCHAR(50),
                marca3 VARCHAR(50),
                nit VARCHAR(50),
                email VARCHAR(100),
                edades_hembras VARCHAR(50),
                edades_machos VARCHAR(50)
            )"""
        )
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                finca_id INT NOT NULL,
                usuario VARCHAR(50) NOT NULL UNIQUE,
                contrasena VARCHAR(255) NOT NULL,
                rol VARCHAR(20) NOT NULL,
                FOREIGN KEY (finca_id) REFERENCES fincas(id) ON DELETE CASCADE
            )"""
        )
        cursor.execute("ALTER TABLE usuarios MODIFY contrasena VARCHAR(255)")
        mysql.connection.commit()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS alertas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                fecha DATE NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                descripcion TEXT,
                tipo ENUM('manual','automatica') DEFAULT 'manual',
                creada_por INT,
                finca_id INT,
                estado ENUM('pendiente','completada') DEFAULT 'pendiente',
                fecha_completada DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creada_por) REFERENCES usuarios(id) ON DELETE SET NULL,
                FOREIGN KEY (finca_id) REFERENCES fincas(id) ON DELETE CASCADE
            )"""
        )
        cursor.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='alertas' AND COLUMN_NAME='estado'"
        )
        row = cursor.fetchone()
        if row and list(row.values())[0] == 0:
            cursor.execute(
                "ALTER TABLE alertas ADD COLUMN estado ENUM('pendiente','completada') DEFAULT 'pendiente'"
            )
        cursor.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='alertas' AND COLUMN_NAME='fecha_completada'"
        )
        row = cursor.fetchone()
        if row and list(row.values())[0] == 0:
            cursor.execute("ALTER TABLE alertas ADD COLUMN fecha_completada DATE")
            
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS insumos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                codigo VARCHAR(50) NOT NULL UNIQUE,
                cantidad DECIMAL(10,2),
                unidad VARCHAR(20),
                fecha_ingreso DATE NOT NULL,
                fecha_vencimiento DATE,
                observaciones TEXT,
                creado_por INT,
                FOREIGN KEY (creado_por) REFERENCES usuarios(id) ON DELETE SET NULL
            )"""
        )
def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('config.py')
    app.secret_key = os.getenv('SECRET_KEY', 'softgan_secret_key')

    mysql.init_app(app)

    from .auth.routes import auth_bp
    from .ganaderia.routes import setup_bp, ganaderia_bp
    from .sanitario.routes import sanitario_bp
    from .almacen.routes import almacen_bp
    from .alertas.routes import alertas_bp
    from .main.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(setup_bp)
    app.register_blueprint(ganaderia_bp)
    app.register_blueprint(sanitario_bp)
    app.register_blueprint(almacen_bp)
    app.register_blueprint(alertas_bp)
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_alertas():
        """Expose tomorrow's alerts count and list for the logged in finca."""
        if 'finca_id' in session:
            with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
                cursor.execute(
                    "SELECT COUNT(*) AS c FROM alertas WHERE finca_id=%s AND tipo='automatica' AND estado='pendiente'",
                    (session['finca_id'],),
                )
                count_row = cursor.fetchone() or {}
                count = count_row.get('c', 0) if isinstance(count_row, dict) else count_row[0]
            return dict(alertas_count=count)
        return dict(alertas_count=0)

    with app.app_context():
        crear_tablas()

    return app
