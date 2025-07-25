from flask import Blueprint, render_template, redirect, url_for, flash, session, request
import MySQLdb.cursors

from .. import mysql

alertas_bp = Blueprint('alertas', __name__, url_prefix='/alertas')

@alertas_bp.route('/')
def lista_alertas():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder.', 'warning')
        return redirect(url_for('auth.login'))
    filtro = request.args.get('filtro', '').strip()
    fecha = request.args.get('fecha', '').strip()
    query = "SELECT a.id, a.fecha, a.nombre, a.descripcion, a.tipo, u.usuario FROM alertas a LEFT JOIN usuarios u ON a.creada_por=u.id WHERE a.finca_id=%s"
    params = [session.get('finca_id')]
    if filtro:
        query += " AND a.nombre LIKE %s"
        params.append(f"%{filtro}%")
    if fecha:
        query += " AND a.fecha=%s"
        params.append(fecha)
    query += " ORDER BY a.fecha DESC"
    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute(query, tuple(params))
        alertas = cursor.fetchall() or []
    return render_template('listar_alertas.html', alertas=alertas, filtro=filtro, fecha=fecha)


@alertas_bp.route('/crear', methods=['GET', 'POST'])
def crear_alerta():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder.', 'warning')
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        fecha = request.form.get('fecha')
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        with mysql.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO alertas (fecha, nombre, descripcion, tipo, creada_por, finca_id) VALUES (%s, %s, %s, 'manual', %s, %s)",
                (fecha, nombre, descripcion, session.get('user_id'), session.get('finca_id')),
            )
            mysql.connection.commit()
        flash('Alerta creada correctamente.', 'success')
        return redirect(url_for('alertas.lista_alertas'))
    return render_template('crear_alerta.html')


@alertas_bp.route('/editar/<int:alerta_id>', methods=['GET', 'POST'])
def editar_alerta(alerta_id):
    if 'usuario' not in session or session.get('rol') not in ['admin', 'supervisor']:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('alertas.lista_alertas'))
    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute('SELECT * FROM alertas WHERE id=%s AND finca_id=%s', (alerta_id, session.get('finca_id')))
        alerta = cursor.fetchone()
    if not alerta:
        flash('Alerta no encontrada', 'warning')
        return redirect(url_for('alertas.lista_alertas'))
    if request.method == 'POST':
        fecha = request.form.get('fecha')
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        with mysql.connection.cursor() as cursor:
            cursor.execute(
                'UPDATE alertas SET fecha=%s, nombre=%s, descripcion=%s WHERE id=%s',
                (fecha, nombre, descripcion, alerta_id),
            )
            mysql.connection.commit()
        flash('Alerta actualizada correctamente.', 'success')
        return redirect(url_for('alertas.lista_alertas'))
    return render_template('editar_alerta.html', alerta=alerta)


@alertas_bp.route('/eliminar/<int:alerta_id>', methods=['GET', 'POST'])
def eliminar_alerta(alerta_id):
    if 'usuario' not in session or session.get('rol') != 'admin':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('alertas.lista_alertas'))
    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute('SELECT id, nombre FROM alertas WHERE id=%s AND finca_id=%s', (alerta_id, session.get('finca_id')))
        alerta = cursor.fetchone()
    if not alerta:
        flash('Alerta no encontrada', 'warning')
        return redirect(url_for('alertas.lista_alertas'))
    if request.method == 'POST':
        with mysql.connection.cursor() as cursor:
            cursor.execute('DELETE FROM alertas WHERE id=%s', (alerta_id,))
            mysql.connection.commit()
        flash('Alerta eliminada correctamente.', 'success')
        return redirect(url_for('alertas.lista_alertas'))
    return render_template('eliminar_alerta.html', alerta=alerta)