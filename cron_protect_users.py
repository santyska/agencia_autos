#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para ser ejecutado como cron job en Render
Este script verifica y restaura los usuarios si han sido eliminados
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
        logging.FileHandler("cron_protection.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CronProtection")

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

def check_and_restore_users():
    """Verifica y restaura los usuarios si es necesario."""
    try:
        logger.info("Iniciando verificación de usuarios...")
        
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
        
        # Verificar si existe la tabla de respaldo
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario_backup'")
        if not cursor.fetchone():
            logger.warning("No existe tabla de respaldo, creando...")
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
            conn.commit()
        
        # Contar usuarios actuales
        cursor.execute("SELECT COUNT(*) FROM usuario")
        user_count = cursor.fetchone()[0]
        logger.info(f"Usuarios actuales en la base de datos: {user_count}")
        
        # Si no hay usuarios, restaurar desde el respaldo
        if user_count == 0:
            logger.warning("No hay usuarios en la base de datos, restaurando desde respaldo...")
            cursor.execute("SELECT username, password, nombre, apellido, email, rol, porcentaje_comision FROM usuario_backup")
            backup_users = cursor.fetchall()
            
            if backup_users:
                for user in backup_users:
                    logger.info(f"Restaurando usuario: {user[0]}")
                    cursor.execute("""
                    INSERT INTO usuario (username, password, nombre, apellido, email, rol, porcentaje_comision)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, user)
                conn.commit()
                logger.info(f"Se restauraron {len(backup_users)} usuarios")
            else:
                logger.warning("No hay usuarios en el respaldo, creando usuario admin por defecto...")
                cursor.execute("""
                INSERT INTO usuario (username, password, nombre, apellido, email, rol, porcentaje_comision)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, ('admin', 'macarena1', 'Administrador', 'Sistema', 'admin@fgdmotors.com', 'administrador_jefe', 0.0))
                conn.commit()
                logger.info("Usuario admin creado exitosamente")
        else:
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
            
            # Hacer respaldo de usuarios actuales
            logger.info("Actualizando respaldo de usuarios...")
            cursor.execute("SELECT id, username, password, nombre, apellido, email, rol, porcentaje_comision FROM usuario")
            users = cursor.fetchall()
            
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
            logger.info(f"Respaldo de {len(users)} usuarios actualizado")
        
        # Cerrar conexión
        conn.close()
        logger.info("Verificación de usuarios completada exitosamente")
        
    except Exception as e:
        logger.error(f"Error durante la verificación: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # Primero ejecutar el script de corrección de base de datos
    try:
        logger.info("Ejecutando script de corrección de base de datos...")
        import fix_database
        fix_database.main()
        logger.info("Script de corrección de base de datos ejecutado exitosamente")
    except Exception as e:
        logger.error(f"Error al ejecutar el script de corrección de base de datos: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Luego ejecutar la verificación y restauración de usuarios
    check_and_restore_users()
