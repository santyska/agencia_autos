#!/usr/bin/env bash
# exit on error
set -o errexit

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt

# Asegurarse de que la base de datos existe
python -c "from app_final import db; db.create_all()"
