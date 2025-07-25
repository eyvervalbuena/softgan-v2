from flask import Flask
from flask_mysqldb import MySQL
import os

mysql = MySQL()


def crear_tablas():
    with mysql.connection.cursor() as cursor:
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario VARCHAR(50) NOT NULL UNIQUE,
                contrasena VARCHAR(100) NOT NULL
            )"""
        )
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS finca (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                ubicacion VARCHAR(255),
                tamano DECIMAL(10,2)
            )"""
        )
        mysql.connection.commit()


def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('config.py')
    app.secret_key = os.getenv('SECRET_KEY', 'softgan_secret_key')

    mysql.init_app(app)

    from .auth.routes import auth_bp
    from .ganaderia.routes import ganaderia_bp
    from .sanitario.routes import sanitario_bp
    from .almacen.routes import almacen_bp
    from .main.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(ganaderia_bp)
    app.register_blueprint(sanitario_bp)
    app.register_blueprint(almacen_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        crear_tablas()

    return app
