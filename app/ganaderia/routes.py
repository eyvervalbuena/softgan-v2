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
    """Crea la finca inicial y el usuario administrador."""
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
    session["usuario"] = data.get("admin_usuario")
    session["finca_id"] = finca_id
    session["rol"] = "admin"
    return json.dumps({"redirect": url_for("main.dashboard")})

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

# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET", "POST"])
def login():
    """autenticacion e inicio de sesion."""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS c FROM fincas")
    count = cursor.fetchone()["c"] if cursor.description else cursor.fetchone()[0]
    cursor.close()
    if count == 0:
        return redirect(url_for("setup.crear_finca_form"))
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
                session["finca_id"] = user.get("finca_id") if isinstance(user, dict) else user[1]
                session["rol"] = user.get("rol") if isinstance(user, dict) else user[4]
                flash("Bienvenido, " + usuario, "success")
                return redirect(url_for("main.dashboard"))
            else:
                flash("Contrase\u00f1a no v\u00e1lida", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "usuario" not in session or session.get("rol") != "admin":
        flash("Acceso no autorizado", "danger")
        return redirect(url_for("auth.login"))
    
    if request.method == "POST":
        usuario = request.form.get("usuario")
        contrasena = request.form.get("contrasena")
        rol = request.form.get("rol") or "worker"
        if not usuario or not contrasena:
            flash("Todos los campos son obligatorios.", "danger")
        elif len(usuario) < 4 or len(contrasena) < 6:
            flash("Usuario m\u00ednimo 4 caracteres y contrase\u00f1a m\u00ednimo 6.", "warning")
        elif not usuario.isalnum():
            flash("El usuario solo puede contener letras y n\u00fameros.", "warning")
        else:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SELECT * FROM usuarios WHERE usuario = %s", (usuario,))
            user = cursor.fetchone()
            if user:
                flash("El usuario ya existe.", "danger")
            else:
                hashed = generate_password_hash(contrasena)
                cursor.execute(
                    "INSERT INTO usuarios (finca_id, usuario, contrasena, rol) VALUES (%s, %s, %s, %s)",
                    (session.get("finca_id"), usuario, hashed, rol),
                )
                mysql.connection.commit()
                flash("Usuario registrado exitosamente.", "success")
                cursor.close()
                return redirect(url_for("main.dashboard"))
            cursor.close()
    return render_template("register.html")


@auth_bp.route("/logout")
def logout():
    session.pop("usuario", None)
    flash("Sesi\u00f3n finalizada.", "info")
    return redirect(url_for("auth.login"))

