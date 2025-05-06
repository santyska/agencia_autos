from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, Usuario
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si el usuario ya está autenticado, redirigir al inicio
    if current_user.is_authenticated:
        return redirect(url_for('inicio'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Validar que se proporcionaron los datos
        if not username or not password:
            flash('Por favor ingrese usuario y contraseña', 'danger')
            return render_template('auth/login.html')
        
        # Buscar el usuario en la base de datos
        usuario = Usuario.query.filter_by(username=username).first()
        
        # Verificar si el usuario existe y la contraseña es correcta
        if usuario and check_password_hash(usuario.password, password):
            # Si el usuario no está activo
            if not usuario.activo:
                flash('Esta cuenta ha sido desactivada. Contacte al administrador.', 'danger')
                return render_template('auth/login.html')
                
            # Iniciar sesión
            login_user(usuario)
            flash(f'Bienvenido, {usuario.nombre}!', 'success')
            
            # Redirigir a la página solicitada o al inicio
            next_page = request.args.get('next')
            return redirect(next_page or url_for('inicio'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('inicio'))

@auth_bp.route('/perfil')
@login_required
def perfil():
    return render_template('auth/perfil.html')

@auth_bp.route('/cambiar-password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    if request.method == 'POST':
        password_actual = request.form.get('password_actual')
        password_nuevo = request.form.get('password_nuevo')
        password_confirmacion = request.form.get('password_confirmacion')
        
        # Validar que se proporcionaron los datos
        if not password_actual or not password_nuevo or not password_confirmacion:
            flash('Por favor complete todos los campos', 'danger')
            return render_template('auth/cambiar_password.html')
            
        # Validar que la contraseña actual es correcta
        if not check_password_hash(current_user.password, password_actual):
            flash('La contraseña actual es incorrecta', 'danger')
            return render_template('auth/cambiar_password.html')
            
        # Validar que las contraseñas nuevas coinciden
        if password_nuevo != password_confirmacion:
            flash('Las contraseñas nuevas no coinciden', 'danger')
            return render_template('auth/cambiar_password.html')
            
        # Actualizar la contraseña
        current_user.password = generate_password_hash(password_nuevo)
        db.session.commit()
        
        flash('Contraseña actualizada correctamente', 'success')
        return redirect(url_for('auth.perfil'))
        
    return render_template('auth/cambiar_password.html')
