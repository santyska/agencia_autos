from flask import Flask
from models import db, Usuario, Auto, EstadoAuto
from werkzeug.security import generate_password_hash
from config.config import config
from utils.helpers import formato_precio, formato_numero
import os

# Importar blueprints
from routes.auth import auth_bp
from routes.autos import autos_bp
from routes.ventas import ventas_bp
from routes.admin import admin_bp
from routes.estadisticas import estadisticas_bp

def create_app(config_name='default'):
    """Crea y configura la aplicación Flask"""
    app = Flask(__name__)
    
    # Cargar configuración
    app.config.from_object(config[config_name])
    
    # Asegurar que exista el directorio de uploads
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Inicializar la base de datos
    db.init_app(app)
    
    # Registrar blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(autos_bp, url_prefix='/autos')
    app.register_blueprint(ventas_bp, url_prefix='/ventas')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(estadisticas_bp, url_prefix='/estadisticas')
    
    # Registrar filtros personalizados
    app.jinja_env.filters['formato_precio'] = formato_precio
    app.jinja_env.filters['number_format'] = formato_numero
    
    # Crear tablas y datos iniciales
    with app.app_context():
        db.create_all()
        crear_datos_iniciales()
    
    return app

def crear_datos_iniciales():
    """Crea datos iniciales si no existen"""
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
