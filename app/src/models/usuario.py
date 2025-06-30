from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from src.core.database import Base


# Definición de la tabla definida para Usuario
class Usuario(Base):
    __tablename__ = "usuarios"

    usuario_id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=False)

    pedidos = relationship(
        "Pedido", back_populates="usuario", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return f"<usuario(usuario_id={self.usuario_id}, nombre={self.nombre}, apellido={self.apellido})>"
