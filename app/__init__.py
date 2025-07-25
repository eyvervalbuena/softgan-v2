from flask import Flask
from flask_mysqldb import MySQL

mysql = MySQL()


def crear_tablas():
    cursor = mysql.connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario VARCHAR(50) NOT NULL UNIQUE,
        contrasena VARCHAR(100) NOT NULL
    )''')
    mysql.connection.commit()
    cursor.close()


def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('config.py')
    app.secret_key = 'softgan_secret_key'

    mysql.init_app(app)

    from .ganaderia.routes import (
        ganaderia_bp,
        almacen_bp,
        sanitario_bp,
        main_bp,
        auth_bp,
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(ganaderia_bp)
    app.register_blueprint(sanitario_bp)
    app.register_blueprint(almacen_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        crear_tablas()

    return app
