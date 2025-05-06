import sqlite3
import os

# Ruta a la base de datos
db_path = 'agencia.db'

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

# Borrar todos los usuarios
cursor.execute("DELETE FROM usuario")
print("Todos los usuarios han sido eliminados de la base de datos")

# Guardar cambios
conn.commit()
conn.close()

print("\nLa base de datos ha sido reiniciada. No hay usuarios en el sistema.")
print("El primer usuario que se registre será creado como administrador_jefe con acceso total.")
