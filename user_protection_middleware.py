#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Middleware de protección de usuarios
Este módulo proporciona un middleware para Flask que verifica
periódicamente la existencia de usuarios y los restaura si es necesario.
"""

import sqlite3
import os
import logging
import threading
import time
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("middleware_protection.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("UserProtectionMiddleware")

class UserProtectionMiddleware:
    """Middleware para proteger usuarios en una aplicación Flask."""
    
    def __init__(self, app, db_path=None, check_interval=900):
        """
        Inicializa el middleware.
        
        Args:
            app: La aplicación Flask
            db_path: Ruta a la base de datos SQLite (si es None, se buscará automáticamente)
            check_interval: Intervalo de verificación en segundos (por defecto 15 minutos)
        """
        self.app = app
        self.db_path = db_path
        self.check_interval = check_interval
        self.protection_thread = None
        self.stop_event = threading.Event()
        
        # Iniciar el thread de protección
        self.start_protection_thread()
        
        # Registrar función de cierre para detener el thread cuando la aplicación se detenga
        if hasattr(app, 'teardown_appcontext'):
            app.teardown_appcontext(self.teardown)
    
    def start_protection_thread(self):
        """Inicia el thread de protección."""
        self.protection_thread = threading.Thread(
            target=self.protection_worker,
            daemon=True
        )
        self.protection_thread.start()
        logger.info("Thread de protección de usuarios iniciado")
    
    def protection_worker(self):
        """Función principal del thread de protección."""
        while not self.stop_event.is_set():
            try:
                self.check_and_protect_users()
            except Exception as e:
                logger.error(f"Error en el thread de protección: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            # Esperar hasta el próximo intervalo o hasta que se solicite detener
            self.stop_event.wait(self.check_interval)
    
    def teardown(self, exception):
        """Detiene el thread de protección cuando la aplicación se cierra."""
        self.stop_event.set()
        if self.protection_thread and self.protection_thread.is_alive():
            self.protection_thread.join(timeout=5)
            logger.info("Thread de protección de usuarios detenido")
    
    def find_database(self):
        """Busca la base de datos si no se especificó una ruta."""
        if self.db_path and os.path.exists(self.db_path):
            return self.db_path
        
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
                self.db_path = path
                return path
        
        # Buscar recursivamente en el directorio actual
        for root, dirs, files in os.walk('.'):
            if 'agencia.db' in files:
                path = os.path.join(root, 'agencia.db')
                logger.info(f"Base de datos encontrada en: {path}")
                self.db_path = path
                return path
        
        logger.error("No se pudo encontrar la base de datos")
        return None
    
    def check_and_protect_users(self):
        """Verifica y restaura los usuarios si es necesario."""
        logger.info("Verificando usuarios desde el middleware...")
        
        # Buscar la base de datos
        db_path = self.find_database()
        if not db_path:
            logger.error("No se pudo encontrar la base de datos, abortando verificación")
            return
        
        try:
            # Conectar a la base de datos
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Verificar si la tabla usuario existe
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
