# app/ganaderia/routes.py
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    request,
    current_app,
    jsonify,
)
import logging
import MySQLdb.cursors
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import os
import time
from datetime import date

ALLOWED_EXTS = {"jpg", "jpeg", "png"}
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2MB
import json
from .. import mysql


def calcular_edad(fecha_nacimiento):
    """Devuelve la edad en formato 'X años Y meses'."""
    if not fecha_nacimiento:
        return ""
    today = date.today()
    years = today.year - fecha_nacimiento.year - (
        (today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
    )
    months = today.month - fecha_nacimiento.month - (
        today.day < fecha_nacimiento.day
    )
    if months < 0:
        months += 12
    return f"{years} años {months} meses"

# ---------------------------------------------------------------------------
# Setup de configuración inicial
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

@ganaderia_bp.route("/hembras", methods=["GET", "POST"])
def registro_hembras():
    if "usuario" not in session:
        flash("Debes iniciar sesi\u00f3n para acceder.", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        nombre = request.form.get("nombre")
        tipo = request.form.get("tipo")
        cond_raw = request.form.get("condicion")
        try:
            condicion = float(cond_raw)
        except (TypeError, ValueError):
            condicion = None
        activo = 1 if request.form.get("activo") else 0
        fecha_nacimiento = request.form.get("fecha_nacimiento") or None
        origen = request.form.get("origen")
        fecha_incorporacion = request.form.get("fecha_incorporacion") or None
        padre_raw = request.form.get("padre_id")
        madre_raw = request.form.get("madre_id")
        try:
            padre_id = int(padre_raw) if padre_raw else None
        except (TypeError, ValueError):
            padre_id = None
        try:
            madre_id = int(madre_raw) if madre_raw else None
        except (TypeError, ValueError):
            madre_id = None
        fecha_desincorporacion = request.form.get("fecha_desincorporacion") or None
        causa_desincorporacion = request.form.get("causa_desincorporacion") or None
        foto_file = request.files.get("foto")
        foto_path = None
        if foto_file and foto_file.filename:
            filename = secure_filename(foto_file.filename)
            ext = filename.rsplit(".", 1)[-1].lower()
            if ext not in ALLOWED_EXTS:
                flash("Formato de imagen no permitido.", "warning")
                return redirect(url_for("ganaderia.registro_hembras"))
            foto_file.seek(0, os.SEEK_END)
            size = foto_file.tell()
            foto_file.seek(0)
            if size > MAX_IMAGE_SIZE:
                flash("La imagen supera el tama\u00f1o m\u00e1ximo permitido.", "warning")
                return redirect(url_for("ganaderia.registro_hembras"))
            dir_path = os.path.join(current_app.root_path, "static", "imagenes", "hembras")
            os.makedirs(dir_path, exist_ok=True)
            unique_name = f"{int(time.time())}_{filename}"
            foto_file.save(os.path.join(dir_path, unique_name))
            foto_path = os.path.join("imagenes", "hembras", unique_name)
        
        if not nombre or condicion is None:
            flash("Nombre y condición son obligatorios.", "warning")
            return redirect(url_for("ganaderia.registro_hembras"))

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute(
                "SELECT id FROM hembras WHERE nombre=%s AND fecha_nacimiento=%s",
                (nombre, fecha_nacimiento),
            )
            existente = cursor.fetchone()

        if existente:
            flash(
                "Ya existe una hembra con ese nombre y fecha de nacimiento.",
                "warning",
            )
            return redirect(url_for("ganaderia.registro_hembras"))

        with mysql.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO hembras (nombre, tipo, condicion, activo, fecha_nacimiento, origen, fecha_incorporacion, padre_id, madre_id, fecha_desincorporacion, causa_desincorporacion, foto) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    nombre,
                    tipo,
                    condicion,
                    activo,
                    fecha_nacimiento,
                    origen,
                    fecha_incorporacion,
                    padre_id,
                    madre_id,
                    fecha_desincorporacion,
                    causa_desincorporacion,
                    foto_path,
                ),
            )
            hembra_id = cursor.lastrowid
            cursor.execute(
                "UPDATE hembras SET numero=%s WHERE id=%s", (hembra_id, hembra_id)
            )
            mysql.connection.commit()
        flash("Hembra registrada correctamente.", "success")
        return redirect(url_for("ganaderia.registro_hembras"))

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute("SELECT COALESCE(MAX(numero),0)+1 AS n FROM hembras")
        row = cursor.fetchone() or {}
        next_numero = row.get("n", 1)
        cursor.execute("SELECT id, numero, nombre FROM machos ORDER BY id")
        machos = cursor.fetchall() or []
        cursor.execute("SELECT id, numero, nombre FROM hembras ORDER BY id")
        madres = cursor.fetchall() or []
        cursor.execute(
            "SELECT h.*, p.numero AS padre_numero, m.numero AS madre_numero "
            "FROM hembras h "
            "LEFT JOIN machos p ON h.padre_id = p.id "
            "LEFT JOIN hembras m ON h.madre_id = m.id "
            "ORDER BY h.id DESC"
        )
        hembras = cursor.fetchall() or []
        for h in hembras:
            h["edad"] = calcular_edad(h.get("fecha_nacimiento"))
            h["numero_partos"] = 0
            h["fecha_ultimo_parto"] = None
    return render_template(
        "registro_hembras.html",
        hembras=hembras,
        next_numero=next_numero,
        machos=machos,
        madres=madres
    )

@ganaderia_bp.route('/registro_hembras/<int:hembra_id>')
def obtener_hembra(hembra_id):
    if 'usuario' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute('SELECT * FROM hembras WHERE id=%s', (hembra_id,))
        hembra = cursor.fetchone()
    if not hembra:
        return jsonify({'error': 'not found'}), 404
    for campo in ['fecha_nacimiento', 'fecha_incorporacion', 'fecha_desincorporacion']:
        if hembra.get(campo):
            hembra[campo] = hembra[campo].isoformat()
    return jsonify(hembra)

@ganaderia_bp.route('/registro_hembras/actualizar', methods=['POST'])
def actualizar_hembra():
    if 'usuario' not in session or session.get('rol') not in ['admin', 'supervisor']:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('ganaderia.registro_hembras'))

    hembra_id = request.form.get('numero')
    if not hembra_id:
        flash('ID inválido', 'warning')
        return redirect(url_for('ganaderia.registro_hembras'))

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute('SELECT * FROM hembras WHERE id=%s', (hembra_id,))
        hembra = cursor.fetchone()
    if not hembra:
        flash('Hembra no encontrada', 'warning')
        return redirect(url_for('ganaderia.registro_hembras'))

    nombre = request.form.get('nombre')
    tipo = request.form.get('tipo')
    cond_raw = request.form.get('condicion')
    try:
        condicion = float(cond_raw)
    except (TypeError, ValueError):
        condicion = None
    activo = 1 if request.form.get('activo') else 0
    fecha_nacimiento = request.form.get('fecha_nacimiento') or None
    origen = request.form.get('origen')
    fecha_incorporacion = request.form.get('fecha_incorporacion') or None
    padre_raw = request.form.get('padre_id')
    madre_raw = request.form.get('madre_id')
    padre_id = int(padre_raw) if padre_raw else None
    madre_id = int(madre_raw) if madre_raw else None
    fecha_desincorporacion = request.form.get('fecha_desincorporacion') or None
    causa_desincorporacion = request.form.get('causa_desincorporacion') or None
    foto_path = hembra.get('foto')
    foto_file = request.files.get('foto')
    if foto_file and foto_file.filename:
        filename = secure_filename(foto_file.filename)
        ext = filename.rsplit('.', 1)[-1].lower()
        if ext not in ALLOWED_EXTS:
            flash('Formato de imagen no permitido.', 'warning')
            return redirect(url_for('ganaderia.registro_hembras'))
        foto_file.seek(0, os.SEEK_END)
        size = foto_file.tell()
        foto_file.seek(0)
        if size > MAX_IMAGE_SIZE:
            flash('La imagen supera el tamaño máximo permitido.', 'warning')
            return redirect(url_for('ganaderia.registro_hembras'))
        dir_path = os.path.join(current_app.root_path, 'static', 'imagenes', 'hembras')
        os.makedirs(dir_path, exist_ok=True)
        unique_name = f"{int(time.time())}_{filename}"
        foto_file.save(os.path.join(dir_path, unique_name))
        foto_path = os.path.join('imagenes', 'hembras', unique_name)

    if not nombre or condicion is None:
        flash('Nombre y condición son obligatorios.', 'warning')
        return redirect(url_for('ganaderia.registro_hembras'))

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute(
            'SELECT id FROM hembras WHERE nombre=%s AND fecha_nacimiento=%s AND id!=%s',
            (nombre, fecha_nacimiento, hembra_id),
        )
        existente = cursor.fetchone()
    if existente:
        flash('Ya existe una hembra con ese nombre y fecha de nacimiento.', 'warning')
        return redirect(url_for('ganaderia.registro_hembras'))

    with mysql.connection.cursor() as cursor:
        cursor.execute(
            'UPDATE hembras SET nombre=%s, tipo=%s, condicion=%s, activo=%s, fecha_nacimiento=%s, origen=%s, fecha_incorporacion=%s, padre_id=%s, madre_id=%s, fecha_desincorporacion=%s, causa_desincorporacion=%s, foto=%s WHERE id=%s',
            (
                nombre,
                tipo,
                condicion,
                activo,
                fecha_nacimiento,
                origen,
                fecha_incorporacion,
                padre_id,
                madre_id,
                fecha_desincorporacion,
                causa_desincorporacion,
                foto_path,
                hembra_id,
            ),
        )
        mysql.connection.commit()
    flash('Hembra actualizada correctamente.', 'success')
    return redirect(url_for('ganaderia.registro_hembras'))
@ganaderia_bp.route("/hembras/editar/<int:hembra_id>", methods=["GET", "POST"])
def editar_hembra(hembra_id):
    if "usuario" not in session or session.get("rol") not in ["admin", "supervisor"]:
        flash("Acceso no autorizado", "danger")
        return redirect(url_for("ganaderia.registro_hembras"))

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM hembras WHERE id=%s", (hembra_id,))
        hembra = cursor.fetchone()

    if not hembra:
        flash("Hembra no encontrada", "warning")
        return redirect(url_for("ganaderia.registro_hembras"))

    if request.method == "POST":
        nombre = request.form.get("nombre")
        tipo = request.form.get("tipo")
        cond_raw = request.form.get("condicion")
        try:
            condicion = float(cond_raw)
        except (TypeError, ValueError):
            condicion = None
        activo = 1 if request.form.get("activo") else 0
        fecha_nacimiento = request.form.get("fecha_nacimiento") or None
        origen = request.form.get("origen")
        fecha_incorporacion = request.form.get("fecha_incorporacion") or None
        padre_raw = request.form.get("padre_id")
        madre_raw = request.form.get("madre_id")
        padre_id = int(padre_raw) if padre_raw else None
        madre_id = int(madre_raw) if madre_raw else None
        fecha_desincorporacion = request.form.get("fecha_desincorporacion") or None
        causa_desincorporacion = request.form.get("causa_desincorporacion") or None
        foto_path = hembra.get("foto")
        foto_file = request.files.get("foto")
        if foto_file and foto_file.filename:
            filename = secure_filename(foto_file.filename)
            ext = filename.rsplit(".", 1)[-1].lower()
            if ext not in ALLOWED_EXTS:
                flash("Formato de imagen no permitido.", "warning")
                return redirect(url_for("ganaderia.editar_hembra", hembra_id=hembra_id))
            foto_file.seek(0, os.SEEK_END)
            size = foto_file.tell()
            foto_file.seek(0)
            if size > MAX_IMAGE_SIZE:
                flash("La imagen supera el tama\u00f1o m\u00e1ximo permitido.", "warning")
                return redirect(url_for("ganaderia.editar_hembra", hembra_id=hembra_id))
            dir_path = os.path.join(current_app.root_path, "static", "imagenes", "hembras")
            os.makedirs(dir_path, exist_ok=True)
            unique_name = f"{int(time.time())}_{filename}"
            foto_file.save(os.path.join(dir_path, unique_name))
            foto_path = os.path.join("imagenes", "hembras", unique_name)

        if not nombre or condicion is None:
            flash("Nombre y condición son obligatorios.", "warning")
        else:
            with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
                cursor.execute(
                    "SELECT id FROM hembras WHERE nombre=%s AND fecha_nacimiento=%s AND id!=%s",
                    (nombre, fecha_nacimiento, hembra_id),
                )
                existente = cursor.fetchone()
            if existente:
                flash(
                    "Ya existe una hembra con ese nombre y fecha de nacimiento.",
                    "warning",
                )
            else:
                with mysql.connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE hembras SET nombre=%s, tipo=%s, condicion=%s, activo=%s, fecha_nacimiento=%s, origen=%s, fecha_incorporacion=%s, padre_id=%s, madre_id=%s, fecha_desincorporacion=%s, causa_desincorporacion=%s, foto=%s WHERE id=%s",
                        (
                            nombre,
                            tipo,
                            condicion,
                            activo,
                            fecha_nacimiento,
                            origen,
                            fecha_incorporacion,
                            padre_id,
                            madre_id,
                            fecha_desincorporacion,
                            causa_desincorporacion,
                            foto_path,
                            hembra_id,
                        ),
                    )
                    mysql.connection.commit()
                flash("Hembra actualizada correctamente.", "success")
                return redirect(url_for("ganaderia.registro_hembras"))

        hembra.update(
            dict(
                nombre=nombre,
                tipo=tipo,
                condicion=cond_raw,
                activo=bool(activo),
                fecha_nacimiento=fecha_nacimiento,
                origen=origen,
                fecha_incorporacion=fecha_incorporacion,
                padre_id=padre_id,
                madre_id=madre_id,
                fecha_desincorporacion=fecha_desincorporacion,
                causa_desincorporacion=causa_desincorporacion,
                foto=foto_path,
            )
        )

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute("SELECT id, numero, nombre FROM machos ORDER BY id")
        machos = cursor.fetchall() or []
        cursor.execute("SELECT id, numero, nombre FROM hembras ORDER BY id")
        madres = cursor.fetchall() or []

    return render_template(
        "editar_hembra.html",
        hembra=hembra,
        machos=machos,
        madres=madres,
    )


@ganaderia_bp.route("/hembras/eliminar/<int:hembra_id>", methods=["GET", "POST"])
def eliminar_hembra(hembra_id):
    if "usuario" not in session or session.get("rol") != "admin":
        flash("Acceso no autorizado", "danger")
        return redirect(url_for("ganaderia.registro_hembras"))

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute("SELECT id, nombre FROM hembras WHERE id=%s", (hembra_id,))
        hembra = cursor.fetchone()

    if not hembra:
        flash("Hembra no encontrada", "warning")
        return redirect(url_for("ganaderia.registro_hembras"))

    if request.method == "POST":
        with mysql.connection.cursor() as cursor:
            cursor.execute("DELETE FROM hembras WHERE id=%s", (hembra_id,))
            mysql.connection.commit()
        flash("Hembra eliminada correctamente.", "success")
        return redirect(url_for("ganaderia.registro_hembras"))

    return render_template("eliminar_hembra.html", hembra=hembra)


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

