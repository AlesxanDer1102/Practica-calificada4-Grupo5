from sqlalchemy import Column, Integer, Float, String, CheckConstraint
from sqlalchemy.orm import relationship

from src.core.database import Base

# Definición de la tabla definida para Producto
class Producto(Base):
    __tablename__ = "productos"

    producto_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_producto = Column(String, nullable=False)
    manufacturador = Column(String, nullable=False)
    precio = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("precio >= 0", name="precio_check"),
    )

    pedidos = relationship("Pedido", back_populates="producto", cascade="all, delete-orphan")

    def __str__(self) -> str:
        return f"<producto(producto_id={self.producto_id}, nombre_producto={self.nombre_producto}, manufacturador={self.manufacturador}, precio={self.precio})>"
