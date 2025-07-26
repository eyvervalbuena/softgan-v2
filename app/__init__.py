from flask import Flask
from flask_mysqldb import MySQL
import os

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


def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('config.py')
    app.secret_key = os.getenv('SECRET_KEY', 'softgan_secret_key')

    mysql.init_app(app)

    from .auth.routes import auth_bp
    from .ganaderia.routes import setup_bp, ganaderia_bp
    from .sanitario.routes import sanitario_bp
    from .almacen.routes import almacen_bp
    from .main.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(setup_bp)
    app.register_blueprint(ganaderia_bp)
    app.register_blueprint(sanitario_bp)
    app.register_blueprint(almacen_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        crear_tablas()

    return app
