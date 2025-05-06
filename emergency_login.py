import sqlite3
import os
import sys
import hashlib
from flask import Flask, redirect, url_for, session, flash

# Crear una mini aplicación Flask para el endpoint de emergencia
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecreto123'

# Ruta para iniciar sesión de emergencia
@app.route('/emergency_login')
def emergency_login():
    try:
        # Buscar la base de datos
        basedir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(basedir, 'agencia.db')
        
        if not os.path.exists(db_path):
            return f"Error: No se encontró la base de datos en {db_path}"
        
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la tabla usuario existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario'")
        if not cursor.fetchone():
            conn.close()
            return "Error: La tabla 'usuario' no existe en la base de datos"
        
        # Verificar si el usuario admin ya existe
        cursor.execute("SELECT id FROM usuario WHERE username = 'admin'")
        admin = cursor.fetchone()
        
        if admin:
            admin_id = admin[0]
            # Actualizar el usuario admin existente
            cursor.execute(
                "UPDATE usuario SET password = ?, rol = ? WHERE id = ?",
                ('admin123', 'administrador_jefe', admin_id)
            )
            conn.commit()
            conn.close()
            
            # Establecer la sesión
            session['user_id'] = admin_id
            session['username'] = 'admin'
            session['rol'] = 'administrador_jefe'
            session['nombre'] = 'Administrador Sistema'
            
            flash('Inicio de sesión de emergencia exitoso', 'success')
            return redirect(url_for('dashboard'))
        else:
            # Crear un nuevo usuario admin
            cursor.execute(
                "INSERT INTO usuario (username, password, nombre, apellido, email, rol, porcentaje_comision) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ('admin', 'admin123', 'Administrador', 'Sistema', 'admin@fgdmotors.com', 'administrador_jefe', 0.0)
            )
            conn.commit()
            
            # Obtener el ID del nuevo usuario
            cursor.execute("SELECT id FROM usuario WHERE username = 'admin'")
            admin_id = cursor.fetchone()[0]
            conn.close()
            
            # Establecer la sesión
            session['user_id'] = admin_id
            session['username'] = 'admin'
            session['rol'] = 'administrador_jefe'
            session['nombre'] = 'Administrador Sistema'
            
            flash('Usuario admin creado y sesión iniciada', 'success')
            return redirect(url_for('dashboard'))
    
    except Exception as e:
        return f"Error: {str(e)}"

# Función para ejecutar desde la línea de comandos
def main():
    try:
        # Buscar la base de datos
        basedir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(basedir, 'agencia.db')
        
        print(f"Buscando base de datos en: {db_path}")
        
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
                sys.exit(1)
        
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print("Conexión a la base de datos establecida")
        
        # Verificar si la tabla usuario existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario'")
        if not cursor.fetchone():
            print("Error: La tabla 'usuario' no existe en la base de datos")
            conn.close()
            sys.exit(1)
        
        # Borrar todos los usuarios existentes para evitar conflictos
        cursor.execute("DELETE FROM usuario")
        print("Todos los usuarios han sido eliminados")
        
        # Crear un nuevo usuario admin con contraseña en texto plano
        cursor.execute(
            "INSERT INTO usuario (username, password, nombre, apellido, email, rol, porcentaje_comision) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('admin', 'admin123', 'Administrador', 'Sistema', 'admin@fgdmotors.com', 'administrador_jefe', 0.0)
        )
        print("Nuevo usuario admin creado con contraseña en texto plano")
        
        # Guardar cambios
        conn.commit()
        
        # Verificar que el usuario se creó correctamente
        cursor.execute("SELECT id, username, password, rol FROM usuario WHERE username = 'admin'")
        admin = cursor.fetchone()
        if admin:
            print(f"Usuario admin verificado: ID={admin[0]}, Password={admin[1]}, Rol={admin[3]}")
        else:
            print("Error: No se pudo verificar el usuario admin")
        
        # Cerrar conexión
        conn.close()
        
        print("\nScript completado. Usuario admin creado con contraseña en texto plano.")
        print("Usuario: admin")
        print("Contraseña: admin123")
        print("Rol: administrador_jefe")
        
    except Exception as e:
        print(f"Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
