from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Usuario
from functools import wraps

# Crear el blueprint
auth_bp = Blueprint('auth', __name__)

# Decorador para requerir inicio de sesión
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debe iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Decorador para requerir rol de administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debe iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if session.get('rol') != 'admin':
            flash('No tiene permisos para acceder a esta página.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya está logueado, redirigir al dashboard
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Validar datos
        if not username or not password:
            flash('Por favor ingrese usuario y contraseña.', 'danger')
            return render_template('login.html')
        
        # Buscar usuario
        usuario = Usuario.query.filter_by(username=username).first()
        
        # Verificar usuario y contraseña
        if usuario and check_password_hash(usuario.password, password):
            # Guardar en sesión
            session['user_id'] = usuario.id
            session['username'] = usuario.username
            session['rol'] = usuario.rol
            
            flash(f'Bienvenido, {usuario.username}!', 'success')
            
            # Redirigir a la página solicitada o al dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    # Limpiar sesión
    session.clear()
    flash('Ha cerrado sesión correctamente.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/usuarios')
@admin_required
def usuarios():
    # Listar usuarios (solo admin)
    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@auth_bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@admin_required
def nuevo_usuario():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        rol = request.form.get('rol')
        
        # Validar datos
        if not username or not password or not rol:
            flash('Todos los campos son obligatorios.', 'danger')
            return redirect(url_for('auth.nuevo_usuario'))
        
        # Verificar si ya existe el usuario
        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya está en uso.', 'danger')
            return redirect(url_for('auth.nuevo_usuario'))
        
        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            username=username,
            password=generate_password_hash(password),
            rol=rol
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        flash('Usuario creado correctamente.', 'success')
        return redirect(url_for('auth.usuarios'))
    
    return render_template('nuevo_usuario.html')
