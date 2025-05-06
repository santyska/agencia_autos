from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, Usuario
from functools import wraps

admin_bp = Blueprint('admin', __name__)

# Decorador para verificar si el usuario es administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
            return redirect(url_for('inicio'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin')
@login_required
@admin_required
def admin_panel():
    return render_template('admin/panel.html')

@admin_bp.route('/admin/usuarios')
@login_required
@admin_required
def listar_usuarios():
    usuarios = Usuario.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@admin_bp.route('/admin/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo_usuario():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        email = request.form.get('email')
        rol = request.form.get('rol')
        porcentaje_comision = request.form.get('porcentaje_comision')
        
        # Validar datos
        if not username or not password or not nombre or not apellido or not email or not rol:
            flash('Todos los campos son obligatorios', 'danger')
            return render_template('admin/nuevo_usuario.html')
            
        # Verificar si el usuario ya existe
        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya está en uso', 'danger')
            return render_template('admin/nuevo_usuario.html')
            
        # Verificar si el email ya existe
        if Usuario.query.filter_by(email=email).first():
            flash('El email ya está en uso', 'danger')
            return render_template('admin/nuevo_usuario.html')
            
        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            username=username,
            password=generate_password_hash(password),
            nombre=nombre,
            apellido=apellido,
            email=email,
            rol=rol,
            porcentaje_comision=float(porcentaje_comision) if porcentaje_comision else 5.0
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        flash('Usuario creado exitosamente', 'success')
        return redirect(url_for('admin.listar_usuarios'))
        
    return render_template('admin/nuevo_usuario.html')

@admin_bp.route('/admin/usuarios/editar/<int:usuario_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        email = request.form.get('email')
        rol = request.form.get('rol')
        porcentaje_comision = request.form.get('porcentaje_comision')
        activo = 'activo' in request.form
        
        # Validar datos
        if not nombre or not apellido or not email or not rol:
            flash('Todos los campos son obligatorios', 'danger')
            return render_template('admin/editar_usuario.html', usuario=usuario)
            
        # Verificar si el email ya existe (excepto para este usuario)
        usuario_email = Usuario.query.filter_by(email=email).first()
        if usuario_email and usuario_email.id != usuario.id:
            flash('El email ya está en uso', 'danger')
            return render_template('admin/editar_usuario.html', usuario=usuario)
            
        # Actualizar usuario
        usuario.nombre = nombre
        usuario.apellido = apellido
        usuario.email = email
        usuario.rol = rol
        usuario.porcentaje_comision = float(porcentaje_comision) if porcentaje_comision else 5.0
        usuario.activo = activo
        
        db.session.commit()
        
        flash('Usuario actualizado exitosamente', 'success')
        return redirect(url_for('admin.listar_usuarios'))
        
    return render_template('admin/editar_usuario.html', usuario=usuario)

@admin_bp.route('/admin/usuarios/reset-password/<int:usuario_id>', methods=['POST'])
@login_required
@admin_required
def reset_password(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # Generar nueva contraseña (podría ser aleatoria o fija)
    nueva_password = 'Temporal123'
    usuario.password = generate_password_hash(nueva_password)
    
    db.session.commit()
    
    flash(f'Contraseña restablecida a: {nueva_password}', 'success')
    return redirect(url_for('admin.editar_usuario', usuario_id=usuario.id))

@admin_bp.route('/admin/comisiones')
@login_required
@admin_required
def comisiones():
    # Obtener vendedores con sus ventas y comisiones
    vendedores = Usuario.query.filter_by(rol='vendedor').all()
    return render_template('admin/comisiones.html', vendedores=vendedores)
