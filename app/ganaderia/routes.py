from flask import Blueprint, render_template

bp = Blueprint('ganaderia', __name__, url_prefix='/registro')

@bp.route('/partos')
def registro_partos():
    return render_template('registro_partos.html')

@bp.route('/carne')
def registro_carne():
    return render_template('registro_carne.html')

@bp.route('/leche')
def registro_leche():
    return render_template('registro_leche.html')

@bp.route('/hembras')
def registro_hembras():
    return render_template('registro_hembras.html')

@bp.route('/machos')
def registro_machos():
    return render_template('registro_machos.html')

@bp.route('/crias')
def registro_crias():
    return render_template('registro_crias.html')

