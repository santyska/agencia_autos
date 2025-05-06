import sqlite3
import os
import hashlib

# Ruta a la base de datos
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'agencia.db')

# Verificar que la base de datos existe
if not os.path.exists(db_path):
    print(f"Error: No se encontró la base de datos en {db_path}")
    exit(1)

# Crear un hash de contraseña simple con SHA-256
def create_password_hash(password):
    method = 'sha256'
    salt = 'fgdmotors2025'  # Salt fijo para asegurar que podamos recrear el hash
    hash_val = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{method}${salt}${hash_val}"

# Conectar a la base de datos
conn = sqlite3.connect(db_path)
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

admin_password = create_password_hash('admin123')

if admin_id:
    # Actualizar el usuario existente
    admin_id = admin_id[0]
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

print("\nUsuario admin configurado correctamente.")
print("Usuario: admin")
print("Contraseña: admin123")
