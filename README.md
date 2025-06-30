# Nombre del proyecto: Orquestador de backups y restauración de datos locales

Este proyecto consiste en la creación de una herramienta que orquestre la copia de seguridad y restauración de datos para bases de datos o servicios con estado en un entorno local, usando volúmenes de Docker o persistencia de Kubernetes.

## Avances desarrollados:

Contamos con un archivo `docker-compose.yml` con la definición de un contenedor `pc_db` en base a una imagen de `PostgreSQL:15` que nos ayude a probar y ejecutar nuestro proyecto consistentemente. Nuestro contenedor contará con la siguiente configuración:

- **Named Volume:** De nombre `postgres_data` almacenado en la dirección `/var/lib/postgresql/data/` dentro del contenedor.
- **Variables de entorno:**
  - _postgres_user_: postgres
  - _postgres_password_: 12345
  - _postgres_db_: pc_db
- **Puerto de conexión**: 5432:5432

Para contar con acceso a este contenedor podemos ejecutar:

```bash
# Creamos los contenedores necesarios
docker-compose up --build

# Accedemos a la interfaz de terminal de la base de datos del contenedor
docker exec -it pc_db bash -c 'psql -U postgres -d pc_db'

# Para eliminar el contendor con sus datos
docker-compose down -v
```

Contamos tambien con el archivo `backup_orchestrator.py` el cual es el script encargado de realizar los backups de las bases de datos de PostgreSql utilizando docker exec el cual generara una carpeta `backups` y guardara un backup con el nombre formateado con el timestamp maneja errores y da informacion de este, para ejecutarlo se debe hacer lo siguiente

```bash
# Creamos el backup con el script
python3 backup_orchestrator.py

# Crear backup con nombre personalizado
python3 backup_orchestrator.py --name mi_backup_especial

# Listar todos los backups disponibles
python3 backup_orchestrator.py --list

```

### Características de Seguridad en Restauración

- **Validación de integridad**: Verifica que el archivo de backup sea válido antes de restaurar
- **Confirmación obligatoria**: Solicita confirmación explícita antes de sobrescribir datos
- **Información detallada**: Muestra información del backup y base de datos objetivo
- **Cancelación segura**: Permite cancelar en cualquier momento del proceso
- **Verificación de contenedor**: Confirma que el contenedor Docker esté disponible
```
# Restauración interactiva
python3 backup_orchestrator.py --restore

# Restaurar archivo específico
python3 backup_orchestrator.py --restore --restore-file backups/backup.sql

```

Se añadió una pequeña aplicación de demostración para la interacción con la base de datos en `src\` accedida mediante `main.py`.
Este es un simple sistema CRUD que maneja usuarios, productos y pedidos; se tienen la siguientes relaciones:

### Tabla usuarios

| Nombre de la columna | Tipo de dato | Restricciones |
| -------------------- | ------------ | ------------- |
| usuario_id           | INTEGER      | PRIMARY KEY   |
| nombre               | STRING       | NOT NULL      |
| apellido             | STRING       | NOT NULL      |

### Tabla productos

| Nombre de la columna | Tipo de dato | Restricciones                 |
| -------------------- | ------------ | ----------------------------- |
| producto_id          | INTEGER      | PRIMARY KEY, AUTO_INCREMENT   |
| nombre_producto      | STRING       | NOT NULL                      |
| manufacturador       | STRING       | NOT NULL                      |
| precio               | FLOAT        | NOT NULL, CHECK (precio >= 0) |

### Tabla pedidos

| Nombre de la columna | Tipo de dato | Restricciones                                                    |
| -------------------- | ------------ | ---------------------------------------------------------------- |
| pedido_id            | INTEGER      | PRIMARY KEY, AUTO_INCREMENT                                      |
| usuario_id           | INTEGER      | FOREIGN KEY → usuarios.usuario_id, NOT NULL, ON DELETE CASCADE   |
| producto_id          | INTEGER      | FOREIGN KEY → productos.producto_id, NOT NULL, ON DELETE CASCADE |
| cantidad             | INTEGER      | NOT NULL, CHECK (cantidad >= 0)                                  |
| fecha_pedido         | DATETIME     | NOT NULL, DEFAULT = NOW()                                        |

### Diagrama Entidad-Relación (Representación gráfica)

```

usuarios:                    pedidos:                     productos:
┌──────────────┐            ┌──────────────┐            ┌──────────────┐
│ usuario_id   │◄───────────┤ usuario_id   │            │ producto_id  │
│ nombre       │            │ producto_id  ├───────────►│ nombre_prod. │
│ apellido     │            │ pedido_id    │            │ manufact.    │
└──────────────┘            │ cantidad     │            │ precio       │
                            │ fecha_pedido │            └──────────────┘
                            └──────────────┘
```

La aplicación cuenta con funcionalidades de un sistema CRUD básico que muestre los datos almacenados desde nuestro contenedor Docker mediante operaciones como:

- **obtener_info_completa**: Obtiene todos los pedidos con información relacionada de usuarios y productos
- **crear_usuario**: Crea un nuevo usuario en el sistema con nombre y apellido
- **crear_producto**: Registra un nuevo producto con nombre, fabricante y precio
- **crear_pedido**: Genera un nuevo pedido asociando usuario, producto y cantidad
- **obtener_usuario**: Busca y retorna un usuario específico por su ID
- **obtener_producto**: Busca y retorna un producto específico por su ID
- **obtener_pedido**: Busca un pedido específico con toda su información relacionada
- **eliminar_base_de_datos**: Elimina todas las tablas y datos de la base de datos

### Acceso a la aplicación

Para acceder a la aplicación se requiere de una inicialización de nuestro contenedor Docker con los comandos anteriormente mencionados. Ahora podemos ejecutar la aplicación de terminal mediante los siguientes comandos:

```bash
# Iniciamos un entorno virtual de python3
python3 -m venv .venv

# Accedemos a este entorno de trabajo
source .venv/bin/activate

# Instalamos las dependencias necesarias
pip3 install -r requirements.txt

# Ejecutamos nuestra aplicación
python3 app.py
```

## Githooks

Para este proyecto estaremos utilizando githooks para validar commits y push, para poder tenerlo activo localmente usa el siguiente comando

Para dar permisos\
```
chmod +x .githooks/setup.sh
```

```
.githooks/setup.sh
```
