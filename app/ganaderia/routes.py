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

# ---------------------- Producción Leche API ----------------------
def _to_iso(d):
    return d.isoformat() if d else None

def _get_hembra_info(hembra_id):
    """Obtiene hembra por id con campos requeridos por módulo de leche."""
    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute(
            """
            SELECT h.id, h.nombre,
                   COALESCE(h.num_crias,0) AS num_crias,
                   h.tipo,
                   h.condicion AS condicion,
                   COALESCE(h.ordenyos_dia,2) AS ordenyos_dia,
                   h.ultimo_parto
            FROM hembras h WHERE h.id=%s
            """,
            (hembra_id,),
        )
        row = cursor.fetchone()
    if not row:
        return None
    # Normalizaciones
    row["ultimo_parto"] = _to_iso(row.get("ultimo_parto"))
    tipo_raw = (row.get("tipo") or "").strip().lower()
    if tipo_raw not in ("productiva", "seca"):
        row["tipo"] = "productiva" if row.get("ordenyos_dia", 0) else "seca"
    else:
        row["tipo"] = tipo_raw
    # Condición a float si aplica
    try:
        if row.get("condicion") is not None:
            row["condicion"] = float(row["condicion"])
    except Exception:
        pass
    return row

def _promedios_hembra(hembra_id, ultimo_parto_iso):
    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute(
            "SELECT AVG(litros) AS avg_sem FROM produccion_leche WHERE hembra_id=%s AND fecha >= (CURDATE() - INTERVAL 6 DAY)",
            (hembra_id,),
        )
        avg_sem = (cursor.fetchone() or {}).get("avg_sem") or 0
        cursor.execute(
            "SELECT AVG(litros) AS avg_mes FROM produccion_leche WHERE hembra_id=%s AND fecha >= (CURDATE() - INTERVAL 29 DAY)",
            (hembra_id,),
        )
        avg_mes = (cursor.fetchone() or {}).get("avg_mes") or 0
        avg_lact = 0
        if ultimo_parto_iso:
            cursor.execute(
                "SELECT AVG(litros) AS avg_lact FROM produccion_leche WHERE hembra_id=%s AND fecha >= %s",
                (hembra_id, ultimo_parto_iso),
            )
            avg_lact = (cursor.fetchone() or {}).get("avg_lact") or 0
        cursor.execute(
            "SELECT fecha, numero_ordenyo, litros FROM produccion_leche WHERE hembra_id=%s ORDER BY fecha DESC, numero_ordenyo DESC LIMIT 1",
            (hembra_id,),
        )
        ult = cursor.fetchone()
    ultimo = None
    if ult:
        ultimo = {
            "fecha": _to_iso(ult.get("fecha")),
            "numero_ordenyo": ult.get("numero_ordenyo"),
            "litros": float(ult.get("litros")),
        }
    return {"semana": float(avg_sem), "mes": float(avg_mes), "lactancia": float(avg_lact)}, ultimo

@ganaderia_bp.route('/leche/api/hembra/<int:hembra_id>')
def leche_api_hembra(hembra_id):
    if 'usuario' not in session:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    h = _get_hembra_info(hembra_id)
    if not h:
        return jsonify({'ok': False, 'error': 'Hembra no encontrada'}), 404
    proms, ult = _promedios_hembra(hembra_id, h.get('ultimo_parto'))
    # contador a secado
    contador = 0
    if h.get('ultimo_parto'):
        try:
            from datetime import date
            up = date.fromisoformat(h['ultimo_parto'])
            dias = (date.today() - up).days
            contador = max(0, 305 - max(0, dias))
        except Exception:
            contador = 0
    return jsonify({
        'ok': True,
        'hembra': {
            'id': h['id'], 'nombre': h['nombre'], 'num_crias': h.get('num_crias',0),
            'tipo': h['tipo'], 'condicion': h.get('condicion'), 'ordenyos_dia': h.get('ordenyos_dia',2),
            'ultimo_parto': h.get('ultimo_parto')
        },
        'promedios': proms,
        'contador_secado_dias': contador,
        'ultimo_pesaje': ult
    })

@ganaderia_bp.route('/leche/api/registrar', methods=['POST'])
def leche_api_registrar():
    if 'usuario' not in session:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    if not request.is_json:
        return jsonify({'ok': False, 'error': 'Contenido no JSON'}), 400
    data = request.get_json(silent=True) or {}
    # Extraer y validar
    try:
        hembra_id = int(data.get('hembra_id'))
    except Exception:
        return jsonify({'ok': False, 'error': 'hembra_id inválido'}), 400
    fecha = data.get('fecha')
    try:
        numero_ordenyo = int(data.get('numero_ordenyo'))
    except Exception:
        return jsonify({'ok': False, 'error': 'numero_ordenyo inválido'}), 400
    try:
        litros = float(data.get('litros'))
    except Exception:
        return jsonify({'ok': False, 'error': 'litros inválido'}), 400
    if litros < 0:
        return jsonify({'ok': False, 'error': 'litros debe ser >= 0'}), 400
    # Validar hembra y rango de ordeños
    h = _get_hembra_info(hembra_id)
    if not h:
        return jsonify({'ok': False, 'error': 'Hembra no encontrada'}), 404
    max_o = max(1, int(h.get('ordenyos_dia', 2)))
    if numero_ordenyo < 1 or numero_ordenyo > max_o:
        return jsonify({'ok': False, 'error': f'numero_ordenyo fuera de rango (1..{max_o})'}), 400
    # UPSERT
    try:
        with mysql.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO produccion_leche (hembra_id, fecha, numero_ordenyo, litros)
                VALUES (%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE litros=VALUES(litros), creado_en=CURRENT_TIMESTAMP
                """,
                (hembra_id, fecha, numero_ordenyo, litros),
            )
            mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
        return jsonify({'ok': False, 'error': 'Error al guardar'}), 500
    return jsonify({'ok': True, 'msg': 'Registro guardado'}), 200

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
        activo = 1 if request.form.getlist("activo")[-1] == "1" else 0
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
        if activo:
            fecha_desincorporacion = None
            causa_desincorporacion = None
            if not nombre or condicion is None:
                flash("Nombre y condición son obligatorios.", "warning")
                return redirect(url_for("ganaderia.registro_hembras"))
        else:
            if not fecha_desincorporacion or not causa_desincorporacion:
                flash(
                    "Fecha y causa de desincorporación son obligatorias al desactivar.",
                    "warning",
                )
                return redirect(url_for("ganaderia.registro_hembras"))
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
            # número único para todos los animales
            cursor.execute("INSERT INTO animales () VALUES ()")
            numero = cursor.lastrowid
            cursor.execute(
                 "INSERT INTO hembras (numero, nombre, tipo, condicion, activo, fecha_nacimiento, origen, fecha_incorporacion, padre_id, madre_id, fecha_desincorporacion, causa_desincorporacion, foto) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    numero,
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
            mysql.connection.commit()
        flash("Hembra registrada correctamente.", "success")
        return redirect(url_for("ganaderia.registro_hembras"))

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute("SELECT COALESCE(MAX(numero),0)+1 AS n FROM animales")
        row = cursor.fetchone() or {}
        next_numero = row.get("n", 1)
        cursor.execute("SELECT id, numero, nombre FROM machos ORDER BY numero")
        machos = cursor.fetchall() or []
        cursor.execute("SELECT id, numero, nombre FROM hembras ORDER BY numero")
        madres = cursor.fetchall() or []
        cursor.execute(
            "SELECT h.*, p.numero AS padre_numero, m.numero AS madre_numero "
            "FROM hembras h "
            "LEFT JOIN machos p ON h.padre_id = p.id "
            "LEFT JOIN hembras m ON h.madre_id = m.id "
            "ORDER BY h.id ASC"
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

@ganaderia_bp.route('/registro_hembras/buscar')
def buscar_hembra():
    if 'usuario' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    term = request.args.get('term', '').strip()
    if not term:
        return jsonify({'error': 'not found'}), 404
    if term.isdigit():
        query = 'SELECT * FROM hembras WHERE numero=%s'
        params = (term,)
    else:
        query = 'SELECT * FROM hembras WHERE nombre LIKE %s ORDER BY numero LIMIT 2'
        params = (f"%{term}%",)
    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute(query, params)
        hembras = cursor.fetchall()
    if not hembras:
        return jsonify({'error': 'not found'}), 404
    hembra = hembras[0]
    for campo in ['fecha_nacimiento', 'fecha_incorporacion', 'fecha_desincorporacion']:
        if hembra.get(campo):
            hembra[campo] = hembra[campo].isoformat()
    # Normalizar condicion a string con 1 decimal para facilitar el llenado del <select>
    try:
        if hembra.get('condicion') is not None:
            hembra['condicion'] = f"{float(hembra['condicion']):.1f}"
    except Exception:
        pass
    if len(hembras) > 1:
        hembra['multiple'] = True
    return jsonify(hembra)
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
    try:
        if hembra.get('condicion') is not None:
            hembra['condicion'] = f"{float(hembra['condicion']):.1f}"
    except Exception:
        pass
    return jsonify(hembra)

@ganaderia_bp.route('/registro_hembras/actualizar', methods=['POST'])
def actualizar_hembra():
    if 'usuario' not in session or session.get('rol') not in ['admin', 'supervisor']:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('ganaderia.registro_hembras'))

    hembra_id = request.form.get('hembra_id')
    if not hembra_id:
        flash('ID inválido', 'warning')
        return redirect(url_for('ganaderia.registro_hembras'))

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute('SELECT * FROM hembras WHERE id=%s', (hembra_id,))
        hembra = cursor.fetchone()
    if not hembra:
        flash('Hembra no encontrada', 'warning')
        return redirect(url_for('ganaderia.registro_hembras'))
    numero_raw = request.form.get('numero')
    try:
        numero = int(numero_raw) if numero_raw else hembra.get('numero')
    except (TypeError, ValueError):
        numero = hembra.get('numero')

    nombre = request.form.get('nombre') or hembra.get('nombre')
    tipo = request.form.get('tipo') or hembra.get('tipo')
    cond_raw = request.form.get('condicion')
    if cond_raw is None:
        condicion = hembra.get('condicion')
    else:
        try:
            condicion = float(cond_raw)
        except (TypeError, ValueError):
            condicion = None
    activo = 1 if request.form.getlist('activo')[-1] == '1' else 0
    fecha_nacimiento = request.form.get('fecha_nacimiento') or hembra.get('fecha_nacimiento')
    origen = request.form.get('origen') or hembra.get('origen')
    fecha_incorporacion = request.form.get('fecha_incorporacion') or hembra.get('fecha_incorporacion')
    padre_raw = request.form.get('padre_id')
    madre_raw = request.form.get('madre_id')
    padre_id = int(padre_raw) if padre_raw else hembra.get('padre_id')  
    madre_id = int(madre_raw) if madre_raw else hembra.get('madre_id')
    if padre_id == 0:
        padre_id = None
    fecha_desincorporacion = request.form.get('fecha_desincorporacion') or None
    causa_desincorporacion = request.form.get('causa_desincorporacion') or None
    if activo:
        fecha_desincorporacion = None
        causa_desincorporacion = None
        if not nombre or condicion is None:
            flash('Nombre y condición son obligatorios.', 'warning')
            return redirect(url_for('ganaderia.registro_hembras'))
    else:
        if not fecha_desincorporacion or not causa_desincorporacion:
            flash('Fecha y causa de desincorporación son obligatorias al desactivar.', 'warning')
            return redirect(url_for('ganaderia.registro_hembras'))
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

    old_numero = hembra.get('numero')
    if numero != old_numero:
        with mysql.connection.cursor() as cursor:
            cursor.execute('SELECT numero FROM animales WHERE numero=%s', (numero,))
            if cursor.fetchone():
                flash('El ID ya existe en el sistema.', 'warning')
                return redirect(url_for('ganaderia.registro_hembras'))
            cursor.execute('UPDATE animales SET numero=%s WHERE numero=%s', (numero, old_numero))

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
            'UPDATE hembras SET numero=%s, nombre=%s, tipo=%s, condicion=%s, activo=%s, fecha_nacimiento=%s, origen=%s, fecha_incorporacion=%s, padre_id=%s, madre_id=%s, fecha_desincorporacion=%s, causa_desincorporacion=%s, foto=%s WHERE id=%s',
            (
                numero,
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
        activo = 1 if request.form.getlist("activo")[-1] == "1" else 0
        nombre = request.form.get("nombre") or hembra.get("nombre")
        tipo = request.form.get("tipo") or hembra.get("tipo")
        cond_raw = request.form.get("condicion")
        if cond_raw is None:
            condicion = hembra.get("condicion")
        else:
            try:
                condicion = float(cond_raw)
            except (TypeError, ValueError):
                condicion = None
        fecha_nacimiento = request.form.get("fecha_nacimiento") or hembra.get("fecha_nacimiento")
        origen = request.form.get("origen") or hembra.get("origen")
        fecha_incorporacion = request.form.get("fecha_incorporacion") or hembra.get("fecha_incorporacion")
        padre_raw = request.form.get("padre_id")
        madre_raw = request.form.get("madre_id")
        padre_id = int(padre_raw) if padre_raw else hembra.get("padre_id")
        madre_id = int(madre_raw) if madre_raw else hembra.get("madre_id")
        fecha_desincorporacion = request.form.get("fecha_desincorporacion") or hembra.get("fecha_desincorporacion")
        causa_desincorporacion = request.form.get("causa_desincorporacion") or hembra.get("causa_desincorporacion")
        if padre_id == 0: 
            padre_id = None 
        if activo:
            fecha_desincorporacion = None
            causa_desincorporacion = None
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

        if activo and (not nombre or condicion is None):
            flash("Nombre y condición son obligatorios.", "warning")
        elif not activo and (not fecha_desincorporacion or not causa_desincorporacion):
            flash(
                "Fecha y causa de desincorporación son obligatorias al desactivar.",
                "warning",
            )
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
                condicion=condicion,
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
        cursor.execute("SELECT id, numero, nombre FROM machos ORDER BY numero")
        machos = cursor.fetchall() or []
        cursor.execute("SELECT id, numero, nombre FROM hembras ORDER BY numero")
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
        cursor.execute("SELECT id, numero, nombre FROM hembras WHERE id=%s", (hembra_id,))
        hembra = cursor.fetchone()

    if not hembra:
        flash("Hembra no encontrada", "warning")
        return redirect(url_for("ganaderia.registro_hembras"))

    if request.method == "POST":
        with mysql.connection.cursor() as cursor:
            cursor.execute("DELETE FROM hembras WHERE id=%s", (hembra_id,))
            cursor.execute("DELETE FROM animales WHERE numero=%s", (hembra['numero'],))
            mysql.connection.commit()
        flash("Hembra eliminada correctamente.", "success")
        return redirect(url_for("ganaderia.registro_hembras"))

    return render_template("eliminar_hembra.html", hembra=hembra)


@ganaderia_bp.route("/machos", methods=["GET", "POST"])
def registro_machos():
    if "usuario" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        nombre = request.form.get("nombre")
        tipo = request.form.get("tipo")
        cond_raw = request.form.get("condicion")
        try:
            condicion = float(cond_raw) if cond_raw else None
        except (TypeError, ValueError):
            condicion = None
        activo = 1 if request.form.getlist("activo")[-1] == "1" else 0
        fecha_nacimiento = request.form.get("fecha_nacimiento") or None
        fecha_incorporacion = request.form.get("fecha_incorporacion") or None
        origen = request.form.get("origen")
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

        if activo:
            fecha_desincorporacion = None
            causa_desincorporacion = None
            if not nombre or condicion is None:
                flash("Nombre y condición son obligatorios.", "warning")
                return redirect(url_for("ganaderia.registro_machos"))
        else:
            if not fecha_desincorporacion or not causa_desincorporacion:
                flash(
                    "Fecha y causa de desincorporación son obligatorias al desactivar.",
                    "warning",
                )
                return redirect(url_for("ganaderia.registro_machos"))

        foto_file = request.files.get("foto")
        foto_path = None
        if foto_file and foto_file.filename:
            filename = secure_filename(foto_file.filename)
            ext = filename.rsplit(".", 1)[-1].lower()
            if ext not in ALLOWED_EXTS:
                flash("Formato de imagen no permitido.", "warning")
                return redirect(url_for("ganaderia.registro_machos"))
            foto_file.seek(0, os.SEEK_END)
            size = foto_file.tell()
            foto_file.seek(0)
            if size > MAX_IMAGE_SIZE:
                flash("La imagen supera el tamaño máximo permitido.", "warning")
                return redirect(url_for("ganaderia.registro_machos"))
            dir_path = os.path.join(current_app.root_path, "static", "imagenes", "machos")
            os.makedirs(dir_path, exist_ok=True)
            unique_name = f"{int(time.time())}_{filename}"
            foto_file.save(os.path.join(dir_path, unique_name))
            foto_path = os.path.join("imagenes", "machos", unique_name)

        with mysql.connection.cursor() as cursor:
            cursor.execute("INSERT INTO animales () VALUES ()")
            numero = cursor.lastrowid
            cursor.execute(
                """INSERT INTO machos (
                    numero, nombre, tipo, condicion, activo, fecha_nacimiento,
                    fecha_incorporacion, origen, padre_id, madre_id,
                    fecha_desincorporacion, causa_desincorporacion, foto
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    numero,
                    nombre,
                    tipo,
                    condicion,
                    activo,
                    fecha_nacimiento,
                    fecha_incorporacion,
                    origen,
                    padre_id,
                    madre_id,
                    fecha_desincorporacion,
                    causa_desincorporacion,
                    foto_path,
                ),
            )
            mysql.connection.commit()
        flash("Macho registrado correctamente.", "success")
        return redirect(url_for("ganaderia.registro_machos"))

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute("SELECT COALESCE(MAX(numero),0)+1 AS n FROM animales")
        row = cursor.fetchone() or {}
        next_numero = row.get("n", 1)

        cursor.execute("SELECT id, numero, nombre FROM machos ORDER BY numero")
        padres = cursor.fetchall() or []
        cursor.execute("SELECT id, numero, nombre FROM hembras ORDER BY numero")
        madres = cursor.fetchall() or []

        cursor.execute(
            "SELECT COUNT(*) AS c FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='pesajes'"
        )
        tiene_pesajes = (cursor.fetchone() or {}).get("c", 0)
        if tiene_pesajes:
            cursor.execute(
                """SELECT m.*, 
                           (SELECT p.peso FROM pesajes p WHERE p.animal_id=m.id ORDER BY p.fecha DESC LIMIT 1) AS ultimo_peso,
                           (SELECT p.fecha FROM pesajes p WHERE p.animal_id=m.id ORDER BY p.fecha DESC LIMIT 1) AS fecha_ultimo_pesaje
                    FROM machos m
                    ORDER BY m.numero ASC"""
            )
        else:
            cursor.execute(
                "SELECT m.*, NULL AS ultimo_peso, NULL AS fecha_ultimo_pesaje FROM machos m ORDER BY m.numero ASC"
            )
        machos = cursor.fetchall() or []

    for m in machos:
        m["edad"] = calcular_edad(m.get("fecha_nacimiento"))

    return render_template(
        "registro_machos.html",
        machos=machos,
        padres=padres,
        madres=madres,
        next_numero=next_numero,
    )

# ---------------------- Partos API ----------------------
@ganaderia_bp.route('/partos/api/hembra')
def partos_api_hembra():
    if 'usuario' not in session:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    numero = request.args.get('numero')
    hid = request.args.get('id')
    hembra = None
    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        if numero:
            cursor.execute("SELECT id, numero, nombre, fecha_nacimiento FROM hembras WHERE numero=%s", (numero,))
        elif hid:
            cursor.execute("SELECT id, numero, nombre, fecha_nacimiento FROM hembras WHERE id=%s", (hid,))
        else:
            return jsonify({'ok': False, 'error': 'parámetro requerido (numero o id)'}), 400
        hembra = cursor.fetchone()
        if not hembra:
            return jsonify({'ok': False, 'error': 'Hembra no encontrada'}), 404
        cursor.execute("SELECT COUNT(*) AS c FROM partos WHERE hembra_id=%s", (hembra['id'],))
        num_crias = (cursor.fetchone() or {}).get('c', 0)
        cursor.execute("SELECT fecha FROM partos WHERE hembra_id=%s ORDER BY fecha DESC LIMIT 2", (hembra['id'],))
        fechas = cursor.fetchall() or []
        ultimo = fechas[0]['fecha'] if len(fechas) >= 1 else None
        penultimo = fechas[1]['fecha'] if len(fechas) >= 2 else None
        cursor.execute("SELECT MIN(fecha) AS first FROM partos WHERE hembra_id=%s", (hembra['id'],))
        first = (cursor.fetchone() or {}).get('first')
    primer_parto_meses = 0
    if hembra.get('fecha_nacimiento') and first:
        fn = hembra['fecha_nacimiento']
        primer_parto_meses = (first.year - fn.year) * 12 + (first.month - fn.month)
        if first.day < fn.day:
            primer_parto_meses = max(0, primer_parto_meses - 1)
    intervalo = 0
    if ultimo and penultimo:
        intervalo = (ultimo - penultimo).days
    return jsonify({
        'ok': True,
        'hembra': {'id': hembra['id'], 'numero': hembra['numero'], 'nombre': hembra['nombre']},
        'resumen': {
            'num_crias': int(num_crias),
            'primer_parto_edad_meses': int(primer_parto_meses),
            'ultimo_parto': ultimo.isoformat() if ultimo else None,
            'penultimo_parto': penultimo.isoformat() if penultimo else None,
            'intervalo_dias': int(intervalo)
        }
    })

@ganaderia_bp.route('/partos/api/registrar', methods=['POST'])
def partos_api_registrar():
    if 'usuario' not in session:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    if not request.is_json:
        return jsonify({'ok': False, 'error': 'Contenido no JSON'}), 400
    data = request.get_json(silent=True) or {}
    numero = data.get('hembra_numero')
    hembra_id = data.get('hembra_id')
    try:
        numero_parto = int(data.get('numero_parto'))
    except Exception:
        return jsonify({'ok': False, 'error': 'numero_parto inválido'}), 400
    fecha = data.get('fecha')
    sexo = data.get('sexo_cria')
    if sexo not in ('Macho','Hembra'):
        return jsonify({'ok': False, 'error': 'sexo_cria inválido'}), 400
    numero_cria = data.get('numero_cria')
    try:
        peso = float(data.get('peso_nacer')) if data.get('peso_nacer') is not None else None
    except Exception:
        return jsonify({'ok': False, 'error': 'peso_nacer inválido'}), 400
    num_toro = data.get('num_toro')
    tipo_parto = data.get('tipo_parto')
    if tipo_parto and tipo_parto not in ('Normal','Asistido','Mortinato'):
        return jsonify({'ok': False, 'error': 'tipo_parto inválido'}), 400

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        if not hembra_id and numero:
            cursor.execute("SELECT id FROM hembras WHERE numero=%s", (numero,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'ok': False, 'error': 'Hembra no encontrada'}), 404
            hembra_id = row['id']
        elif hembra_id:
            try:
                hembra_id = int(hembra_id)
            except Exception:
                return jsonify({'ok': False, 'error': 'hembra_id inválido'}), 400
        else:
            return jsonify({'ok': False, 'error': 'Indique hembra_numero o hembra_id'}), 400
        toro_id = None
        if num_toro:
            cursor.execute("SELECT id FROM machos WHERE numero=%s", (num_toro,))
            toro = cursor.fetchone()
            toro_id = toro['id'] if toro else None
        try:
            cursor.execute(
                """
                INSERT INTO partos (hembra_id, numero_parto, fecha, sexo_cria, numero_cria, peso_nacer, toro_id, tipo_parto)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE fecha=VALUES(fecha), sexo_cria=VALUES(sexo_cria),
                    numero_cria=VALUES(numero_cria), peso_nacer=VALUES(peso_nacer), toro_id=VALUES(toro_id), tipo_parto=VALUES(tipo_parto)
                """,
                (hembra_id, numero_parto, fecha, sexo, numero_cria, peso, toro_id, tipo_parto)
            )
            mysql.connection.commit()
        except Exception:
            mysql.connection.rollback()
            return jsonify({'ok': False, 'error': 'Error al guardar'}), 500
    return jsonify({'ok': True, 'msg': 'Parto registrado'}), 200

@ganaderia_bp.route('/registro_machos/buscar')
def buscar_macho():
    if 'usuario' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    term = request.args.get('term', '').strip()
    if not term:
        return jsonify({'error': 'not found'}), 404
    if term.isdigit():
        query = 'SELECT * FROM machos WHERE numero=%s'
        params = (term,)
    else:
        query = 'SELECT * FROM machos WHERE nombre LIKE %s ORDER BY numero LIMIT 2'
        params = (f"%{term}%",)
    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute(query, params)
        machos = cursor.fetchall()
    if not machos:
        return jsonify({'error': 'not found'}), 404
    macho = machos[0]
    for campo in ['fecha_nacimiento', 'fecha_incorporacion', 'fecha_desincorporacion']:
        if macho.get(campo):
            macho[campo] = macho[campo].isoformat()
    if len(machos) > 1:
        macho['multiple'] = True
    return jsonify(macho)

@ganaderia_bp.route('/registro_machos/actualizar', methods=['POST'])
def actualizar_macho():
    if 'usuario' not in session or session.get('rol') not in ['admin', 'supervisor']:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('ganaderia.registro_machos'))

    macho_id = request.form.get('macho_id')
    if not macho_id:
        flash('ID inválido', 'warning')
        return redirect(url_for('ganaderia.registro_machos'))

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute('SELECT * FROM machos WHERE id=%s', (macho_id,))
        macho = cursor.fetchone()
    if not macho:
        flash('Macho no encontrado', 'warning')
        return redirect(url_for('ganaderia.registro_machos'))

    numero_raw = request.form.get('numero')
    try:
        numero = int(numero_raw) if numero_raw else macho.get('numero')
    except (TypeError, ValueError):
        numero = macho.get('numero')
    nombre = request.form.get('nombre') or macho.get('nombre')
    tipo = request.form.get('tipo') or macho.get('tipo')
    cond_raw = request.form.get('condicion')
    if cond_raw is None:
        condicion = macho.get('condicion')
    else:
        try:
            condicion = float(cond_raw)
        except (TypeError, ValueError):
            condicion = None
    activo = 1 if request.form.getlist('activo')[-1] == '1' else 0
    fecha_nacimiento = request.form.get('fecha_nacimiento') or macho.get('fecha_nacimiento')
    origen = request.form.get('origen') or macho.get('origen')
    fecha_incorporacion = request.form.get('fecha_incorporacion') or macho.get('fecha_incorporacion')
    padre_raw = request.form.get('padre_id')
    madre_raw = request.form.get('madre_id')
    padre_id = int(padre_raw) if padre_raw else macho.get('padre_id')
    madre_id = int(madre_raw) if madre_raw else macho.get('madre_id')
    if padre_id == 0:
        padre_id = None
    fecha_desincorporacion = request.form.get('fecha_desincorporacion') or None
    causa_desincorporacion = request.form.get('causa_desincorporacion') or None
    if activo:
        fecha_desincorporacion = None
        causa_desincorporacion = None
        if not nombre or condicion is None:
            flash('Nombre y condición son obligatorios.', 'warning')
            return redirect(url_for('ganaderia.registro_machos'))
    else:
        if not fecha_desincorporacion or not causa_desincorporacion:
            flash('Fecha y causa de desincorporación son obligatorias al desactivar.', 'warning')
            return redirect(url_for('ganaderia.registro_machos'))

    foto_path = macho.get('foto')
    foto_file = request.files.get('foto')
    if foto_file and foto_file.filename:
        filename = secure_filename(foto_file.filename)
        ext = filename.rsplit('.', 1)[-1].lower()
        if ext not in ALLOWED_EXTS:
            flash('Formato de imagen no permitido.', 'warning')
            return redirect(url_for('ganaderia.registro_machos'))
        foto_file.seek(0, os.SEEK_END)
        size = foto_file.tell()
        foto_file.seek(0)
        if size > MAX_IMAGE_SIZE:
            flash('La imagen supera el tamaño máximo permitido.', 'warning')
            return redirect(url_for('ganaderia.registro_machos'))
        dir_path = os.path.join(current_app.root_path, 'static', 'imagenes', 'machos')
        os.makedirs(dir_path, exist_ok=True)
        unique_name = f"{int(time.time())}_{filename}"
        foto_file.save(os.path.join(dir_path, unique_name))
        foto_path = os.path.join('imagenes', 'machos', unique_name)

    old_numero = macho.get('numero')
    if numero != old_numero:
        with mysql.connection.cursor() as cursor:
            cursor.execute('SELECT numero FROM animales WHERE numero=%s', (numero,))
            if cursor.fetchone():
                flash('El ID ya existe en el sistema.', 'warning')
                return redirect(url_for('ganaderia.registro_machos'))
            cursor.execute('UPDATE animales SET numero=%s WHERE numero=%s', (numero, old_numero))

    with mysql.connection.cursor() as cursor:
        cursor.execute(
            'UPDATE machos SET numero=%s, nombre=%s, tipo=%s, condicion=%s, activo=%s, fecha_nacimiento=%s, fecha_incorporacion=%s, origen=%s, padre_id=%s, madre_id=%s, fecha_desincorporacion=%s, causa_desincorporacion=%s, foto=%s WHERE id=%s',
            (numero, nombre, tipo, condicion, activo, fecha_nacimiento, fecha_incorporacion, origen, padre_id, madre_id, fecha_desincorporacion, causa_desincorporacion, foto_path, macho_id),
        )
        mysql.connection.commit()
    flash('Macho actualizado correctamente.', 'success')
    return redirect(url_for('ganaderia.registro_machos'))

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

