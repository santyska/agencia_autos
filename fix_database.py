#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para solucionar definitivamente el problema de eliminación de usuarios
Este script modifica la estructura de la base de datos para proteger a los usuarios
"""

import os
import sqlite3
import logging
import sys
import shutil
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fix_database.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FixDatabase")

def find_database():
    """Busca la base de datos en varias ubicaciones posibles."""
    possible_paths = [
        '/var/data/database/agencia.db',  # Ubicación persistente en Render
        './agencia.db',                   # Directorio actual
        '/var/data/agencia.db',           # Directorio persistente en Render (ruta antigua)
        '/opt/render/project/src/agencia.db',  # Ruta de proyecto en Render
        os.path.join(os.getcwd(), 'agencia.db'),
        os.path.join(os.path.dirname(os.getcwd()), 'agencia.db')
    ]
    
    logger.info(f"Buscando base de datos en las siguientes ubicaciones: {possible_paths}")
    
    # Verificar todas las ubicaciones posibles
    for path in possible_paths:
        if os.path.exists(path):
            try:
                # Verificar que el archivo sea una base de datos SQLite válida
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                conn.close()
                
                if result and result[0] == 'ok':
                    file_size = os.path.getsize(path)
                    logger.info(f"Base de datos válida encontrada en: {path} (Tamaño: {file_size} bytes)")
                    return path
                else:
                    logger.warning(f"Archivo encontrado en {path} pero no es una base de datos SQLite válida")
            except Exception as e:
                logger.warning(f"Error al verificar la base de datos en {path}: {e}")
    
    # Buscar recursivamente en el directorio actual
    logger.info("Buscando base de datos recursivamente en el directorio actual...")
    for root, dirs, files in os.walk('.'):
        if 'agencia.db' in files:
            path = os.path.join(root, 'agencia.db')
            try:
                # Verificar que el archivo sea una base de datos SQLite válida
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                conn.close()
                
                if result and result[0] == 'ok':
                    file_size = os.path.getsize(path)
                    logger.info(f"Base de datos válida encontrada en: {path} (Tamaño: {file_size} bytes)")
                    return path
            except Exception as e:
                logger.warning(f"Error al verificar la base de datos en {path}: {e}")
    
    # Si no se encuentra ninguna base de datos válida, intentar crear una nueva en la ubicación persistente
    persistent_path = '/var/data/database/agencia.db'
    try:
        if os.path.exists('/var/data/database'):
            logger.warning("No se encontró ninguna base de datos válida, creando una nueva en ubicación persistente")
            conn = sqlite3.connect(persistent_path)
            conn.close()
            return persistent_path
    except Exception as e:
        logger.error(f"Error al crear nueva base de datos: {e}")
    
    logger.error("No se pudo encontrar ni crear la base de datos")
    return None

def backup_database(db_path):
    """Crea una copia de seguridad de la base de datos."""
    backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'agencia_backup_{timestamp}.db')
    
    try:
        shutil.copy2(db_path, backup_path)
        logger.info(f"Copia de seguridad creada en: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Error al crear copia de seguridad: {e}")
        return None

def create_persistent_users_table(conn):
    """Crea una tabla de usuarios persistente que no será eliminada."""
    cursor = conn.cursor()
    
    # Verificar si la tabla ya existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='persistent_users'")
    if cursor.fetchone():
        logger.info("La tabla persistent_users ya existe")
        return
    
    # Crear la tabla
    logger.info("Creando tabla persistent_users...")
    cursor.execute("""
    CREATE TABLE persistent_users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        nombre TEXT,
        apellido TEXT,
        email TEXT,
        rol TEXT,
        porcentaje_comision REAL,
        fecha_backup TEXT
    )
    """)
    conn.commit()
    logger.info("Tabla persistent_users creada exitosamente")

def backup_users_to_persistent(conn):
    """Copia los usuarios actuales a la tabla persistente."""
    cursor = conn.cursor()
    
    # Verificar si hay usuarios en la tabla usuario
    cursor.execute("SELECT COUNT(*) FROM usuario")
    user_count = cursor.fetchone()[0]
    
    if user_count == 0:
        logger.warning("No hay usuarios en la tabla usuario")
        
        # Verificar si hay usuarios en la tabla persistente
        cursor.execute("SELECT COUNT(*) FROM persistent_users")
        persistent_count = cursor.fetchone()[0]
        
        if persistent_count > 0:
            logger.info(f"Restaurando {persistent_count} usuarios desde la tabla persistente...")
            
            # Restaurar usuarios desde la tabla persistente
            cursor.execute("""
            INSERT OR IGNORE INTO usuario (username, password, nombre, apellido, email, rol, porcentaje_comision)
            SELECT username, password, nombre, apellido, email, rol, porcentaje_comision
            FROM persistent_users
            """)
            conn.commit()
            
            # Verificar que se restauraron correctamente
            cursor.execute("SELECT COUNT(*) FROM usuario")
            new_count = cursor.fetchone()[0]
            logger.info(f"Se restauraron {new_count} usuarios")
            
            return
    
    # Copiar usuarios a la tabla persistente
    logger.info(f"Copiando {user_count} usuarios a la tabla persistente...")
    cursor.execute("""
    INSERT OR REPLACE INTO persistent_users (username, password, nombre, apellido, email, rol, porcentaje_comision, fecha_backup)
    SELECT username, password, nombre, apellido, email, rol, porcentaje_comision, datetime('now')
    FROM usuario
    """)
    conn.commit()
    
    # Verificar que se copiaron correctamente
    cursor.execute("SELECT COUNT(*) FROM persistent_users")
    persistent_count = cursor.fetchone()[0]
    logger.info(f"Se copiaron {persistent_count} usuarios a la tabla persistente")

def create_trigger_to_protect_users(conn):
    """Crea un trigger en la base de datos para restaurar usuarios automáticamente."""
    cursor = conn.cursor()
    
    # Eliminar trigger existente si existe
    cursor.execute("DROP TRIGGER IF EXISTS restore_users_trigger")
    
    # Crear trigger para restaurar usuarios cuando se eliminen todos
    logger.info("Creando trigger para restaurar usuarios automáticamente...")
    cursor.execute("""
    CREATE TRIGGER restore_users_trigger
    AFTER DELETE ON usuario
    WHEN (SELECT COUNT(*) FROM usuario) = 0
    BEGIN
        INSERT OR IGNORE INTO usuario (username, password, nombre, apellido, email, rol, porcentaje_comision)
        SELECT username, password, nombre, apellido, email, rol, porcentaje_comision
        FROM persistent_users;
    END;
    """)
    conn.commit()
    logger.info("Trigger creado exitosamente")

def ensure_admin_exists(conn):
    """Asegura que el usuario administrador existe."""
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
        
        # Asegurarse de que también está en la tabla persistente
        cursor.execute("""
        INSERT OR REPLACE INTO persistent_users (username, password, nombre, apellido, email, rol, porcentaje_comision, fecha_backup)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, ('admin', 'macarena1', 'Administrador', 'Sistema', 'admin@fgdmotors.com', 'administrador_jefe', 0.0))
        conn.commit()
    else:
        logger.info("Usuario admin existe, verificando rol...")
        # Asegurar que el rol sea administrador_jefe
        cursor.execute("UPDATE usuario SET rol = 'administrador_jefe' WHERE username = 'admin'")
        conn.commit()
        logger.info("Rol de admin actualizado a administrador_jefe")
        
        # Actualizar también en la tabla persistente
        cursor.execute("UPDATE persistent_users SET rol = 'administrador_jefe' WHERE username = 'admin'")
        conn.commit()

def main():
    """Función principal."""
    try:
        logger.info("Iniciando script de corrección de base de datos...")
        
        # Buscar la base de datos
        db_path = find_database()
        if not db_path:
            logger.error("No se pudo encontrar la base de datos, abortando")
            return
        
        # Crear copia de seguridad
        backup_path = backup_database(db_path)
        if not backup_path:
            logger.warning("No se pudo crear copia de seguridad, continuando con precaución")
        
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        logger.info("Conexión a la base de datos establecida")
        
        # Verificar si la tabla usuario existe
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario'")
        if not cursor.fetchone():
            logger.error("La tabla 'usuario' no existe en la base de datos")
            conn.close()
            return
        
        # Crear tabla de usuarios persistente
        create_persistent_users_table(conn)
        
        # Copiar usuarios a la tabla persistente
        backup_users_to_persistent(conn)
        
        # Crear trigger para proteger usuarios
        create_trigger_to_protect_users(conn)
        
        # Asegurar que el admin existe
        ensure_admin_exists(conn)
        
        # Cerrar conexión
        conn.close()
        logger.info("Script de corrección de base de datos completado exitosamente")
        
    except Exception as e:
        logger.error(f"Error durante la ejecución: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
