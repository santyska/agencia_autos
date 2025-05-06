import sqlite3
import os
import hashlib
import sys

# Ruta a la base de datos
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'agencia.db')

# Verificar que la base de datos existe
if not os.path.exists(db_path):
    print(f"Error: No se encontró la base de datos en {db_path}")
    exit(1)

# Función de hash idéntica a la de app_final.py
def custom_generate_password_hash(password):
    """Genera un hash de contraseña usando SHA-256"""
    # Usamos un salt fijo para garantizar que podamos recrear el hash exacto
    method = 'sha256'
    salt = 'fgdmotors2025'
    hash_val = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{method}${salt}${hash_val}"

# Conectar a la base de datos
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # Para acceder a las columnas por nombre
cursor = conn.cursor()

# Verificar si la tabla usuario existe
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario'")
if not cursor.fetchone():
    print("Error: La tabla 'usuario' no existe en la base de datos")
    conn.close()
    exit(1)

# Verificar si el usuario admin ya existe
cursor.execute("SELECT id FROM usuario WHERE username = 'admin'")
admin_id = cursor.fetchone()

admin_password = custom_generate_password_hash('admin123')

if admin_id:
    # Actualizar el usuario existente
    admin_id = admin_id['id']
    cursor.execute(
        "UPDATE usuario SET password = ?, nombre = ?, apellido = ?, email = ?, rol = ? WHERE id = ?",
        (admin_password, 'Administrador', 'Sistema', 'admin@fgdmotors.com', 'administrador_jefe', admin_id)
    )
    print(f"Usuario admin (ID: {admin_id}) actualizado con éxito")
else:
    # Crear un nuevo usuario admin
    cursor.execute(
        "INSERT INTO usuario (username, password, nombre, apellido, email, rol, porcentaje_comision) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ('admin', admin_password, 'Administrador', 'Sistema', 'admin@fgdmotors.com', 'administrador_jefe', 0.0)
    )
    print("Nuevo usuario admin creado con éxito")

# Guardar cambios
conn.commit()
conn.close()

print("Usuario administrador creado/actualizado con éxito.")
print("Usuario: admin")
print("Contraseña: admin123")
print("Rol: administrador_jefe")
