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


