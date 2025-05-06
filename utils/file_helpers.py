import os
import uuid
from werkzeug.utils import secure_filename

def normalize_path(path):
    """Normaliza una ruta de archivo para que use forward slashes (/) en lugar de backslashes (\)"""
    return path.replace('\\', '/')

def save_image(file, destination_dir):
    """Guarda una imagen en el directorio especificado y devuelve la ruta relativa normalizada"""
    if not file or not file.filename:
        return None
    
    # Crear directorio si no existe
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
    
    # Generar nombre único para el archivo
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(destination_dir, unique_filename)
    
    # Guardar archivo
    file.save(file_path)
    
    # Normalizar la ruta para URLs (usar forward slashes)
    relative_path = os.path.relpath(file_path, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))
    normalized_path = normalize_path(relative_path)
    
    return normalized_path
