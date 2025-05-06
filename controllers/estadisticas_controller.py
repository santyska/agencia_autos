from flask import render_template, session, redirect, url_for
from models import db, Venta, Auto, EstadoAuto
from datetime import datetime
import calendar

def estadisticas():
    if session.get('rol') != 'admin':
        return redirect(url_for('dashboard'))
    
    # Obtener año actual
    anio_actual = datetime.now().year
    
    # Datos para gráfico de ventas por mes
    datos_ventas_mes = obtener_ventas_por_mes(anio_actual)
    
    # Datos para gráfico de ganancias por mes
    datos_ganancias_mes = obtener_ganancias_por_mes(anio_actual)
    
    # Datos para gráfico de ventas por marca
    datos_ventas_marca = obtener_ventas_por_marca()
    
    # Resumen general
    resumen = obtener_resumen_general()
    
    return render_template('estadisticas.html',
                          datos_ventas_mes=datos_ventas_mes,
                          datos_ganancias_mes=datos_ganancias_mes,
                          datos_ventas_marca=datos_ventas_marca,
                          resumen=resumen,
                          anio_actual=anio_actual)

def obtener_ventas_por_mes(anio):
    """Obtiene el número de ventas por mes para un año específico"""
    datos_ventas = []
    
    for mes in range(1, 13):
        # Contar ventas para este mes y año
        count = Venta.query.filter(
            db.extract('year', Venta.fecha_venta) == anio,
            db.extract('month', Venta.fecha_venta) == mes
        ).count()
        
        # Agregar datos al resultado
        datos_ventas.append({
            'mes': calendar.month_name[mes],
            'cantidad': count
        })
    
    return datos_ventas

def obtener_ganancias_por_mes(anio):
    """Obtiene las ganancias por mes para un año específico"""
    datos_ganancias = []
    
    for mes in range(1, 13):
        # Obtener ventas para este mes y año
        ventas = Venta.query.filter(
            db.extract('year', Venta.fecha_venta) == anio,
            db.extract('month', Venta.fecha_venta) == mes
        ).all()
        
        # Calcular ganancia total
        ganancia_total = sum(venta.precio_venta - venta.auto.precio_compra for venta in ventas)
        
        # Agregar datos al resultado
        datos_ganancias.append({
            'mes': calendar.month_name[mes],
            'ganancia': ganancia_total
        })
    
    return datos_ganancias

def obtener_ventas_por_marca():
    """Obtiene el número de ventas por marca de auto"""
    # Consulta para obtener ventas agrupadas por marca
    ventas_por_marca = db.session.query(
        Auto.marca,
        db.func.count(Venta.id).label('cantidad')
    ).join(Venta, Venta.auto_id == Auto.id)\
     .group_by(Auto.marca)\
     .order_by(db.func.count(Venta.id).desc())\
     .all()
    
    return [{'marca': marca, 'cantidad': cantidad} for marca, cantidad in ventas_por_marca]

def obtener_resumen_general():
    """Obtiene un resumen general de las estadísticas"""
    # Total de autos en inventario
    total_autos = Auto.query.count()
    
    # Total de autos disponibles
    autos_disponibles = Auto.query.filter_by(estado=EstadoAuto.DISPONIBLE).count()
    
    # Total de ventas
    total_ventas = Venta.query.count()
    
    # Ventas del mes actual
    mes_actual = datetime.now().month
    anio_actual = datetime.now().year
    ventas_mes = Venta.query.filter(
        db.extract('year', Venta.fecha_venta) == anio_actual,
        db.extract('month', Venta.fecha_venta) == mes_actual
    ).count()
    
    # Ingresos totales
    ingresos_totales = db.session.query(db.func.sum(Venta.precio_venta)).scalar() or 0
    
    # Ganancias totales (precio de venta - precio de compra)
    ventas = Venta.query.all()
    ganancias_totales = sum(venta.precio_venta - venta.auto.precio_compra for venta in ventas)
    
    return {
        'total_autos': total_autos,
        'autos_disponibles': autos_disponibles,
        'total_ventas': total_ventas,
        'ventas_mes': ventas_mes,
        'ingresos_totales': ingresos_totales,
        'ganancias_totales': ganancias_totales
    }
