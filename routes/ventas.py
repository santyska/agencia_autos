from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import Auto, Venta, db
from datetime import datetime, date
from sqlalchemy import extract

ventas_bp = Blueprint('ventas', __name__)

@ventas_bp.route('/ventas')
@login_required
def ventas():
    # Obtener parámetros de filtro
    mes = request.args.get('mes', type=int)
    anio = request.args.get('anio', type=int)
    estado = request.args.get('estado')
    vendedor_id = request.args.get('vendedor_id', type=int)
    
    # Si no se especifica año y mes, usar el actual
    if not anio:
        anio = datetime.now().year
    if not mes:
        mes = datetime.now().month
        
    # Construir la consulta base
    query = Venta.query
    
    # Aplicar filtros
    if mes and anio:
        # Filtrar por mes y año de la fecha de seña
        query = query.filter(
            extract('year', Venta.fecha_seña) == anio,
            extract('month', Venta.fecha_seña) == mes
        )
    elif anio:
        # Filtrar solo por año
        query = query.filter(extract('year', Venta.fecha_seña) == anio)
    
    if estado:
        query = query.filter(Venta.estado_pago == EstadoPago(estado))
        
    if vendedor_id:
        query = query.filter(Venta.vendedor_id == vendedor_id)
    
    # Ordenar por fecha (más recientes primero)
    query = query.order_by(Venta.fecha_seña.desc())
    
    # Ejecutar consulta
    ventas_lista = query.all()
    
    # Obtener lista de vendedores para el filtro
    vendedores = Usuario.query.filter_by(rol='vendedor').all()
    
    # Obtener años disponibles para el filtro (desde 2023 hasta 2030)
    anios_disponibles = list(range(2023, 2031))
    
    # Obtener meses para el filtro
    meses = [(i, calendar.month_name[i]) for i in range(1, 13)]
    
    return render_template(
        'ventas.html', 
        ventas=ventas_lista,
        mes_seleccionado=mes,
        anio_seleccionado=anio,
        meses=meses,
        anios=anios_disponibles,
        estados=[e.value for e in EstadoPago],
        estado_seleccionado=estado,
        vendedores=vendedores,
        vendedor_seleccionado=vendedor_id
    )

@ventas_bp.route('/ventas/nueva', methods=['GET', 'POST'])
@login_required
def nueva_venta():
    # Solo autos disponibles
    autos_disponibles = Auto.query.filter_by(estado=EstadoAuto.DISPONIBLE).all()
    
    if request.method == 'POST':
        auto_id = request.form.get('auto_id')
        fecha_str = request.form.get('fecha')
        cliente_nombre = request.form.get('cliente_nombre')
        cliente_apellido = request.form.get('cliente_apellido')
        cliente_telefono = request.form.get('cliente_telefono')
        cliente_email = request.form.get('cliente_email')
        cliente_dni = request.form.get('cliente_dni')
        precio_venta = request.form.get('precio_venta')
        precio_compra = request.form.get('precio_compra')
        monto_seña = request.form.get('monto_seña')
        estado_pago = request.form.get('estado_pago')
        
        # Validar campos obligatorios
        if not auto_id or not fecha_str or not cliente_nombre or not cliente_apellido or not precio_venta:
            flash('Los campos marcados con * son obligatorios.', 'danger')
            return render_template('nueva_venta.html', autos=autos_disponibles)
        
        # Validar y convertir tipos
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
            precio_venta = float(precio_venta)
            precio_compra = float(precio_compra) if precio_compra else 0
            monto_seña = float(monto_seña) if monto_seña else 0
        except ValueError:
            flash('Formato de fecha o valores numéricos inválidos.', 'danger')
            return render_template('nueva_venta.html', autos=autos_disponibles)
        
        # Obtener auto y verificar disponibilidad
        auto = Auto.query.get(auto_id)
        if not auto or auto.estado != EstadoAuto.DISPONIBLE:
            flash('Auto no disponible.', 'danger')
            return render_template('nueva_venta.html', autos=autos_disponibles)
        
        # Calcular ganancia
        ganancia = precio_venta - precio_compra
        
        # Calcular saldo restante
        saldo_restante = precio_venta - monto_seña
        
        # Determinar estado del pago
        if not estado_pago:
            if monto_seña > 0 and monto_seña < precio_venta:
                estado_pago = EstadoPago.SEÑADO
            elif monto_seña >= precio_venta:
                estado_pago = EstadoPago.PAGADO
            else:
                estado_pago = EstadoPago.PENDIENTE
        else:
            estado_pago = EstadoPago(estado_pago)
        
        # Actualizar estado del auto
        if estado_pago == EstadoPago.PAGADO:
            auto.estado = EstadoAuto.VENDIDO
            fecha_venta = fecha
        else:
            auto.estado = EstadoAuto.RESERVADO
            fecha_venta = None
        
        # Calcular comisión del vendedor
        monto_comision = 0
        if current_user.rol == 'vendedor':
            monto_comision = ganancia * (current_user.porcentaje_comision / 100)
            vendedor_id = current_user.id
        else:
            vendedor_id = request.form.get('vendedor_id', type=int)
            if vendedor_id:
                vendedor = Usuario.query.get(vendedor_id)
                if vendedor and vendedor.rol == 'vendedor':
                    monto_comision = ganancia * (vendedor.porcentaje_comision / 100)
        
        # Crear venta
        venta = Venta(
            auto_id=auto_id,
            fecha_seña=fecha,
            fecha_venta=fecha_venta,
            cliente_nombre=cliente_nombre,
            cliente_apellido=cliente_apellido,
            cliente_telefono=cliente_telefono,
            cliente_email=cliente_email,
            cliente_dni=cliente_dni,
            precio_venta=precio_venta,
            precio_compra=precio_compra,
            monto_seña=monto_seña,
            saldo_restante=saldo_restante,
            estado_pago=estado_pago,
            ganancia=ganancia,
            vendedor_id=vendedor_id,
            monto_comision=monto_comision
        )
        
        db.session.add(venta)
        db.session.commit()
        
        flash('Venta registrada exitosamente.', 'success')
        return redirect(url_for('ventas.recibo', venta_id=venta.id))
    
    # Obtener vendedores para el selector
    vendedores = Usuario.query.filter_by(rol='vendedor', activo=True).all()
    
    return render_template('nueva_venta.html', 
                           autos=autos_disponibles, 
                           vendedores=vendedores,
                           estados=[e.value for e in EstadoPago])

@ventas_bp.route('/ventas/editar/<int:venta_id>', methods=['GET', 'POST'])
@login_required
def editar_venta(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    
    if request.method == 'POST':
        # Actualizar datos básicos
        venta.cliente_nombre = request.form.get('cliente_nombre')
        venta.cliente_apellido = request.form.get('cliente_apellido')
        venta.cliente_telefono = request.form.get('cliente_telefono')
        venta.cliente_email = request.form.get('cliente_email')
        venta.cliente_dni = request.form.get('cliente_dni')
        
        # Actualizar montos
        try:
            nuevo_precio_venta = float(request.form.get('precio_venta'))
            nuevo_monto_seña = float(request.form.get('monto_seña')) if request.form.get('monto_seña') else 0
            
            # Actualizar precio y recalcular
            venta.precio_venta = nuevo_precio_venta
            venta.monto_seña = nuevo_monto_seña
            venta.saldo_restante = nuevo_precio_venta - nuevo_monto_seña
            venta.ganancia = nuevo_precio_venta - venta.precio_compra
            
            # Recalcular comisión si hay vendedor
            if venta.vendedor_id:
                vendedor = Usuario.query.get(venta.vendedor_id)
                if vendedor:
                    venta.monto_comision = venta.ganancia * (vendedor.porcentaje_comision / 100)
        except ValueError:
            flash('Los valores de precio y seña deben ser numéricos.', 'danger')
            return redirect(url_for('ventas.editar_venta', venta_id=venta.id))
        
        # Actualizar estado de pago
        nuevo_estado = request.form.get('estado_pago')
        if nuevo_estado:
            venta.estado_pago = EstadoPago(nuevo_estado)
            
            # Si cambia a PAGADO y no tenía fecha de venta, establecerla
            if venta.estado_pago == EstadoPago.PAGADO and not venta.fecha_venta:
                venta.fecha_venta = datetime.now()
                venta.auto.estado = EstadoAuto.VENDIDO
            # Si cambia a otro estado y tenía VENDIDO, cambiar a RESERVADO
            elif venta.estado_pago != EstadoPago.PAGADO and venta.auto.estado == EstadoAuto.VENDIDO:
                venta.auto.estado = EstadoAuto.RESERVADO
                venta.fecha_venta = None
        
        db.session.commit()
        flash('Venta actualizada exitosamente.', 'success')
        return redirect(url_for('ventas.ventas'))
    
    return render_template('editar_venta.html', 
                          venta=venta,
                          estados=[e.value for e in EstadoPago])

@ventas_bp.route('/ventas/recibo/<int:venta_id>')
@login_required
def recibo(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    return render_template('recibo.html', venta=venta)

@ventas_bp.route('/ventas/generar-recibo/<int:venta_id>')
@login_required
def generar_recibo(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    
    # Crear PDF con FPDF
    pdf = FPDF()
    pdf.add_page()
    
    # Configurar fuente
    pdf.set_font('Arial', 'B', 16)
    
    # Título
    pdf.cell(190, 10, 'RECIBO DE PAGO', 0, 1, 'C')
    pdf.line(10, 30, 200, 30)
    
    # Información de la agencia
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(190, 10, 'Agencia de Autos', 0, 1, 'C')
    pdf.set_font('Arial', '', 10)
    pdf.cell(190, 6, 'Dirección: Av. Principal 123', 0, 1, 'C')
    pdf.cell(190, 6, 'Teléfono: (123) 456-7890', 0, 1, 'C')
    pdf.cell(190, 6, 'Email: contacto@agenciaautos.com', 0, 1, 'C')
    pdf.ln(5)
    
    # Información del recibo
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(190, 10, f'Recibo N°: {venta.id}', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(95, 6, f'Fecha: {venta.fecha_seña.strftime("%d/%m/%Y")}', 0, 0)
    if venta.fecha_venta:
        pdf.cell(95, 6, f'Fecha de Venta: {venta.fecha_venta.strftime("%d/%m/%Y")}', 0, 1)
    else:
        pdf.cell(95, 6, 'Fecha de Venta: Pendiente', 0, 1)
    pdf.ln(5)
    
    # Información del cliente
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(190, 10, 'Datos del Cliente:', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(190, 6, f'Nombre: {venta.cliente_nombre} {venta.cliente_apellido}', 0, 1)
    if venta.cliente_dni:
        pdf.cell(190, 6, f'DNI: {venta.cliente_dni}', 0, 1)
    if venta.cliente_telefono:
        pdf.cell(190, 6, f'Teléfono: {venta.cliente_telefono}', 0, 1)
    if venta.cliente_email:
        pdf.cell(190, 6, f'Email: {venta.cliente_email}', 0, 1)
    pdf.ln(5)
    
    # Información del auto
    if venta.auto:
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(190, 10, 'Datos del Vehículo:', 0, 1)
        pdf.set_font('Arial', '', 10)
        pdf.cell(190, 6, f'Marca: {venta.auto.marca}', 0, 1)
        pdf.cell(190, 6, f'Modelo: {venta.auto.modelo}', 0, 1)
        pdf.cell(190, 6, f'Año: {venta.auto.anio}', 0, 1)
        if venta.auto.color:
            pdf.cell(190, 6, f'Color: {venta.auto.color}', 0, 1)
        pdf.ln(5)
    
    # Información del pago
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(190, 10, 'Detalles del Pago:', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(190, 6, f'Precio de Venta: ${venta.precio_venta:,.2f}', 0, 1)
    pdf.cell(190, 6, f'Monto de Seña: ${venta.monto_seña:,.2f}', 0, 1)
    pdf.cell(190, 6, f'Saldo Restante: ${venta.saldo_restante:,.2f}', 0, 1)
    pdf.cell(190, 6, f'Estado: {venta.estado_pago.value}', 0, 1)
    pdf.ln(10)
    
    # Firmas
    pdf.line(40, 230, 80, 230)
    pdf.line(120, 230, 160, 230)
    pdf.set_font('Arial', '', 8)
    pdf.cell(95, 6, 'Firma del Cliente', 0, 0, 'C')
    pdf.cell(95, 6, 'Firma del Vendedor', 0, 1, 'C')
    
    # Generar QR con el ID de la venta
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr_data = f"ID Venta: {venta.id}, Cliente: {venta.cliente_nombre} {venta.cliente_apellido}, Fecha: {venta.fecha_seña.strftime('%d/%m/%Y')}"
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_path = os.path.join(current_app.root_path, 'static', 'temp', f'qr_{venta.id}.png')
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    img.save(img_path)
    
    # Agregar QR al PDF
    pdf.image(img_path, x=85, y=240, w=40)
    pdf.set_font('Arial', '', 8)
    pdf.set_xy(0, 280)
    pdf.cell(210, 10, 'Este documento es un comprobante de pago.', 0, 1, 'C')
    
    # Guardar PDF a un buffer en memoria
    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    
    # Eliminar archivo temporal del QR
    try:
        os.remove(img_path)
    except:
        pass
    
    # Devolver PDF como descarga
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'recibo_venta_{venta.id}.pdf'
    )

@ventas_bp.route('/ventas/completar-pago/<int:venta_id>', methods=['POST'])
@login_required
def completar_pago(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    
    # Verificar que la venta no esté ya pagada
    if venta.estado_pago == EstadoPago.PAGADO:
        flash('Esta venta ya está pagada.', 'warning')
        return redirect(url_for('ventas.ventas'))
    
    # Obtener monto adicional
    try:
        monto_adicional = float(request.form.get('monto_adicional', 0))
    except ValueError:
        flash('El monto debe ser un número válido.', 'danger')
        return redirect(url_for('ventas.ventas'))
    
    # Actualizar montos
    venta.monto_seña += monto_adicional
    venta.saldo_restante = max(0, venta.precio_venta - venta.monto_seña)
    
    # Si se pagó completamente, actualizar estado
    if venta.saldo_restante <= 0:
        venta.estado_pago = EstadoPago.PAGADO
        venta.fecha_venta = datetime.now()
        venta.auto.estado = EstadoAuto.VENDIDO
    
    db.session.commit()
    flash('Pago registrado exitosamente.', 'success')
    return redirect(url_for('ventas.recibo', venta_id=venta.id))

@ventas_bp.route('/ventas/cancelar/<int:venta_id>', methods=['POST'])
@login_required
def cancelar_venta(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    
    # Verificar que la venta no esté pagada completamente
    if venta.estado_pago == EstadoPago.PAGADO:
        flash('No se puede cancelar una venta ya pagada.', 'danger')
        return redirect(url_for('ventas.ventas'))
    
    # Liberar el auto
    if venta.auto:
        venta.auto.estado = EstadoAuto.DISPONIBLE
    
    # Marcar la venta como cancelada
    venta.estado_pago = EstadoPago.CANCELADO
    
    db.session.commit()
    flash('Venta cancelada exitosamente.', 'success')
    return redirect(url_for('ventas.ventas'))
