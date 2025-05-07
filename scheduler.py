#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scheduler para protección de usuarios
Este script ejecuta periódicamente la protección de usuarios
para evitar que sean eliminados.
"""

import time
import subprocess
import logging
import os
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("UserProtectionScheduler")

def run_protection_script():
    """Ejecuta el script de protección de usuarios."""
    logger.info("Ejecutando script de protección de usuarios...")
    try:
        result = subprocess.run(
            ["python", "protect_users.py"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Script ejecutado exitosamente: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error al ejecutar el script: {e}")
        logger.error(f"Salida de error: {e.stderr}")
    except Exception as e:
        logger.error(f"Error inesperado: {e}")

def main():
    """Función principal del scheduler."""
    logger.info("Iniciando scheduler de protección de usuarios...")
    
    # Ejecutar inmediatamente al inicio
    run_protection_script()
    
    # Intervalo en segundos (cada 30 minutos)
    interval = 30 * 60
    
    try:
        while True:
            # Esperar hasta el próximo intervalo
            next_run = datetime.now()
            logger.info(f"Próxima ejecución programada para: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(interval)
            
            # Ejecutar el script de protección
            run_protection_script()
    except KeyboardInterrupt:
        logger.info("Scheduler detenido por el usuario")
    except Exception as e:
        logger.error(f"Error en el scheduler: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
