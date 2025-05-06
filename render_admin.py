import sqlite3
import os
import hashlib

# Ruta a la base de datos
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'agencia.db')

print(f"Buscando base de datos en: {db_path}")

# Verificar que la base de datos existe
if not os.path.exists(db_path):
    print(f"Error: No se encontró la base de datos en {db_path}")
    # Intentar buscar en otras ubicaciones comunes
    possible_paths = [
        './agencia.db',
        '/opt/render/project/src/agencia.db',
        '/var/data/agencia.db'
    ]
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            print(f"Base de datos encontrada en: {db_path}")
            break
    else:
        print("No se pudo encontrar la base de datos en ninguna ubicación")
        exit(1)

# Función para generar un hash SHA-256 simple
def generate_simple_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Conectar a la base de datos
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print("Conexión a la base de datos establecida")
except Exception as e:
    print(f"Error al conectar a la base de datos: {e}")
    exit(1)

# Verificar si la tabla usuario existe
try:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario'")
    if not cursor.fetchone():
        print("Error: La tabla 'usuario' no existe en la base de datos")
        conn.close()
        exit(1)
    print("Tabla 'usuario' encontrada")
except Exception as e:
    print(f"Error al verificar la tabla usuario: {e}")
    conn.close()
    exit(1)

# Verificar si el usuario admin ya existe
try:
    cursor.execute("SELECT id, username, password, rol FROM usuario WHERE username = 'admin'")
    admin = cursor.fetchone()
    if admin:
        admin_id, username, password, rol = admin
        print(f"Usuario admin encontrado: ID={admin_id}, Rol={rol}")
        
        # Actualizar el usuario existente
        simple_password = generate_simple_hash('admin123')
        cursor.execute(
            "UPDATE usuario SET password = ?, rol = ? WHERE id = ?",
            (simple_password, 'administrador_jefe', admin_id)
        )
        print(f"Usuario admin (ID: {admin_id}) actualizado con contraseña simple")
    else:
        # Crear un nuevo usuario admin con contraseña simple
        simple_password = generate_simple_hash('admin123')
        cursor.execute(
            "INSERT INTO usuario (username, password, nombre, apellido, email, rol, porcentaje_comision) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('admin', simple_password, 'Administrador', 'Sistema', 'admin@fgdmotors.com', 'administrador_jefe', 0.0)
        )
        print("Nuevo usuario admin creado con contraseña simple")
        
    # Guardar cambios
    conn.commit()
except Exception as e:
    print(f"Error al crear/actualizar usuario admin: {e}")
    conn.rollback()
    conn.close()
    exit(1)

# Listar todos los usuarios para diagnóstico
try:
    cursor.execute("SELECT id, username, rol FROM usuario")
    users = cursor.fetchall()
    print("\nUsuarios en la base de datos:")
    for user in users:
        print(f"ID: {user[0]}, Username: {user[1]}, Rol: {user[2]}")
except Exception as e:
    print(f"Error al listar usuarios: {e}")

# Cerrar conexión
conn.close()

print("\nScript completado. Usuario admin creado/actualizado con contraseña simple.")
print("Usuario: admin")
print("Contraseña: admin123")
print("Rol: administrador_jefe")
