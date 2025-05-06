from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from models import db, Auto, EstadoAuto, Venta, Usuario
from blueprints.auth import login_required
from datetime import datetime, timedelta

# Crear el blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Redirigir al login si no está autenticado, o al dashboard si lo está
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return redirect(url_for('main.dashboard'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Estadísticas para el dashboard
    autos_disponibles = Auto.query.filter_by(estado=EstadoAuto.DISPONIBLE).count()
    autos_vendidos = Auto.query.filter_by(estado=EstadoAuto.VENDIDO).count()
    
    # Ventas recientes (último mes)
    fecha_inicio = datetime.now() - timedelta(days=30)
    ventas_recientes = Venta.query.filter(Venta.fecha >= fecha_inicio).order_by(Venta.fecha.desc()).limit(5).all()
    
    # Total de ventas del mes actual
    mes_actual = datetime.now().month
    anio_actual = datetime.now().year
    total_ventas_mes = db.session.query(db.func.sum(Venta.precio_venta)).\
        filter(db.extract('month', Venta.fecha) == mes_actual).\
        filter(db.extract('year', Venta.fecha) == anio_actual).scalar() or 0
    
    # Autos agregados recientemente
    autos_recientes = Auto.query.order_by(Auto.fecha_publicacion.desc()).limit(6).all()
    
    # Estadísticas adicionales para administradores
    if session.get('rol') == 'admin':
        # Total de usuarios
        total_usuarios = Usuario.query.count()
        
        # Ganancia total del mes
        total_ganancia_mes = 0
        ventas_mes = Venta.query.filter(db.extract('month', Venta.fecha) == mes_actual).\
            filter(db.extract('year', Venta.fecha) == anio_actual).all()
        
        for venta in ventas_mes:
            ganancia = venta.precio_venta - venta.auto.precio_compra
            total_ganancia_mes += ganancia
        
        # Top vendedores del mes
        top_vendedores = db.session.query(
            Usuario.username, 
            db.func.count(Venta.id).label('total_ventas')
        ).join(Venta, Venta.vendedor_id == Usuario.id).\
            filter(db.extract('month', Venta.fecha) == mes_actual).\
            filter(db.extract('year', Venta.fecha) == anio_actual).\
            group_by(Usuario.username).\
            order_by(db.func.count(Venta.id).desc()).limit(5).all()
    else:
        total_usuarios = 0
        total_ganancia_mes = 0
        top_vendedores = []
    
    return render_template('dashboard.html',
                        autos_disponibles=autos_disponibles,
                        autos_vendidos=autos_vendidos,
                        ventas_recientes=ventas_recientes,
                        total_ventas_mes=total_ventas_mes,
                        autos_recientes=autos_recientes,
                        total_usuarios=total_usuarios,
                        total_ganancia_mes=total_ganancia_mes,
                        top_vendedores=top_vendedores)

@main_bp.route('/perfil')
@login_required
def perfil():
    # Obtener datos del usuario actual
    usuario = Usuario.query.get(session['user_id'])
    
    # Estadísticas del usuario (si es vendedor)
    if usuario.rol == 'vendedor':
        # Ventas totales
        ventas_totales = Venta.query.filter_by(vendedor_id=usuario.id).count()
        
        # Ventas del mes actual
        mes_actual = datetime.now().month
        anio_actual = datetime.now().year
        ventas_mes = Venta.query.filter_by(vendedor_id=usuario.id).\
            filter(db.extract('month', Venta.fecha) == mes_actual).\
            filter(db.extract('year', Venta.fecha) == anio_actual).count()
        
        # Monto total de ventas
        monto_total = db.session.query(db.func.sum(Venta.precio_venta)).\
            filter(Venta.vendedor_id == usuario.id).scalar() or 0
    else:
        ventas_totales = 0
        ventas_mes = 0
        monto_total = 0
    
    return render_template('perfil.html',
                        usuario=usuario,
                        ventas_totales=ventas_totales,
                        ventas_mes=ventas_mes,
                        monto_total=monto_total)
