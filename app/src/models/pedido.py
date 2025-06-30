from sqlalchemy import Column, Integer, DateTime, CheckConstraint, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.core.database import Base


# Definición de la tabla definida para Pedido
class Pedido(Base):
    __tablename__ = "pedidos"

    pedido_id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(
        Integer, ForeignKey("usuarios.usuario_id", ondelete="CASCADE"), nullable=False
    )
    producto_id = Column(
        Integer, ForeignKey("productos.producto_id", ondelete="CASCADE"), nullable=False
    )
    cantidad = Column(Integer, nullable=False)
    fecha_pedido = Column(DateTime, nullable=False, default=func.now())

    __table_args__ = (CheckConstraint("cantidad >= 0", name="cantidad_check"),)

    usuario = relationship("Usuario", back_populates="pedidos")
    producto = relationship("Producto", back_populates="pedidos")

    def __str__(self) -> str:
        return f"<pedido(pedido_id={self.pedido_id}, usuario_id={self.usuario_id}, producto_id={self.producto_id}, cantidad={self.cantidad}, fecha_pedido={self.fecha_pedido})>"
