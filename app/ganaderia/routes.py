"""Centralized route definitions for the application.

This module now contains all Blueprints used in the project in order to keep
the routing logic in a single place.  Each section is clearly separated so the
original structure of the application is still recognisable.
"""

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
from werkzeug.security import check_password_hash

from .. import mysql

# ---------------------------------------------------------------------------
# Ganaderia routes
# ---------------------------------------------------------------------------

ganaderia_bp = Blueprint("ganaderia", __name__, url_prefix="/registro")

@ganaderia_bp.route("/partos")
def registro_partos():
    return render_template('registro_partos.html')

@ganaderia_bp.route("/carne")
def registro_carne():
    return render_template('registro_carne.html')

@ganaderia_bp.route("/leche")
def registro_leche():
    return render_template('registro_leche.html')

@ganaderia_bp.route("/hembras")
def registro_hembras():
    return render_template('registro_hembras.html')

@ganaderia_bp.route("/machos")
def registro_machos():
    return render_template('registro_machos.html')

@ganaderia_bp.route("/crias")
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


@sanitario_bp.route("/ciclo")
def registro_ciclo():
    return render_template("registro_ciclo.html")


@sanitario_bp.route("/individual")
def registro_individual():
    return render_template("registro_individual.html")


@sanitario_bp.route("/patologia")
def registro_patologia():
    return render_template("registro_patologia.html")

# ---------------------------------------------------------------------------
# Main routes
# ---------------------------------------------------------------------------

main_bp = Blueprint("main", __name__)


@main_bp.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        flash("Debes iniciar sesi\u00f3n para acceder.", "warning")
        return redirect(url_for("auth.login"))
    return render_template("dashboard.html", usuario=session["usuario"])


# Nueva ruta para crear una finca
@main_bp.route("/crear_finca")
def crear_finca():
    """Muestra el formulario de registro de fincas."""
    if "usuario" not in session:
        flash("Debes iniciar sesi\u00f3n para acceder.", "warning")
        return redirect(url_for("auth.login"))
    return render_template("crear_finca.html")

# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET", "POST"])
def login():
    """Authenticate user and start a session."""
    if request.method == "POST":
        usuario = request.form.get("usuario")
        contrasena = request.form.get("contrasena")

        logger.debug("Login POST data usuario=%s contrasena=%s", usuario, contrasena)

        if not usuario or not contrasena:
            flash("Usuario y contrase\u00f1a son obligatorios.", "warning")
            return render_template("login.html")

        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SET NAMES utf8mb4")
        except Exception:
            cursor = mysql.connection.cursor()

        cursor.execute("SELECT * FROM usuarios WHERE usuario = %s", (usuario,))
        user = cursor.fetchone()
        logger.debug("User fetched from DB: %s", user)
        cursor.close()

        if not user:
            flash("Usuario no v\u00e1lido", "danger")
        else:
            stored_pass = user.get("contrasena") if isinstance(user, dict) else user[2]
            logger.debug(
                "Comparing stored_pass=%s with provided contrasena=%s",
                stored_pass,
                contrasena,
            )
            if stored_pass is None:
                flash("Contrase\u00f1a no v\u00e1lida", "danger")
            elif check_password_hash(stored_pass, contrasena) or stored_pass == contrasena:
                session["usuario"] = usuario
                flash("Bienvenido, " + usuario, "success")
                return redirect(url_for("main.dashboard"))
            else:
                flash("Contrase\u00f1a no v\u00e1lida", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        contrasena = request.form.get("contrasena")
        if not usuario or not contrasena:
            flash("Todos los campos son obligatorios.", "danger")
        elif len(usuario) < 4 or len(contrasena) < 6:
            flash("Usuario m\u00ednimo 4 caracteres y contrase\u00f1a m\u00ednimo 6.", "warning")
        elif not usuario.isalnum():
            flash("El usuario solo puede contener letras y n\u00fameros.", "warning")
        else:
            try:
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            except Exception:
                cursor = mysql.connection.cursor()
            cursor.execute("SELECT * FROM usuarios WHERE usuario = %s", (usuario,))
            user = cursor.fetchone()
            if user:
                flash("El usuario ya existe.", "danger")
            else:
                cursor.execute(
                    "INSERT INTO usuarios (usuario, contrasena) VALUES (%s, %s)",
                    (usuario, contrasena),
                )
                mysql.connection.commit()
                flash(
                    "Usuario registrado exitosamente. Ahora puedes iniciar sesi\u00f3n.",
                    "success",
                )
                cursor.close()
                return redirect(url_for("auth.login"))
            cursor.close()
    return render_template("register.html")


@auth_bp.route("/logout")
def logout():
    session.pop("usuario", None)
    flash("Sesi\u00f3n finalizada.", "info")
    return redirect(url_for("auth.login"))

