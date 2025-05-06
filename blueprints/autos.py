from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from models import db, Auto, EstadoAuto, FotoAuto
from blueprints.auth import login_required
from werkzeug.utils import secure_filename
from utils.helpers import guardar_imagen, generar_url_compartir
import os
import uuid

# Crear el blueprint
autos_bp = Blueprint('autos', __name__)

@autos_bp.route('/')
@login_required
def listar():
    # Filtros
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
    if anio:
        query = query.filter(Auto.anio == int(anio))
    
    # Obtener resultados
    autos = query.order_by(Auto.fecha_publicacion.desc()).all()
    
    return render_template('autos.html', autos=autos)

@autos_bp.route('/<int:auto_id>')
@login_required
def detalle(auto_id):
    auto = Auto.query.get_or_404(auto_id)
    
    # Generar URL para compartir si no existe
    if not auto.url_compartir:
        auto.url_compartir = generar_url_compartir(request, auto.id)
        db.session.commit()
    
    return render_template('detalle_auto.html', auto=auto)

@autos_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    if request.method == 'POST':
        # Obtener datos del formulario
        marca = request.form.get('marca')
        modelo = request.form.get('modelo')
        anio = request.form.get('anio')
        precio = request.form.get('precio')
        color = request.form.get('color')
        kilometraje = request.form.get('kilometraje')
        descripcion = request.form.get('descripcion')
        
        # Precio de compra (solo para administradores)
        precio_compra = 0
        if request.form.get('precio_compra') and request.form.get('rol') == 'admin':
            precio_compra = float(request.form.get('precio_compra'))
        
        # Crear nuevo auto
        nuevo_auto = Auto(
            marca=marca,
            modelo=modelo,
            anio=int(anio),
            precio=float(precio),
            precio_compra=precio_compra,
            color=color,
            kilometraje=int(kilometraje) if kilometraje else 0,
            descripcion=descripcion,
            estado=EstadoAuto.DISPONIBLE
        )
        
        db.session.add(nuevo_auto)
        db.session.commit()
        
        # Generar URL para compartir
        nuevo_auto.url_compartir = generar_url_compartir(request, nuevo_auto.id)
        db.session.commit()
        
        # Procesar las fotos
        if 'fotos' in request.files:
            fotos = request.files.getlist('fotos')
            for foto in fotos:
                if foto and foto.filename:
                    # Crear directorio para las fotos
                    directorio_fotos = os.path.join(
                        current_app.config['UPLOAD_FOLDER'], 
                        'autos', 
                        str(nuevo_auto.id)
                    )
                    
                    # Guardar la foto
                    ruta_archivo = guardar_imagen(foto, directorio_fotos)
                    
                    # Crear registro en la base de datos
                    if ruta_archivo:
                        foto_auto = FotoAuto(ruta_archivo=ruta_archivo, auto_id=nuevo_auto.id)
                        db.session.add(foto_auto)
            
            db.session.commit()
        
        flash('Auto agregado correctamente', 'success')
        return redirect(url_for('autos.listar'))
    
    return render_template('nuevo_auto.html')

@autos_bp.route('/editar/<int:auto_id>', methods=['GET', 'POST'])
@login_required
def editar(auto_id):
    auto = Auto.query.get_or_404(auto_id)
    
    if request.method == 'POST':
        # Actualizar datos
        auto.marca = request.form.get('marca')
        auto.modelo = request.form.get('modelo')
        auto.anio = int(request.form.get('anio'))
        auto.precio = float(request.form.get('precio'))
        auto.color = request.form.get('color')
        auto.kilometraje = int(request.form.get('kilometraje')) if request.form.get('kilometraje') else 0
        auto.descripcion = request.form.get('descripcion')
        auto.estado = request.form.get('estado')
        
        # Precio de compra (solo para administradores)
        if request.form.get('precio_compra') and request.form.get('rol') == 'admin':
            auto.precio_compra = float(request.form.get('precio_compra'))
        
        db.session.commit()
        
        # Procesar nuevas fotos
        if 'fotos' in request.files:
            fotos = request.files.getlist('fotos')
            for foto in fotos:
                if foto and foto.filename:
                    # Crear directorio para las fotos
                    directorio_fotos = os.path.join(
                        current_app.config['UPLOAD_FOLDER'], 
                        'autos', 
                        str(auto.id)
                    )
                    
                    # Guardar la foto
                    ruta_archivo = guardar_imagen(foto, directorio_fotos)
                    
                    # Crear registro en la base de datos
                    if ruta_archivo:
                        foto_auto = FotoAuto(ruta_archivo=ruta_archivo, auto_id=auto.id)
                        db.session.add(foto_auto)
            
            db.session.commit()
        
        flash('Auto actualizado correctamente', 'success')
        return redirect(url_for('autos.detalle', auto_id=auto.id))
    
    return render_template('editar_auto.html', auto=auto)

@autos_bp.route('/eliminar/<int:auto_id>')
@login_required
def eliminar(auto_id):
    auto = Auto.query.get_or_404(auto_id)
    
    # Eliminar fotos asociadas
    for foto in auto.fotos:
        # Eliminar archivo físico
        ruta_completa = os.path.join(current_app.root_path, 'static', foto.ruta_archivo)
        if os.path.exists(ruta_completa):
            os.remove(ruta_completa)
    
    # Eliminar auto de la base de datos
    db.session.delete(auto)
    db.session.commit()
    
    flash('Auto eliminado correctamente', 'success')
    return redirect(url_for('autos.listar'))
