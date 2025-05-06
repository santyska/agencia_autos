# Este archivo es un punto de entrada para Gunicorn en Render
# Importa la aplicación desde app_final.py

from app_final import app

# Si este archivo se ejecuta directamente, inicia la aplicación
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
