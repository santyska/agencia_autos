#!/usr/bin/env bash
# Script de inicio para Render
# Este script se ejecuta automáticamente al iniciar el servidor en Render

echo "=== SISTEMA DE PERSISTENCIA DE DATOS PARA RENDER ==="
echo "Fecha y hora de inicio: $(date)"

# Esperar a que el sistema de archivos esté completamente disponible
echo "Esperando a que el sistema de archivos esté disponible..."
sleep 5

# Crear directorios persistentes necesarios
echo "Creando directorios persistentes..."
mkdir -p /var/data/database
mkdir -p /var/data/backups
chmod -R 777 /var/data

# Registrar información del entorno
echo "Información del entorno:"
echo "Directorio actual: $(pwd)"
echo "Contenido del directorio: $(ls -la)"
echo "Contenido de /var/data: $(ls -la /var/data)"

# Verificar si existe la base de datos en alguna ubicación
echo "Verificando ubicaciones de la base de datos:"
if [ -f "agencia.db" ]; then
    echo "Base de datos encontrada en directorio actual"
    DB_SIZE=$(du -h agencia.db | cut -f1)
    echo "Tamaño: $DB_SIZE"
    
    # Copiar a ubicación persistente si no existe o es más reciente
    if [ ! -f "/var/data/database/agencia.db" ] || [ "agencia.db" -nt "/var/data/database/agencia.db" ]; then
        echo "Copiando base de datos a ubicación persistente..."
        cp -f agencia.db /var/data/database/
        echo "Base de datos copiada exitosamente"
    fi
fi

if [ -f "/var/data/database/agencia.db" ]; then
    echo "Base de datos encontrada en ubicación persistente"
    DB_SIZE=$(du -h /var/data/database/agencia.db | cut -f1)
    echo "Tamaño: $DB_SIZE"
    
    # Crear un enlace simbólico si no existe
    if [ ! -f "agencia.db" ] || [ "/var/data/database/agencia.db" -nt "agencia.db" ]; then
        echo "Creando enlace simbólico a la base de datos persistente..."
        ln -sf /var/data/database/agencia.db agencia.db
        echo "Enlace creado exitosamente"
    fi
fi

# Hacer una copia de seguridad antes de iniciar
echo "Creando copia de seguridad de la base de datos..."
if [ -f "/var/data/database/agencia.db" ]; then
    cp -f /var/data/database/agencia.db /var/data/backups/agencia_$(date +%Y%m%d_%H%M%S).db
    echo "Copia de seguridad creada exitosamente"
fi

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
