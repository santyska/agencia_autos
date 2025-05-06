from flask import Flask
from models import db, Usuario
from app import custom_generate_password_hash

# Crear una mini aplicación Flask para inicializar la base de datos
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agencia.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Crear un usuario administrador
with app.app_context():
    # Verificar si ya existe un usuario admin
    admin = Usuario.query.filter_by(username='admin').first()
    
    if admin:
        # Actualizar la contraseña del admin existente
        admin.password = custom_generate_password_hash('admin123')
        print("Contraseña del usuario admin actualizada.")
    else:
        # Crear un nuevo usuario admin
        nuevo_admin = Usuario(
            username='admin',
            password=custom_generate_password_hash('admin123'),
            nombre='Administrador',
            apellido='Sistema',
            email='admin@fgdmotors.com',
            rol='admin',
            porcentaje_comision=0.0
        )
        db.session.add(nuevo_admin)
        print("Nuevo usuario admin creado.")
    
    # Guardar cambios
    db.session.commit()
    
    print("Usuario admin configurado correctamente.")
    print("Usuario: admin")
    print("Contraseña: admin123")
