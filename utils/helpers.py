import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

def formato_precio(valor):
    """Formatea un número como precio en formato $X,XXX.XX"""
    return f"${valor:,.2f}"

def formato_numero(valor, decimales=2, separador=',', punto='.'):
    """Formatea un número con separadores de miles y decimales personalizados"""
    if valor is None:
        return ''
    return format(valor, f',.{decimales}f').replace(',', separador).replace('.', punto)

def guardar_imagen(archivo, directorio_destino):
    """Guarda una imagen en el directorio especificado y devuelve la ruta relativa"""
    if not archivo or not archivo.filename:
        return None
    
    # Crear directorio si no existe
    if not os.path.exists(directorio_destino):
        os.makedirs(directorio_destino)
    
    # Generar nombre único para el archivo
    nombre_seguro = secure_filename(archivo.filename)
    nombre_archivo = f"{uuid.uuid4()}_{nombre_seguro}"
    ruta_completa = os.path.join(directorio_destino, nombre_archivo)
    
    # Guardar archivo
    archivo.save(ruta_completa)
    
    # Devolver ruta relativa desde la carpeta static
    ruta_relativa = os.path.relpath(ruta_completa, os.path.join(current_app.root_path, 'static'))
    return ruta_relativa

def generar_url_compartir(request, auto_id):
    """Genera una URL para compartir un auto"""
    return f"{request.host_url}auto/{auto_id}"
