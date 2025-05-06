from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, Usuario
from functools import wraps

# Decorador para requerir inicio de sesión
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debe iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Decorador para requerir rol de administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debe iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('login', next=request.url))
        if session.get('rol') != 'admin':
            flash('No tiene permisos para acceder a esta página', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Por favor, ingrese usuario y contraseña', 'danger')
            return render_template('login.html')
        
        # Buscar usuario en la base de datos
        usuario = Usuario.query.filter_by(username=username).first()
        
        if not usuario or not check_password_hash(usuario.password, password):
            flash('Usuario o contraseña incorrectos', 'danger')
            return render_template('login.html')
        
        # Guardar datos del usuario en la sesión
        session['user_id'] = usuario.id
        session['username'] = usuario.username
        session['nombre'] = f"{usuario.nombre} {usuario.apellido}"
        session['rol'] = usuario.rol
        
        flash(f'Bienvenido, {usuario.nombre}!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

def logout():
    session.clear()
    flash('Ha cerrado sesión correctamente', 'success')
    return redirect(url_for('login'))

def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('dashboard.html')

def usuarios():
    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

def nuevo_usuario():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        email = request.form.get('email')
        rol = request.form.get('rol')
        porcentaje_comision = request.form.get('porcentaje_comision', '0')
        
        # Validar datos
        if not username or not password or not nombre or not apellido or not email or not rol:
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('usuarios'))
        
        # Verificar si el usuario ya existe
        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya está en uso', 'danger')
            return redirect(url_for('usuarios'))
        
        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            username=username,
            password=generate_password_hash(password),
            nombre=nombre,
            apellido=apellido,
            email=email,
            rol=rol,
            porcentaje_comision=float(porcentaje_comision) if porcentaje_comision else 0.0
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        flash('Usuario creado correctamente', 'success')
        return redirect(url_for('usuarios'))
    
    return redirect(url_for('usuarios'))

def editar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    
    if request.method == 'POST':
        usuario.nombre = request.form.get('nombre')
        usuario.apellido = request.form.get('apellido')
        usuario.email = request.form.get('email')
        usuario.rol = request.form.get('rol')
        usuario.porcentaje_comision = float(request.form.get('porcentaje_comision', '0'))
        
        # Actualizar contraseña solo si se proporciona una nueva
        nueva_password = request.form.get('password')
        if nueva_password:
            usuario.password = generate_password_hash(nueva_password)
        
        db.session.commit()
        flash('Usuario actualizado correctamente', 'success')
        return redirect(url_for('usuarios'))
    
    return render_template('editar_usuario.html', usuario=usuario)

def eliminar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # No permitir eliminar al usuario actualmente logueado
    if usuario.id == session.get('user_id'):
        flash('No puede eliminar su propio usuario', 'danger')
        return redirect(url_for('usuarios'))
    
    db.session.delete(usuario)
    db.session.commit()
    
    flash('Usuario eliminado correctamente', 'success')
    return redirect(url_for('usuarios'))
