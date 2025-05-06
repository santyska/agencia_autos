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

# Borrar todos los usuarios
cursor.execute("DELETE FROM usuario")

# Verificar que se hayan eliminado todos los usuarios
cursor.execute("SELECT COUNT(*) FROM usuario")
count = cursor.fetchone()[0]
if count > 0:
    print(f"ADVERTENCIA: Aún hay {count} usuarios en la base de datos. Intentando eliminar con otro método...")
    cursor.execute("DELETE FROM usuario WHERE 1=1")
    conn.commit()
    
    # Verificar nuevamente
    cursor.execute("SELECT COUNT(*) FROM usuario")
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"ERROR: No se pudieron eliminar todos los usuarios. Aún quedan {count} usuarios.")
    else:
        print("Todos los usuarios han sido eliminados de la base de datos")
else:
    print("Todos los usuarios han sido eliminados de la base de datos")

# Guardar cambios
conn.commit()
conn.close()

print("\nLa base de datos ha sido reiniciada. No hay usuarios en el sistema.")
print("El primer usuario que se registre será creado como administrador_jefe con acceso total.")
