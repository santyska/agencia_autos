import os
import threading
import logging
from app_final import app

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("wsgi.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("WSGI")

def run_scheduler():
    """Ejecuta el scheduler de protección de usuarios en un hilo separado."""
    try:
        logger.info("Iniciando scheduler de protección de usuarios...")
        import scheduler
        scheduler.main()
    except Exception as e:
        logger.error(f"Error al ejecutar el scheduler: {e}")
        import traceback
        logger.error(traceback.format_exc())

# Función para ejecutar el script keep_alive en un hilo separado
def run_keep_alive():
    """Ejecuta el script keep_alive en un hilo separado."""
    try:
        logger.info("Iniciando script keep_alive...")
        import keep_alive
        keep_alive.main()
    except Exception as e:
        logger.error(f"Error al ejecutar el script keep_alive: {e}")
        import traceback
        logger.error(traceback.format_exc())

# Iniciar el scheduler en un hilo separado
try:
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Scheduler iniciado en un hilo separado")
except Exception as e:
    logger.error(f"Error al iniciar el hilo del scheduler: {e}")

# Iniciar el script keep_alive en un hilo separado
try:
    keep_alive_thread = threading.Thread(target=run_keep_alive, daemon=True)
    keep_alive_thread.start()
    logger.info("Script keep_alive iniciado en un hilo separado")
except Exception as e:
    logger.error(f"Error al iniciar el hilo del script keep_alive: {e}")

if __name__ == "__main__":
    # Ejecutar el script de almacenamiento persistente antes de iniciar la aplicación
    try:
        logger.info("Ejecutando sistema de almacenamiento persistente...")
        import persistent_storage
        persistent_storage.main()
        logger.info("Sistema de almacenamiento persistente ejecutado exitosamente")
    except Exception as e:
        logger.error(f"Error al ejecutar el sistema de almacenamiento persistente: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Ejecutar el script de corrección de base de datos antes de iniciar la aplicación
    try:
        logger.info("Ejecutando script de corrección de base de datos...")
        import fix_database
        fix_database.main()
        logger.info("Script de corrección de base de datos ejecutado exitosamente")
    except Exception as e:
        logger.error(f"Error al ejecutar el script de corrección de base de datos: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Ejecutar el script de protección de usuarios antes de iniciar la aplicación
    try:
        logger.info("Ejecutando script de protección de usuarios...")
        import protect_users
        protect_users.main()
        logger.info("Script de protección de usuarios ejecutado exitosamente")
    except Exception as e:
        logger.error(f"Error al ejecutar el script de protección de usuarios: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Iniciar la aplicación
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
