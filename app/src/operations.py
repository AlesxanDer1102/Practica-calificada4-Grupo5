from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.orm.strategy_options import joinedload
from sqlalchemy.sql.expression import cast
from src.models.pedido import Pedido
from src.models.producto import Producto
from src.models.usuario import Usuario


def obtener_info_completa(db: Session) -> List[Pedido]:
    """
    Obtiene información enlazada sobre los productos, usuarios y pedidos disponibles
    """
    try:
        total_pedidos = (
            db.query(Pedido)
            .options(joinedload(Pedido.usuario))
            .options(joinedload(Pedido.producto))
            .all()
        )
        return total_pedidos
    except Exception as e:
        print(f"Error en la base de datos: {e}")
        db.rollback()
        return []


def crear_usuario(db: Session, nombre: str, apellido: str) -> int:
    """
    Crea un nuevo usuario
    """
    try:
        nuevo_usuario = Usuario(nombre=nombre, apellido=apellido)
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)
        return nuevo_usuario.usuario_id
    except Exception as e:
        print(f"Error en la base de datos: {e}")
        db.rollback()
        return -1


def crear_producto(
    db: Session, nombre_producto: str, manufacturador: str, precio: float
) -> int:
    """
    Crea un nuevo producto
    """
    try:
        nuevo_producto = Producto(
            nombre_producto=nombre_producto,
            manufacturador=manufacturador,
            precio=precio,
        )
        db.add(nuevo_producto)
        db.commit()
        db.refresh(nuevo_producto)
        return nuevo_producto.producto_id
    except Exception as e:
        print(f"Error en la base de datos: {e}")
        db.rollback()
        return -1


def crear_pedido(db: Session, usuario_id: int, producto_id: int, cantidad: int) -> int:
    """
    Crea un nuevo pedido
    """
    try:
        nuevo_pedido = Pedido(
            usuario_id=usuario_id, producto_id=producto_id, cantidad=cantidad
        )
        db.add(nuevo_pedido)
        db.commit()
        db.refresh(nuevo_pedido)
        return nuevo_pedido.pedido_id
    except Exception as e:
        print(f"Error en la base de datos: {e}")
        db.rollback()
        return -1


def obtener_usuario(db: Session, usuario_id: int) -> Optional[Usuario]:
    """
    Obtiene un usuario por su ID
    """
    try:
        usuario = db.query(Usuario).filter(Usuario.usuario_id == usuario_id).first()
        return usuario
    except Exception as e:
        print(f"Error al obtener usuario: {e}")
        return None


def obtener_producto(db: Session, producto_id: int) -> Optional[Producto]:
    """
    Obtiene un producto por su ID
    """
    try:
        producto = (
            db.query(Producto).filter(Producto.producto_id == producto_id).first()
        )
        return producto
    except Exception as e:
        print(f"Error al obtener producto: {e}")
        return None


def obtener_pedido(db: Session, pedido_id: int) -> Optional[Pedido]:
    """
    Obtiene un pedido por su ID con información completa del usuario y producto
    """
    try:
        pedido = (
            db.query(Pedido)
            .options(joinedload(Pedido.usuario))
            .options(joinedload(Pedido.producto))
            .filter(Pedido.pedido_id == pedido_id)
            .first()
        )
        return pedido
    except Exception as e:
        print(f"Error al obtener pedido: {e}")
        return None


def eliminar_base_de_datos(db: Session) -> None:
    """
    Elimina todas las tablas de la base de datos
    """
    try:
        db.execute(text("DROP TABLE IF EXISTS pedidos CASCADE"))
        db.execute(text("DROP TABLE IF EXISTS productos CASCADE"))
        db.execute(text("DROP TABLE IF EXISTS usuarios CASCADE"))
        db.commit()
        print("Base de datos eliminada exitosamente")
    except Exception as e:
        print(f"Error al eliminar la base de datos: {e}")
        db.rollback()
