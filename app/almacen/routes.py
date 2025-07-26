from flask import Blueprint, render_template

almacen_bp = Blueprint('almacen', __name__, url_prefix='/almacen')

@almacen_bp.route('/')
def almacen_insumos():
    return render_template('almacen_insumos.html')

@almacen_bp.route('/maquinaria')
def almacen_maquinaria():
    return render_template('almacen_maquinaria.html')

@almacen_bp.route('/agroquimicos')
def almacen_agroquimicos():
    return render_template('almacen_agroquimicos.html')
