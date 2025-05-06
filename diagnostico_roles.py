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

# Contar usuarios
cursor.execute("SELECT COUNT(*) FROM usuario")
count = cursor.fetchone()[0]
print(f"Número total de usuarios en la base de datos: {count}")

# Listar usuarios con todos sus detalles
cursor.execute("SELECT * FROM usuario")
usuarios = cursor.fetchall()
if usuarios:
    print("\nLista detallada de usuarios:")
    for usuario in usuarios:
        print(f"ID: {usuario['id']}")
        print(f"Username: {usuario['username']}")
        print(f"Nombre: {usuario['nombre']} {usuario['apellido']}")
        print(f"Email: {usuario['email']}")
        print(f"Rol: {usuario['rol']}")
        print(f"Porcentaje comisión: {usuario['porcentaje_comision']}")
        print("-" * 50)
else:
    print("\nNo hay usuarios en la base de datos.")

# Verificar la estructura de la tabla usuario
cursor.execute("PRAGMA table_info(usuario)")
columnas = cursor.fetchall()
print("\nEstructura de la tabla usuario:")
for col in columnas:
    print(f"Columna: {col['name']}, Tipo: {col['type']}")

# Cerrar conexión
conn.close()

print("\nDiagnóstico completado.")
