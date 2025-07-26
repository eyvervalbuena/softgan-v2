# app/ganaderia/routes.py
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
import MySQLdb.cursors
from werkzeug.security import check_password_hash, generate_password_hash
import json
from .. import mysql

# ---------------------------------------------------------------------------
# Setup routes for initial configuration
# ---------------------------------------------------------------------------

setup_bp = Blueprint("setup", __name__)


@setup_bp.route("/finca")
def crear_finca_form():
    return render_template("crear_finca.html")


@setup_bp.route("/api/finca", methods=["POST"])
def crear_finca_api():
    data = request.get_json() or {}
    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT INTO fincas (nombre, encargado, direccion, hectareas, num_potreros, marca1, marca2, marca3, nit, email, edades_hembras, edades_machos) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            data.get("nombre"),
            data.get("encargado"),
            data.get("direccion"),
            data.get("hectareas"),
            data.get("num_potreros"),
            data.get("marca1"),
            data.get("marca2"),
            data.get("marca3"),
            data.get("nit"),
            data.get("email"),
            data.get("edades_hembras"),
            data.get("edades_machos"),
        ),
    )
    finca_id = cursor.lastrowid
    password = generate_password_hash(data.get("admin_contrasena"))
    cursor.execute(
        "INSERT INTO usuarios (finca_id, usuario, contrasena, rol) VALUES (%s, %s, %s, 'admin')",
        (finca_id, data.get("admin_usuario"), password),
    )
    mysql.connection.commit()
    cursor.close()
    return json.dumps({"message": "Registro exitoso"})

# ---------------------------------------------------------------------------
# Ganaderia routes
# ---------------------------------------------------------------------------

ganaderia_bp = Blueprint("ganaderia", __name__, url_prefix="/registro")

@ganaderia_bp.route("/partos")
def registro_partos():
    return render_template('registro_partos.html')

@ganaderia_bp.route('/carne')
def registro_carne():
    return render_template('registro_carne.html')

@ganaderia_bp.route('/leche')
def registro_leche():
    return render_template('registro_leche.html')

@ganaderia_bp.route('/hembras')
def registro_hembras():
    return render_template('registro_hembras.html')

@ganaderia_bp.route('/machos')
def registro_machos():
    return render_template('registro_machos.html')

@ganaderia_bp.route('/crias')
def registro_crias():
    return render_template('registro_crias.html')

# ---------------------------------------------------------------------------
# Almacen routes
# ---------------------------------------------------------------------------

almacen_bp = Blueprint("almacen", __name__, url_prefix="/almacen")

@almacen_bp.route("/")
def almacen_insumos():
    return render_template("almacen_insumos.html")

@almacen_bp.route("/maquinaria")
def almacen_maquinaria():
    return render_template("almacen_maquinaria.html")

@almacen_bp.route("/agroquimicos")
def almacen_agroquimicos():
    return render_template("almacen_agroquimicos.html")

# ---------------------------------------------------------------------------
# Sanitario routes
# ---------------------------------------------------------------------------

sanitario_bp = Blueprint("sanitario", __name__, url_prefix="/sanitario")

@sanitario_bp.r_
