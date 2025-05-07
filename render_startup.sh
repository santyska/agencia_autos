#!/usr/bin/env bash
# Script de inicio para Render
# Este script se ejecuta automáticamente al iniciar el servidor en Render

echo "=== SISTEMA DE PERSISTENCIA DE DATOS PARA RENDER ==="

# Esperar a que el sistema de archivos esté completamente disponible
sleep 5

# Crear directorios persistentes necesarios
mkdir -p /var/data/database
mkdir -p /var/data/backups

# Registrar información del entorno
echo "Información del entorno:"
echo "Directorio actual: $(pwd)"
echo "Contenido del directorio: $(ls -la)"
echo "Contenido de /var/data: $(ls -la /var/data)"

# Configurar la base de datos persistente
echo "Configurando base de datos persistente..."
python setup_persistent_db.py

# Ejecutar scripts de protección
echo "Iniciando script de corrección de base de datos..."
python fix_database.py

echo "Iniciando script de protección de usuarios..."
python protect_users.py

# Asegurarse de que los scripts tienen permisos de ejecución
chmod +x setup_persistent_db.py
chmod +x fix_database.py
chmod +x protect_users.py

# Sincronizar la base de datos
echo "Sincronizando base de datos..."
if [ -f "/var/data/database/sync_db.sh" ]; then
    bash /var/data/database/sync_db.sh
fi

# Crear un archivo de marca para saber cuándo se reinició el servidor
echo "Servidor reiniciado el $(date)" > /var/data/last_restart.txt

echo "=== SISTEMA DE PERSISTENCIA DE DATOS COMPLETADO ==="

# Continuar con el comando de inicio normal
exec "$@"
