#!/usr/bin/env bash
# exit on error
set -o errexit

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt

# Asegurarse de que la base de datos existe
python -c "from app import db; db.create_all()"

# Crear usuario administrador (método 1)
python create_admin.py || echo "Método 1 falló, intentando método 2"

# Método alternativo para crear usuario admin directamente en SQLite
python reset_admin.py
