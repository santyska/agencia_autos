from app_final import app, db
from models import Venta, Auto
import sqlite3
import os

def actualizar_ventas():
    with app.app_context():
        # Obtener la ruta correcta de la base de datos desde la configuración de la app
        db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'agencia.db')
        print(f"Usando base de datos en: {db_path}")
        
        # Verificar si la base de datos existe
        if not os.path.exists(db_path):
            print(f"Error: La base de datos no existe en {db_path}")
            return
        
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar las tablas existentes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tablas = cursor.fetchall()
        print("Tablas en la base de datos:")
        for tabla in tablas:
            print(f"- {tabla[0]}")
        
        # Verificar si la tabla venta existe
        tabla_venta = next((t[0] for t in tablas if t[0].lower() == 'venta'), None)
        if not tabla_venta:
            print("Error: La tabla 'venta' no existe en la base de datos.")
            conn.close()
            return
        
        # Verificar si la columna moneda ya existe en la tabla venta
        cursor.execute(f"PRAGMA table_info({tabla_venta})")
        columnas = cursor.fetchall()
        print(f"Columnas de la tabla {tabla_venta}:")
        for col in columnas:
            print(f"  {col[1]} ({col[2]})")
        
        columna_moneda_existe = any(col[1] == 'moneda' for col in columnas)
        
        if not columna_moneda_existe:
            print(f"Agregando columna 'moneda' a la tabla {tabla_venta}...")
            cursor.execute(f"ALTER TABLE {tabla_venta} ADD COLUMN moneda VARCHAR(3) DEFAULT 'ARS'")
            conn.commit()
            print("Columna 'moneda' agregada correctamente.")
        else:
            print(f"La columna 'moneda' ya existe en la tabla {tabla_venta}.")
        
        # Actualizar los valores de moneda en las ventas basados en el auto asociado
        print("Actualizando valores de moneda en ventas existentes...")
        ventas = Venta.query.all()
        actualizadas = 0
        
        for venta in ventas:
            auto = Auto.query.get(venta.auto_id)
            if auto and hasattr(auto, 'moneda') and auto.moneda:
                venta.moneda = auto.moneda
                actualizadas += 1
        
        db.session.commit()
        print(f"Se actualizaron {actualizadas} ventas con la moneda correspondiente.")
        
        conn.close()
        print("Actualización completada.")

if __name__ == "__main__":
    actualizar_ventas()
