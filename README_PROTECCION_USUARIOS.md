# Sistema de Protección de Usuarios

Este documento explica el sistema de protección de usuarios implementado para evitar la pérdida accidental de cuentas de usuario en la aplicación.

## Problema Resuelto

Se identificó un problema crítico donde los usuarios eran eliminados automáticamente después de un tiempo, debido a scripts que se ejecutaban durante los reinicios del servidor o despliegues en Render.

## Solución Implementada

Hemos implementado un sistema de protección de usuarios con múltiples capas de seguridad:

### 1. Modificación de Scripts Problemáticos

- Se modificaron los scripts `fix_render_auth.py` y `emergency_login.py` para que **nunca eliminen usuarios existentes**.
- Estos scripts ahora solo verifican si el usuario admin existe y lo crean o actualizan si es necesario.

### 2. Script de Protección de Usuarios

- Se creó el script `protect_users.py` que:
  - Hace una copia de seguridad de todos los usuarios en una tabla `usuario_backup`
  - Verifica si hay usuarios en la base de datos y los restaura desde el respaldo si es necesario
  - Asegura que el usuario admin siempre exista

### 3. Scheduler de Protección

- Se implementó un scheduler (`scheduler.py`) que ejecuta el script de protección periódicamente
- Se ejecuta en un hilo separado para no interferir con la aplicación principal

### 4. Script de Inicio para Render

- Se creó un script de inicio personalizado (`render_startup.sh`) que ejecuta el script de protección antes de iniciar la aplicación
- Se configuró en `render.yaml` para que se ejecute automáticamente al iniciar el servidor

### 5. Cron Job en Render

- Se configuró un cron job en Render para ejecutar el script de protección cada 15 minutos
- Proporciona una capa adicional de seguridad en caso de que el scheduler interno falle

### 6. Middleware de Protección

- Se implementó un middleware de Flask (`user_protection_middleware.py`) que verifica periódicamente la existencia de usuarios durante la ejecución de la aplicación
- Se ejecuta cada 5 minutos y restaura usuarios si es necesario

## Cómo Funciona

1. **Al iniciar la aplicación**:
   - Se ejecuta el script de protección de usuarios
   - Se inicia el scheduler en un hilo separado
   - Se inicializa el middleware de protección

2. **Durante la ejecución**:
   - El scheduler verifica los usuarios cada 30 minutos
   - El middleware verifica los usuarios cada 5 minutos
   - El cron job de Render verifica los usuarios cada 15 minutos

3. **Si se eliminan los usuarios**:
   - El sistema detectará que no hay usuarios en la base de datos
   - Restaurará automáticamente los usuarios desde la tabla de respaldo
   - Si no hay respaldo, creará al menos el usuario admin por defecto

## Mantenimiento

Este sistema de protección es completamente automático y no requiere mantenimiento. Sin embargo, si se desea modificar:

- Los intervalos de verificación se pueden ajustar en:
  - `scheduler.py` - Variable `interval`
  - `user_protection_middleware.py` - Parámetro `check_interval`
  - `render.yaml` - Configuración `schedule` del cron job

## Solución de Problemas

Si aún se experimentan problemas con la eliminación de usuarios:

1. Verificar los logs en:
   - `user_protection.log`
   - `scheduler.log`
   - `middleware_protection.log`
   - `cron_protection.log`

2. Asegurarse de que los scripts de protección se estén ejecutando correctamente:
   - Verificar que el script `protect_users.py` se ejecute al iniciar la aplicación
   - Verificar que el cron job esté configurado correctamente en Render

## Conclusión

Este sistema de protección de usuarios proporciona múltiples capas de seguridad para evitar la pérdida accidental de cuentas de usuario. Con estas medidas implementadas, los usuarios deberían persistir incluso después de reinicios del servidor o despliegues en Render.
