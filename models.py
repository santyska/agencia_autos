from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum

db = SQLAlchemy()

class EstadoAuto(enum.Enum):
    DISPONIBLE = "Disponible"
    RESERVADO = "Reservado"
    VENDIDO = "Vendido"
    REPARACION = "En reparación"
    BAJA = "Baja"

class EstadoVenta(enum.Enum):
    PENDIENTE = "Pendiente"
    PAGADO = "Pagado"
    CANCELADO = "Cancelado"
    REPARACION = "En reparación"
    BAJA = "Baja"

class EstadoPago(enum.Enum):
    PENDIENTE = "Pendiente"
    SEÑADO = "Señado"
    PAGADO = "Pagado"
    CANCELADO = "Cancelado"

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    rol = db.Column(db.String(20), default='vendedor')  # 'administrador_jefe', 'administrador' o 'vendedor'
    porcentaje_comision = db.Column(db.Float, default=5.0)  # Porcentaje de comisión por venta
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    
    # Relación con ventas
    ventas = db.relationship('Venta', backref='vendedor', lazy=True)
    
    def __repr__(self):
        return f'<Usuario {self.username}>'

class Auto(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Identificador único
    marca = db.Column(db.String(50), nullable=False)  # Marca del auto
    modelo = db.Column(db.String(50), nullable=False)  # Modelo del auto
    anio = db.Column(db.Integer, nullable=False)  # Año de fabricación
    precio = db.Column(db.Float, nullable=False)  # Precio de venta (público)
    precio_compra = db.Column(db.Float, default=0)  # Precio de compra (solo admin)
    moneda = db.Column(db.String(3), default='ARS')  # Moneda (ARS o USD)
    descripcion = db.Column(db.Text)  # Descripción detallada
    estado = db.Column(db.Enum(EstadoAuto), default=EstadoAuto.DISPONIBLE)  # Estado del auto
    fecha_publicacion = db.Column(db.DateTime, default=datetime.utcnow)
    color = db.Column(db.String(50))  # Color del auto
    kilometraje = db.Column(db.Integer)  # Kilometraje
    url_compartir = db.Column(db.String(255))  # URL para compartir
    
    # Relación con fotos
    fotos = db.relationship('FotoAuto', backref='auto', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Auto {self.marca} {self.modelo}>'
        
    @property
    def foto_principal(self):
        """Retorna la primera foto o None si no hay fotos"""
        return self.fotos[0] if self.fotos else None

class FotoAuto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    auto_id = db.Column(db.Integer, db.ForeignKey('auto.id'), nullable=False)
    ruta_archivo = db.Column(db.String(255), nullable=False)  # Ruta al archivo de imagen
    es_principal = db.Column(db.Boolean, default=False)  # Indica si es la foto principal
    orden = db.Column(db.Integer, default=0)  # Orden para mostrar en el carrusel
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Foto {self.id} de Auto {self.auto_id}>"

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    auto_id = db.Column(db.Integer, db.ForeignKey('auto.id'), nullable=False)
    fecha_seña = db.Column(db.DateTime, nullable=False)
    fecha_venta = db.Column(db.DateTime, nullable=True)
    
    # Datos del cliente
    cliente_nombre = db.Column(db.String(100), nullable=False)
    cliente_apellido = db.Column(db.String(100), nullable=False)
    cliente_telefono = db.Column(db.String(20))
    cliente_email = db.Column(db.String(100))
    cliente_dni = db.Column(db.String(20))
    
    # Datos financieros
    precio_compra = db.Column(db.Float, default=0)
    precio_venta = db.Column(db.Float, nullable=False)
    moneda = db.Column(db.String(3), default='ARS')  # Moneda (ARS o USD)
    monto_seña = db.Column(db.Float, default=0)
    saldo_restante = db.Column(db.Float, default=0)
    estado_pago = db.Column(db.Enum(EstadoPago), default=EstadoPago.PENDIENTE)
    
    # Datos de comisión
    ganancia = db.Column(db.Float, default=0)  # Calculado al crear/actualizar la venta
    vendedor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    monto_comision = db.Column(db.Float, default=0)  # Calculado basado en ganancia y porcentaje
    comision_pagada = db.Column(db.Boolean, default=False)  # Si ya se pagó la comisión
    
    # Notas y observaciones
    observaciones = db.Column(db.Text)  # Notas adicionales sobre la venta
    
    # Relaciones
    auto = db.relationship('Auto', backref=db.backref('ventas', lazy=True))
    
    def calcular_ganancia(self):
        """Calcula la ganancia de la venta"""
        return self.precio_venta - self.precio_compra
    
    def calcular_ganancia_neta(self):
        """Calcula la ganancia después de comisiones"""
        return self.ganancia - (self.monto_comision or 0)
    
    def calcular_comision(self):
        """Calcula la comisión del vendedor basada en su porcentaje"""
        if self.vendedor and hasattr(self.vendedor, 'porcentaje_comision'):
            return (self.ganancia * self.vendedor.porcentaje_comision) / 100
        return 0
    
    def actualizar_calculos(self):
        """Actualiza todos los cálculos de la venta"""
        self.ganancia = self.calcular_ganancia()
        self.monto_comision = self.calcular_comision()
        self.saldo_restante = self.precio_venta - self.monto_seña

    def __repr__(self):
        return f'<Venta {self.id} - {self.cliente_nombre}>'

# Tabla para registrar pagos parciales
class Pago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('venta.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    monto = db.Column(db.Float, nullable=False)
    metodo_pago = db.Column(db.String(50))  # Efectivo, Transferencia, etc.
    comprobante = db.Column(db.String(255))  # Número de comprobante o referencia
    
    # Relación con la venta
    venta = db.relationship('Venta', backref=db.backref('pagos', lazy=True))
    
    def __repr__(self):
        return f'<Pago {self.id} de Venta {self.venta_id}: ${self.monto}>'

