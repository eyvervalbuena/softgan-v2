from flask import Blueprint, render_template

# Blueprint mínimo para módulo Sanitario
sanitario_bp = Blueprint('sanitario', __name__, url_prefix='/sanitario')


@sanitario_bp.route('/ciclo')
def registro_ciclo():
    return render_template('registro_ciclo.html')


@sanitario_bp.route('/individual')
def registro_individual():
    return render_template('registro_individual.html')


@sanitario_bp.route('/patologia')
def registro_patologia():
    return render_template('registro_patologia.html')

