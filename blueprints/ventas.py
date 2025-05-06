from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from models import db, Auto, EstadoAuto, Venta, EstadoPago
from blueprints.auth import login_required, admin_required
from datetime import datetime

# Crear el blueprint
ventas_bp = Blueprint('ventas', __name__)

@ventas_bp.route('/')
@login_required
def listar():
    # Obtener parámetros de filtro
    mes = request.args.get('mes', type=int)
    anio = request.args.get('anio', type=int, default=datetime.now().year)
    estado = request.args.get('estado')
    
    # Consulta base
    query = Venta.query
    
    # Aplicar filtros
    if mes:
        query = query.filter(db.extract('month', Venta.fecha) == mes)
    if anio:
        query = query.filter(db.extract('year', Venta.fecha) == anio)
    if estado:
        query = query.filter(Venta.estado == estado)
    
    # Obtener ventas
    ventas = query.order_by(Venta.fecha.desc()).all()
    
    # Preparar datos para la vista
    meses = [(1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'), 
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')]
    
    # Obtener años con ventas
    anios = db.session.query(db.extract('year', Venta.fecha).distinct()).order_by(db.extract('year', Venta.fecha).desc()).all()
    anios = [a[0] for a in anios] if anios else [datetime.now().year]
    
    # Estados de venta
    estados = [e.value for e in EstadoPago]
    
    return render_template('ventas.html', 
                        ventas=ventas, 
                        meses=meses, 
                        anios=anios,
                        estados=estados,
                        mes_seleccionado=mes,
                        anio_seleccionado=anio,
                        estado_seleccionado=estado)

@ventas_bp.route('/registrar', methods=['GET', 'POST'])
@login_required
def registrar():
    # Obtener auto_id si se proporciona
    auto_id = request.args.get('auto_id', type=int)
    auto = None
    if auto_id:
        auto = Auto.query.get_or_404(auto_id)
    
    # Obtener autos disponibles
    autos_disponibles = Auto.query.filter_by(estado=EstadoAuto.DISPONIBLE).all()
    
    if request.method == 'POST':
        # Obtener datos del formulario
        auto_id = request.form.get('auto_id', type=int)
        precio = request.form.get('precio', type=float)
        cliente_nombre = request.form.get('cliente_nombre')
        cliente_documento = request.form.get('cliente_documento')
        cliente_telefono = request.form.get('cliente_telefono', '')
        cliente_email = request.form.get('cliente_email', '')
        fecha_str = request.form.get('fecha')
        estado = request.form.get('estado')
        metodo_pago = request.form.get('metodo_pago', '')
        notas = request.form.get('notas', '')
        
        # Validar datos
        if not auto_id or not precio or not cliente_nombre or not cliente_documento:
            flash('Por favor complete todos los campos obligatorios', 'danger')
            return redirect(url_for('ventas.registrar'))
        
        # Obtener el auto
        auto = Auto.query.get_or_404(auto_id)
        
        # Convertir fecha
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
        except ValueError:
            fecha = datetime.now()
        
        # Crear venta
        venta = Venta(
            auto_id=auto_id,
            precio_venta=precio,
            precio_compra=auto.precio_compra,
            cliente_nombre=cliente_nombre,
            cliente_apellido=cliente_nombre.split(' ')[-1] if ' ' in cliente_nombre else "",
            cliente_dni=cliente_documento,
            cliente_telefono=cliente_telefono,
            cliente_email=cliente_email,
            fecha_seña=fecha,
            fecha_venta=fecha if estado == EstadoPago.PAGADO.value else None,
            estado_pago=EstadoPago.PAGADO if estado == EstadoPago.PAGADO.value else EstadoPago.PENDIENTE,
            observaciones=notas,
            vendedor_id=session.get('user_id'),
            monto_seña=0  # No hay seña en este caso
        )
        
        # Actualizar estado del auto
        auto.estado = EstadoAuto.VENDIDO
        
        # Guardar en la base de datos
        db.session.add(venta)
        db.session.commit()
        
        flash('Venta registrada correctamente', 'success')
        return redirect(url_for('ventas.listar'))
    
    return render_template('registrar_venta.html', 
                        auto=auto, 
                        autos_disponibles=autos_disponibles,
                        today=datetime.now().strftime('%Y-%m-%d'))

@ventas_bp.route('/<int:venta_id>')
@login_required
def detalle(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    return render_template('detalle_venta.html', venta=venta)

@ventas_bp.route('/<int:venta_id>/recibo')
@login_required
def generar_recibo(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    # Aquí iría la lógica para generar un PDF
    # Por ahora, solo redireccionamos a la vista de detalle
    flash('Funcionalidad de generación de recibo en desarrollo', 'info')
    return redirect(url_for('ventas.detalle', venta_id=venta_id))

@ventas_bp.route('/<int:venta_id>/pagar')
@login_required
def marcar_pagado(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    venta.estado = EstadoPago.PAGADO.value
    db.session.commit()
    flash('Venta marcada como pagada', 'success')
    return redirect(url_for('ventas.listar'))

@ventas_bp.route('/exportar')
@login_required
def exportar():
    # Aquí iría la lógica para exportar a Excel
    flash('Funcionalidad de exportación en desarrollo', 'info')
    return redirect(url_for('ventas.listar'))

@ventas_bp.route('/estadisticas')
@admin_required
def estadisticas():
    # Obtener datos de ventas por mes para el año actual
    anio_actual = datetime.now().year
    datos_ventas = []
    
    for mes in range(1, 13):
        total_mes = db.session.query(db.func.sum(Venta.precio_venta)).\
            filter(db.extract('year', Venta.fecha) == anio_actual).\
            filter(db.extract('month', Venta.fecha) == mes).scalar() or 0
        datos_ventas.append(total_mes)
    
    # En lugar de generar un gráfico, devolvemos los datos para mostrar en una tabla
    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    
    datos = [{'mes': meses[i], 'ventas': datos_ventas[i]} for i in range(12)]
    
    # Calcular estadísticas
    total_ventas = sum(datos_ventas)
    promedio_ventas = total_ventas / 12 if total_ventas > 0 else 0
    mejor_mes = meses[datos_ventas.index(max(datos_ventas))] if max(datos_ventas) > 0 else 'Ninguno'
    
    return render_template('estadisticas.html', 
                        datos=datos, 
                        anio_actual=anio_actual,
                        total_ventas=total_ventas,
                        promedio_ventas=promedio_ventas,
                        mejor_mes=mejor_mes)
