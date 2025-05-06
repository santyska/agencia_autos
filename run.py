from app_factory import create_app

# Crear la aplicación con la configuración por defecto (desarrollo)
app = create_app()

if __name__ == '__main__':
    # Iniciar el servidor
    app.run(debug=True)
