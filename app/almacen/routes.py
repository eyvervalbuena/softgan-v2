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
        cantidad = request.form.get('cantidad') or 0
        unidad = request.form.get('unidad')
        fecha_ingreso = request.form.get('fechaIngreso')
        fecha_vencimiento = request.form.get('fechaVencimiento') or None
        observaciones = request.form.get('Observaciones')

        if not nombre or not codigo or not fecha_ingreso:
            flash('Nombre, código y fecha de ingreso son obligatorios.', 'warning')
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
                flash('Insumo guardado correctamente.', 'success')
            except Exception:
                mysql.connection.rollback()
                flash('Error al guardar el insumo.', 'danger')

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute(
            'SELECT i.*, u.usuario FROM insumos i '
            'LEFT JOIN usuarios u ON i.creado_por=u.id '
            'ORDER BY fecha_ingreso DESC'
        )
        insumos = cursor.fetchall() or []

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
        cantidad = request.form.get('cantidad') or 0
        unidad = request.form.get('unidad')
        fecha_ingreso = request.form.get('fecha_ingreso')
        fecha_vencimiento = request.form.get('fecha_vencimiento') or None
        observaciones = request.form.get('observaciones')

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



@almacen_bp.route('/maquinaria')
def almacen_maquinaria():
    return render_template('almacen_maquinaria.html')

@almacen_bp.route('/agroquimicos')
def almacen_agroquimicos():
    return render_template('almacen_agroquimicos.html')
