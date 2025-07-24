from flask import Flask
from .routes import bp_main, mysql

def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('config.py')
    app.secret_key = 'softgan_secret_key'
    mysql.init_app(app)
    app.register_blueprint(bp_main)
    with app.app_context():
        cursor = mysql.connection.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            usuario VARCHAR(50) NOT NULL UNIQUE,
            contrasena VARCHAR(100) NOT NULL
        )''')
        mysql.connection.commit()
        cursor.close()
    return app
    app = Flask(__name__)
    app.config.from_pyfile('config.py')
    app.register_blueprint(bp_main)
    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_finca)
    crear_tablas()
    return app

