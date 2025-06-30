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


# Orquestrador de Backup

## Funcionalidades

- **Detección automática de entorno**: Docker vs Kubernetes
- **Estrategias de backup**: Completos e incrementales con decisión automática
- **Políticas de retención**: Eliminación automática por categorías (daily, weekly, monthly, full)
- **Multi-entorno**: Contenedores Docker y pods Kubernetes

## Estrategias de Backup

### Backup Completo (Full)
- Incluye esquema completo y todos los datos
- Argumentos pg_dump: `--clean --create --verbose`
- Se ejecuta automáticamente cuando:
  - No existe backup completo previo
  - Último backup completo > 7 días
  - Hay más de 5 backups incrementales desde el último completo

### Backup Incremental
- Backup optimizado sin metadatos de permisos
- Argumentos pg_dump: `--verbose --no-owner --no-privileges`
- Se ejecuta cuando hay un backup completo reciente y pocos incrementales

### Decisión Automática
- El sistema evalúa el estado actual y decide el tipo apropiado
- Mantiene balance entre eficiencia y completitud
- Utiliza metadatos almacenados en `.metadata/backup_state.json`

## Comandos de Backup

### Comandos Básicos
```bash
# Backup automático (decisión inteligente)
python3 backup_orchestrator.py

# Backup con información detallada
python3 backup_orchestrator.py --verbose

# Backup con nombre personalizado
python3 backup_orchestrator.py --name "backup_personalizado"

# Backup en directorio específico
python3 backup_orchestrator.py --dir /ruta/backups
```

### Estrategias Específicas
```bash
# Forzar backup completo
python3 backup_orchestrator.py --force-full

# Especificar tipo explícitamente
python3 backup_orchestrator.py --backup-type full
python3 backup_orchestrator.py --backup-type incremental
python3 backup_orchestrator.py --backup-type auto

# Backup completo con nombre específico
python3 backup_orchestrator.py --force-full --name "pre_migration"
```

### Restauración
```bash
# Restauración interactiva (selecciona de lista)
python3 backup_orchestrator.py --restore

# Restaurar archivo específico
python3 backup_orchestrator.py --restore --restore-file backups/backup_20250630.sql

# Restauración silenciosa
python3 backup_orchestrator.py --restore --quiet
```

## Políticas de Retención

### Categorías de Retención
- **Daily**: Backups regulares (lunes a sábado)
- **Weekly**: Backups creados en domingo
- **Monthly**: Backups creados el día 1 del mes
- **Full**: Todos los backups completos

### Límites por Defecto
- Daily: 7 backups
- Weekly: 4 backups
- Monthly: 12 backups
- Full: 3 backups

### Comandos de Configuración
```bash
# Configurar políticas individuales
python3 backup_orchestrator.py --retention-daily 10
python3 backup_orchestrator.py --retention-weekly 6
python3 backup_orchestrator.py --retention-monthly 24
python3 backup_orchestrator.py --retention-full 5

# Configurar múltiples políticas
python3 backup_orchestrator.py \
  --retention-daily 15 \
  --retention-weekly 8 \
  --retention-monthly 36 \
  --retention-full 10
```

### Aplicación de Políticas
```bash
# Ver qué backups se eliminarían (dry run)
python3 backup_orchestrator.py --retention-dry-run

# Aplicar políticas de retención
python3 backup_orchestrator.py --apply-retention

# Configurar y aplicar en un comando
python3 backup_orchestrator.py \
  --retention-daily 5 \
  --apply-retention
```

## Comandos de Gestión

### Información y Listado
```bash
# Listar backups existentes
python3 backup_orchestrator.py --list

# Resumen completo de backups y políticas
python3 backup_orchestrator.py --backup-summary

# Ver ayuda completa
python3 backup_orchestrator.py --help
```

### Opciones de Salida
```bash
# Ejecución silenciosa
python3 backup_orchestrator.py --quiet

# Sin colores en la salida
python3 backup_orchestrator.py --no-color

# Sobrescribir backup existente
python3 backup_orchestrator.py --name "backup" --force
```

## Comandos Específicos por Entorno

### Kubernetes
```bash
# Detección automática (busca app=postgres)
python3 backup_orchestrator.py

# Pod específico
python3 backup_orchestrator.py --pod postgres-0

# Namespace específico
python3 backup_orchestrator.py --pod postgres-0 --namespace production

# Selección por labels
python3 backup_orchestrator.py --labels app=postgres,version=13

# Contenedor específico en pod
python3 backup_orchestrator.py --pod postgres-0 --k8s-container postgres

# Forzar entorno Kubernetes
python3 backup_orchestrator.py --force-kubernetes
```

### Docker
```bash
# Detección automática de contenedores PostgreSQL
python3 backup_orchestrator.py

# Contenedor específico
python3 backup_orchestrator.py --container postgres_container

# Forzar entorno Docker
python3 backup_orchestrator.py --force-docker
```

## Combinaciones de Comandos

### Flujo de Desarrollo
```bash
# Backup antes de cambios importantes
python3 backup_orchestrator.py --force-full --name "pre_changes"

# Backup diario automático
python3 backup_orchestrator.py

# Limpieza semanal
python3 backup_orchestrator.py --retention-dry-run
python3 backup_orchestrator.py --apply-retention
```

### Flujo de Producción
```bash
# Configuración robusta
python3 backup_orchestrator.py \
  --retention-daily 30 \
  --retention-weekly 12 \
  --retention-monthly 24 \
  --retention-full 12 \
  --force-full \
  --name "prod_$(date +%Y%m%d)"

# Monitoreo regular
python3 backup_orchestrator.py --backup-summary
```

### Mantenimiento
```bash
# Revisión completa del sistema
python3 backup_orchestrator.py --backup-summary
python3 backup_orchestrator.py --retention-dry-run
python3 backup_orchestrator.py --apply-retention
python3 backup_orchestrator.py --list
```

## Estructura de Archivos

```
backups/
├── backup_20250630_143022_full.sql
├── backup_20250701_020000_incremental.sql
└── .metadata/
    ├── backup_state.json
    ├── backup_20250630_143022_full.json
    └── backup_20250701_020000_incremental.json
```

## Configuración de Base de Datos

El sistema utiliza automáticamente:
- Database: `pc_db`
- Usuario: `postgres`
- Password: `12345`
- Detección automática de pod `postgres-0` con label `app=postgres`


## Githooks

Para este proyecto estaremos utilizando githooks para validar commits y push, para poder tenerlo activo localmente usa el siguiente comando

Para dar permisos\
```
chmod +x .githooks/setup.sh
```

```
.githooks/setup.sh
```
