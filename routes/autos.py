from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, abort, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import Auto, FotoAuto, db, EstadoAuto, Venta
import os
import uuid
from datetime import datetime
import qrcode
from io import BytesIO
import base64

autos_bp = Blueprint('autos', __name__)

# Función auxiliar para verificar extensiones permitidas
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@autos_bp.route('/autos')
def autos():
    # Obtener parámetros de filtro básicos
    marca = request.args.get('marca')
    
    # Construir la consulta base - solo autos disponibles para el catálogo
    query = Auto.query.filter(Auto.estado == EstadoAuto.DISPONIBLE)
    
    # Aplicar filtros si están presentes
    if marca:
        query = query.filter(Auto.marca == marca)
    
    # Obtener la lista de autos filtrada
    autos_lista = query.all()
    
    # Obtener todas las marcas para el filtro
    marcas = db.session.query(Auto.marca).distinct().all()
    marcas = [m[0] for m in marcas]  # Convertir a lista simple
    
    return render_template('autos.html', autos=autos_lista, marcas=marcas)

@autos_bp.route('/autos/stock')
@login_required
def stock():
    # Obtener parámetros de filtro
    marca = request.args.get('marca')
    modelo = request.args.get('modelo')
    estado = request.args.get('estado')
    precio_min = request.args.get('precio_min', type=float)
    precio_max = request.args.get('precio_max', type=float)
    
    # Construir la consulta base
    query = Auto.query
    
    # Aplicar filtros si están presentes
    if marca:
        query = query.filter(Auto.marca == marca)
    if modelo:
        query = query.filter(Auto.modelo.like(f'%{modelo}%'))
    if estado:
        query = query.filter(Auto.estado == EstadoAuto(estado))
    if precio_min is not None:
        query = query.filter(Auto.precio >= precio_min)
    if precio_max is not None:
        query = query.filter(Auto.precio <= precio_max)
    
    # Ordenar por fecha de publicación (más recientes primero)
    query = query.order_by(Auto.fecha_publicacion.desc())
    
    # Obtener la lista de autos filtrada
    autos_lista = query.all()
    
    # Obtener todas las marcas y estados para los filtros
    marcas = db.session.query(Auto.marca).distinct().all()
    marcas = [m[0] for m in marcas]  # Convertir a lista simple
    
    return render_template('stock.html', 
                          autos=autos_lista, 
                          marcas=marcas,
                          estados=[e.value for e in EstadoAuto])

@autos_bp.route('/autos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_auto():
    if request.method == 'POST':
        # Obtener datos básicos del formulario
        marca = request.form.get('marca')
        modelo = request.form.get('modelo')
        anio = request.form.get('anio')
        precio = request.form.get('precio')
        color = request.form.get('color')
        kilometraje = request.form.get('kilometraje')
        descripcion = request.form.get('descripcion')
        
        # Validar campos obligatorios
        if not marca or not modelo or not anio or not precio:
            flash('Los campos marca, modelo, año y precio son obligatorios.', 'danger')
            return redirect(url_for('autos.nuevo_auto'))
        
        # Validar y convertir tipos numéricos
        try:
            anio = int(anio)
            precio = float(precio)
            kilometraje = int(kilometraje) if kilometraje else 0
        except ValueError:
            flash('Año, precio y kilometraje deben ser números.', 'danger')
            return redirect(url_for('autos.nuevo_auto'))
        
        # Crear nuevo auto
        auto = Auto(
            marca=marca, 
            modelo=modelo, 
            anio=anio, 
            precio=precio,
            color=color,
            kilometraje=kilometraje,
            descripcion=descripcion,
            estado=EstadoAuto.DISPONIBLE,
            fecha_publicacion=datetime.now()
        )
        
        db.session.add(auto)
        db.session.commit()
        
        # Procesar fotos
        fotos = request.files.getlist('fotos')
        if fotos and fotos[0].filename != '':
            for i, foto in enumerate(fotos):
                if foto and allowed_file(foto.filename):
                    # Generar nombre único para el archivo
                    filename = secure_filename(foto.filename)
                    extension = filename.rsplit('.', 1)[1].lower()
                    nuevo_filename = f"{uuid.uuid4().hex}.{extension}"
                    
                    # Guardar archivo
                    ruta_guardado = os.path.join(current_app.config['UPLOAD_FOLDER'], 'autos', nuevo_filename)
                    foto.save(ruta_guardado)
                    
                    # Crear registro en la base de datos
                    foto_auto = FotoAuto(
                        auto_id=auto.id,
                        ruta_archivo=f"uploads/autos/{nuevo_filename}",
                        es_principal=(i == 0),  # Primera foto como principal
                        orden=i
                    )
                    db.session.add(foto_auto)
        
        db.session.commit()
        flash('Auto agregado exitosamente.', 'success')
        return redirect(url_for('autos.ficha', auto_id=auto.id))
    
    return render_template('nuevo_auto.html')

@autos_bp.route('/autos/editar/<int:auto_id>', methods=['GET', 'POST'])
@login_required
def editar_auto(auto_id):
    auto = Auto.query.get_or_404(auto_id)
    
    if request.method == 'POST':
        # Actualizar datos básicos
        auto.marca = request.form.get('marca')
        auto.modelo = request.form.get('modelo')
        auto.color = request.form.get('color')
        auto.descripcion = request.form.get('descripcion')
        auto.estado = EstadoAuto(request.form.get('estado'))
        
        # Validar y convertir tipos numéricos
        try:
            auto.anio = int(request.form.get('anio'))
            auto.precio = float(request.form.get('precio'))
            auto.kilometraje = int(request.form.get('kilometraje')) if request.form.get('kilometraje') else 0
        except ValueError:
            flash('Año, precio y kilometraje deben ser números.', 'danger')
            return redirect(url_for('autos.editar_auto', auto_id=auto.id))
        
        # Procesar fotos nuevas
        fotos = request.files.getlist('fotos')
        if fotos and fotos[0].filename != '':
            for i, foto in enumerate(fotos):
                if foto and allowed_file(foto.filename):
                    # Generar nombre único para el archivo
                    filename = secure_filename(foto.filename)
                    extension = filename.rsplit('.', 1)[1].lower()
                    nuevo_filename = f"{uuid.uuid4().hex}.{extension}"
                    
                    # Guardar archivo
                    ruta_guardado = os.path.join(current_app.config['UPLOAD_FOLDER'], 'autos', nuevo_filename)
                    foto.save(ruta_guardado)
                    
                    # Crear registro en la base de datos
                    orden = len(auto.fotos) + i
                    es_principal = not auto.fotos and i == 0  # Primera foto como principal solo si no hay otras
                    
                    foto_auto = FotoAuto(
                        auto_id=auto.id,
                        ruta_archivo=f"uploads/autos/{nuevo_filename}",
                        es_principal=es_principal,
                        orden=orden
                    )
                    db.session.add(foto_auto)
        
        db.session.commit()
        flash('Auto actualizado exitosamente.', 'success')
        return redirect(url_for('autos.ficha', auto_id=auto.id))
    
    return render_template('editar_auto.html', auto=auto, estados=[e.value for e in EstadoAuto])

@autos_bp.route('/autos/eliminar/<int:auto_id>', methods=['POST'])
@login_required
def eliminar_auto(auto_id):
    auto = Auto.query.get_or_404(auto_id)
    
    # Verificar si el auto tiene ventas asociadas
    if auto.ventas:
        flash('No se puede eliminar este auto porque tiene ventas asociadas.', 'danger')
        return redirect(url_for('autos.stock'))
    
    # Eliminar fotos físicas
    for foto in auto.fotos:
        try:
            ruta_completa = os.path.join(current_app.root_path, 'static', foto.ruta_archivo)
            if os.path.exists(ruta_completa):
                os.remove(ruta_completa)
        except Exception as e:
            # Registrar error pero continuar
            print(f"Error al eliminar archivo: {e}")
    
    # Eliminar auto (las fotos se eliminarán en cascada)
    db.session.delete(auto)
    db.session.commit()
    flash('Auto eliminado exitosamente.', 'success')
    return redirect(url_for('autos.stock'))

@autos_bp.route('/autos/foto-principal/<int:foto_id>', methods=['POST'])
@login_required
def establecer_foto_principal(foto_id):
    foto = FotoAuto.query.get_or_404(foto_id)
    auto = foto.auto
    
    # Quitar marca de principal de todas las fotos del auto
    for f in auto.fotos:
        f.es_principal = False
    
    # Establecer la nueva foto principal
    foto.es_principal = True
    db.session.commit()
    
    flash('Foto principal actualizada.', 'success')
    return redirect(url_for('autos.editar_auto', auto_id=auto.id))

@autos_bp.route('/autos/eliminar-foto/<int:foto_id>', methods=['POST'])
@login_required
def eliminar_foto(foto_id):
    foto = FotoAuto.query.get_or_404(foto_id)
    auto_id = foto.auto_id
    
    # Eliminar archivo físico
    try:
        ruta_completa = os.path.join(current_app.root_path, 'static', foto.ruta_archivo)
        if os.path.exists(ruta_completa):
            os.remove(ruta_completa)
    except Exception as e:
        # Registrar error pero continuar
        print(f"Error al eliminar archivo: {e}")
    
    # Si era la foto principal, establecer otra como principal
    era_principal = foto.es_principal
    
    # Eliminar registro de la base de datos
    db.session.delete(foto)
    db.session.commit()
    
    # Si era principal y hay más fotos, establecer la primera como principal
    if era_principal:
        auto = Auto.query.get(auto_id)
        if auto.fotos:
            auto.fotos[0].es_principal = True
            db.session.commit()
    
    flash('Foto eliminada exitosamente.', 'success')
    return redirect(url_for('autos.editar_auto', auto_id=auto_id))

@autos_bp.route('/autos/ficha/<int:auto_id>')
def ficha(auto_id):
    auto = Auto.query.get_or_404(auto_id)
    
    # Generar QR para compartir
    url_ficha = url_for('autos.ficha', auto_id=auto.id, _external=True)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url_ficha)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered)
    qr_code = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    # URL para compartir en WhatsApp
    whatsapp_text = f"¡Mira este {auto.marca} {auto.modelo} {auto.anio} en nuestra agencia! Precio: ${auto.precio:,.2f}. Más información: {url_ficha}"
    whatsapp_url = f"https://wa.me/?text={whatsapp_text}"
    
    return render_template('ficha_auto.html', 
                          auto=auto, 
                          qr_code=qr_code, 
                          whatsapp_url=whatsapp_url,
                          url_ficha=url_ficha)

@autos_bp.route('/autos/api/disponibles')
def api_autos_disponibles():
    """API para obtener autos disponibles en formato JSON"""
    autos = Auto.query.filter_by(estado=EstadoAuto.DISPONIBLE).all()
    resultado = []
    
    for auto in autos:
        foto = None
        for f in auto.fotos:
            if f.es_principal:
                foto = f.ruta_archivo
                break
        if not foto and auto.fotos:
            foto = auto.fotos[0].ruta_archivo
            
        resultado.append({
            'id': auto.id,
            'marca': auto.marca,
            'modelo': auto.modelo,
            'anio': auto.anio,
            'precio': auto.precio,
            'color': auto.color,
            'foto': url_for('static', filename=foto) if foto else None,
            'ficha_url': url_for('autos.ficha', auto_id=auto.id, _external=True)
        })
    
    return jsonify(resultado)
