#!/usr/bin/env bash
# exit on error
set -o errexit

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt

# Asegurarse de que la base de datos existe
python -c "from app import db; db.create_all()"

# Ejecutar script de protección de usuarios
python protect_users.py

# SCRIPTS DE CREACIÓN DE USUARIOS DESHABILITADOS
# Ya no son necesarios porque el problema de login ha sido resuelto
# Ahora solo el administrador jefe puede gestionar usuarios

# # Crear usuario administrador (método 1)
# python create_admin.py || echo "Método 1 falló, intentando método 2"

# # Método alternativo para crear usuario admin directamente en SQLite
# python reset_admin.py || echo "Método 2 falló, intentando método 3"

# # Método optimizado con salt fijo para crear usuario admin
# python create_admin_fixed.py || echo "Método 3 falló, intentando método 4"

# # Método de emergencia con hash simple para Render
# python render_admin.py || echo "Método 4 falló, intentando método 5"

# # Solución final: crear usuario con contraseña en texto plano
# python fix_render_auth.py || echo "Método 5 falló, intentando método 6"

# # Solución de emergencia final
# python emergency_login.py || echo "Método 6 falló, intentando método 7"

# # Actualizar todas las contraseñas a un formato compatible
# python update_passwords.py
