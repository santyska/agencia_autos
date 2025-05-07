from flask import render_template, request, redirect, url_for, flash, session, current_app
from models import db, Venta, Auto, EstadoPago, EstadoAuto
from datetime import datetime

def ventas():
    # Obtener parámetros de filtro
    mes = request.args.get('mes', type=int)
    anio = request.args.get('anio', type=int, default=datetime.now().year)
    estado = request.args.get('estado')
    
    # Consulta base
    query = Venta.query
    
    # Aplicar filtros solo si se especifican
    if mes is not None:
        # Filtrar por mes considerando ambas fechas posibles
        query = query.filter(
            db.or_(
                db.extract('month', Venta.fecha_venta) == mes,
                db.extract('month', Venta.fecha_seña) == mes
            )
        )
    
    if anio is not None:
        # Filtrar por año considerando ambas fechas posibles
        query = query.filter(
            db.or_(
                db.extract('year', Venta.fecha_venta) == anio,
                db.extract('year', Venta.fecha_seña) == anio
            )
        )
    
    if estado:
        # Convertir string a enum
        try:
            estado_enum = EstadoPago[estado]
            query = query.filter(Venta.estado_pago == estado_enum)
        except (KeyError, ValueError):
            # Si el estado no es válido, ignorar este filtro
            pass
    
    # Obtener ventas con manejo de errores
    try:
        ventas = query.order_by(Venta.fecha_venta.desc()).all()
    except Exception as e:
        print(f"Error al obtener ventas: {e}")
        # Si hay error con el orden, intentar con ID
        ventas = query.order_by(Venta.id.desc()).all()
    
    # Preparar datos para la vista
    meses = [(1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'), 
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')]
    
    # Obtener años con ventas considerando ambas fechas posibles
    try:
        # Consulta para años con fecha_venta
        anios_venta_query = db.session.query(db.extract('year', Venta.fecha_venta).distinct())
        anios_venta_query = anios_venta_query.filter(Venta.fecha_venta != None)
        anios_venta_query = anios_venta_query.order_by(db.extract('year', Venta.fecha_venta).desc())
        
        # Manejar la conversión de años de manera segura
        anios_venta = []
        for a in anios_venta_query.all():
            if a[0] is not None:
                try:
                    anios_venta.append(int(a[0]))
                except (ValueError, TypeError):
                    # Si no se puede convertir a int, registrar y continuar
                    print(f"No se pudo convertir {a[0]} a entero, tipo: {type(a[0])}")
        
        # Consulta para años con fecha_seña
        anios_seña_query = db.session.query(db.extract('year', Venta.fecha_seña).distinct())
        anios_seña_query = anios_seña_query.filter(Venta.fecha_seña != None)
        anios_seña_query = anios_seña_query.order_by(db.extract('year', Venta.fecha_seña).desc())
        
        # Manejar la conversión de años de manera segura
        anios_seña = []
        for a in anios_seña_query.all():
            if a[0] is not None:
                try:
                    anios_seña.append(int(a[0]))
                except (ValueError, TypeError):
                    # Si no se puede convertir a int, registrar y continuar
                    print(f"No se pudo convertir {a[0]} a entero, tipo: {type(a[0])}")

        
        # Combinar y eliminar duplicados
        anios = sorted(set(anios_venta + anios_seña), reverse=True)
    except Exception as e:
        print(f"Error al obtener años con ventas: {e}")
        anios = []
    
    if not anios:  # Si no hay años con ventas, usar el año actual
        anios = [datetime.now().year]
    
    # Estados de pago
    estados = [e.value for e in EstadoPago]
    
    return render_template('ventas.html', 
                        ventas=ventas, 
                        meses=meses, 
                        anios=anios,
                        estados=estados,
                        mes_seleccionado=mes,
                        anio_seleccionado=anio,
                        estado_seleccionado=estado)

def registrar_venta():
    if request.method == 'POST':
        # Obtener datos del formulario
        auto_id = request.form.get('auto_id')
        cliente_nombre = request.form.get('cliente_nombre')
        cliente_apellido = request.form.get('cliente_apellido')
        cliente_email = request.form.get('cliente_email')
        cliente_telefono = request.form.get('cliente_telefono')
        precio_venta = request.form.get('precio_venta')
        estado_pago = request.form.get('estado_pago')
        monto_seña = request.form.get('monto_seña', '0')
        
        # Validar datos
        if not auto_id or not cliente_nombre or not precio_venta:
            flash('Faltan datos obligatorios', 'danger')
            return redirect(url_for('registrar_venta'))
        
        # Convertir valores
        try:
            precio_venta = float(precio_venta)
            monto_seña = float(monto_seña) if monto_seña else 0
        except ValueError:
            flash('Error en los valores numéricos', 'danger')
            return redirect(url_for('registrar_venta'))
        
        # Obtener el auto
        auto = Auto.query.get_or_404(auto_id)
        
        # Crear la venta
        nueva_venta = Venta(
            auto_id=auto_id,
            cliente_nombre=cliente_nombre,
            cliente_apellido=cliente_apellido,
            cliente_email=cliente_email,
            cliente_telefono=cliente_telefono,
            precio_venta=precio_venta,
            estado_pago=EstadoPago[estado_pago],
            fecha_seña=datetime.now(),
            monto_seña=monto_seña
        )
        
        # Si el pago es completo, establecer la fecha de venta
        if estado_pago == 'PAGADO':
            nueva_venta.fecha_venta = datetime.now()
        
        # Cambiar el estado del auto a vendido
        auto.estado = EstadoAuto.VENDIDO
        
        # Guardar en la base de datos
        db.session.add(nueva_venta)
        db.session.commit()
        
        flash('Venta registrada correctamente', 'success')
        return redirect(url_for('ventas'))
    
    # Para GET, mostrar el formulario
    autos_disponibles = Auto.query.filter_by(estado=EstadoAuto.DISPONIBLE).all()
    return render_template('registrar_venta.html', autos=autos_disponibles, estados_pago=[e.value for e in EstadoPago])

def detalle_venta(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    return render_template('detalle_venta.html', venta=venta)

def marcar_pagado(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    venta.estado_pago = EstadoPago.PAGADO
    venta.fecha_venta = datetime.now()  # Actualizar la fecha de venta al marcar como pagado
    db.session.commit()
    flash('Venta marcada como pagada', 'success')
    return redirect(url_for('ventas'))

def generar_recibo(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    # Aquí iría la lógica para generar un PDF
    flash('Funcionalidad de generación de recibo en desarrollo', 'info')
    return redirect(url_for('ventas'))

def exportar_ventas():
    # Aquí iría la lógica para exportar a Excel
    flash('Funcionalidad de exportación en desarrollo', 'info')
    return redirect(url_for('ventas'))
