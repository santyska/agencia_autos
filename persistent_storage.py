#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para manejar almacenamiento persistente de usuarios en Render
Este script guarda los usuarios en un archivo JSON en el sistema de archivos persistente de Render
"""

import os
import json
import sqlite3
import logging
import sys
import time
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("persistent_storage.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PersistentStorage")

# Definir rutas de almacenamiento persistente en Render
# Render mantiene estos directorios entre reinicios
PERSISTENT_DIRS = [
    '/var/data',  # Directorio persistente en Render
    '/opt/render/project/.render',  # Directorio de configuración de Render
    os.path.expanduser('~'),  # Directorio home del usuario
    os.getcwd(),  # Directorio actual
]

def find_persistent_dir():
    """Encuentra un directorio persistente donde guardar los datos."""
    for dir_path in PERSISTENT_DIRS:
        try:
            if os.path.exists(dir_path):
                test_file = os.path.join(dir_path, 'test_persistence.txt')
                with open(test_file, 'w') as f:
                    f.write(f"Test {datetime.now()}")
                
                # Verificar que se puede leer el archivo
                if os.path.exists(test_file):
                    with open(test_file, 'r') as f:
                        content = f.read()
                    
                    if content and 'Test' in content:
                        logger.info(f"Directorio persistente encontrado: {dir_path}")
                        return dir_path
        except Exception as e:
            logger.warning(f"No se puede usar {dir_path} como directorio persistente: {e}")
    
    # Si no se encuentra ningún directorio persistente, usar el directorio actual
    logger.warning("No se encontró ningún directorio persistente, usando directorio actual")
    return os.getcwd()

def find_database():
    """Busca la base de datos en varias ubicaciones posibles."""
    possible_paths = [
        './agencia.db',
        '/opt/render/project/src/agencia.db',
        '/var/data/agencia.db',
        os.path.join(os.getcwd(), 'agencia.db'),
        os.path.join(os.path.dirname(os.getcwd()), 'agencia.db')
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"Base de datos encontrada en: {path}")
            return path
    
    # Buscar recursivamente en el directorio actual
    for root, dirs, files in os.walk('.'):
        if 'agencia.db' in files:
            path = os.path.join(root, 'agencia.db')
            logger.info(f"Base de datos encontrada en: {path}")
            return path
    
    logger.error("No se pudo encontrar la base de datos")
    return None

def backup_users_to_file():
    """Guarda los usuarios de la base de datos en un archivo JSON persistente."""
    try:
        # Encontrar la base de datos
        db_path = find_database()
        if not db_path:
            logger.error("No se pudo encontrar la base de datos, abortando backup")
            return False
        
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si hay usuarios
        cursor.execute("SELECT COUNT(*) FROM usuario")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            logger.warning("No hay usuarios en la base de datos para hacer backup")
            conn.close()
            return False
        
        # Obtener todos los usuarios
        cursor.execute("""
        SELECT id, username, password, nombre, apellido, email, rol, porcentaje_comision
        FROM usuario
        """)
        users = cursor.fetchall()
        
        # Convertir a formato JSON
        users_data = []
        for user in users:
            users_data.append({
                'id': user[0],
                'username': user[1],
                'password': user[2],
                'nombre': user[3],
                'apellido': user[4],
                'email': user[5],
                'rol': user[6],
                'porcentaje_comision': user[7]
            })
        
        # Encontrar un directorio persistente
        persistent_dir = find_persistent_dir()
        
        # Crear directorio de backups si no existe
        backup_dir = os.path.join(persistent_dir, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Guardar en archivo JSON
        backup_file = os.path.join(backup_dir, 'usuarios_backup.json')
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        
        # Guardar también en un archivo con timestamp para tener un historial
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        history_file = os.path.join(backup_dir, f'usuarios_backup_{timestamp}.json')
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Backup de {len(users_data)} usuarios guardado en {backup_file}")
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"Error al hacer backup de usuarios: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def restore_users_from_file():
    """Restaura los usuarios desde el archivo JSON persistente a la base de datos."""
    try:
        # Encontrar un directorio persistente
        persistent_dir = find_persistent_dir()
        
        # Verificar si existe el archivo de backup
        backup_file = os.path.join(persistent_dir, 'backups', 'usuarios_backup.json')
        if not os.path.exists(backup_file):
            logger.warning(f"No se encontró archivo de backup en {backup_file}")
            return False
        
        # Leer el archivo JSON
        with open(backup_file, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        
        if not users_data:
            logger.warning("El archivo de backup está vacío")
            return False
        
        # Encontrar la base de datos
        db_path = find_database()
        if not db_path:
            logger.error("No se pudo encontrar la base de datos, abortando restauración")
            return False
        
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si hay usuarios en la base de datos
        cursor.execute("SELECT COUNT(*) FROM usuario")
        user_count = cursor.fetchone()[0]
        
        if user_count > 0:
            logger.info(f"Ya hay {user_count} usuarios en la base de datos, no es necesario restaurar")
            conn.close()
            return True
        
        # Restaurar usuarios
        for user in users_data:
            cursor.execute("""
            INSERT OR IGNORE INTO usuario 
            (username, password, nombre, apellido, email, rol, porcentaje_comision)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user['username'],
                user['password'],
                user['nombre'],
                user['apellido'],
                user['email'],
                user['rol'],
                user['porcentaje_comision']
            ))
        
        conn.commit()
        
        # Verificar que se restauraron correctamente
        cursor.execute("SELECT COUNT(*) FROM usuario")
        new_count = cursor.fetchone()[0]
        
        logger.info(f"Se restauraron {new_count} usuarios desde el archivo de backup")
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"Error al restaurar usuarios: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def ensure_admin_exists():
    """Asegura que el usuario administrador existe."""
    try:
        # Encontrar la base de datos
        db_path = find_database()
        if not db_path:
            logger.error("No se pudo encontrar la base de datos, abortando")
            return False
        
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si el usuario admin existe
        cursor.execute("SELECT id FROM usuario WHERE username = 'admin'")
        admin_user = cursor.fetchone()
        
        if not admin_user:
            logger.warning("Usuario admin no encontrado, creando...")
            cursor.execute("""
            INSERT INTO usuario (username, password, nombre, apellido, email, rol, porcentaje_comision)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ('admin', 'macarena1', 'Administrador', 'Sistema', 'admin@fgdmotors.com', 'administrador_jefe', 0.0))
            conn.commit()
            logger.info("Usuario admin creado exitosamente")
        else:
            logger.info("Usuario admin existe")
        
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"Error al verificar/crear usuario admin: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Función principal."""
    try:
        logger.info("Iniciando sistema de almacenamiento persistente...")
        
        # Primero intentar restaurar usuarios desde el archivo persistente
        restore_success = restore_users_from_file()
        
        # Asegurar que el admin existe
        admin_success = ensure_admin_exists()
        
        # Hacer backup de los usuarios actuales
        backup_success = backup_users_to_file()
        
        if restore_success and admin_success and backup_success:
            logger.info("Sistema de almacenamiento persistente ejecutado exitosamente")
            return True
        else:
            logger.warning("Sistema de almacenamiento persistente completado con advertencias")
            return False
    
    except Exception as e:
        logger.error(f"Error en el sistema de almacenamiento persistente: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Esperar un poco para asegurarse de que la base de datos está lista
    time.sleep(2)
    main()
