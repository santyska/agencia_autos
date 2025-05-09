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
mkdir -p /var/data/logs
chmod -R 777 /var/data

# Configurar logging
LOG_FILE="/var/data/logs/startup_$(date +%Y%m%d_%H%M%S).log"
echo "Iniciando log en: $LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

# Registrar información del entorno
echo "Información del entorno:"
echo "Directorio actual: $(pwd)"
echo "Contenido del directorio: $(ls -la)"
echo "Contenido de /var/data: $(ls -la /var/data)"
echo "Variables de entorno relacionadas con la base de datos:"
echo "PERSISTENT_STORAGE=${PERSISTENT_STORAGE}"
echo "DB_PERSISTENT_PATH=${DB_PERSISTENT_PATH}"
echo "FORCE_PERSISTENT_DB=${FORCE_PERSISTENT_DB}"

# Verificar si existe la base de datos en alguna ubicación
echo "Verificando ubicaciones de la base de datos:"

# Verificar si existe la base de datos persistente
PERSISTENT_DB="/var/data/database/agencia.db"
LOCAL_DB="agencia.db"

# Crear una copia de seguridad antes de cualquier operación
if [ -f "$LOCAL_DB" ]; then
    echo "Creando backup de la base de datos local..."
    cp -f "$LOCAL_DB" "/var/data/backups/agencia_local_$(date +%Y%m%d_%H%M%S).db"
fi

if [ -f "$PERSISTENT_DB" ]; then
    echo "Creando backup de la base de datos persistente..."
    cp -f "$PERSISTENT_DB" "/var/data/backups/agencia_persistent_$(date +%Y%m%d_%H%M%S).db"
fi

# Determinar qué base de datos usar
if [ -f "$PERSISTENT_DB" ]; then
    echo "Base de datos encontrada en ubicación persistente"
    DB_SIZE=$(du -h "$PERSISTENT_DB" | cut -f1)
    echo "Tamaño: $DB_SIZE"
    
    # Si FORCE_PERSISTENT_DB está activado, siempre usar la persistente
    if [ "$FORCE_PERSISTENT_DB" = "true" ]; then
        echo "Forzando uso de base de datos persistente"
        if [ -f "$LOCAL_DB" ]; then
            echo "Eliminando base de datos local para evitar conflictos"
            rm -f "$LOCAL_DB"
        fi
        echo "Creando enlace simbólico a la base de datos persistente..."
        ln -sf "$PERSISTENT_DB" "$LOCAL_DB"
        echo "Enlace creado exitosamente"
    else
        # Comparar fechas de modificación
        if [ -f "$LOCAL_DB" ]; then
            LOCAL_MOD=$(stat -c %Y "$LOCAL_DB" 2>/dev/null || stat -f %m "$LOCAL_DB")
            PERSISTENT_MOD=$(stat -c %Y "$PERSISTENT_DB" 2>/dev/null || stat -f %m "$PERSISTENT_DB")
            
            if [ "$LOCAL_MOD" -gt "$PERSISTENT_MOD" ]; then
                echo "La base de datos local es más reciente, copiando a ubicación persistente"
                cp -f "$LOCAL_DB" "$PERSISTENT_DB"
                echo "Base de datos copiada exitosamente"
            else
                echo "La base de datos persistente es más reciente, usando esta"
                rm -f "$LOCAL_DB"
                ln -sf "$PERSISTENT_DB" "$LOCAL_DB"
                echo "Enlace creado exitosamente"
            fi
        else
            echo "No existe base de datos local, usando la persistente"
            ln -sf "$PERSISTENT_DB" "$LOCAL_DB"
            echo "Enlace creado exitosamente"
        fi
    fi
elif [ -f "$LOCAL_DB" ]; then
    echo "Solo se encontró base de datos en directorio local"
    DB_SIZE=$(du -h "$LOCAL_DB" | cut -f1)
    echo "Tamaño: $DB_SIZE"
    
    echo "Copiando base de datos a ubicación persistente..."
    cp -f "$LOCAL_DB" "$PERSISTENT_DB"
    echo "Base de datos copiada exitosamente"
    
    echo "Creando enlace simbólico para asegurar consistencia..."
    rm -f "$LOCAL_DB"
    ln -sf "$PERSISTENT_DB" "$LOCAL_DB"
    echo "Enlace creado exitosamente"
else
    echo "No se encontró ninguna base de datos existente"
    echo "Se creará una nueva base de datos al iniciar la aplicación"
fi

# Verificar permisos
echo "Verificando permisos de la base de datos..."
if [ -f "$PERSISTENT_DB" ]; then
    chmod 666 "$PERSISTENT_DB"
    echo "Permisos actualizados para la base de datos persistente"
fi
if [ -f "$LOCAL_DB" ]; then
    chmod 666 "$LOCAL_DB"
    echo "Permisos actualizados para la base de datos local"
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
