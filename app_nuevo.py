from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, Auto, EstadoAuto, Usuario, Venta, EstadoPago, FotoAuto
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from functools import wraps

# Crear la app Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecreto123'

# Configurar la base de datos SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'agencia.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración para carga de archivos
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB máximo

# Asegurar que existan las carpetas de uploads
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'autos'), exist_ok=True)

# Inicializar extensiones
db.init_app(app)

# Filtros personalizados para Jinja2
@app.template_filter('formato_precio')
def formato_precio(value):
    """Formatea un número como precio con separador de miles y símbolo de moneda"""
    if value is None:
        return "$0"
    return f"${value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# Decoradores para autenticación
def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped_view

def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('login'))
        if session.get('rol') != 'admin':
            flash('No tienes permisos para acceder a esta página', 'danger')
            return redirect(url_for('dashboard'))
        return view(*args, **kwargs)
    return wrapped_view

# Rutas de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya está logueado, redirigir al inicio
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Usuario.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            # Guardar en sesión
            session['user_id'] = user.id
            session['username'] = user.username
            session['rol'] = user.rol
            session['nombre'] = f"{user.nombre} {user.apellido}"
            
            flash(f'Bienvenido, {user.nombre}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('login'))

# Ruta principal - dashboard
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    # Contar autos disponibles
    autos_disponibles = Auto.query.filter_by(estado=EstadoAuto.DISPONIBLE).count()
    
    # Obtener últimos autos agregados
    ultimos_autos = Auto.query.order_by(Auto.id.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                          autos_disponibles=autos_disponibles,
                          ultimos_autos=ultimos_autos,
                          usuario=session.get('nombre'),
                          rol=session.get('rol'))

# Rutas para autos
@app.route('/autos')
def autos():
    # Filtros (solo disponibles para usuarios logueados)
    if 'user_id' in session:
        marca = request.args.get('marca', '')
        modelo = request.args.get('modelo', '')
        anio = request.args.get('anio', '')
        
        # Consulta base
        query = Auto.query
        
        # Aplicar filtros si existen
        if marca:
            query = query.filter(Auto.marca.ilike(f'%{marca}%'))
        if modelo:
            query = query.filter(Auto.modelo.ilike(f'%{modelo}%'))
        if anio and anio.isdigit():
            query = query.filter(Auto.anio == int(anio))
        
        # Obtener resultados
        try:
            autos = query.order_by(Auto.id.desc()).all()
        except Exception as e:
            app.logger.error(f"Error al obtener autos: {e}")
            # Si hay error con fecha_publicacion, ordenar por id
            autos = query.order_by(Auto.id.desc()).all()
    else:
        # Para visitantes, mostrar solo autos disponibles sin filtros
        try:
            autos = Auto.query.filter_by(estado=EstadoAuto.DISPONIBLE).order_by(Auto.id.desc()).all()
        except Exception as e:
            app.logger.error(f"Error al obtener autos para visitantes: {e}")
            autos = Auto.query.filter_by(estado=EstadoAuto.DISPONIBLE).order_by(Auto.id.desc()).all()
    
    return render_template('autos.html', autos=autos, is_logged_in='user_id' in session)

@app.route('/auto/<int:auto_id>')
def detalle_auto(auto_id):
    auto = Auto.query.get_or_404(auto_id)
    
    # Generar URL para compartir si no existe
    if not auto.url_compartir:
        auto.url_compartir = f"{request.host_url}auto/{auto.id}"
        db.session.commit()
    
    # Normalizar las rutas de las fotos para URLs
    for foto in auto.fotos:
        if foto.ruta_archivo and '\\' in foto.ruta_archivo:
            foto.ruta_archivo = foto.ruta_archivo.replace('\\', '/')
    
    return render_template('detalle_auto.html', auto=auto)

@app.route('/autos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_auto():
    if request.method == 'POST':
        # Obtener datos del formulario
        marca = request.form.get('marca', '')
        modelo = request.form.get('modelo', '')
        anio = request.form.get('anio', '0')
        precio = request.form.get('precio', '0')
        color = request.form.get('color', '')
        kilometraje = request.form.get('kilometraje', '0')
        descripcion = request.form.get('descripcion', '')
        
        # Precio de compra (solo para administradores)
        precio_compra = request.form.get('precio_compra', '0')
        if not precio_compra:
            precio_compra = 0
        
        # Validar y convertir los valores
        try:
            anio_int = int(anio) if anio else 0
            precio_float = float(precio) if precio else 0.0
            precio_compra_float = float(precio_compra) if precio_compra else 0.0
            kilometraje_int = int(kilometraje) if kilometraje else 0
        except ValueError:
            flash('Error en los datos ingresados. Verifique los valores numéricos.', 'danger')
            return redirect(url_for('nuevo_auto'))
        
        # Crear nuevo auto
        nuevo_auto = Auto(
            marca=marca,
            modelo=modelo,
            anio=anio_int,
            precio=precio_float,
            precio_compra=precio_compra_float,
            color=color,
            kilometraje=kilometraje_int,
            descripcion=descripcion,
            estado=EstadoAuto.DISPONIBLE
        )
        
        db.session.add(nuevo_auto)
        db.session.commit()
        
        # Generar URL para compartir
        nuevo_auto.url_compartir = f"{request.host_url}auto/{nuevo_auto.id}"
        db.session.commit()
        
        # Procesar las fotos
        if 'fotos' in request.files:
            fotos = request.files.getlist('fotos')
            for foto in fotos:
                if foto and foto.filename:
                    # Crear directorio si no existe
                    directorio_fotos = os.path.join(app.static_folder, 'uploads', 'autos', str(nuevo_auto.id))
                    if not os.path.exists(directorio_fotos):
                        os.makedirs(directorio_fotos)
                    
                    # Guardar la foto
                    filename = secure_filename(foto.filename)
                    nombre_archivo = f"{uuid.uuid4()}_{filename}"
                    ruta_relativa = os.path.join('uploads', 'autos', str(nuevo_auto.id), nombre_archivo)
                    ruta_completa = os.path.join(app.static_folder, ruta_relativa)
                    foto.save(ruta_completa)
                    
                    # Normalizar la ruta para URLs (usar forward slashes)
                    ruta_normalizada = ruta_relativa.replace('\\', '/')
                    
                    # Crear registro en la base de datos
                    foto_auto = FotoAuto(ruta_archivo=ruta_normalizada, auto_id=nuevo_auto.id)
                    db.session.add(foto_auto)
        
        db.session.commit()
        
        flash('Auto agregado correctamente', 'success')
        return redirect(url_for('autos'))
    
    return render_template('nuevo_auto.html')

@app.route('/auto/<int:auto_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_auto(auto_id):
    auto = Auto.query.get_or_404(auto_id)
    
    if request.method == 'POST':
        # Obtener datos del formulario
        auto.marca = request.form.get('marca', '')
        auto.modelo = request.form.get('modelo', '')
        auto.anio = int(request.form.get('anio', '0'))
        auto.precio = float(request.form.get('precio', '0'))
        auto.color = request.form.get('color', '')
        auto.kilometraje = int(request.form.get('kilometraje', '0'))
        auto.descripcion = request.form.get('descripcion', '')
        
        # Precio de compra (solo para administradores)
        if session.get('rol') == 'admin':
            auto.precio_compra = float(request.form.get('precio_compra', '0'))
        
        # Actualizar el estado si se especifica
        estado = request.form.get('estado')
        if estado and estado in [e.name for e in EstadoAuto]:
            auto.estado = EstadoAuto[estado]
        
        db.session.commit()
        
        # Procesar las fotos nuevas
        if 'fotos' in request.files:
            fotos = request.files.getlist('fotos')
            for foto in fotos:
                if foto and foto.filename:
                    # Crear directorio si no existe
                    directorio_fotos = os.path.join(app.static_folder, 'uploads', 'autos', str(auto.id))
                    if not os.path.exists(directorio_fotos):
                        os.makedirs(directorio_fotos)
                    
                    # Guardar la foto
                    filename = secure_filename(foto.filename)
                    nombre_archivo = f"{uuid.uuid4()}_{filename}"
                    ruta_relativa = os.path.join('uploads', 'autos', str(auto.id), nombre_archivo)
                    ruta_completa = os.path.join(app.static_folder, ruta_relativa)
                    foto.save(ruta_completa)
                    
                    # Normalizar la ruta para URLs (usar forward slashes)
                    ruta_normalizada = ruta_relativa.replace('\\', '/')
                    
                    # Crear registro en la base de datos
                    foto_auto = FotoAuto(ruta_archivo=ruta_normalizada, auto_id=auto.id)
                    db.session.add(foto_auto)
        
        db.session.commit()
        
        flash('Auto actualizado correctamente', 'success')
        return redirect(url_for('detalle_auto', auto_id=auto.id))
    
    # Preparar datos para la vista
    estados = [e.name for e in EstadoAuto]
    
    return render_template('editar_auto.html', auto=auto, estados=estados)

@app.route('/auto/<int:auto_id>/fotos/eliminar/<int:foto_id>', methods=['POST'])
@login_required
def eliminar_foto(auto_id, foto_id):
    foto = FotoAuto.query.get_or_404(foto_id)
    
    # Verificar que la foto pertenezca al auto
    if foto.auto_id != auto_id:
        flash('La foto no pertenece a este auto', 'danger')
        return redirect(url_for('editar_auto', auto_id=auto_id))
    
    # Eliminar el archivo físico si existe
    if foto.ruta_archivo:
        ruta_completa = os.path.join(app.static_folder, foto.ruta_archivo)
        if os.path.exists(ruta_completa):
            os.remove(ruta_completa)
    
    # Eliminar el registro de la base de datos
    db.session.delete(foto)
    db.session.commit()
    
    flash('Foto eliminada correctamente', 'success')
    return redirect(url_for('editar_auto', auto_id=auto_id))
    if request.method == 'POST':
        # Obtener datos del formulario
        marca = request.form.get('marca', '')
        modelo = request.form.get('modelo', '')
        anio = request.form.get('anio', '0')
        precio = request.form.get('precio', '0')
        color = request.form.get('color', '')
        kilometraje = request.form.get('kilometraje', '0')
        descripcion = request.form.get('descripcion', '')
        
        # Precio de compra (solo para administradores)
        precio_compra = request.form.get('precio_compra', '0')
        if not precio_compra:
            precio_compra = 0
        
        # Validar y convertir los valores
        try:
            anio_int = int(anio) if anio else 0
            precio_float = float(precio) if precio else 0.0
            precio_compra_float = float(precio_compra) if precio_compra else 0.0
            kilometraje_int = int(kilometraje) if kilometraje else 0
        except ValueError:
            flash('Error en los datos ingresados. Verifique los valores numéricos.', 'danger')
            return redirect(url_for('nuevo_auto'))
        
        # Crear nuevo auto
        nuevo_auto = Auto(
            marca=marca,
            modelo=modelo,
            anio=anio_int,
            precio=precio_float,
            precio_compra=precio_compra_float,
            color=color,
            kilometraje=kilometraje_int,
            descripcion=descripcion,
            estado=EstadoAuto.DISPONIBLE
        )
        
        db.session.add(nuevo_auto)
        db.session.commit()
        
        # Generar URL para compartir
        nuevo_auto.url_compartir = f"{request.host_url}auto/{nuevo_auto.id}"
        db.session.commit()
        
        # Procesar las fotos
        if 'fotos' in request.files:
            fotos = request.files.getlist('fotos')
            for foto in fotos:
                if foto and foto.filename:
                    # Crear directorio si no existe
                    directorio_fotos = os.path.join(app.static_folder, 'uploads', 'autos', str(nuevo_auto.id))
                    if not os.path.exists(directorio_fotos):
                        os.makedirs(directorio_fotos)
                    
                    # Guardar la foto
                    filename = secure_filename(foto.filename)
                    nombre_archivo = f"{uuid.uuid4()}_{filename}"
                    ruta_relativa = os.path.join('uploads', 'autos', str(nuevo_auto.id), nombre_archivo)
                    ruta_completa = os.path.join(app.static_folder, ruta_relativa)
                    foto.save(ruta_completa)
                    
                    # Normalizar la ruta para URLs (usar forward slashes)
                    ruta_normalizada = ruta_relativa.replace('\\', '/')
                    
                    # Crear registro en la base de datos
                    foto_auto = FotoAuto(ruta_archivo=ruta_normalizada, auto_id=nuevo_auto.id)
                    db.session.add(foto_auto)
        
        db.session.commit()
        
        flash('Auto agregado correctamente', 'success')
        return redirect(url_for('autos'))
    
    return render_template('nuevo_auto.html')

# Rutas para ventas
@app.route('/ventas')
@login_required
def ventas():
    # Obtener parámetros de filtro
    mes = request.args.get('mes', type=int)
    anio = request.args.get('anio', type=int, default=datetime.now().year)
    estado = request.args.get('estado')
    
    # Consulta base
    query = Venta.query
    
    # Aplicar filtros solo si se especifican
    if mes is not None:
        # Filtrar por mes considerando ambas fechas posibles
        query = query.filter(
            db.or_(
                db.extract('month', Venta.fecha_venta) == mes,
                db.extract('month', Venta.fecha_seña) == mes
            )
        )
    
    if anio is not None:
        # Filtrar por año considerando ambas fechas posibles
        query = query.filter(
            db.or_(
                db.extract('year', Venta.fecha_venta) == anio,
                db.extract('year', Venta.fecha_seña) == anio
            )
        )
    
    if estado:
        # Convertir string a enum
        try:
            estado_enum = EstadoPago[estado]
            query = query.filter(Venta.estado_pago == estado_enum)
        except (KeyError, ValueError):
            # Si el estado no es válido, ignorar este filtro
            pass
    
    # Obtener ventas con manejo de errores
    try:
        ventas = query.order_by(Venta.id.desc()).all()
    except Exception as e:
        app.logger.error(f"Error al obtener ventas: {e}")
        # Si hay error con el orden, intentar con ID
        ventas = query.order_by(Venta.id.desc()).all()
    
    # Preparar datos para la vista
    meses = [(1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'), 
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')]
    
    # Obtener años con ventas considerando ambas fechas posibles
    try:
        # Consulta para años con fecha_venta
        anios_venta_query = db.session.query(db.extract('year', Venta.fecha_venta).distinct())
        anios_venta_query = anios_venta_query.filter(Venta.fecha_venta != None)
        anios_venta_query = anios_venta_query.order_by(db.extract('year', Venta.fecha_venta).desc())
        anios_venta = [int(a[0]) for a in anios_venta_query.all() if a[0] is not None]
        
        # Consulta para años con fecha_seña
        anios_seña_query = db.session.query(db.extract('year', Venta.fecha_seña).distinct())
        anios_seña_query = anios_seña_query.filter(Venta.fecha_seña != None)
        anios_seña_query = anios_seña_query.order_by(db.extract('year', Venta.fecha_seña).desc())
        anios_seña = [int(a[0]) for a in anios_seña_query.all() if a[0] is not None]
        
        # Combinar y eliminar duplicados
        anios = sorted(set(anios_venta + anios_seña), reverse=True)
    except Exception as e:
        app.logger.error(f"Error al obtener años con ventas: {e}")
        anios = []
    
    if not anios:  # Si no hay años con ventas, usar el año actual
        anios = [datetime.now().year]
    
    # Estados de pago
    estados = [e.value for e in EstadoPago]
    
    return render_template('ventas.html', 
                        ventas=ventas, 
                        meses=meses, 
                        anios=anios,
                        estados=estados,
                        mes_seleccionado=mes,
                        anio_seleccionado=anio,
                        estado_seleccionado=estado)

@app.route('/ventas/registrar', methods=['GET', 'POST'])
@login_required
def registrar_venta():
    # Obtener autos disponibles
    autos_disponibles = Auto.query.filter_by(estado=EstadoAuto.DISPONIBLE).all()
    
    if request.method == 'POST':
        # Obtener datos del formulario
        auto_id = request.form.get('auto_id')
        cliente_nombre = request.form.get('cliente_nombre')
        cliente_email = request.form.get('cliente_email')
        cliente_telefono = request.form.get('cliente_telefono')
        monto_seña = request.form.get('monto_seña', '0')
        
        # Validar datos
        if not auto_id or not cliente_nombre:
            flash('Faltan datos obligatorios', 'danger')
            return redirect(url_for('registrar_venta'))
        
        # Obtener el auto
        auto = Auto.query.get_or_404(auto_id)
        
        # Verificar que el auto esté disponible
        if auto.estado != EstadoAuto.DISPONIBLE:
            flash('El auto seleccionado no está disponible', 'danger')
            return redirect(url_for('registrar_venta'))
        
        # Crear la venta
        try:
            monto_seña_float = float(monto_seña) if monto_seña else 0.0
        except ValueError:
            flash('El monto de la seña debe ser un número válido', 'danger')
            return redirect(url_for('registrar_venta'))
        
        # Determinar estado de pago
        estado_pago = EstadoPago.SEÑADO if monto_seña_float > 0 else EstadoPago.PENDIENTE
        
        # Crear la venta
        nueva_venta = Venta(
            auto_id=auto_id,
            cliente_nombre=cliente_nombre,
            cliente_email=cliente_email,
            cliente_telefono=cliente_telefono,
            monto_seña=monto_seña_float,
            precio_venta=auto.precio,
            fecha_seña=datetime.now() if monto_seña_float > 0 else None,
            estado_pago=estado_pago,
            vendedor_id=session.get('user_id')
        )
        
        # Actualizar estado del auto
        auto.estado = EstadoAuto.VENDIDO
        
        # Guardar cambios
        db.session.add(nueva_venta)
        db.session.commit()
        
        flash('Venta registrada correctamente', 'success')
        return redirect(url_for('ventas'))
    
    return render_template('registrar_venta.html', autos=autos_disponibles)

@app.route('/ventas/<int:venta_id>')
@login_required
def detalle_venta(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    return render_template('detalle_venta.html', venta=venta)

@app.route('/ventas/<int:venta_id>/pagar')
@login_required
def marcar_pagado(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    venta.estado_pago = EstadoPago.PAGADO
    venta.fecha_venta = datetime.now()  # Actualizar la fecha de venta al marcar como pagado
    db.session.commit()
    flash('Venta marcada como pagada', 'success')
    return redirect(url_for('ventas'))

@app.route('/ventas/<int:venta_id>/recibo')
@login_required
def generar_recibo(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    # Aquí iría la lógica para generar un PDF
    flash('Funcionalidad de generación de recibo en desarrollo', 'info')
    return redirect(url_for('ventas'))

@app.route('/ventas/exportar')
@login_required
def exportar_ventas():
    # Aquí iría la lógica para exportar a Excel
    flash('Funcionalidad de exportación en desarrollo', 'info')
    return redirect(url_for('ventas'))

# Rutas para usuarios
@app.route('/usuarios')
@admin_required
def usuarios():
    # Obtener todos los usuarios
    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/usuarios/nuevo', methods=['POST'])
@admin_required
def nuevo_usuario():
    # Obtener datos del formulario
    username = request.form.get('username')
    password = request.form.get('password')
    nombre = request.form.get('nombre')
    apellido = request.form.get('apellido')
    email = request.form.get('email')
    rol = request.form.get('rol')
    porcentaje_comision = float(request.form.get('porcentaje_comision', 0))
    
    # Verificar si el usuario ya existe
    if Usuario.query.filter_by(username=username).first():
        flash('El nombre de usuario ya existe', 'danger')
        return redirect(url_for('usuarios'))
    
    # Crear nuevo usuario
    nuevo_usuario = Usuario(
        username=username,
        password=generate_password_hash(password),
        nombre=nombre,
        apellido=apellido,
        email=email,
        rol=rol,
        porcentaje_comision=porcentaje_comision
    )
    
    # Guardar en la base de datos
    db.session.add(nuevo_usuario)
    db.session.commit()
    
    flash('Usuario creado correctamente', 'success')
    return redirect(url_for('usuarios'))

@app.route('/usuarios/<int:usuario_id>/editar', methods=['GET', 'POST'])
@admin_required
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

@app.route('/usuarios/<int:usuario_id>/eliminar', methods=['POST'])
@admin_required
def eliminar_usuario(usuario_id):
    # No permitir eliminar al usuario actualmente logueado
    if int(session.get('user_id')) == usuario_id:
        flash('No puede eliminar su propio usuario', 'danger')
        return redirect(url_for('usuarios'))
    
    # Buscar el usuario
    usuario = Usuario.query.get_or_404(usuario_id)
    
    db.session.delete(usuario)
    db.session.commit()
    
    flash('Usuario eliminado correctamente', 'success')
    return redirect(url_for('usuarios'))

# Rutas para estadísticas
@app.route('/estadisticas')
@admin_required
def estadisticas():
    # Obtener estadísticas de ventas por mes para el año actual
    año_actual = datetime.now().year
    
    # Ventas por mes
    ventas_por_mes = []
    for mes in range(1, 13):
        # Contar ventas para este mes
        count = Venta.query.filter(
            db.extract('year', Venta.fecha_venta) == año_actual,
            db.extract('month', Venta.fecha_venta) == mes
        ).count()
        
        ventas_por_mes.append(count)
    
    # Ventas por vendedor
    vendedores = Usuario.query.filter(Usuario.rol.in_(['admin', 'vendedor'])).all()
    ventas_por_vendedor = []
    
    for vendedor in vendedores:
        count = Venta.query.filter_by(vendedor_id=vendedor.id).count()
        if count > 0:  # Solo incluir vendedores con ventas
            ventas_por_vendedor.append({
                'nombre': f"{vendedor.nombre} {vendedor.apellido}",
                'ventas': count
            })
    
    # Ordenar por cantidad de ventas (descendente)
    ventas_por_vendedor = sorted(ventas_por_vendedor, key=lambda x: x['ventas'], reverse=True)
    
    # Marcas más vendidas
    marcas = db.session.query(
        Auto.marca, 
        db.func.count(Venta.id).label('count')
    ).join(Venta, Auto.id == Venta.auto_id).group_by(Auto.marca).order_by(db.desc('count')).limit(5).all()
    
    marcas_vendidas = [{'marca': marca, 'count': count} for marca, count in marcas]
    
    # Ingresos totales
    ingresos_totales = db.session.query(db.func.sum(Venta.precio_venta)).filter(
        Venta.estado_pago == EstadoPago.PAGADO
    ).scalar() or 0
    
    # Ingresos por mes
    ingresos_por_mes = []
    for mes in range(1, 13):
        # Sumar ingresos para este mes
        total = db.session.query(db.func.sum(Venta.precio_venta)).filter(
            db.extract('year', Venta.fecha_venta) == año_actual,
            db.extract('month', Venta.fecha_venta) == mes,
            Venta.estado_pago == EstadoPago.PAGADO
        ).scalar() or 0
        
        ingresos_por_mes.append(total)
    
    return render_template('estadisticas.html',
                          ventas_por_mes=ventas_por_mes,
                          ventas_por_vendedor=ventas_por_vendedor,
                          marcas_vendidas=marcas_vendidas,
                          ingresos_totales=ingresos_totales,
                          ingresos_por_mes=ingresos_por_mes,
                          año_actual=año_actual)

# Crear tablas y datos iniciales
with app.app_context():
    db.create_all()
    
    # Crear usuario administrador si no existe
    if not Usuario.query.filter_by(username='admin').first():
        admin = Usuario(
            username='admin',
            password=generate_password_hash('admin123'),
            nombre='Administrador',
            apellido='Sistema',
            email='admin@agenciaautos.com',
            rol='admin',
            porcentaje_comision=0.0
        )
        db.session.add(admin)
        db.session.commit()
        print("Usuario administrador creado con éxito.")
        print("Usuario: admin")
        print("Contraseña: admin123")
    
    # Crear auto de prueba si no hay autos
    if not Auto.query.first():
        auto_prueba = Auto(
            marca='Toyota', 
            modelo='Corolla', 
            anio=2022, 
            precio=35000.0,
            precio_compra=30000.0,
            descripcion='Auto de prueba en excelente estado',
            color='Blanco',
            kilometraje=0,
            estado=EstadoAuto.DISPONIBLE
        )
        db.session.add(auto_prueba)
        db.session.commit()
        print("Auto de prueba agregado.")

# Iniciar el servidor
if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
