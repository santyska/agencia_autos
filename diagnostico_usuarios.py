import sqlite3
import os

# Ruta a la base de datos
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'agencia.db')

# Verificar que la base de datos existe
if not os.path.exists(db_path):
    print(f"Error: No se encontró la base de datos en {db_path}")
    exit(1)

# Conectar a la base de datos
conn = sqlite3.connect(db_path)
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

# Listar usuarios
cursor.execute("SELECT id, username, rol FROM usuario")
usuarios = cursor.fetchall()
if usuarios:
    print("\nLista de usuarios:")
    for usuario in usuarios:
        print(f"ID: {usuario[0]}, Username: {usuario[1]}, Rol: {usuario[2]}")
else:
    print("\nNo hay usuarios en la base de datos.")

# Cerrar conexión
conn.close()
