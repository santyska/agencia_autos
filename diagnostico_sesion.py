from flask import Flask, session, redirect, url_for, flash, render_template
from models import db, Usuario, Auto, Venta, FotoAuto, EstadoAuto, EstadoPago
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_agencia'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agencia.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Función para generar hash de contraseña compatible con Python 3.11
def custom_generate_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Función para verificar contraseña
def custom_check_password_hash(stored_password, provided_password):
    hashed_provided = hashlib.sha256(provided_password.encode()).hexdigest()
    return stored_password == hashed_provided

@app.route('/')
def index():
    # Mostrar información de la sesión actual
    session_info = {}
    for key in session:
        session_info[key] = session[key]
    
    # Obtener información de todos los usuarios
    usuarios = []
    try:
        for user in Usuario.query.all():
            usuarios.append({
                'id': user.id,
                'username': user.username,
                'rol': user.rol,
                'nombre': f"{user.nombre} {user.apellido}"
            })
    except Exception as e:
        print(f"Error al obtener usuarios: {e}")
    
    return render_template('diagnostico.html', session=session_info, usuarios=usuarios)

# Crear plantilla para diagnóstico
with app.app_context():
    os.makedirs('templates', exist_ok=True)
    with open('templates/diagnostico.html', 'w') as f:
        f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Diagnóstico de Sesión</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
    <div class="container mt-5">
        <h1>Diagnóstico de Sesión</h1>
        
        <div class="card mb-4">
            <div class="card-header">
                <h2>Información de Sesión Actual</h2>
            </div>
            <div class="card-body">
                {% if session %}
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Clave</th>
                                <th>Valor</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for key, value in session.items() %}
                            <tr>
                                <td>{{ key }}</td>
                                <td>{{ value }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p>No hay información de sesión disponible.</p>
                {% endif %}
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h2>Usuarios en la Base de Datos</h2>
            </div>
            <div class="card-body">
                {% if usuarios %}
                    <table class="table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Username</th>
                                <th>Rol</th>
                                <th>Nombre</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for user in usuarios %}
                            <tr>
                                <td>{{ user.id }}</td>
                                <td>{{ user.username }}</td>
                                <td>{{ user.rol }}</td>
                                <td>{{ user.nombre }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p>No hay usuarios en la base de datos.</p>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>
        """)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
