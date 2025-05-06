import unittest
import os
import sys
from app_final import app, db
from models import Usuario, Auto, Venta, EstadoAuto, EstadoPago, FotoAuto

class AgenciaAutosTests(unittest.TestCase):
    def setUp(self):
        # Configurar la aplicación para pruebas
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        
        # Crear un contexto de aplicación
        with app.app_context():
            # Crear todas las tablas en la base de datos en memoria
            db.create_all()
            
            # Crear un usuario administrador para pruebas
            admin = Usuario(
                username='admin_test',
                password='pbkdf2:sha256:150000$nQoAX9Ym$dd2fa1b7c9c4e9214aeee0d0237d9566376588432e3c8473ca43f582ab628731',  # 'admin123'
                nombre='Admin',
                apellido='Test',
                email='admin@test.com',
                rol='admin'
            )
            db.session.add(admin)
            
            # Crear un auto de prueba
            auto = Auto(
                marca='Toyota',
                modelo='Corolla',
                anio=2022,
                precio=35000.0,
                color='Blanco',
                kilometraje=0,
                descripcion='Auto de prueba',
                estado=EstadoAuto.DISPONIBLE
            )
            db.session.add(auto)
            db.session.commit()
    
    def tearDown(self):
        # Limpiar después de cada prueba
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def login(self, username, password):
        return self.app.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)
    
    def logout(self):
        return self.app.get('/logout', follow_redirects=True)
    
    # Pruebas de autenticación
    def test_login_logout(self):
        # Probar login con credenciales correctas
        response = self.login('admin_test', 'admin123')
        self.assertIn(b'Bienvenido', response.data)
        
        # Probar logout
        response = self.logout()
        self.assertIn(b'Has cerrado sesi', response.data)  # 'Has cerrado sesión'
    
    def test_login_incorrecto(self):
        # Probar login con credenciales incorrectas
        response = self.login('admin_test', 'passwordincorrecta')
        self.assertIn(b'Usuario o contrase', response.data)  # 'Usuario o contraseña incorrectos'
    
    # Pruebas de acceso a rutas protegidas
    def test_acceso_dashboard(self):
        # Sin login, debería redirigir a login
        response = self.app.get('/dashboard', follow_redirects=True)
        self.assertIn(b'Iniciar sesi', response.data)  # 'Iniciar sesión'
        
        # Con login, debería mostrar el dashboard
        self.login('admin_test', 'admin123')
        response = self.app.get('/dashboard', follow_redirects=True)
        self.assertIn(b'Dashboard', response.data)
    
    # Pruebas de funcionalidades de autos
    def test_listar_autos(self):
        # Listar autos (accesible sin login)
        response = self.app.get('/autos', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Toyota', response.data)
        self.assertIn(b'Corolla', response.data)
    
    def test_detalle_auto(self):
        # Ver detalle de un auto
        with app.app_context():
            auto_id = Auto.query.first().id
            response = self.app.get(f'/auto/{auto_id}', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Toyota', response.data)
            self.assertIn(b'Corolla', response.data)
    
    def test_crear_auto(self):
        # Iniciar sesión primero
        self.login('admin_test', 'admin123')
        
        # Crear un nuevo auto
        response = self.app.post('/autos/nuevo', data=dict(
            marca='Honda',
            modelo='Civic',
            anio='2023',
            precio='40000',
            color='Azul',
            kilometraje='100',
            descripcion='Auto de prueba creado'
        ), follow_redirects=True)
        
        self.assertIn(b'Auto agregado correctamente', response.data)
        self.assertIn(b'Honda', response.data)
        self.assertIn(b'Civic', response.data)
    
    def test_editar_auto(self):
        # Iniciar sesión primero
        self.login('admin_test', 'admin123')
        
        # Obtener ID del auto existente
        with app.app_context():
            auto_id = Auto.query.first().id
            
            # Editar el auto
            response = self.app.post(f'/auto/{auto_id}/editar', data=dict(
                marca='Toyota',
                modelo='Camry',  # Cambiado de Corolla a Camry
                anio='2022',
                precio='38000',  # Precio actualizado
                color='Negro',   # Color actualizado
                kilometraje='0',
                descripcion='Auto de prueba actualizado'
            ), follow_redirects=True)
            
            self.assertIn(b'Auto actualizado correctamente', response.data)
            self.assertIn(b'Camry', response.data)
            self.assertIn(b'Negro', response.data)
    
    # Pruebas de ventas
    def test_listar_ventas(self):
        # Iniciar sesión primero
        self.login('admin_test', 'admin123')
        
        # Acceder a la lista de ventas
        response = self.app.get('/ventas', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Ventas', response.data)
    
    def test_registrar_venta(self):
        # Iniciar sesión primero
        self.login('admin_test', 'admin123')
        
        # Obtener ID del auto existente
        with app.app_context():
            auto_id = Auto.query.first().id
            
            # Registrar una venta
            response = self.app.post('/ventas/registrar', data=dict(
                auto_id=auto_id,
                cliente_nombre='Cliente Prueba',
                cliente_email='cliente@test.com',
                cliente_telefono='123456789',
                monto_seña='5000'
            ), follow_redirects=True)
            
            self.assertIn(b'Venta registrada correctamente', response.data)
            self.assertIn(b'Cliente Prueba', response.data)
            
            # Verificar que el auto ahora está vendido
            auto = Auto.query.get(auto_id)
            self.assertEqual(auto.estado, EstadoAuto.VENDIDO)
    
    # Pruebas de usuarios
    def test_listar_usuarios(self):
        # Iniciar sesión primero
        self.login('admin_test', 'admin123')
        
        # Acceder a la lista de usuarios
        response = self.app.get('/usuarios', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Usuarios', response.data)
        self.assertIn(b'admin_test', response.data)
    
    def test_crear_usuario(self):
        # Iniciar sesión primero
        self.login('admin_test', 'admin123')
        
        # Crear un nuevo usuario
        response = self.app.post('/usuarios/nuevo', data=dict(
            username='vendedor1',
            password='vendedor123',
            nombre='Vendedor',
            apellido='Uno',
            email='vendedor@test.com',
            rol='vendedor',
            porcentaje_comision='5.0'
        ), follow_redirects=True)
        
        self.assertIn(b'Usuario creado correctamente', response.data)
        self.assertIn(b'vendedor1', response.data)
    
    # Pruebas de estadísticas
    def test_ver_estadisticas(self):
        # Iniciar sesión primero
        self.login('admin_test', 'admin123')
        
        # Acceder a las estadísticas
        response = self.app.get('/estadisticas', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Estad', response.data)  # 'Estadísticas'

if __name__ == '__main__':
    unittest.main()
