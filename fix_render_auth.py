import sqlite3
import os
import hashlib
import sys

# Imprimir información del entorno para diagnóstico
print("Entorno de ejecución:")
print(f"Directorio actual: {os.getcwd()}")
print(f"Listado de archivos: {os.listdir('.')}")
print(f"Variables de entorno: {dict(os.environ)}")

# Buscar la base de datos en todas las ubicaciones posibles
possible_paths = [
    './agencia.db',
    '/opt/render/project/src/agencia.db',
    '/var/data/agencia.db',
    os.path.join(os.getcwd(), 'agencia.db'),
    os.path.join(os.path.dirname(os.getcwd()), 'agencia.db')
]

db_path = None
for path in possible_paths:
    if os.path.exists(path):
        db_path = path
        print(f"Base de datos encontrada en: {db_path}")
        break

if not db_path:
    print("No se pudo encontrar la base de datos en ninguna ubicación")
    print("Buscando en todo el sistema...")
    
    # Buscar recursivamente en el directorio actual
    for root, dirs, files in os.walk('.'):
        if 'agencia.db' in files:
            db_path = os.path.join(root, 'agencia.db')
            print(f"Base de datos encontrada en: {db_path}")
            break
    
    if not db_path:
        print("No se pudo encontrar la base de datos en ninguna ubicación")
        exit(1)

# Crear una contraseña directa sin hash para pruebas
plain_password = 'macarena1'

try:
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print("Conexión a la base de datos establecida")
    
    # Verificar si la tabla usuario existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario'")
    if not cursor.fetchone():
        print("Error: La tabla 'usuario' no existe en la base de datos")
        print("Tablas disponibles:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            print(f"- {table[0]}")
        conn.close()
        exit(1)
    
    # Verificar la estructura de la tabla usuario
    cursor.execute("PRAGMA table_info(usuario)")
    columns = cursor.fetchall()
    print("Estructura de la tabla usuario:")
    for col in columns:
        print(f"- {col[1]} ({col[2]})")
    
    # NUNCA BORRAR USUARIOS EXISTENTES
    # Solo verificar si el usuario admin existe
    print("Verificando si el usuario admin existe...")
    cursor.execute("SELECT id FROM usuario WHERE username = 'admin'")
    admin_user = cursor.fetchone()
    
    if admin_user:
        # Actualizar el usuario admin existente
        cursor.execute(
            "UPDATE usuario SET password = ?, rol = 'administrador_jefe' WHERE username = 'admin'",
            (plain_password,)
        )
        print("Usuario admin actualizado con contraseña sin hash")
    else:
        # Crear un nuevo usuario admin con contraseña sin hash
        cursor.execute(
            "INSERT INTO usuario (username, password, nombre, apellido, email, rol, porcentaje_comision) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('admin', plain_password, 'Administrador', 'Sistema', 'admin@fgdmotors.com', 'administrador_jefe', 0.0)
        )
        print("Nuevo usuario admin creado con contraseña sin hash")
    
    # Guardar cambios
    conn.commit()
    
    # Verificar que el usuario se creó correctamente
    cursor.execute("SELECT id, username, password, rol FROM usuario WHERE username = 'admin'")
    admin = cursor.fetchone()
    if admin:
        print(f"Usuario admin verificado: ID={admin[0]}, Password={admin[2]}, Rol={admin[3]}")
    else:
        print("Error: No se pudo verificar el usuario admin")
    
    # Cerrar conexión
    conn.close()
    
    print("\nScript completado. Usuario admin creado o actualizado con contraseña sin hash.")
    print("Usuario: admin")
    print("Contraseña: macarena1")
    print("Rol: administrador_jefe")
    
except Exception as e:
    print(f"Error durante la ejecución: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
