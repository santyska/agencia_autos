from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from models import db, Venta, Usuario, Auto, EstadoPago
from sqlalchemy import extract, func
from datetime import datetime, date
import calendar
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from functools import wraps

stats_bp = Blueprint('estadisticas', __name__)

# Decorador para verificar si el usuario es administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
            return redirect(url_for('inicio'))
        return f(*args, **kwargs)
    return decorated_function

@stats_bp.route('/estadisticas')
@login_required
def dashboard():
    # Obtener año y mes actuales
    anio_actual = datetime.now().year
    mes_actual = datetime.now().month
    
    # Obtener ventas del mes actual
    ventas_mes = Venta.query.filter(
        extract('year', Venta.fecha_seña) == anio_actual,
        extract('month', Venta.fecha_seña) == mes_actual
    ).all()
    
    # Calcular estadísticas básicas
    total_ventas = len(ventas_mes)
    ingresos_mes = sum(v.precio_venta for v in ventas_mes)
    ganancia_mes = sum(v.ganancia for v in ventas_mes)
    
    # Obtener top vendedores del mes
    vendedores = {}
    for venta in ventas_mes:
        if venta.vendedor:
            vendedor_nombre = f"{venta.vendedor.nombre} {venta.vendedor.apellido}"
            if vendedor_nombre in vendedores:
                vendedores[vendedor_nombre] += 1
            else:
                vendedores[vendedor_nombre] = 1
    
    top_vendedores = sorted(vendedores.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Generar gráfico de ventas por día del mes
    ventas_por_dia = {}
    for venta in ventas_mes:
        dia = venta.fecha_seña.day
        if dia in ventas_por_dia:
            ventas_por_dia[dia] += 1
        else:
            ventas_por_dia[dia] = 1
    
    # Llenar días sin ventas
    dias_en_mes = calendar.monthrange(anio_actual, mes_actual)[1]
    for dia in range(1, dias_en_mes + 1):
        if dia not in ventas_por_dia:
            ventas_por_dia[dia] = 0
    
    # Ordenar por día
    dias = sorted(ventas_por_dia.keys())
    conteo_ventas = [ventas_por_dia[dia] for dia in dias]
    
    # Crear gráfico
    plt.figure(figsize=(10, 4))
    plt.bar(dias, conteo_ventas)
    plt.title(f'Ventas por día - {calendar.month_name[mes_actual]} {anio_actual}')
    plt.xlabel('Día del mes')
    plt.ylabel('Cantidad de ventas')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Convertir gráfico a imagen base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    grafico_ventas_diarias = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return render_template(
        'estadisticas/dashboard.html',
        total_ventas=total_ventas,
        ingresos_mes=ingresos_mes,
        ganancia_mes=ganancia_mes,
        top_vendedores=top_vendedores,
        grafico_ventas_diarias=grafico_ventas_diarias,
        mes_actual=calendar.month_name[mes_actual],
        anio_actual=anio_actual
    )

@stats_bp.route('/estadisticas/ventas-mensuales')
@login_required
def ventas_mensuales():
    # Obtener año seleccionado (por defecto el actual)
    anio = request.args.get('anio', type=int, default=datetime.now().year)
    
    # Consultar ventas por mes para el año seleccionado
    ventas_por_mes = db.session.query(
        extract('month', Venta.fecha_seña).label('mes'),
        func.count(Venta.id).label('total_ventas'),
        func.sum(Venta.precio_venta).label('ingresos'),
        func.sum(Venta.ganancia).label('ganancias')
    ).filter(
        extract('year', Venta.fecha_seña) == anio
    ).group_by(
        extract('month', Venta.fecha_seña)
    ).all()
    
    # Preparar datos para la vista
    meses = []
    total_ventas = []
    ingresos = []
    ganancias = []
    
    # Inicializar con ceros para todos los meses
    for i in range(1, 13):
        meses.append(calendar.month_name[i])
        total_ventas.append(0)
        ingresos.append(0)
        ganancias.append(0)
    
    # Llenar con datos reales
    for vm in ventas_por_mes:
        mes_idx = int(vm.mes) - 1  # Ajustar índice (0-11)
        total_ventas[mes_idx] = vm.total_ventas
        ingresos[mes_idx] = float(vm.ingresos) if vm.ingresos else 0
        ganancias[mes_idx] = float(vm.ganancias) if vm.ganancias else 0
    
    # Crear gráfico de barras para ventas mensuales
    plt.figure(figsize=(12, 6))
    plt.bar(meses, total_ventas)
    plt.title(f'Ventas mensuales - {anio}')
    plt.xlabel('Mes')
    plt.ylabel('Cantidad de ventas')
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    # Convertir gráfico a imagen base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    grafico_ventas = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    # Crear gráfico de líneas para ingresos y ganancias
    plt.figure(figsize=(12, 6))
    plt.plot(meses, ingresos, marker='o', label='Ingresos')
    plt.plot(meses, ganancias, marker='s', label='Ganancias')
    plt.title(f'Ingresos y Ganancias mensuales - {anio}')
    plt.xlabel('Mes')
    plt.ylabel('Monto ($)')
    plt.xticks(rotation=45)
    plt.grid(linestyle='--', alpha=0.7)
    plt.legend()
    plt.tight_layout()
    
    # Convertir gráfico a imagen base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    grafico_ingresos = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    # Obtener años disponibles para el selector
    años_disponibles = db.session.query(
        extract('year', Venta.fecha_seña).distinct()
    ).order_by(
        extract('year', Venta.fecha_seña).desc()
    ).all()
    
    # Manejar la conversión de años de manera segura
    años_disponibles_list = []
    for año in años_disponibles:
        if año[0] is not None:
            try:
                años_disponibles_list.append(int(año[0]))
            except (ValueError, TypeError):
                # Si no se puede convertir a int, registrar y continuar
                print(f"No se pudo convertir {año[0]} a entero, tipo: {type(año[0])}")
    
    if not años_disponibles_list:
        años_disponibles_list = [datetime.now().year]
    
    return render_template(
        'estadisticas/ventas_mensuales.html',
        meses=meses,
        total_ventas=total_ventas,
        ingresos=ingresos,
        ganancias=ganancias,
        anio_seleccionado=anio,
        años_disponibles=años_disponibles_list,
        grafico_ventas=grafico_ventas,
        grafico_ingresos=grafico_ingresos
    )

@stats_bp.route('/estadisticas/comisiones')
@login_required
@admin_required
def comisiones_vendedores():
    # Obtener período seleccionado
    anio = request.args.get('anio', type=int, default=datetime.now().year)
    mes = request.args.get('mes', type=int, default=datetime.now().month)
    
    # Consultar comisiones por vendedor para el período seleccionado
    vendedores_comisiones = db.session.query(
        Usuario,
        func.count(Venta.id).label('total_ventas'),
        func.sum(Venta.monto_comision).label('total_comision')
    ).join(
        Venta, Usuario.id == Venta.vendedor_id
    ).filter(
        extract('year', Venta.fecha_seña) == anio,
        extract('month', Venta.fecha_seña) == mes if mes else True,
        Usuario.rol == 'vendedor'
    ).group_by(
        Usuario.id
    ).all()
    
    # Preparar datos para la vista
    datos_vendedores = []
    for v, total_ventas, total_comision in vendedores_comisiones:
        datos_vendedores.append({
            'id': v.id,
            'nombre': f"{v.nombre} {v.apellido}",
            'total_ventas': total_ventas,
            'porcentaje_comision': v.porcentaje_comision,
            'total_comision': float(total_comision) if total_comision else 0
        })
    
    # Ordenar por total de comisiones (mayor a menor)
    datos_vendedores.sort(key=lambda x: x['total_comision'], reverse=True)
    
    # Crear gráfico de barras para comisiones
    if datos_vendedores:
        nombres = [v['nombre'] for v in datos_vendedores]
        comisiones = [v['total_comision'] for v in datos_vendedores]
        
        plt.figure(figsize=(12, 6))
        plt.bar(nombres, comisiones)
        plt.title(f'Comisiones por vendedor - {calendar.month_name[mes] if mes else "Todo el año"} {anio}')
        plt.xlabel('Vendedor')
        plt.ylabel('Comisión ($)')
        plt.xticks(rotation=45)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        # Convertir gráfico a imagen base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico_comisiones = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
    else:
        grafico_comisiones = None
    
    # Obtener años y meses disponibles para los selectores
    años_disponibles = db.session.query(
        extract('year', Venta.fecha_seña).distinct()
    ).order_by(
        extract('year', Venta.fecha_seña).desc()
    ).all()
    
    # Manejar la conversión de años de manera segura
    años_disponibles_list = []
    for año in años_disponibles:
        if año[0] is not None:
            try:
                años_disponibles_list.append(int(año[0]))
            except (ValueError, TypeError):
                # Si no se puede convertir a int, registrar y continuar
                print(f"No se pudo convertir {año[0]} a entero, tipo: {type(año[0])}")
    
    if not años_disponibles_list:
        años_disponibles_list = [datetime.now().year]
    
    return render_template(
        'estadisticas/comisiones.html',
        vendedores=datos_vendedores,
        anio_seleccionado=anio,
        mes_seleccionado=mes,
        años_disponibles=años_disponibles_list,
        meses=[(i, calendar.month_name[i]) for i in range(1, 13)],
        grafico_comisiones=grafico_comisiones
    )

@stats_bp.route('/estadisticas/exportar-excel')
@login_required
@admin_required
def exportar_excel():
    # Obtener período seleccionado
    anio = request.args.get('anio', type=int, default=datetime.now().year)
    
    # Consultar ventas para el año seleccionado
    ventas = Venta.query.filter(
        extract('year', Venta.fecha_seña) == anio
    ).all()
    
    # Crear DataFrame con los datos
    datos = []
    for v in ventas:
        vendedor = f"{v.vendedor.nombre} {v.vendedor.apellido}" if v.vendedor else "Sin vendedor"
        auto = f"{v.auto.marca} {v.auto.modelo} ({v.auto.anio})" if v.auto else "Auto no disponible"
        
        datos.append({
            'ID': v.id,
            'Fecha Seña': v.fecha_seña,
            'Fecha Venta': v.fecha_venta,
            'Auto': auto,
            'Cliente': f"{v.cliente_nombre} {v.cliente_apellido}",
            'Vendedor': vendedor,
            'Precio Compra': v.precio_compra,
            'Precio Venta': v.precio_venta,
            'Seña': v.monto_seña,
            'Saldo': v.saldo_restante,
            'Estado': v.estado_pago.value if v.estado_pago else "Desconocido",
            'Ganancia': v.ganancia,
            'Comisión': v.monto_comision
        })
    
    # Crear Excel
    df = pd.DataFrame(datos)
    
    # Guardar a un buffer en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=f'Ventas {anio}', index=False)
    
    output.seek(0)
    
    # Devolver el archivo para descarga
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'ventas_{anio}.xlsx'
    )
