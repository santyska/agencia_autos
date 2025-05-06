import sqlite3
import os

def verificar_tablas():
    # Conectar a la base de datos
    db_path = os.path.join(os.path.dirname(__file__), 'agencia_autos.db')
    if not os.path.exists(db_path):
        print(f"La base de datos no existe en: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Obtener lista de tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tablas = cursor.fetchall()
    
    print("Tablas en la base de datos:")
    for tabla in tablas:
        print(f"- {tabla[0]}")
        
        # Mostrar estructura de cada tabla
        cursor.execute(f"PRAGMA table_info({tabla[0]})")
        columnas = cursor.fetchall()
        print(f"  Columnas de {tabla[0]}:")
        for col in columnas:
            print(f"    {col[1]} ({col[2]})")
    
    conn.close()

if __name__ == "__main__":
    verificar_tablas()
