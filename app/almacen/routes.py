from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    request,
)
import MySQLdb.cursors
from datetime import date
from .. import mysql

almacen_bp = Blueprint('almacen', __name__, url_prefix='/almacen')

@almacen_bp.route('/', methods=['GET', 'POST'])
def almacen_insumos():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder.', 'warning')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        if session.get('rol') not in ['admin', 'supervisor']:
            flash('Acceso no autorizado', 'danger')
            return redirect(url_for('almacen.almacen_insumos'))

        nombre = request.form.get('nombreInsumo')
        codigo = request.form.get('Codigo')
        cantidad_raw = request.form.get('cantidad')
        try:
            cantidad = float(cantidad_raw)
        except (TypeError, ValueError):
            cantidad = 0
        unidad = request.form.get('unidad')
        fecha_ingreso = request.form.get('fechaIngreso')
        fecha_vencimiento = request.form.get('fechaVencimiento') or None
        observaciones = request.form.get('Observaciones')

        if not nombre or not codigo or not fecha_ingreso:
            flash('Nombre, código y fecha de ingreso son obligatorios.', 'warning')
        if cantidad <= 0:
            flash('La cantidad debe ser mayor que cero.', 'warning')
        else:
            try:
                with mysql.connection.cursor() as cursor:
                    cursor.execute(
                        'INSERT INTO insumos (nombre, codigo, cantidad, unidad, fecha_ingreso, fecha_vencimiento, observaciones, creado_por) '
                        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                        (
                            nombre,
                            codigo,
                            cantidad,
                            unidad,
                            fecha_ingreso,
                            fecha_vencimiento,
                            observaciones,
                            session.get('user_id'),
                        ),
                    )
                    mysql.connection.commit()
                    if fecha_vencimiento:
                        try:
                            fv = date.fromisoformat(fecha_vencimiento)
                            dias = (fv - date.today()).days
                            if 0 <= dias <= 30:
                                cursor.execute(
                                    "SELECT id FROM alertas WHERE tipo='automatica' AND nombre=%s AND finca_id=%s AND estado='pendiente'",
                                    (nombre, session.get('finca_id')),
                                )
                                existe = cursor.fetchone()
                                if not existe:
                                    cursor.execute(
                                        "INSERT INTO alertas (fecha, nombre, descripcion, tipo, creada_por, finca_id, estado, visto) "
                                        "VALUES (%s, %s, 'Vencimiento pr\xc3\xb3ximo', 'automatica', NULL, %s, 'pendiente', 0)",
                                        (fecha_vencimiento, nombre, session.get('finca_id')),
                                    )
                                    mysql.connection.commit()
                        except ValueError:
                            pass
                flash('Insumo guardado correctamente.', 'success')
            except Exception:
                mysql.connection.rollback()
                flash('Error al guardar el insumo.', 'danger')

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute(
            'SELECT i.*, u.usuario FROM insumos i '
            'LEFT JOIN usuarios u ON i.creado_por=u.id '
            'ORDER BY codigo ASC'
        )
        insumos = cursor.fetchall() or []
        
    hoy = date.today()
    with mysql.connection.cursor() as cursor:
        for ins in insumos:
            clase = ''
            fv = ins.get('fecha_vencimiento')
            if fv:
                dias = (fv - hoy).days
                if dias < 0:
                    clase = 'table-secondary'
                elif dias <= 7:
                    clase = 'table-danger'
                elif dias <= 30:
                    clase = 'table-warning'
                if 0 <= dias <= 30:
                    cursor.execute(
                        "SELECT id FROM alertas WHERE tipo='automatica' AND nombre=%s AND finca_id=%s AND estado='pendiente'",
                        (ins['nombre'], session.get('finca_id')),
                    )
                    if not cursor.fetchone():
                        cursor.execute(
                            "INSERT INTO alertas (fecha, nombre, descripcion, tipo, creada_por, finca_id, estado, visto) "
                            "VALUES (%s, %s, 'Vencimiento pr\xc3\xb3ximo', 'automatica', NULL, %s, 'pendiente', 0)",
                            (ins['fecha_vencimiento'], ins['nombre'], session.get('finca_id')),
                        )
            ins['row_class'] = clase
        mysql.connection.commit()

    return render_template('almacen_insumos.html', insumos=insumos)


@almacen_bp.route('/editar/<int:insumo_id>', methods=['GET', 'POST'])
def editar_insumo(insumo_id):
    if 'usuario' not in session or session.get('rol') not in ['admin', 'supervisor']:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('almacen.almacen_insumos'))

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute('SELECT * FROM insumos WHERE id=%s', (insumo_id,))
        insumo = cursor.fetchone()

    if not insumo:
        flash('Insumo no encontrado', 'warning')
        return redirect(url_for('almacen.almacen_insumos'))

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        codigo = request.form.get('codigo')
        cantidad_raw = request.form.get('cantidad')
        try:
            cantidad = float(cantidad_raw)
        except (TypeError, ValueError):
            cantidad = 0
        unidad = request.form.get('unidad')
        fecha_ingreso = request.form.get('fecha_ingreso')
        fecha_vencimiento = request.form.get('fecha_vencimiento') or None
        observaciones = request.form.get('observaciones')


        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute(
                'SELECT id FROM insumos WHERE codigo=%s AND id!=%s',
                (codigo, insumo_id),
            )
            existente = cursor.fetchone()

        if existente:
            flash(
                'Este c\xc3\xb3digo ya est\xc3\xa1 en uso por otro insumo. Por favor usa uno \xc3\xbAnico.',
                'warning',
            )

    
            insumo.update(
                dict(
                    nombre=nombre,
                    codigo=codigo,
                    cantidad=cantidad,
                    unidad=unidad,
                    fecha_ingreso=fecha_ingreso,
                    fecha_vencimiento=fecha_vencimiento,
                    observaciones=observaciones,
                )
            )
            return render_template('editar_insumo.html', insumo=insumo)
        

        elif cantidad <= 0:
            flash('La cantidad debe ser mayor que cero.', 'warning')
            insumo.update(
                dict(
                    nombre=nombre,
                    codigo=codigo,
                    cantidad=cantidad_raw,
                    unidad=unidad,
                    fecha_ingreso=fecha_ingreso,
                    fecha_vencimiento=fecha_vencimiento,
                    observaciones=observaciones,
                )
            )
            return render_template('editar_insumo.html', insumo=insumo)

        with mysql.connection.cursor() as cursor:
            cursor.execute(
                'UPDATE insumos SET nombre=%s, codigo=%s, cantidad=%s, unidad=%s, fecha_ingreso=%s, fecha_vencimiento=%s, observaciones=%s WHERE id=%s',
                (
                    nombre,
                    codigo,
                    cantidad,
                    unidad,
                    fecha_ingreso,
                    fecha_vencimiento,
                    observaciones,
                    insumo_id,
                ),
            )
            mysql.connection.commit()
            if fecha_vencimiento:
                try:
                    fv = date.fromisoformat(fecha_vencimiento)
                    dias = (fv - date.today()).days
                    if 0 <= dias <= 30:
                        cursor.execute(
                            "SELECT id FROM alertas WHERE tipo='automatica' AND nombre=%s AND finca_id=%s AND estado='pendiente'",
                            (nombre, session.get('finca_id')),
                        )
                        existe = cursor.fetchone()
                        if not existe:
                            cursor.execute(
                                "INSERT INTO alertas (fecha, nombre, descripcion, tipo, creada_por, finca_id, estado, visto) "
                                "VALUES (%s, %s, 'Vencimiento pr\xc3\xb3ximo', 'automatica', NULL, %s, 'pendiente', 0)",
                                (fecha_vencimiento, nombre, session.get('finca_id')),
                            )
                            mysql.connection.commit()
                except ValueError:
                    pass
        flash('Insumo actualizado correctamente.', 'success')
        return redirect(url_for('almacen.almacen_insumos'))

    return render_template('editar_insumo.html', insumo=insumo)


@almacen_bp.route('/eliminar/<int:insumo_id>', methods=['GET', 'POST'])
def eliminar_insumo(insumo_id):
    if 'usuario' not in session or session.get('rol') != 'admin':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('almacen.almacen_insumos'))

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute('SELECT nombre FROM insumos WHERE id=%s', (insumo_id,))
        insumo = cursor.fetchone()

    if not insumo:
        flash('Insumo no encontrado', 'warning')
        return redirect(url_for('almacen.almacen_insumos'))

    if request.method == 'POST':
        with mysql.connection.cursor() as cursor:
            cursor.execute('DELETE FROM insumos WHERE id=%s', (insumo_id,))
            mysql.connection.commit()
        flash('Insumo eliminado correctamente.', 'success')
        return redirect(url_for('almacen.almacen_insumos'))

    return render_template('eliminar_insumo.html', insumo=insumo)



@almacen_bp.route('/maquinaria', methods=['GET', 'POST'])
def almacen_maquinaria():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder.', 'warning')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        if session.get('rol') not in ['admin', 'supervisor']:
            flash('Acceso no autorizado', 'danger')
            return redirect(url_for('almacen.almacen_maquinaria'))

        nombre = request.form.get('nombreInsumo')
        codigo = request.form.get('Codigo')
        cantidad_raw = request.form.get('cantidad')
        try:
            cantidad = int(cantidad_raw)
        except (TypeError, ValueError):
            cantidad = 0
        fecha_ingreso = request.form.get('fechaIngreso')
        marca = request.form.get('marca') or None
        serie = request.form.get('serie') or None
        observaciones = request.form.get('Observaciones')

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('SELECT id FROM maquinaria WHERE codigo=%s', (codigo,))
            existente = cursor.fetchone()

        if not nombre or not codigo or not fecha_ingreso:
            flash('Nombre, código y fecha de ingreso son obligatorios.', 'warning')
        elif existente:
            flash('El código ya existe. Usa uno diferente.', 'warning')
        elif cantidad <= 0:
            flash('La cantidad debe ser mayor que cero.', 'warning')
        else:
            with mysql.connection.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO maquinaria (nombre, codigo, cantidad, fecha_ingreso, marca, serie, observaciones, creado_por) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                    (
                        nombre,
                        codigo,
                        cantidad,
                        fecha_ingreso,
                        marca,
                        serie,
                        observaciones,
                        session.get('user_id'),
                    ),
                )
                mysql.connection.commit()
            flash('Maquinaria guardada correctamente.', 'success')

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute(
            'SELECT m.*, u.usuario FROM maquinaria m '
            'LEFT JOIN usuarios u ON m.creado_por=u.id '
            'ORDER BY codigo ASC'
        )
        maquinaria = cursor.fetchall() or []

    return render_template('almacen_maquinaria.html', maquinaria=maquinaria)


@almacen_bp.route('/maquinaria/editar/<int:maq_id>', methods=['GET', 'POST'])
def editar_maquinaria(maq_id):
    if 'usuario' not in session or session.get('rol') not in ['admin', 'supervisor']:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('almacen.almacen_maquinaria'))

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute('SELECT * FROM maquinaria WHERE id=%s', (maq_id,))
        maquinaria = cursor.fetchone()

    if not maquinaria:
        flash('Maquinaria no encontrada', 'warning')
        return redirect(url_for('almacen.almacen_maquinaria'))

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        codigo = request.form.get('codigo')
        cantidad_raw = request.form.get('cantidad')
        try:
            cantidad = int(cantidad_raw)
        except (TypeError, ValueError):
            cantidad = 0
        fecha_ingreso = request.form.get('fecha_ingreso')
        marca = request.form.get('marca') or None
        serie = request.form.get('serie') or None
        observaciones = request.form.get('observaciones')

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('SELECT id FROM maquinaria WHERE codigo=%s AND id!=%s', (codigo, maq_id))
            existente = cursor.fetchone()

        if existente:
            flash('Este código ya está en uso por otra maquinaria. Por favor usa uno único.', 'warning')
            maquinaria.update(dict(nombre=nombre, codigo=codigo, cantidad=cantidad_raw, fecha_ingreso=fecha_ingreso, marca=marca, serie=serie, observaciones=observaciones))
            return render_template('editar_maquinaria.html', maquinaria=maquinaria)
        elif cantidad <= 0:
            flash('La cantidad debe ser mayor que cero.', 'warning')
            maquinaria.update(dict(nombre=nombre, codigo=codigo, cantidad=cantidad_raw, fecha_ingreso=fecha_ingreso, marca=marca, serie=serie, observaciones=observaciones))
            return render_template('editar_maquinaria.html', maquinaria=maquinaria)

        with mysql.connection.cursor() as cursor:
            cursor.execute(
                'UPDATE maquinaria SET nombre=%s, codigo=%s, cantidad=%s, fecha_ingreso=%s, marca=%s, serie=%s, observaciones=%s WHERE id=%s',
                (nombre, codigo, cantidad, fecha_ingreso, marca, serie, observaciones, maq_id),
            )
            mysql.connection.commit()
        flash('Maquinaria actualizada correctamente.', 'success')
        return redirect(url_for('almacen.almacen_maquinaria'))

    return render_template('editar_maquinaria.html', maquinaria=maquinaria)


@almacen_bp.route('/maquinaria/eliminar/<int:maq_id>', methods=['GET', 'POST'])
def eliminar_maquinaria(maq_id):
    if 'usuario' not in session or session.get('rol') != 'admin':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('almacen.almacen_maquinaria'))

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute('SELECT nombre FROM maquinaria WHERE id=%s', (maq_id,))
        maquinaria = cursor.fetchone()

    if not maquinaria:
        flash('Maquinaria no encontrada', 'warning')
        return redirect(url_for('almacen.almacen_maquinaria'))

    if request.method == 'POST':
        with mysql.connection.cursor() as cursor:
            cursor.execute('DELETE FROM maquinaria WHERE id=%s', (maq_id,))
            mysql.connection.commit()
        flash('Maquinaria eliminada correctamente.', 'success')
        return redirect(url_for('almacen.almacen_maquinaria'))

    return render_template('eliminar_maquinaria.html', maquinaria=maquinaria)



@almacen_bp.route('/agroquimicos')
def almacen_agroquimicos():
    return render_template('almacen_agroquimicos.html')
#API para validar código de insumo
@almacen_bp.route('/api/validar-codigo')
def validar_codigo_api():
    """Devuelve si un código ya existe para otro insumo."""
    codigo = request.args.get('codigo')
    insumo_id = request.args.get('id', type=int) or 0
    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute(
            'SELECT id FROM insumos WHERE codigo=%s AND id!=%s',
            (codigo, insumo_id),
        )
        existente = cursor.fetchone()
        return {'exists': bool(existente)}


@almacen_bp.route('/api/validar-codigo-maquinaria')
def validar_codigo_maquinaria_api():
    codigo = request.args.get('codigo')
    maq_id = request.args.get('id', type=int) or 0
    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute('SELECT id FROM maquinaria WHERE codigo=%s AND id!=%s', (codigo, maq_id))
        existente = cursor.fetchone()
    return {'exists': bool(existente)}