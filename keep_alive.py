#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para mantener viva la instancia de Render y verificar usuarios periódicamente
Este script se ejecuta como un proceso en segundo plano
"""

import os
import time
import sqlite3
import logging
import sys
import json
import requests
from datetime import datetime
import traceback

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("keep_alive.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("KeepAlive")

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

def find_persistent_dir():
    """Encuentra un directorio persistente donde guardar los datos."""
    persistent_dirs = [
        '/var/data',  # Directorio persistente en Render
        '/opt/render/project/.render',  # Directorio de configuración de Render
        os.path.expanduser('~'),  # Directorio home del usuario
        os.getcwd(),  # Directorio actual
    ]
    
    for dir_path in persistent_dirs:
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

def check_users():
    """Verifica que existan usuarios en la base de datos y los restaura si es necesario."""
    try:
        # Encontrar la base de datos
        db_path = find_database()
        if not db_path:
            logger.error("No se pudo encontrar la base de datos")
            return False
        
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si hay usuarios
        cursor.execute("SELECT COUNT(*) FROM usuario")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            logger.warning("No hay usuarios en la base de datos, intentando restaurar...")
            
            # Intentar restaurar desde la tabla persistente si existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='persistent_users'")
            if cursor.fetchone():
                logger.info("Restaurando desde tabla persistent_users...")
                cursor.execute("""
                INSERT OR IGNORE INTO usuario (username, password, nombre, apellido, email, rol, porcentaje_comision)
                SELECT username, password, nombre, apellido, email, rol, porcentaje_comision
                FROM persistent_users
                """)
                conn.commit()
            
            # Verificar si se restauraron usuarios
            cursor.execute("SELECT COUNT(*) FROM usuario")
            new_count = cursor.fetchone()[0]
            
            if new_count == 0:
                # Intentar restaurar desde archivo JSON
                persistent_dir = find_persistent_dir()
                backup_file = os.path.join(persistent_dir, 'backups', 'usuarios_backup.json')
                
                if os.path.exists(backup_file):
                    logger.info(f"Restaurando desde archivo {backup_file}...")
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        users_data = json.load(f)
                    
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
                
                # Verificar si ahora hay usuarios
                cursor.execute("SELECT COUNT(*) FROM usuario")
                final_count = cursor.fetchone()[0]
                
                if final_count == 0:
                    # Crear al menos el usuario admin
                    logger.warning("No se pudieron restaurar usuarios, creando admin por defecto...")
                    cursor.execute("""
                    INSERT INTO usuario (username, password, nombre, apellido, email, rol, porcentaje_comision)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, ('admin', 'macarena1', 'Administrador', 'Sistema', 'admin@fgdmotors.com', 'administrador_jefe', 0.0))
                    conn.commit()
                    logger.info("Usuario admin creado exitosamente")
                else:
                    logger.info(f"Se restauraron {final_count} usuarios desde el archivo JSON")
            else:
                logger.info(f"Se restauraron {new_count} usuarios desde la tabla persistent_users")
        else:
            logger.info(f"Hay {user_count} usuarios en la base de datos")
            
            # Hacer backup de los usuarios actuales a la tabla persistente
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='persistent_users'")
            if cursor.fetchone():
                cursor.execute("""
                INSERT OR REPLACE INTO persistent_users (username, password, nombre, apellido, email, rol, porcentaje_comision, fecha_backup)
                SELECT username, password, nombre, apellido, email, rol, porcentaje_comision, datetime('now')
                FROM usuario
                """)
                conn.commit()
                logger.info("Backup de usuarios actualizado en tabla persistent_users")
            
            # Hacer backup a archivo JSON
            persistent_dir = find_persistent_dir()
            backup_dir = os.path.join(persistent_dir, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            cursor.execute("""
            SELECT id, username, password, nombre, apellido, email, rol, porcentaje_comision
            FROM usuario
            """)
            users = cursor.fetchall()
            
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
            
            backup_file = os.path.join(backup_dir, 'usuarios_backup.json')
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Backup de {len(users_data)} usuarios guardado en {backup_file}")
        
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"Error al verificar/restaurar usuarios: {e}")
        logger.error(traceback.format_exc())
        return False

def keep_alive():
    """Mantiene viva la instancia de Render haciendo ping al servidor."""
    try:
        # Obtener la URL del servidor
        hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
        if not hostname:
            logger.warning("No se pudo obtener el hostname de Render, usando localhost")
            hostname = 'localhost:5000'
        
        url = f"https://{hostname}"
        if 'localhost' in hostname:
            url = f"http://{hostname}"
        
        # Hacer ping al servidor
        logger.info(f"Haciendo ping a {url}...")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Ping exitoso: {response.status_code}")
            return True
        else:
            logger.warning(f"Ping fallido: {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"Error al hacer ping al servidor: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Función principal."""
    logger.info("Iniciando script keep_alive...")
    
    # Intervalo entre verificaciones (en segundos)
    check_interval = 300  # 5 minutos
    ping_interval = 600   # 10 minutos
    
    last_check_time = 0
    last_ping_time = 0
    
    try:
        while True:
            current_time = time.time()
            
            # Verificar usuarios periódicamente
            if current_time - last_check_time >= check_interval:
                logger.info("Ejecutando verificación de usuarios...")
                check_users()
                last_check_time = current_time
            
            # Mantener viva la instancia periódicamente
            if current_time - last_ping_time >= ping_interval:
                logger.info("Ejecutando keep-alive...")
                keep_alive()
                last_ping_time = current_time
            
            # Esperar un poco antes de la siguiente iteración
            time.sleep(60)  # Esperar 1 minuto
    
    except KeyboardInterrupt:
        logger.info("Script keep_alive detenido manualmente")
    except Exception as e:
        logger.error(f"Error en el script keep_alive: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
