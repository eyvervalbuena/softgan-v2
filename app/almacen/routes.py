from flask import Blueprint, render_template

bp = Blueprint('almacen', __name__, url_prefix='/almacen')

@bp.route('/')
def almacen_insumos():
    return render_template('almacen_insumos.html')

@bp.route('/maquinaria')
def almacen_maquinaria():
    return render_template('almacen_maquinaria.html')

@bp.route('/agroquimicos')
def almacen_agroquimicos():
    return render_template('almacen_agroquimicos.html')
