#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para configurar una base de datos persistente en Render
Este script mueve la base de datos a un directorio persistente y crea un enlace simbólico
"""

import os
import sys
import shutil
import sqlite3
import logging
import time
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("persistent_db.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PersistentDB")

# Definir las rutas
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DB_PATH = os.path.join(CURRENT_DIR, 'agencia.db')
PERSISTENT_DIRS = [
    '/var/data',  # Directorio persistente en Render
    '/opt/render/project/.render',  # Directorio de configuración de Render
    os.path.expanduser('~/persistent_data'),  # Directorio en el home del usuario
    os.path.join(CURRENT_DIR, 'persistent_data')  # Directorio en la carpeta actual
]

def find_or_create_persistent_dir():
    """Encuentra o crea un directorio persistente para almacenar la base de datos."""
    for dir_path in PERSISTENT_DIRS:
        try:
            # Intentar crear el directorio si no existe
            os.makedirs(dir_path, exist_ok=True)
            
            # Verificar si podemos escribir en el directorio
            test_file = os.path.join(dir_path, f'test_{int(time.time())}.txt')
            with open(test_file, 'w') as f:
                f.write(f"Test {datetime.now()}")
            
            # Verificar que podemos leer el archivo
            if os.path.exists(test_file):
                with open(test_file, 'r') as f:
                    content = f.read()
                
                if 'Test' in content:
                    # Limpiar el archivo de prueba
                    os.remove(test_file)
                    
                    # Crear subdirectorio para la base de datos
                    db_dir = os.path.join(dir_path, 'database')
                    os.makedirs(db_dir, exist_ok=True)
                    
                    logger.info(f"Directorio persistente encontrado y verificado: {db_dir}")
                    return db_dir
        except Exception as e:
            logger.warning(f"No se puede usar {dir_path} como directorio persistente: {e}")
    
    # Si no se encuentra ningún directorio persistente, crear uno en el directorio actual
    fallback_dir = os.path.join(CURRENT_DIR, 'persistent_data', 'database')
    os.makedirs(fallback_dir, exist_ok=True)
    logger.warning(f"No se encontró ningún directorio persistente, usando: {fallback_dir}")
    return fallback_dir

def find_existing_db():
    """Busca la base de datos en todas las ubicaciones posibles."""
    # Primero buscar en la ubicación por defecto
    if os.path.exists(DEFAULT_DB_PATH):
        logger.info(f"Base de datos encontrada en la ubicación por defecto: {DEFAULT_DB_PATH}")
        return DEFAULT_DB_PATH
    
    # Buscar en directorios persistentes
    for dir_path in PERSISTENT_DIRS:
        db_path = os.path.join(dir_path, 'database', 'agencia.db')
        if os.path.exists(db_path):
            logger.info(f"Base de datos encontrada en ubicación persistente: {db_path}")
            return db_path
    
    # Buscar en el directorio actual y subdirectorios
    for root, _, files in os.walk(CURRENT_DIR):
        if 'agencia.db' in files:
            db_path = os.path.join(root, 'agencia.db')
            logger.info(f"Base de datos encontrada en: {db_path}")
            return db_path
    
    logger.warning("No se encontró ninguna base de datos existente")
    return None

def setup_persistent_database():
    """Configura la base de datos en un directorio persistente."""
    try:
        # Encontrar un directorio persistente
        persistent_dir = find_or_create_persistent_dir()
        persistent_db_path = os.path.join(persistent_dir, 'agencia.db')
        
        # Buscar la base de datos existente
        existing_db = find_existing_db()
        
        # Si no se encuentra ninguna base de datos, crear una nueva en la ubicación persistente
        if not existing_db:
            logger.info(f"Creando nueva base de datos en: {persistent_db_path}")
            conn = sqlite3.connect(persistent_db_path)
            conn.close()
            
            # Crear un enlace simbólico a la ubicación por defecto
            try:
                if os.path.exists(DEFAULT_DB_PATH):
                    os.remove(DEFAULT_DB_PATH)
                
                # En Windows, necesitamos permisos de administrador para crear enlaces simbólicos
                if os.name == 'nt':
                    # En Windows, copiar en lugar de crear un enlace simbólico
                    shutil.copy2(persistent_db_path, DEFAULT_DB_PATH)
                    logger.info(f"Archivo copiado de {persistent_db_path} a {DEFAULT_DB_PATH}")
                else:
                    os.symlink(persistent_db_path, DEFAULT_DB_PATH)
                    logger.info(f"Enlace simbólico creado: {DEFAULT_DB_PATH} -> {persistent_db_path}")
                
                return persistent_db_path
            except Exception as e:
                logger.error(f"Error al crear enlace simbólico: {e}")
                return persistent_db_path
        
        # Si la base de datos ya existe en la ubicación persistente, no hacer nada
        if existing_db == persistent_db_path:
            logger.info(f"La base de datos ya está en la ubicación persistente: {persistent_db_path}")
            
            # Asegurarse de que el enlace simbólico existe
            if not os.path.exists(DEFAULT_DB_PATH) or not os.path.samefile(DEFAULT_DB_PATH, persistent_db_path):
                try:
                    if os.path.exists(DEFAULT_DB_PATH):
                        os.remove(DEFAULT_DB_PATH)
                    
                    if os.name == 'nt':
                        # En Windows, copiar en lugar de crear un enlace simbólico
                        shutil.copy2(persistent_db_path, DEFAULT_DB_PATH)
                        logger.info(f"Archivo copiado de {persistent_db_path} a {DEFAULT_DB_PATH}")
                    else:
                        os.symlink(persistent_db_path, DEFAULT_DB_PATH)
                        logger.info(f"Enlace simbólico creado: {DEFAULT_DB_PATH} -> {persistent_db_path}")
                except Exception as e:
                    logger.error(f"Error al crear enlace simbólico: {e}")
            
            return persistent_db_path
        
        # Si la base de datos existe en otra ubicación, moverla a la ubicación persistente
        logger.info(f"Moviendo base de datos de {existing_db} a {persistent_db_path}")
        
        # Hacer una copia de seguridad antes de mover
        backup_path = os.path.join(persistent_dir, f'agencia_backup_{int(time.time())}.db')
        if os.path.exists(persistent_db_path):
            shutil.copy2(persistent_db_path, backup_path)
            logger.info(f"Copia de seguridad creada en: {backup_path}")
        
        # Copiar la base de datos existente a la ubicación persistente
        shutil.copy2(existing_db, persistent_db_path)
        logger.info(f"Base de datos copiada a: {persistent_db_path}")
        
        # Crear un enlace simbólico desde la ubicación original a la persistente
        try:
            if os.path.exists(DEFAULT_DB_PATH):
                os.remove(DEFAULT_DB_PATH)
            
            if os.name == 'nt':
                # En Windows, copiar en lugar de crear un enlace simbólico
                shutil.copy2(persistent_db_path, DEFAULT_DB_PATH)
                logger.info(f"Archivo copiado de {persistent_db_path} a {DEFAULT_DB_PATH}")
            else:
                os.symlink(persistent_db_path, DEFAULT_DB_PATH)
                logger.info(f"Enlace simbólico creado: {DEFAULT_DB_PATH} -> {persistent_db_path}")
        except Exception as e:
            logger.error(f"Error al crear enlace simbólico: {e}")
        
        return persistent_db_path
    
    except Exception as e:
        logger.error(f"Error al configurar la base de datos persistente: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def verify_database(db_path):
    """Verifica que la base de datos sea válida y contenga las tablas necesarias."""
    try:
        if not os.path.exists(db_path):
            logger.error(f"La base de datos no existe en: {db_path}")
            return False
        
        # Intentar conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la tabla usuario existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario'")
        if not cursor.fetchone():
            logger.warning("La tabla 'usuario' no existe en la base de datos")
            
            # Verificar qué tablas existen
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            if tables:
                logger.info(f"Tablas existentes: {', '.join([t[0] for t in tables])}")
            else:
                logger.warning("No hay tablas en la base de datos")
            
            conn.close()
            return False
        
        # Verificar si hay usuarios
        cursor.execute("SELECT COUNT(*) FROM usuario")
        user_count = cursor.fetchone()[0]
        logger.info(f"Número de usuarios en la base de datos: {user_count}")
        
        # Verificar si existe el usuario admin
        cursor.execute("SELECT id, username, rol FROM usuario WHERE username = 'admin'")
        admin = cursor.fetchone()
        if admin:
            logger.info(f"Usuario admin encontrado: ID={admin[0]}, Rol={admin[2]}")
            
            # Asegurarse de que el usuario admin tenga el rol correcto
            if admin[2] != 'administrador_jefe':
                cursor.execute("UPDATE usuario SET rol = 'administrador_jefe' WHERE username = 'admin'")
                conn.commit()
                logger.info("Rol de admin actualizado a 'administrador_jefe'")
        else:
            logger.warning("El usuario admin no existe en la base de datos")
            
            # Crear el usuario admin si no existe
            try:
                cursor.execute(
                    "INSERT INTO usuario (username, password, nombre, apellido, email, rol, porcentaje_comision) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ('admin', 'macarena1', 'Administrador', 'Sistema', 'admin@fgdmotors.com', 'administrador_jefe', 0.0)
                )
                conn.commit()
                logger.info("Usuario admin creado correctamente")
            except Exception as e:
                logger.error(f"Error al crear el usuario admin: {e}")
                conn.rollback()
        
        # Verificar otras tablas importantes
        tables_to_check = ['auto', 'venta', 'foto_auto']
        for table in tables_to_check:
            cursor.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone()[0] == 0:
                logger.warning(f"La tabla '{table}' no existe en la base de datos")
            else:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"Tabla '{table}' encontrada con {count} registros")
        
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"Error al verificar la base de datos: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def setup_sync_mechanism(db_path, default_path):
    """Configura un mecanismo para sincronizar la base de datos entre reinicios."""
    try:
        # Crear un script que sincronice la base de datos
        sync_script_path = os.path.join(os.path.dirname(db_path), 'sync_db.sh')
        
        script_content = f"""#!/bin/bash
# Script para sincronizar la base de datos entre reinicios
# Este script se ejecuta automáticamente al iniciar y detener la aplicación

echo "Sincronizando base de datos..."
date

# Asegurarse de que el directorio persistente existe
mkdir -p {os.path.dirname(db_path)}

# Si la base de datos existe en la ubicación por defecto pero no en la persistente
if [ -f "{default_path}" ] && [ ! -f "{db_path}" ]; then
    echo "Copiando base de datos de {default_path} a {db_path}"
    cp "{default_path}" "{db_path}"
fi

# Si la base de datos existe en la ubicación persistente pero no en la por defecto
if [ -f "{db_path}" ] && [ ! -f "{default_path}" ]; then
    echo "Copiando base de datos de {db_path} a {default_path}"
    cp "{db_path}" "{default_path}"
fi

# Si ambas bases de datos existen, usar la más reciente
if [ -f "{db_path}" ] && [ -f "{default_path}" ]; then
    DEFAULT_TIME=$(stat -c %Y "{default_path}" 2>/dev/null || stat -f %m "{default_path}")
    PERSISTENT_TIME=$(stat -c %Y "{db_path}" 2>/dev/null || stat -f %m "{db_path}")
    
    if [ $DEFAULT_TIME -gt $PERSISTENT_TIME ]; then
        echo "La base de datos en {default_path} es más reciente, copiando a {db_path}"
        cp "{default_path}" "{db_path}"
    else
        echo "La base de datos en {db_path} es más reciente, copiando a {default_path}"
        cp "{db_path}" "{default_path}"
    fi
fi

echo "Sincronización completada"
date
"""
        
        # Escribir el script
        with open(sync_script_path, 'w') as f:
            f.write(script_content)
        
        # Hacer el script ejecutable
        os.chmod(sync_script_path, 0o755)
        
        logger.info(f"Script de sincronización creado en: {sync_script_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error al configurar el mecanismo de sincronización: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Función principal."""
    logger.info("Iniciando configuración de base de datos persistente...")
    
    # Configurar la base de datos persistente
    db_path = setup_persistent_database()
    if not db_path:
        logger.error("No se pudo configurar la base de datos persistente")
        return False
    
    # Verificar la base de datos
    if not verify_database(db_path):
        logger.warning("La base de datos no es válida o está incompleta")
    
    # Configurar mecanismo de sincronización
    if not setup_sync_mechanism(db_path, DEFAULT_DB_PATH):
        logger.warning("No se pudo configurar el mecanismo de sincronización")
    
    logger.info("Configuración de base de datos persistente completada")
    return True

if __name__ == "__main__":
    main()
