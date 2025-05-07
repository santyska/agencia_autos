#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de protección de usuarios
Este script verifica que los usuarios existentes no sean eliminados
y los restaura si es necesario.
"""

import os
import sqlite3
import sys
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("user_protection.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ProtectUsers")

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

def backup_users(conn):
    """Crea una copia de seguridad de los usuarios actuales."""
    cursor = conn.cursor()
    
    # Verificar si existe la tabla de respaldo
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario_backup'")
    if not cursor.fetchone():
        logger.info("Creando tabla de respaldo de usuarios...")
        cursor.execute("""
        CREATE TABLE usuario_backup (
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
    
    # Obtener usuarios actuales
    cursor.execute("SELECT id, username, password, nombre, apellido, email, rol, porcentaje_comision FROM usuario")
    users = cursor.fetchall()
    
    # Guardar en la tabla de respaldo
    for user in users:
        # Verificar si ya existe un respaldo para este usuario
        cursor.execute("SELECT id FROM usuario_backup WHERE username = ?", (user[1],))
        existing_backup = cursor.fetchone()
        
        if existing_backup:
            # Actualizar respaldo existente
            cursor.execute("""
            UPDATE usuario_backup 
            SET password = ?, nombre = ?, apellido = ?, email = ?, rol = ?, porcentaje_comision = ?, fecha_backup = ?
            WHERE username = ?
            """, (user[2], user[3], user[4], user[5], user[6], user[7], datetime.now().isoformat(), user[1]))
        else:
            # Crear nuevo respaldo
            cursor.execute("""
            INSERT INTO usuario_backup (username, password, nombre, apellido, email, rol, porcentaje_comision, fecha_backup)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user[1], user[2], user[3], user[4], user[5], user[6], user[7], datetime.now().isoformat()))
    
    conn.commit()
    logger.info(f"Respaldo de {len(users)} usuarios completado")
    return users

def restore_users_if_needed(conn):
    """Restaura usuarios si han sido eliminados."""
    cursor = conn.cursor()
    
    # Verificar si existe la tabla de respaldo
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario_backup'")
    if not cursor.fetchone():
        logger.warning("No existe tabla de respaldo, no se pueden restaurar usuarios")
        return
    
    # Obtener usuarios de respaldo
    cursor.execute("SELECT username, password, nombre, apellido, email, rol, porcentaje_comision FROM usuario_backup")
    backup_users = cursor.fetchall()
    
    if not backup_users:
        logger.warning("No hay usuarios en la tabla de respaldo")
        return
    
    # Obtener usuarios actuales
    cursor.execute("SELECT username FROM usuario")
    current_users = [row[0] for row in cursor.fetchall()]
    
    # Restaurar usuarios faltantes
    restored_count = 0
    for user in backup_users:
        username = user[0]
        if username not in current_users:
            logger.warning(f"Usuario {username} no encontrado en la base de datos actual, restaurando...")
            cursor.execute("""
            INSERT INTO usuario (username, password, nombre, apellido, email, rol, porcentaje_comision)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, user)
            restored_count += 1
    
    if restored_count > 0:
        conn.commit()
        logger.info(f"Se restauraron {restored_count} usuarios")
    else:
        logger.info("No fue necesario restaurar ningún usuario")

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
    else:
        logger.info("Usuario admin existe, verificando rol...")
        # Asegurar que el rol sea administrador_jefe
        cursor.execute("UPDATE usuario SET rol = 'administrador_jefe' WHERE username = 'admin'")
        conn.commit()
        logger.info("Rol de admin actualizado a administrador_jefe")

def main():
    """Función principal."""
    try:
        logger.info("Iniciando script de protección de usuarios...")
        
        # Buscar la base de datos
        db_path = find_database()
        if not db_path:
            logger.error("No se pudo encontrar la base de datos, abortando")
            return
        
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
        
        # Hacer respaldo de usuarios actuales
        backup_users(conn)
        
        # Restaurar usuarios si es necesario
        restore_users_if_needed(conn)
        
        # Asegurar que el admin existe
        ensure_admin_exists(conn)
        
        # Cerrar conexión
        conn.close()
        logger.info("Script de protección de usuarios completado exitosamente")
        
    except Exception as e:
        logger.error(f"Error durante la ejecución: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
