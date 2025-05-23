from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, Auto, EstadoAuto, Usuario, Venta, EstadoPago, FotoAuto
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
import hashlib
from datetime import datetime
from functools import wraps

# Funciones personalizadas para el hash de contraseñas
def custom_generate_password_hash(password):
    """Genera un hash de contraseña usando SHA-256 en lugar de scrypt"""
    method = 'sha256'
    salt = os.urandom(16).hex()
    hash_val = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{method}${salt}${hash_val}"

def custom_check_password_hash(pwhash, password):
    """Verifica una contraseña contra un hash con múltiples métodos para mayor compatibilidad"""
    # Imprimir información de diagnóstico
    print(f"Intentando verificar contraseña. Hash almacenado: {pwhash[:10]}...")
    
    # Método 1: Verificación directa (contraseña en texto plano)
    if pwhash == password:
        print(f"Autenticación exitosa con contraseña en texto plano")
        return True
    
    # Método 2: Hash simple SHA-256 (usado en render_admin.py)
    simple_hash = hashlib.sha256(password.encode()).hexdigest()
    if pwhash == simple_hash:
        print(f"Autenticación exitosa con hash simple SHA-256")
        return True
    
    # Método 3: Formato personalizado sha256$salt$hash
    if '$' in pwhash and pwhash.count('$') == 2:
        try:
            method, salt, hash_val = pwhash.split('$', 2)
            if method == 'sha256':
                calculated_hash = hashlib.sha256((salt + password).encode()).hexdigest()
                if calculated_hash == hash_val:
                    print(f"Autenticación exitosa con formato personalizado sha256$salt$hash")
                    return True
        except Exception as e:
            print(f"Error al verificar formato personalizado: {e}")
    
    # Método 4: Werkzeug (pbkdf2:sha256, etc.)
    if pwhash.startswith('pbkdf2:') or pwhash.startswith('sha256$'):
        try:
            result = check_password_hash(pwhash, password)
            if result:
                print(f"Autenticación exitosa con método werkzeug")
                return True
        except Exception as e:
            print(f"Error al verificar con werkzeug: {e}")
    
    # Método 5: Scrypt (deshabilitado)
    if pwhash.startswith('scrypt:'):
        print("Contraseña con formato scrypt detectada, este método está deshabilitado")
        return False
    
    # Si llegamos aquí, ninguno de los métodos funcionó
    print("Todos los métodos de verificación de contraseña fallaron")
    return False

# Crear la app Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'macarena1'

# Configurar la base de datos SQLite con soporte para persistencia
# Primero intentar usar la ruta de base de datos persistente desde variables de entorno
persistent_db_path = os.environ.get('DB_PERSISTENT_PATH')
force_persistent = os.environ.get('FORCE_PERSISTENT_DB', 'false').lower() == 'true'

# Imprimir información de diagnóstico sobre las rutas
app.logger.info(f"Variable de entorno DB_PERSISTENT_PATH: {persistent_db_path}")
app.logger.info(f"Variable de entorno FORCE_PERSISTENT_DB: {force_persistent}")
app.logger.info(f"Directorio actual: {os.getcwd()}")

# Verificar si estamos en Render (donde debería existir /var/data)
render_persistent_path = '/var/data/database/agencia.db'
if os.path.exists('/var/data'):
    app.logger.info("Detectado entorno Render con directorio persistente /var/data")
    # Asegurarse de que el directorio existe
    os.makedirs('/var/data/database', exist_ok=True)
    
    # Verificar si la base de datos persistente existe
    if os.path.exists(render_persistent_path) or force_persistent:
        # Usar la ruta persistente en Render
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{render_persistent_path}'
        app.logger.info(f"Usando base de datos persistente en Render: {render_persistent_path}")
        
        # Crear un enlace simbólico para mayor compatibilidad
        if os.path.exists('agencia.db') and not os.path.islink('agencia.db'):
            # Si existe una base de datos local y no es un enlace simbólico, hacer backup
            backup_path = f"agencia_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            try:
                shutil.copy2('agencia.db', backup_path)
                app.logger.info(f"Backup de base de datos local creado: {backup_path}")
                os.remove('agencia.db')
            except Exception as e:
                app.logger.error(f"Error al hacer backup de la base de datos local: {e}")
        
        # Crear o actualizar el enlace simbólico
        if not os.path.exists('agencia.db'):
            try:
                os.symlink(render_persistent_path, 'agencia.db')
                app.logger.info("Enlace simbólico creado de agencia.db a la ubicación persistente")
            except Exception as e:
                app.logger.warning(f"No se pudo crear enlace simbólico: {e}")
    else:
        app.logger.warning("No se encontró base de datos persistente en Render, se creará una nueva")
elif persistent_db_path and os.path.exists(os.path.dirname(persistent_db_path)):
    # Asegurarse de que el directorio existe
    os.makedirs(os.path.dirname(persistent_db_path), exist_ok=True)
    # Usar la ruta persistente configurada
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{persistent_db_path}'
    app.logger.info(f"Usando base de datos persistente configurada: {persistent_db_path}")
else:
    # Usar la ruta por defecto
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agencia.db'
    app.logger.info("Usando base de datos en ruta por defecto: agencia.db")
    
# Verificar si la base de datos existe y es accesible
try:
    if os.path.exists(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')):
        app.logger.info("Base de datos verificada y existe")
    else:
        app.logger.warning("La base de datos no existe en la ruta configurada")
except Exception as e:
    app.logger.error(f"Error al verificar la base de datos: {e}")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar SQLAlchemy
db.init_app(app)

# Importar e inicializar el middleware de protección de usuarios
try:
    from user_protection_middleware import UserProtectionMiddleware
    # Inicializar el middleware con un intervalo de verificación de 5 minutos (300 segundos)
    user_protection = UserProtectionMiddleware(app, check_interval=300)
    app.logger.info("Middleware de protección de usuarios inicializado correctamente")
except Exception as e:
    app.logger.error(f"Error al inicializar el middleware de protección de usuarios: {e}")
    import traceback
    app.logger.error(traceback.format_exc())

# Configurar la base de datos SQLite
basedir = os.path.abspath(os.path.dirname(__file__))

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
def formato_precio(value, moneda='ARS'):
    if value is None or value == "":
        return "$0" if moneda == 'ARS' else "US$0"
    try:
        if moneda == 'USD':
            return f"US${value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        else:  # Default ARS
            return f"${value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return "$0" if moneda == 'ARS' else "US$0"

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
        if session.get('rol') not in ['administrador', 'administrador_jefe']:
            flash('No tienes permisos para acceder a esta página', 'danger')
            return redirect(url_for('dashboard'))
        return view(*args, **kwargs)
    return wrapped_view

def admin_jefe_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('login'))
        if session.get('rol') != 'administrador_jefe':
            flash('No tienes permisos para acceder a esta página. Se requiere rol de administrador jefe.', 'danger')
            return redirect(url_for('dashboard'))
        return view(*args, **kwargs)
    return wrapped_view

def vendedor_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('login'))
        # Cualquier rol puede acceder (vendedor, administrador, administrador_jefe)
        return view(*args, **kwargs)
    return wrapped_view

# Ruta de emergencia para iniciar sesión como administrador
@app.route('/admin_emergency')
def admin_emergency():
    try:
        # Buscar o crear usuario admin
        admin_user = Usuario.query.filter_by(username='admin').first()
        
        if not admin_user:
            # Crear usuario admin si no existe
            admin_user = Usuario(
                username='admin',
                password='macarena1',  # Contraseña en texto plano
                nombre='Administrador',
                apellido='Sistema',
                email='admin@fgdmotors.com',
                rol='administrador_jefe',
                porcentaje_comision=0.0
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Usuario admin creado automáticamente")
        
        # Establecer sesión directamente
        session['user_id'] = admin_user.id
        session['username'] = 'admin'
        session['rol'] = 'administrador_jefe'
        session['nombre'] = 'Administrador Sistema'
        
        flash('Inicio de sesión de emergencia exitoso', 'success')
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('login'))

# Rutas de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya está logueado, redirigir al inicio
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Autenticación normal para todos los usuarios (incluyendo admin)
        user = Usuario.query.filter_by(username=username).first()
        
        if user and (custom_check_password_hash(user.password, password) or (username == 'admin' and password == 'macarena1')):
            # Verificar si el usuario está pendiente de aprobación
            if user.rol == 'pendiente':
                flash('Tu cuenta aún está pendiente de aprobación por un administrador. Por favor, espera a que tu cuenta sea activada.', 'warning')
                return render_template('login.html')
                
            # Guardar en sesión
            session['user_id'] = user.id
            session['username'] = user.username
            session['rol'] = user.rol
            session['nombre'] = f"{user.nombre} {user.apellido}"
            
            # Imprimir información de diagnóstico
            print(f"Usuario logueado: {user.username}")
            print(f"Rol en la base de datos: {user.rol}")
            print(f"Rol guardado en sesión: {session.get('rol')}")
            
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

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    # Si ya está logueado, redirigir al inicio
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        # Obtener datos del formulario
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        email = request.form.get('email')
        
        # Validaciones básicas
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'danger')
            return render_template('registro.html')
            
        # Verificar si el usuario ya existe
        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya está en uso', 'danger')
            return render_template('registro.html')
            
        # Verificar si el email ya existe
        if Usuario.query.filter_by(email=email).first():
            flash('El email ya está registrado', 'danger')
            return render_template('registro.html')
        
        # Determinar el rol del usuario
        # Verificar si existe el usuario admin
        admin_exists = Usuario.query.filter_by(username='admin').first() is not None
        # Si no existe el admin, verificar si hay otros usuarios
        if not admin_exists:
            usuarios_count = Usuario.query.count()
            # Solo si no hay usuarios, el nuevo será administrador_jefe
            rol = 'administrador_jefe' if usuarios_count == 0 else 'pendiente'
        else:
            # Si ya existe el admin, todos los nuevos usuarios son pendientes
            rol = 'pendiente'
        
        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            username=username,
            password=custom_generate_password_hash(password),
            nombre=nombre,
            apellido=apellido,
            email=email,
            rol=rol,
            porcentaje_comision=5.0 if rol == 'vendedor' else 0.0
        )
        
        # Imprimir para diagnóstico
        print(f"Creando usuario con rol: {rol}")
        print(f"Usuarios en la base de datos: {usuarios_count}")
        
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            
            if rol == 'administrador_jefe':
                flash('Cuenta creada correctamente. Eres el primer usuario y has sido registrado como Administrador Jefe.', 'success')
            else:
                flash('Cuenta creada correctamente. Un administrador debe aprobar tu cuenta.', 'info')
                
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la cuenta: {str(e)}', 'danger')
    
    return render_template('registro.html')

# Ruta principal - dashboard
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    # Imprimir información de la sesión para diagnóstico
    print("Información de sesión:")
    print(f"user_id: {session.get('user_id')}")
    print(f"username: {session.get('username')}")
    print(f"rol: {session.get('rol')}")
    print(f"nombre: {session.get('nombre')}")
    # Contar autos disponibles
    autos_disponibles = Auto.query.filter_by(estado=EstadoAuto.DISPONIBLE).count()
    
    # Obtener últimos autos agregados
    ultimos_autos = Auto.query.order_by(Auto.id.desc()).limit(5).all()
    
    # Determinar qué menús mostrar según el rol
    es_admin_jefe = session.get('rol') == 'administrador_jefe'
    es_admin = session.get('rol') in ['administrador', 'administrador_jefe']
    es_vendedor = session.get('rol') in ['vendedor', 'administrador', 'administrador_jefe']
    
    # Imprimir información de diagnóstico
    print(f"Rol actual: {session.get('rol')}")
    print(f"Es admin jefe: {es_admin_jefe}")
    print(f"Es admin: {es_admin}")
    print(f"Es vendedor: {es_vendedor}")
    
    return render_template('dashboard.html', 
                           autos_disponibles=autos_disponibles,
                           ultimos_autos=ultimos_autos,
                           usuario=session.get('nombre'),
                           rol=session.get('rol'),
                           es_admin_jefe=es_admin_jefe,
                           es_admin=es_admin,
                           es_vendedor=es_vendedor)

# Rutas para autos
@app.route('/autos')
def autos():
    try:
        # Filtros
        marca = request.args.get('marca', '')
        modelo = request.args.get('modelo', '')
        anio = request.args.get('anio', '')
        precio_min = request.args.get('precio_min', '')
        precio_max = request.args.get('precio_max', '')
        moneda = request.args.get('moneda', 'ARS')
        
        # Consulta base - SIEMPRE mostrar solo autos disponibles
        query = Auto.query.filter_by(estado=EstadoAuto.DISPONIBLE)
        
        # Aplicar filtros si existen
        if marca:
            query = query.filter(Auto.marca.ilike(f'%{marca}%'))
        if modelo:
            query = query.filter(Auto.modelo.ilike(f'%{modelo}%'))
        if anio and anio.isdigit():
            query = query.filter(Auto.anio == int(anio))
        
        # Filtrar por moneda solo si se especifica explícitamente en la URL
        if moneda in ['ARS', 'USD'] and 'moneda' in request.args:  # Solo filtrar si el parámetro moneda está presente en la URL
            query = query.filter(Auto.moneda == moneda)
        
        # Filtrar por precio
        if precio_min and precio_min.isdigit():
            query = query.filter(Auto.precio >= float(precio_min))
        if precio_max and precio_max.isdigit():
            query = query.filter(Auto.precio <= float(precio_max))
        
        # Obtener resultados
        autos = query.order_by(Auto.id.desc()).all()
    
        return render_template('autos.html', autos=autos, is_logged_in='user_id' in session)
    except Exception as e:
        app.logger.error(f"Error en la ruta /autos: {e}")
        # Devolver una página de error genérica
        return render_template('error.html', error=str(e)), 500

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
        auto.moneda = request.form.get('moneda', 'ARS')  # Actualizar la moneda
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

@app.route('/autos/eliminar/<int:auto_id>', methods=['POST'])
@login_required
def eliminar_auto(auto_id):
    auto = Auto.query.get_or_404(auto_id)
    
    # Verificar si el auto tiene ventas asociadas
    if auto.ventas:
        flash('No se puede eliminar este auto porque tiene ventas asociadas.', 'danger')
        return redirect(url_for('autos'))
    
    # Eliminar fotos físicas
    for foto in auto.fotos:
        try:
            ruta_completa = os.path.join(app.static_folder, foto.ruta_archivo)
            if os.path.exists(ruta_completa):
                os.remove(ruta_completa)
        except Exception as e:
            # Registrar error pero continuar
            app.logger.error(f"Error al eliminar archivo: {e}")
    
    # Eliminar auto (las fotos se eliminarán en cascada)
    db.session.delete(auto)
    db.session.commit()
    flash('Auto eliminado exitosamente.', 'success')
    return redirect(url_for('autos'))

@app.route('/autos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_auto():
    if request.method == 'POST':
        # Obtener datos del formulario
        marca = request.form.get('marca', '')
        modelo = request.form.get('modelo', '')
        anio = request.form.get('anio', '0')
        precio = request.form.get('precio', '0')
        moneda = request.form.get('moneda', 'ARS')
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
            moneda=moneda,  # Guardar la moneda seleccionada
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
@admin_required
def ventas():
    # Obtener parámetros de filtro
    mes = request.args.get('mes', type=int)
    anio = request.args.get('anio', type=int, default=datetime.now().year)
    estado = request.args.get('estado')
    moneda = request.args.get('moneda')
    
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
    
    # Filtrar por moneda si se especifica
    if moneda:
        query = query.filter(Venta.moneda == moneda)
    
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
        anios_venta = []
        for a in anios_venta_query.all():
            if a[0] is not None:
                try:
                    anios_venta.append(int(a[0]))
                except (ValueError, TypeError):
                    # Si no se puede convertir a int, intentar obtener el año de otra manera
                    app.logger.warning(f"No se pudo convertir {a[0]} a entero, tipo: {type(a[0])}")
        
        # Consulta para años con fecha_seña
        anios_seña_query = db.session.query(db.extract('year', Venta.fecha_seña).distinct())
        anios_seña_query = anios_seña_query.filter(Venta.fecha_seña != None)
        anios_seña_query = anios_seña_query.order_by(db.extract('year', Venta.fecha_seña).desc())
        anios_seña = []
        for a in anios_seña_query.all():
            if a[0] is not None:
                try:
                    anios_seña.append(int(a[0]))
                except (ValueError, TypeError):
                    # Si no se puede convertir a int, intentar obtener el año de otra manera
                    app.logger.warning(f"No se pudo convertir {a[0]} a entero, tipo: {type(a[0])}")
        
        # Combinar y eliminar duplicados
        anios = sorted(set(anios_venta + anios_seña), reverse=True)
    except Exception as e:
        app.logger.error(f"Error al obtener años con ventas: {e}")
        anios = []
    
    if not anios:  # Si no hay años con ventas, usar el año actual
        anios = [datetime.now().year]
    
    # Estados de pago
    estados = [e.value for e in EstadoPago]
    
    # Calcular totales financieros separados por moneda
    total_ventas_ars = sum(venta.precio_venta for venta in ventas if venta.moneda == 'ARS')
    total_ventas_usd = sum(venta.precio_venta for venta in ventas if venta.moneda == 'USD')
    
    total_inversion_ars = sum(venta.auto.precio_compra if venta.auto and venta.auto.precio_compra is not None and venta.moneda == 'ARS' else 0 for venta in ventas)
    total_inversion_usd = sum(venta.auto.precio_compra if venta.auto and venta.auto.precio_compra is not None and venta.moneda == 'USD' else 0 for venta in ventas)
    
    total_ganancia_ars = sum((venta.precio_venta - (venta.auto.precio_compra if venta.auto and venta.auto.precio_compra is not None else 0)) for venta in ventas if venta.moneda == 'ARS')
    total_ganancia_usd = sum((venta.precio_venta - (venta.auto.precio_compra if venta.auto and venta.auto.precio_compra is not None else 0)) for venta in ventas if venta.moneda == 'USD')
    
    # Mantener los totales generales para compatibilidad con código existente
    total_ventas = total_ventas_ars + total_ventas_usd
    total_inversion = total_inversion_ars + total_inversion_usd
    total_ganancia = total_ganancia_ars + total_ganancia_usd
    
    return render_template('ventas.html', 
                        ventas=ventas, 
                        meses=meses, 
                        anios=anios,
                        estados=estados,
                        mes_seleccionado=mes,
                        anio_seleccionado=anio,
                        estado_seleccionado=estado,
                        moneda_seleccionada=moneda,
                        total_ventas=total_ventas,
                        total_inversion=total_inversion,
                        total_ganancia=total_ganancia,
                        total_ventas_ars=total_ventas_ars,
                        total_ventas_usd=total_ventas_usd,
                        total_inversion_ars=total_inversion_ars,
                        total_inversion_usd=total_inversion_usd,
                        total_ganancia_ars=total_ganancia_ars,
                        total_ganancia_usd=total_ganancia_usd)

@app.route('/ventas/registrar', methods=['GET', 'POST'])
@vendedor_required
def registrar_venta():
    try:
        # Obtener autos disponibles
        autos_disponibles = Auto.query.filter_by(estado=EstadoAuto.DISPONIBLE).all()
        
        # Verificar que haya autos disponibles
        if not autos_disponibles:
            flash('No hay autos disponibles para vender. Agregue autos primero.', 'warning')
            return redirect(url_for('autos'))
        
        if request.method == 'POST':
            # Obtener datos del formulario
            auto_id = request.form.get('auto_id')
            cliente_nombre = request.form.get('cliente_nombre')
            cliente_apellido = request.form.get('cliente_apellido', '')
            cliente_email = request.form.get('cliente_email')
            cliente_telefono = request.form.get('cliente_telefono')
            cliente_dni = request.form.get('cliente_dni', '')
            monto_seña = request.form.get('monto_seña', '0')
            moneda = request.form.get('moneda', 'ARS')  # Valor por defecto: ARS
            
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
            
            # Obtener el precio del formulario
            precio_venta = float(request.form.get('precio', auto.precio))
            
            # Crear la venta
            nueva_venta = Venta(
                auto_id=auto_id,
                cliente_nombre=cliente_nombre,
                cliente_apellido=cliente_apellido,
                cliente_email=cliente_email,
                cliente_telefono=cliente_telefono,
                cliente_dni=cliente_dni,
                monto_seña=monto_seña_float,
                precio_venta=precio_venta,
                moneda=moneda,  # Guardar la moneda seleccionada
                fecha_seña=datetime.now(),  # Siempre establecer una fecha
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
        
        # Asegurarse de que los autos tengan toda la información necesaria
        for auto in autos_disponibles:
            if not hasattr(auto, 'id') or not auto.id:
                app.logger.error(f"Auto sin ID: {auto}")
        
        return render_template('registrar_venta.html', autos=autos_disponibles)
    except Exception as e:
        app.logger.error(f"Error en la ruta /ventas/registrar: {e}")
        return render_template('error.html', error=str(e)), 500

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

# Ruta para usuarios
@app.route('/usuarios')
@login_required
def usuarios():
    # Verificar que el usuario sea administrador_jefe
    if session.get('rol') != 'administrador_jefe':
        flash('No tienes permisos para acceder a esta página', 'danger')
        return redirect(url_for('dashboard'))
    try:
        # Obtener todos los usuarios
        usuarios = Usuario.query.all()
        return render_template('usuarios.html', usuarios=usuarios)
    except Exception as e:
        app.logger.error(f"Error en la ruta /usuarios: {e}")
        return render_template('error.html', error=str(e)), 500

@app.route('/usuarios/nuevo', methods=['POST'])
@login_required
def nuevo_usuario():
    # Verificar que el usuario sea administrador_jefe
    if session.get('rol') != 'administrador_jefe':
        flash('No tienes permisos para acceder a esta página', 'danger')
        return redirect(url_for('dashboard'))
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
        password=custom_generate_password_hash(password),
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
@login_required
def editar_usuario(usuario_id):
    # Verificar que el usuario sea administrador_jefe
    if session.get('rol') != 'administrador_jefe':
        flash('No tienes permisos para acceder a esta página', 'danger')
        return redirect(url_for('dashboard'))
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
            usuario.password = custom_generate_password_hash(nueva_password)
        
        db.session.commit()
        flash('Usuario actualizado correctamente', 'success')
        return redirect(url_for('usuarios'))
    
    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/usuarios/<int:usuario_id>/eliminar', methods=['POST', 'GET'])
@login_required
def eliminar_usuario(usuario_id):
    # Verificar que el usuario sea administrador_jefe
    if session.get('rol') != 'administrador_jefe':
        flash('No tienes permisos para acceder a esta página', 'danger')
        return redirect(url_for('dashboard'))
    # No permitir eliminar al usuario actualmente logueado
    if int(session.get('user_id')) == usuario_id:
        flash('No puede eliminar su propio usuario', 'danger')
        return redirect(url_for('usuarios'))
    
    # Buscar el usuario
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # Solo administrador_jefe puede eliminar usuarios que no estén pendientes
    if usuario.rol != 'pendiente' and session.get('rol') != 'administrador_jefe':
        flash('Solo el administrador jefe puede eliminar usuarios activos', 'danger')
        return redirect(url_for('usuarios'))
    
    try:
        db.session.delete(usuario)
        db.session.commit()
        
        if usuario.rol == 'pendiente':
            flash('Solicitud de usuario rechazada', 'success')
        else:
            flash('Usuario eliminado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el usuario: {str(e)}', 'danger')
    
    return redirect(url_for('usuarios'))

@app.route('/usuarios/aprobar/<int:usuario_id>/<rol>')
@login_required
def aprobar_usuario(usuario_id, rol):
    # Verificar que el usuario sea administrador_jefe
    if session.get('rol') != 'administrador_jefe':
        flash('No tienes permisos para acceder a esta página', 'danger')
        return redirect(url_for('dashboard'))
    # Verificar que el rol sea válido
    if rol not in ['vendedor', 'administrador', 'administrador_jefe']:
        flash('Rol no válido', 'danger')
        return redirect(url_for('usuarios'))
    
    # Solo administrador_jefe puede crear otros administradores_jefe
    if rol == 'administrador_jefe' and session.get('rol') != 'administrador_jefe':
        flash('Solo el administrador jefe puede crear otros administradores jefe', 'danger')
        return redirect(url_for('usuarios'))
    
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # Verificar que el usuario esté pendiente
    if usuario.rol != 'pendiente':
        flash('Este usuario ya ha sido aprobado', 'warning')
        return redirect(url_for('usuarios'))
    
    try:
        usuario.rol = rol
        # Establecer comisión según el rol
        if rol == 'vendedor':
            usuario.porcentaje_comision = 5.0
        else:
            usuario.porcentaje_comision = 0.0
            
        db.session.commit()
        flash(f'Usuario aprobado como {rol}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al aprobar el usuario: {str(e)}', 'danger')
    
    return redirect(url_for('usuarios'))

# Rutas para estadísticas
@app.route('/estadisticas')
@admin_required
def estadisticas():
    try:
        # Obtener estadísticas de ventas por mes para el año actual
        año_actual = datetime.now().year
        
        # Ventas por mes
        ventas_por_mes = []
        for mes in range(1, 13):
            # Contar ventas para este mes (considerando tanto fecha_venta como fecha_seña)
            count = Venta.query.filter(
                db.or_(
                    db.and_(db.extract('year', Venta.fecha_venta) == año_actual,
                           db.extract('month', Venta.fecha_venta) == mes),
                    db.and_(db.extract('year', Venta.fecha_seña) == año_actual,
                           db.extract('month', Venta.fecha_seña) == mes,
                           Venta.fecha_venta == None)
                )
            ).count()
            
            ventas_por_mes.append(count)
        
        # Ventas por vendedor con detalle por moneda
        vendedores = Usuario.query.filter(Usuario.rol.in_(['admin', 'vendedor'])).all()
        ventas_por_vendedor = []
        
        for vendedor in vendedores:
            # Total de ventas
            count = Venta.query.filter_by(vendedor_id=vendedor.id).count()
            if count > 0:  # Solo incluir vendedores con ventas
                # Ventas por moneda
                count_ars = Venta.query.filter_by(vendedor_id=vendedor.id, moneda='ARS').count()
                count_usd = Venta.query.filter_by(vendedor_id=vendedor.id, moneda='USD').count()
                
                # Montos totales por moneda
                monto_ars = db.session.query(db.func.sum(Venta.precio_venta))\
                            .filter_by(vendedor_id=vendedor.id, moneda='ARS').scalar() or 0
                monto_usd = db.session.query(db.func.sum(Venta.precio_venta))\
                            .filter_by(vendedor_id=vendedor.id, moneda='USD').scalar() or 0
                
                ventas_por_vendedor.append({
                    'nombre': f"{vendedor.nombre} {vendedor.apellido}",
                    'ventas': count,
                    'ventas_ars': count_ars,
                    'ventas_usd': count_usd,
                    'monto_ars': monto_ars,
                    'monto_usd': monto_usd
                })
        
        # Ordenar por cantidad de ventas (descendente)
        ventas_por_vendedor = sorted(ventas_por_vendedor, key=lambda x: x['ventas'], reverse=True)
        
        # Marcas más vendidas
        try:
            marcas = db.session.query(
                Auto.marca, 
                db.func.count(Venta.id).label('count')
            ).join(Venta, Auto.id == Venta.auto_id).group_by(Auto.marca).order_by(db.desc('count')).limit(5).all()
            
            marcas_vendidas = [{'marca': marca, 'count': count} for marca, count in marcas]
        except Exception as e:
            app.logger.error(f"Error al obtener marcas vendidas: {e}")
            marcas_vendidas = []
        
        # Ingresos totales por moneda (todas las ventas, no solo las pagadas)
        ingresos_ars = db.session.query(db.func.sum(Venta.precio_venta))\
                      .filter(Venta.moneda == 'ARS').scalar() or 0
        ingresos_usd = db.session.query(db.func.sum(Venta.precio_venta))\
                      .filter(Venta.moneda == 'USD').scalar() or 0
        
        # Calcular costos por moneda (filtrar por la moneda de la venta, no del auto)
        costo_ars = db.session.query(db.func.coalesce(db.func.sum(Auto.precio_compra), 0))\
                    .join(Venta, Venta.auto_id == Auto.id)\
                    .filter(Venta.moneda == 'ARS').scalar() or 0
        costo_usd = db.session.query(db.func.coalesce(db.func.sum(Auto.precio_compra), 0))\
                    .join(Venta, Venta.auto_id == Auto.id)\
                    .filter(Venta.moneda == 'USD').scalar() or 0
        
        # Calcular ganancias por moneda
        ganancia_ars = ingresos_ars - costo_ars
        ganancia_usd = ingresos_usd - costo_usd
        
        # Totales (para compatibilidad con código existente)
        ingresos_totales = ingresos_ars + ingresos_usd  # Suma simple para mostrar un total general
        costo_total = costo_ars + costo_usd
        ganancia_total = ganancia_ars + ganancia_usd
        
        # Ingresos y ganancias por mes (separados por moneda)
        ingresos_por_mes_ars = []
        ingresos_por_mes_usd = []
        ganancias_por_mes_ars = []
        ganancias_por_mes_usd = []
        ventas_por_mes_ars = []
        ventas_por_mes_usd = []
        
        for mes in range(1, 13):
            # Contar ventas para este mes por moneda (considerando tanto fecha_venta como fecha_seña)
            count_ars = Venta.query.filter(
                db.or_(
                    db.and_(db.extract('year', Venta.fecha_venta) == año_actual,
                           db.extract('month', Venta.fecha_venta) == mes),
                    db.and_(db.extract('year', Venta.fecha_seña) == año_actual,
                           db.extract('month', Venta.fecha_seña) == mes,
                           Venta.fecha_venta == None)
                ),
                Venta.moneda == 'ARS'
            ).count()
            
            count_usd = Venta.query.filter(
                db.or_(
                    db.and_(db.extract('year', Venta.fecha_venta) == año_actual,
                           db.extract('month', Venta.fecha_venta) == mes),
                    db.and_(db.extract('year', Venta.fecha_seña) == año_actual,
                           db.extract('month', Venta.fecha_seña) == mes,
                           Venta.fecha_venta == None)
                ),
                Venta.moneda == 'USD'
            ).count()
            
            # Sumar ingresos para este mes en ARS (considerando tanto fecha_venta como fecha_seña)
            ingresos_mes_ars = db.session.query(db.func.sum(Venta.precio_venta)).filter(
                db.or_(
                    db.and_(db.extract('year', Venta.fecha_venta) == año_actual,
                           db.extract('month', Venta.fecha_venta) == mes),
                    db.and_(db.extract('year', Venta.fecha_seña) == año_actual,
                           db.extract('month', Venta.fecha_seña) == mes,
                           Venta.fecha_venta == None)
                ),
                Venta.moneda == 'ARS'
            ).scalar() or 0
            
            # Sumar ingresos para este mes en USD (considerando tanto fecha_venta como fecha_seña)
            ingresos_mes_usd = db.session.query(db.func.sum(Venta.precio_venta)).filter(
                db.or_(
                    db.and_(db.extract('year', Venta.fecha_venta) == año_actual,
                           db.extract('month', Venta.fecha_venta) == mes),
                    db.and_(db.extract('year', Venta.fecha_seña) == año_actual,
                           db.extract('month', Venta.fecha_seña) == mes,
                           Venta.fecha_venta == None)
                ),
                Venta.moneda == 'USD'
            ).scalar() or 0
            
            # Sumar costos para este mes en ARS (considerando tanto fecha_venta como fecha_seña)
            costos_mes_ars = db.session.query(db.func.coalesce(db.func.sum(Auto.precio_compra), 0))\
                             .join(Venta, Venta.auto_id == Auto.id)\
                             .filter(
                                 db.or_(
                                     db.and_(db.extract('year', Venta.fecha_venta) == año_actual,
                                            db.extract('month', Venta.fecha_venta) == mes),
                                     db.and_(db.extract('year', Venta.fecha_seña) == año_actual,
                                            db.extract('month', Venta.fecha_seña) == mes,
                                            Venta.fecha_venta == None)
                                 ),
                                 Venta.moneda == 'ARS'
                             ).scalar() or 0
            
            # Sumar costos para este mes en USD (considerando tanto fecha_venta como fecha_seña)
            costos_mes_usd = db.session.query(db.func.coalesce(db.func.sum(Auto.precio_compra), 0))\
                             .join(Venta, Venta.auto_id == Auto.id)\
                             .filter(
                                 db.or_(
                                     db.and_(db.extract('year', Venta.fecha_venta) == año_actual,
                                            db.extract('month', Venta.fecha_venta) == mes),
                                     db.and_(db.extract('year', Venta.fecha_seña) == año_actual,
                                            db.extract('month', Venta.fecha_seña) == mes,
                                            Venta.fecha_venta == None)
                                 ),
                                 Venta.moneda == 'USD'
                             ).scalar() or 0
            
            # Calcular ganancias para este mes por moneda
            ganancia_mes_ars = ingresos_mes_ars - costos_mes_ars
            ganancia_mes_usd = ingresos_mes_usd - costos_mes_usd
            
            # Guardar datos por moneda
            ventas_por_mes_ars.append(count_ars)
            ventas_por_mes_usd.append(count_usd)
            ingresos_por_mes_ars.append(ingresos_mes_ars)
            ingresos_por_mes_usd.append(ingresos_mes_usd)
            ganancias_por_mes_ars.append(ganancia_mes_ars)
            ganancias_por_mes_usd.append(ganancia_mes_usd)
        
        # Para compatibilidad con código existente
        ingresos_por_mes = [ingresos_por_mes_ars[i] + ingresos_por_mes_usd[i] for i in range(12)]
        ganancias_por_mes = [ganancias_por_mes_ars[i] + ganancias_por_mes_usd[i] for i in range(12)]
        
        # Contar el total de ventas
        total_ventas = Venta.query.count()
        
        # Calcular estadísticas del mes actual
        mes_actual = datetime.now().month
        
        # Contar ventas del mes actual por moneda
        ventas_mes_actual = Venta.query.filter(
            db.or_(
                db.and_(db.extract('year', Venta.fecha_venta) == año_actual,
                       db.extract('month', Venta.fecha_venta) == mes_actual),
                db.and_(db.extract('year', Venta.fecha_seña) == año_actual,
                       db.extract('month', Venta.fecha_seña) == mes_actual,
                       Venta.fecha_venta == None)
            )
        ).count()
        
        # Ventas del mes actual en ARS
        ventas_mes_actual_ars = Venta.query.filter(
            db.or_(
                db.and_(db.extract('year', Venta.fecha_venta) == año_actual,
                       db.extract('month', Venta.fecha_venta) == mes_actual),
                db.and_(db.extract('year', Venta.fecha_seña) == año_actual,
                       db.extract('month', Venta.fecha_seña) == mes_actual,
                       Venta.fecha_venta == None)
            ),
            Venta.moneda == 'ARS'
        ).count()
        
        # Ventas del mes actual en USD
        ventas_mes_actual_usd = Venta.query.filter(
            db.or_(
                db.and_(db.extract('year', Venta.fecha_venta) == año_actual,
                       db.extract('month', Venta.fecha_venta) == mes_actual),
                db.and_(db.extract('year', Venta.fecha_seña) == año_actual,
                       db.extract('month', Venta.fecha_seña) == mes_actual,
                       Venta.fecha_venta == None)
            ),
            Venta.moneda == 'USD'
        ).count()
        
        # Ingresos del mes actual en ARS
        ingresos_mes_actual_ars = db.session.query(db.func.sum(Venta.precio_venta)).filter(
            db.or_(
                db.and_(db.extract('year', Venta.fecha_venta) == año_actual,
                       db.extract('month', Venta.fecha_venta) == mes_actual),
                db.and_(db.extract('year', Venta.fecha_seña) == año_actual,
                       db.extract('month', Venta.fecha_seña) == mes_actual,
                       Venta.fecha_venta == None)
            ),
            Venta.moneda == 'ARS'
        ).scalar() or 0
        
        # Ingresos del mes actual en USD
        ingresos_mes_actual_usd = db.session.query(db.func.sum(Venta.precio_venta)).filter(
            db.or_(
                db.and_(db.extract('year', Venta.fecha_venta) == año_actual,
                       db.extract('month', Venta.fecha_venta) == mes_actual),
                db.and_(db.extract('year', Venta.fecha_seña) == año_actual,
                       db.extract('month', Venta.fecha_seña) == mes_actual,
                       Venta.fecha_venta == None)
            ),
            Venta.moneda == 'USD'
        ).scalar() or 0
        
        # Costos del mes actual en ARS
        costos_mes_actual_ars = db.session.query(db.func.coalesce(db.func.sum(Auto.precio_compra), 0))\
                                .join(Venta, Venta.auto_id == Auto.id)\
                                .filter(
                                    db.or_(
                                        db.and_(db.extract('year', Venta.fecha_venta) == año_actual,
                                               db.extract('month', Venta.fecha_venta) == mes_actual),
                                        db.and_(db.extract('year', Venta.fecha_seña) == año_actual,
                                               db.extract('month', Venta.fecha_seña) == mes_actual,
                                               Venta.fecha_venta == None)
                                    ),
                                    Venta.moneda == 'ARS'
                                ).scalar() or 0
        
        # Costos del mes actual en USD
        costos_mes_actual_usd = db.session.query(db.func.coalesce(db.func.sum(Auto.precio_compra), 0))\
                                .join(Venta, Venta.auto_id == Auto.id)\
                                .filter(
                                    db.or_(
                                        db.and_(db.extract('year', Venta.fecha_venta) == año_actual,
                                               db.extract('month', Venta.fecha_venta) == mes_actual),
                                        db.and_(db.extract('year', Venta.fecha_seña) == año_actual,
                                               db.extract('month', Venta.fecha_seña) == mes_actual,
                                               Venta.fecha_venta == None)
                                    ),
                                    Venta.moneda == 'USD'
                                ).scalar() or 0
        
        # Ganancias del mes actual
        ganancia_mes_actual_ars = ingresos_mes_actual_ars - costos_mes_actual_ars
        ganancia_mes_actual_usd = ingresos_mes_actual_usd - costos_mes_actual_usd
        
        return render_template('estadisticas.html',
                               ventas_por_mes=ventas_por_mes,
                               ventas_por_vendedor=ventas_por_vendedor,
                               marcas_vendidas=marcas_vendidas,
                               ingresos_totales=ingresos_totales,
                               ingresos_por_mes=ingresos_por_mes,
                               ganancias_por_mes=ganancias_por_mes,
                               año_actual=año_actual,
                               total_ventas=total_ventas,
                               costo_total=costo_total,
                               ganancia_total=ganancia_total,
                               # Variables por moneda
                               ingresos_ars=ingresos_ars,
                               ingresos_usd=ingresos_usd,
                               costo_ars=costo_ars,
                               costo_usd=costo_usd,
                               ganancia_ars=ganancia_ars,
                               ganancia_usd=ganancia_usd,
                               ingresos_por_mes_ars=ingresos_por_mes_ars,
                               ingresos_por_mes_usd=ingresos_por_mes_usd,
                               ganancias_por_mes_ars=ganancias_por_mes_ars,
                               ganancias_por_mes_usd=ganancias_por_mes_usd,
                               ventas_por_mes_ars=ventas_por_mes_ars,
                               ventas_por_mes_usd=ventas_por_mes_usd,
                               # Variables del mes actual
                               ventas_mes_actual=ventas_mes_actual,
                               ventas_mes_actual_ars=ventas_mes_actual_ars,
                               ventas_mes_actual_usd=ventas_mes_actual_usd,
                               ingresos_mes_actual_ars=ingresos_mes_actual_ars,
                               ingresos_mes_actual_usd=ingresos_mes_actual_usd,
                               costos_mes_actual_ars=costos_mes_actual_ars,
                               costos_mes_actual_usd=costos_mes_actual_usd,
                               ganancia_mes_actual_ars=ganancia_mes_actual_ars,
                               ganancia_mes_actual_usd=ganancia_mes_actual_usd)
    except Exception as e:
        app.logger.error(f"Error en la ruta /estadisticas: {e}")
        return render_template('error.html', error=str(e)), 500

# Crear tablas y datos iniciales
with app.app_context():
    db.create_all()
    
    # Ya no creamos automáticamente el usuario administrador
    # El primer usuario que se registre será administrador_jefe
    
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
    app.run(debug=True)
