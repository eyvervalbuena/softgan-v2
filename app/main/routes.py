from flask import Blueprint, render_template, redirect, url_for, flash, session

bp = Blueprint('main', __name__)

@bp.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder.', 'warning')
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html', usuario=session['usuario'])

