import sqlite3
import os
import hashlib
import sys

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

# Función para generar un hash simple
def generate_simple_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

try:
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print("Conexión a la base de datos establecida")
    
    # Listar todos los usuarios
    cursor.execute("SELECT id, username, password, rol FROM usuario")
    users = cursor.fetchall()
    
    print("\nUsuarios en la base de datos:")
    for user in users:
        user_id, username, password, rol = user
        print(f"ID: {user_id}, Username: {username}, Rol: {rol}")
        
        # Actualizar la contraseña a un formato simple
        # Usamos el nombre de usuario como contraseña para simplificar
        new_password = generate_simple_hash(username)
        
        cursor.execute(
            "UPDATE usuario SET password = ? WHERE id = ?",
            (new_password, user_id)
        )
        print(f"  - Contraseña actualizada para {username}. Nueva contraseña: {username}")
    
    # Guardar cambios
    conn.commit()
    print("\nTodas las contraseñas han sido actualizadas.")
    
    # Verificar los cambios
    cursor.execute("SELECT id, username, password, rol FROM usuario")
    updated_users = cursor.fetchall()
    
    print("\nUsuarios actualizados:")
    for user in updated_users:
        user_id, username, password, rol = user
        print(f"ID: {user_id}, Username: {username}, Rol: {rol}")
        print(f"  - Hash de contraseña: {password[:15]}...")
    
    # Cerrar conexión
    conn.close()
    
except Exception as e:
    print(f"Error durante la ejecución: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\nScript completado. Ahora los usuarios pueden iniciar sesión con su nombre de usuario como contraseña.")
print("Por ejemplo:")
print("Usuario: admin")
print("Contraseña: admin")
print("Usuario: vendedor1")
print("Contraseña: vendedor1")
