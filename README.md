# FGD Motors - Sistema de Gestión

Sistema web para la gestión de inventario, ventas y estadísticas de FGD Motors.

## Características

- Gestión de inventario de autos
- Registro de ventas
- Estadísticas de ventas en ARS y USD
- Panel de administración
- Gestión de usuarios
- Catálogo de autos

## Tecnologías utilizadas

- Flask
- SQLAlchemy
- SQLite
- Bootstrap 5
- Font Awesome
- JavaScript

## Instalación local

1. Clonar el repositorio
2. Instalar dependencias: `pip install -r requirements.txt`
3. Ejecutar la aplicación: `python app_final.py`

## Despliegue

La aplicación está preparada para ser desplegada en plataformas como:
- Render.com
- PythonAnywhere
- Heroku

## Estructura del proyecto

La aplicación tiene una estructura modular con blueprints organizados en la carpeta 'routes/':
- routes/auth.py: Gestión de autenticación y usuarios
- routes/autos.py: Gestión del catálogo de autos
- routes/ventas.py: Gestión de ventas
- routes/admin.py: Funcionalidades de administración
- routes/estadisticas.py: Generación de estadísticas y reportes

## Contacto

FGD Motors
- Email: fgdmotors@gmail.com
- Teléfono: 1130446269
- Dirección: Av. 12 de Octubre, B1664 Manuel Alberti, Provincia de Buenos Aires
