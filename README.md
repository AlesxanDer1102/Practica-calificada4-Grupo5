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
docker exec -it pc_db -c 'psql -U postgres'
```
