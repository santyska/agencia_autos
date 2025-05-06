from app_final import app, db
from models import Venta, Auto
import sqlite3
import os

def actualizar_ventas():
    with app.app_context():
        # Verificar si la columna moneda ya existe en la tabla venta
        conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'agencia_autos.db'))
        cursor = conn.cursor()
        
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(venta)")
        columnas = cursor.fetchall()
        columna_moneda_existe = any(col[1] == 'moneda' for col in columnas)
        
        if not columna_moneda_existe:
            print("Agregando columna 'moneda' a la tabla venta...")
            cursor.execute("ALTER TABLE venta ADD COLUMN moneda VARCHAR(3) DEFAULT 'ARS'")
            conn.commit()
            print("Columna 'moneda' agregada correctamente.")
        else:
            print("La columna 'moneda' ya existe en la tabla venta.")
        
        # Actualizar los valores de moneda en las ventas basados en el auto asociado
        print("Actualizando valores de moneda en ventas existentes...")
        ventas = Venta.query.all()
        actualizadas = 0
        
        for venta in ventas:
            auto = Auto.query.get(venta.auto_id)
            if auto and auto.moneda:
                venta.moneda = auto.moneda
                actualizadas += 1
        
        db.session.commit()
        print(f"Se actualizaron {actualizadas} ventas con la moneda correspondiente.")
        
        conn.close()
        print("Actualización completada.")

if __name__ == "__main__":
    actualizar_ventas()
