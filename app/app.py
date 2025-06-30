from datetime import datetime
from src.core.database import SessionLocal
from src.operations import *

def mostrar_menu():
    """
    Muestra el menú principal de opciones
    """
    print("\n" + "="*50)
    print("         SISTEMA DE GESTIÓN DE PEDIDOS")
    print("="*50)
    print("1. Ver todos los pedidos")
    print("2. Crear usuario")
    print("3. Crear producto")
    print("4. Crear pedido")
    print("5. Buscar usuario por ID")
    print("6. Buscar producto por ID")
    print("7. Buscar pedido por ID")
    print("8. Eliminar base de datos")
    print("9. Salir")
    print("="*50)

def validar_entero(mensaje: str) -> int:
    """
    Obtiene una entrada entera del usuario con validación
    """
    while True:
        try:
            return int(input(mensaje))
        except ValueError:
            print("Por favor, ingrese un número válido.")

def validar_float(mensaje: str) -> float:
    """
    Obtiene una entrada flotante del usuario con validación
    """
    while True:
        try:
            return float(input(mensaje))
        except ValueError:
            print("Por favor, ingrese un número decimal válido.")

def manejar_ver_pedidos(db: Session):
    """
    Maneja la opción de ver todos los pedidos
    """
    print("\n--- TODOS LOS PEDIDOS ---")
    pedidos = obtener_info_completa(db)

    if not pedidos:
        print("No hay pedidos registrados.")
        return

    for pedido in pedidos:
        print(f"\nPedido ID: {pedido.pedido_id}")
        print(f"Usuario: {pedido.usuario.nombre} {pedido.usuario.apellido}")
        print(f"Producto: {pedido.producto.nombre_producto}")
        print(f"Manufacturador: {pedido.producto.manufacturador}")
        print(f"Cantidad: {pedido.cantidad}")
        print(f"Precio unitario: ${pedido.producto.precio}")
        print(f"Total: ${pedido.producto.precio * pedido.cantidad}")
        print(f"Fecha: {pedido.fecha_pedido}")
        print("-" * 40)

def manejar_crear_usuario(db: Session):
    """
    Maneja la creación de un nuevo usuario
    """
    print("\n--- CREAR USUARIO ---")
    nombre = input("Ingrese el nombre: ").strip()
    apellido = input("Ingrese el apellido: ").strip()

    if not nombre or not apellido:
        print("El nombre y apellido no pueden estar vacíos.")
        return

    usuario_id = crear_usuario(db, nombre, apellido)
    if usuario_id > 0:
        print(f"Usuario creado exitosamente con ID: {usuario_id}")
    else:
        print("Error al crear el usuario.")

def manejar_crear_producto(db: Session):
    """
    Maneja la creación de un nuevo producto
    """
    print("\n--- CREAR PRODUCTO ---")
    nombre_producto = input("Ingrese el nombre del producto: ").strip()
    manufacturador = input("Ingrese el manufacturador: ").strip()
    precio = validar_float("Ingrese el precio: $")

    if not nombre_producto or not manufacturador:
        print("El nombre del producto y manufacturador no pueden estar vacíos.")
        return

    if precio <= 0:
        print("El precio debe ser mayor a 0.")
        return

    producto_id = crear_producto(db, nombre_producto, manufacturador, precio)
    if producto_id > 0:
        print(f"Producto creado exitosamente con ID: {producto_id}")
    else:
        print("Error al crear el producto.")

def manejar_crear_pedido(db: Session):
    """
    Maneja la creación de un nuevo pedido
    """
    print("\n--- CREAR PEDIDO ---")
    usuario_id = validar_entero("Ingrese el ID del usuario: ")
    producto_id = validar_entero("Ingrese el ID del producto: ")
    cantidad = validar_entero("Ingrese la cantidad: ")

    if cantidad <= 0:
        print("La cantidad debe ser mayor a 0.")
        return

    usuario = obtener_usuario(db, usuario_id)
    producto = obtener_producto(db, producto_id)

    if not usuario:
        print(f"No se encontró un usuario con ID: {usuario_id}")
        return

    if not producto:
        print(f"No se encontró un producto con ID: {producto_id}")
        return

    pedido_id = crear_pedido(db, usuario_id, producto_id, cantidad)

    if pedido_id > 0:
        print(f"Pedido creado exitosamente con ID: {pedido_id}")
        print(f"Usuario: {usuario.nombre} {usuario.apellido}")
        print(f"Producto: {producto.nombre_producto}")
        print(f"Cantidad: {cantidad}")
        print(f"Total: ${producto.precio * cantidad}")
    else:
        print("Error al crear el pedido.")

def manejar_buscar_usuario(db: Session):
    """
    Maneja la búsqueda de un usuario por ID
    """
    print("\n--- BUSCAR USUARIO ---")
    usuario_id = validar_entero("Ingrese el ID del usuario: ")

    usuario = obtener_usuario(db, usuario_id)
    if usuario:
        print(f"\nUsuario encontrado:")
        print(f"ID: {usuario.usuario_id}")
        print(f"Nombre: {usuario.nombre}")
        print(f"Apellido: {usuario.apellido}")
    else:
        print(f"No se encontró un usuario con ID: {usuario_id}")

def manejar_buscar_producto(db: Session):
    """
    Maneja la búsqueda de un producto por ID
    """
    print("\n--- BUSCAR PRODUCTO ---")
    producto_id = validar_entero("Ingrese el ID del producto: ")

    producto = obtener_producto(db, producto_id)
    if producto:
        print(f"\nProducto encontrado:")
        print(f"ID: {producto.producto_id}")
        print(f"Nombre: {producto.nombre_producto}")
        print(f"Manufacturador: {producto.manufacturador}")
        print(f"Precio: ${producto.precio}")
    else:
        print(f"No se encontró un producto con ID: {producto_id}")

def manejar_buscar_pedido(db: Session):
    """
    Maneja la búsqueda de un pedido por ID
    """
    print("\n--- BUSCAR PEDIDO ---")
    pedido_id = validar_entero("Ingrese el ID del pedido: ")

    pedido = obtener_pedido(db, pedido_id)
    if pedido:
        print(f"\nPedido encontrado:")
        print(f"ID: {pedido.pedido_id}")
        print(f"Usuario: {pedido.usuario.nombre} {pedido.usuario.apellido}")
        print(f"Producto: {pedido.producto.nombre_producto}")
        print(f"Manufacturador: {pedido.producto.manufacturador}")
        print(f"Cantidad: {pedido.cantidad}")
        print(f"Precio unitario: ${pedido.producto.precio}")
        print(f"Total: ${pedido.producto.precio * pedido.cantidad}")
        print(f"Fecha: {pedido.fecha_pedido}")
    else:
        print(f"No se encontró un pedido con ID: {pedido_id}")

def manejar_eliminar_base_datos(db: Session):
    """
    Maneja la eliminación de la base de datos
    """
    print("\n--- ELIMINAR BASE DE DATOS ---")
    confirmacion = input("¿Está seguro que desea eliminar TODA la base de datos? (si/no): ").lower().strip()

    if confirmacion in ['si', 'sí', 's', 'yes', 'y']:
        eliminar_base_de_datos(db)
        print("¡ADVERTENCIA! La base de datos ha sido eliminada.")
    else:
        print("Operación cancelada.")

def main():
    print("¡Bienvenido al Sistema de Gestión de Pedidos!")

    while True:
        db = None
        try:
            db = SessionLocal()
            mostrar_menu()
            opcion = input("\nSeleccione una opción (1-9): ").strip()

            if opcion == "1":
                manejar_ver_pedidos(db)
            elif opcion == "2":
                manejar_crear_usuario(db)
            elif opcion == "3":
                manejar_crear_producto(db)
            elif opcion == "4":
                manejar_crear_pedido(db)
            elif opcion == "5":
                manejar_buscar_usuario(db)
            elif opcion == "6":
                manejar_buscar_producto(db)
            elif opcion == "7":
                manejar_buscar_pedido(db)
            elif opcion == "8":
                manejar_eliminar_base_datos(db)
            elif opcion == "9":
                print("\n¡Gracias por usar el Sistema de Gestión de Pedidos!")
                print("¡Hasta luego!")
                break
            else:
                print("Opción no válida. Por favor, seleccione una opción del 1 al 9.")

            input("\nPresione Enter para continuar...")

        except KeyboardInterrupt:
            print("\n\nPrograma interrumpido por el usuario.")
            break
        except Exception as e:
            print(f"\nError inesperado: {e}")
        finally:
            if db is not None:
                db.close()

if __name__ == "__main__":
    main()
