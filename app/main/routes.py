from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    request,
    jsonify,
)
import logging
import MySQLdb.cursors
from .. import mysql

main_bp = Blueprint('main', __name__)

def _edad(fecha_nacimiento):
    from datetime import date
    if not fecha_nacimiento:
        return ''
    today = date.today()
    years = today.year - fecha_nacimiento.year - (
        (today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
    )
    months = today.month - fecha_nacimiento.month - (today.day < fecha_nacimiento.day)
    if months < 0:
        months += 12
    return f"{years} años {months} meses"

@main_bp.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder.', 'warning')
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html', usuario=session['usuario'])

@main_bp.route('/crear_finca')
def crear_finca():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder.', 'warning')
        return redirect(url_for('auth.login'))
    return render_template('crear_finca.html')


@main_bp.route('/semovientes')
def semovientes():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder.', 'warning')
        return redirect(url_for('auth.login'))

    page = request.args.get('page', default=1, type=int)
    q = (request.args.get('q') or '').strip()
    per_page = 10
    offset = (page - 1) * per_page

    where = []
    params = []
    if q:
        like = f"%{q}%"
        where.append("(nombre LIKE %s OR origen LIKE %s OR sexo LIKE %s OR CAST(numero AS CHAR) LIKE %s)")
        params.extend([like, like, like, like])
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
        cursor.execute(f"SELECT COUNT(*) AS c FROM semovientes{where_sql}", params)
        total = (cursor.fetchone() or {}).get('c', 0)

        cursor.execute(
            f"SELECT * FROM semovientes{where_sql} ORDER BY numero ASC LIMIT %s OFFSET %s",
            params + [per_page, offset],
        )
        items = cursor.fetchall() or []

        # Contadores de activos (total, Hembra, Macho) respondiendo al filtro
        cursor.execute(
            f"""
            SELECT
              SUM(CASE WHEN activo=1 THEN 1 ELSE 0 END) AS activos_total,
              SUM(CASE WHEN activo=1 AND sexo='Hembra' THEN 1 ELSE 0 END) AS activos_h,
              SUM(CASE WHEN activo=1 AND sexo='Macho' THEN 1 ELSE 0 END) AS activos_m
            FROM semovientes{where_sql}
            """,
            params,
        )
        counts_row = cursor.fetchone() or {}
        activos_total = counts_row.get('activos_total', 0) or 0
        activos_h = counts_row.get('activos_h', 0) or 0
        activos_m = counts_row.get('activos_m', 0) or 0

    for it in items:
        it['edad'] = _edad(it.get('fecha_nacimiento'))

    total_pages = (total + per_page - 1) // per_page if per_page else 1
    # Soporte modo parcial para AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('partial') == '1'
    if is_ajax:
        tbody_html = render_template('partials/_semovientes_tbody.html', rows=items)
        pagination_html = render_template(
            'partials/_semovientes_pagination.html',
            page=page,
            total_pages=total_pages,
            q=q,
        )
        summary_html = render_template(
            'partials/_semovientes_summary.html',
            activos_total=activos_total,
            activos_h=activos_h,
            activos_m=activos_m,
        )
        # Preferimos JSON para evitar inserciones inválidas dentro de <tbody>
        return jsonify({
            'tbody': tbody_html,
            'pagination': pagination_html,
            'summary': summary_html,
        })

    return render_template(
        'semovientes.html',
        items=items,
        page=page,
        total_pages=total_pages,
        q=q,
        total=total,
        per_page=per_page,
        activos_total=activos_total,
        activos_h=activos_h,
        activos_m=activos_m,
    )


@main_bp.route('/semovientes/propietario', methods=['POST'])
def actualizar_propietario_semoviente():
    if 'usuario' not in session:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    rol = (session.get('rol') or '').lower()
    if rol not in ('admin', 'administrador'):
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    try:
        data = request.get_json(silent=True) or {}
        sid = int(data.get('id'))
        sexo = (data.get('sexo') or '').upper()
        propietario = (data.get('propietario') or '').strip()
    except Exception:
        return jsonify({'ok': False, 'error': 'invalid_payload'}), 400
    if not sid or sexo not in ('M', 'H'):
        return jsonify({'ok': False, 'error': 'invalid_parameters'}), 400

    table = 'machos' if sexo == 'M' else 'hembras'
    with mysql.connection.cursor() as cursor:
        try:
            cursor.execute(f"UPDATE {table} SET propietario=%s WHERE id=%s", (propietario or None, sid))
            mysql.connection.commit()
        except Exception as e:
            return jsonify({'ok': False, 'error': 'db_error'}), 500
    return jsonify({'ok': True, 'propietario': propietario or ''})


