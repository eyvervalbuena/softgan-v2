from flask import Flask
from flask_mysqldb import MySQL
import os

mysql = MySQL()


def crear_tablas():
# Crear tablas si no existen

with mysql.connection.cursor() as cursor:
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS fincas (
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
        )'''
    )
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            finca_id INT NOT NULL,
            usuario VARCHAR(50) NOT NULL UNIQUE,
            contrasena VARCHAR(255) NOT NULL,
            rol VARCHAR(20) NOT NULL,
            FOREIGN KEY (finca_id) REFERENCES fincas(id) ON DELETE CASCADE
        )'''
    )
    mysql.connection.commit()

    from .ganaderia.routes import (
    setup_bp,
    ganaderia_bp,
    almacen_bp,
    sanitario_bp,
    main_bp,
    auth_bp,
)

app.register_blueprint(setup_bp)
app.register_blueprint(ganaderia_bp)
app.register_blueprint(almacen_bp)
app.register_blueprint(sanitario_bp)
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)