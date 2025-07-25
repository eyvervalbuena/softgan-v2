from flask import Blueprint, render_template

ganaderia_bp = Blueprint('ganaderia', __name__, url_prefix='/registro')

@ganaderia_bp.route('/partos')
def registro_partos():
    return render_template('registro_partos.html')

@ganaderia_bp.route('/carne')
def registro_carne():
    return render_template('registro_carne.html')

@ganaderia_bp.route('/leche')
def registro_leche():
    return render_template('registro_leche.html')

@ganaderia_bp.route('/hembras')
def registro_hembras():
    return render_template('registro_hembras.html')

@ganaderia_bp.route('/machos')
def registro_machos():
    return render_template('registro_machos.html')

@ganaderia_bp.route('/crias')
def registro_crias():
    return render_template('registro_crias.html')
