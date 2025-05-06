from flask import render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from models import db, Auto, FotoAuto, EstadoAuto
import os
import uuid
from datetime import datetime

def autos():
    # Filtros (solo disponibles para usuarios logueados)
    if 'user_id' in session:
        marca = request.args.get('marca', '')
        modelo = request.args.get('modelo', '')
        anio = request.args.get('anio', '')
        
        # Consulta base
        query = Auto.query
        
        # Aplicar filtros si existen
        if marca:
            query = query.filter(Auto.marca.ilike(f'%{marca}%'))
        if modelo:
            query = query.filter(Auto.modelo.ilike(f'%{modelo}%'))
        if anio and anio.isdigit():
            query = query.filter(Auto.anio == int(anio))
        
        # Obtener resultados
        try:
            autos = query.order_by(Auto.fecha_publicacion.desc()).all()
        except Exception as e:
            print(f"Error al obtener autos: {e}")
            # Si hay error con fecha_publicacion, ordenar por id
            autos = query.order_by(Auto.id.desc()).all()
    else:
        # Para visitantes, mostrar solo autos disponibles sin filtros
        try:
            autos = Auto.query.filter_by(estado=EstadoAuto.DISPONIBLE).order_by(Auto.fecha_publicacion.desc()).all()
        except Exception as e:
            print(f"Error al obtener autos para visitantes: {e}")
            autos = Auto.query.filter_by(estado=EstadoAuto.DISPONIBLE).order_by(Auto.id.desc()).all()
    
    return render_template('autos.html', autos=autos, is_logged_in='user_id' in session)

def detalle_auto(auto_id):
    auto = Auto.query.get_or_404(auto_id)
    return render_template('detalle_auto.html', auto=auto)

def nuevo_auto():
    if request.method == 'POST':
        # Obtener datos del formulario
        marca = request.form.get('marca', '')
        modelo = request.form.get('modelo', '')
        anio = request.form.get('anio', '0')
        precio = request.form.get('precio', '0')
        color = request.form.get('color', '')
        kilometraje = request.form.get('kilometraje', '0')
        descripcion = request.form.get('descripcion', '')
        
        # Precio de compra (solo para administradores)
        precio_compra = request.form.get('precio_compra', '0')
        if not precio_compra:
            precio_compra = 0
        
        # Validar y convertir los valores
        try:
            anio_int = int(anio) if anio else 0
            precio_float = float(precio) if precio else 0.0
            precio_compra_float = float(precio_compra) if precio_compra else 0.0
            kilometraje_int = int(kilometraje) if kilometraje else 0
        except ValueError:
            flash('Error en los datos ingresados. Verifique los valores numéricos.', 'danger')
            return redirect(url_for('nuevo_auto'))
        
        # Crear nuevo auto
        nuevo_auto = Auto(
            marca=marca,
            modelo=modelo,
            anio=anio_int,
            precio=precio_float,
            precio_compra=precio_compra_float,
            color=color,
            kilometraje=kilometraje_int,
            descripcion=descripcion,
            estado=EstadoAuto.DISPONIBLE
        )
        
        db.session.add(nuevo_auto)
        db.session.commit()
        
        # Generar URL para compartir
        nuevo_auto.url_compartir = f"{request.host_url}auto/{nuevo_auto.id}"
        db.session.commit()
        
        # Procesar las fotos
        if 'fotos' in request.files:
            fotos = request.files.getlist('fotos')
            for foto in fotos:
                if foto and foto.filename:
                    # Crear directorio si no existe
                    directorio_fotos = os.path.join(current_app.static_folder, 'uploads', 'autos', str(nuevo_auto.id))
                    if not os.path.exists(directorio_fotos):
                        os.makedirs(directorio_fotos)
                    
                    # Guardar la foto
                    filename = secure_filename(foto.filename)
                    nombre_archivo = f"{uuid.uuid4()}_{filename}"
                    ruta_relativa = os.path.join('uploads', 'autos', str(nuevo_auto.id), nombre_archivo)
                    ruta_completa = os.path.join(current_app.static_folder, ruta_relativa.replace('uploads/', ''))
                    foto.save(ruta_completa)
                    
                    # Normalizar la ruta para URLs (usar forward slashes)
                    ruta_normalizada = ruta_relativa.replace('\\', '/')
                    
                    # Crear registro en la base de datos
                    foto_auto = FotoAuto(ruta_archivo=ruta_normalizada, auto_id=nuevo_auto.id)
                    db.session.add(foto_auto)
        
        db.session.commit()
        
        flash('Auto agregado correctamente', 'success')
        return redirect(url_for('autos'))
    
    return render_template('nuevo_auto.html')
