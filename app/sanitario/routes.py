from flask import Blueprint, render_template

bp = Blueprint('sanitario', __name__, url_prefix='/sanitario')

@bp.route('/ciclo')
def registro_ciclo():
    return render_template('registro_ciclo.html')

@bp.route('/individual')
def registro_individual():
    return render_template('registro_individual.html')

@bp.route('/patologia')
def registro_patologia():
    return render_template('registro_patologia.html')
