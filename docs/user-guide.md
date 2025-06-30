# Guía de Usuario

## Setup inicial

### Lo que necesitas tener instalado

- Python 3.10 o mayor
- Docker funcionando O un cluster de Kubernetes local
- PostgreSQL corriendo en contenedor/pod

### Instalación

```bash
# Clona nuestro proyecto
git clone https://github.com/AlesxanDer1102/Practica-calificada4-Grupo5
cd Practica-calificada4-Grupo5

# Crea el entorno virtual (recomendado)
python3 -m venv .venv
source .venv/bin/activate

# Instala las dependencias
pip install -r requirements.txt
```

### Prueba que funciona

```bash
# Si tienes backups, los verás listados
python3 backup_orchestrator.py --list

# Si no tienes backups aún, verás:
# No se encontraron archivos de backup
```

## Casos de uso que probamos

### 1. Backup rutinario para desarrollo

**Situación**: Necesitas backup diario mientras desarrollas.

```bash
# Backup automático (el sistema decide si full o incremental)
python3 backup_orchestrator.py

# Si quieres ver que está pasando:
python3 backup_orchestrator.py --verbose
```

El sistema detecta automáticamente si estás en Docker o Kubernetes y hace lo necesario.

### 2. Backup antes de cambios importantes

**Situación**: Vas a hacer cambios grandes en la DB y quieres un punto de restauración.

```bash
# Backup completo con nombre descriptivo
python3 backup_orchestrator.py \
  --force-full \
  --name "antes_refactor_schema" \
  --verbose

# Verifica que se creó
python3 backup_orchestrator.py --list
```

### 3. Restaurar cuando algo se rompió

**Situación**: Algo salió mal y necesitas restaurar datos.

```bash
# Opción 1: Selección interactiva (más fácil)
python3 backup_orchestrator.py --restore

# Te muestra una lista numerada de backups disponibles:
# 1. antes_refactor_schema.sql     5.2 MB    2024-06-30 14:25:30
# 2. backup_20240629_103045.sql   4.8 MB    2024-06-29 10:30:45
# Seleccione el número del backup (0 para cancelar): 1

# Opción 2: Archivo específico
python3 backup_orchestrator.py \
  --restore \
  --restore-file backups/antes_refactor_schema.sql
```

### 4. Migrar datos entre entornos

**Situación**: Copiar datos de desarrollo a staging.

```bash
# 1. Backup en desarrollo
python3 backup_orchestrator.py \
  --force-full \
  --name "datos_para_staging" \
  --container postgres_dev

# 2. Copiar el archivo al otro ambiente
scp backups/datos_para_staging.sql servidor_staging:/tmp/

# 3. Restaurar en staging
python3 backup_orchestrator.py \
  --restore \
  --restore-file /tmp/datos_para_staging.sql \
  --container postgres_staging
```

### 5. Automatizar con cron

**Situación**: Backup automático sin que tengas que acordarte.

```bash
# Edita tu crontab
crontab -e

# Backup diario a las 2 AM
0 2 * * * cd /ruta/al/proyecto && python3 backup_orchestrator.py --quiet

# Backup completo semanal (domingos a la 1 AM)  
0 1 * * 0 cd /ruta/al/proyecto && python3 backup_orchestrator.py --force-full --quiet

# Limpieza mensual de backups viejos
0 3 1 * * cd /ruta/al/proyecto && python3 backup_orchestrator.py --apply-retention
```

## Configuraciones que aprendimos a usar

### Retención personalizada

Por defecto el sistema mantiene:
- 7 backups diarios
- 4 backups semanales  
- 12 backups mensuales
- 3 backups completos

Pero puedes cambiarlo:

```bash
# Para desarrollo (menos espacio)
python3 backup_orchestrator.py \
  --retention-daily 3 \
  --retention-weekly 1 \
  --retention-monthly 1

# Para producción (más historia)
python3 backup_orchestrator.py \
  --retention-daily 30 \
  --retention-weekly 12 \
  --retention-monthly 24
```

### Trabajar con Kubernetes

```bash
# Backup en pod específico
python3 backup_orchestrator.py \
  --pod postgres-primary-0 \
  --namespace production

# Si tienes múltiples namespaces
for env in development staging production; do
  python3 backup_orchestrator.py \
    --pod postgres-0 \
    --namespace $env \
    --name "${env}_backup"
done
```

## Problemas comunes que resolvimos

### "Container not found"

```bash
# Verifica que contenedores tienes corriendo
docker ps

# Usa el nombre correcto
python3 backup_orchestrator.py --container nombre_real_del_contenedor
```

### "Permission denied"

```bash
# Verifica permisos del directorio de backups
ls -la backups/

# Si no existe, créalo
mkdir -p backups
chmod 755 backups
```

### "Database connection failed"

```bash
# Verifica que la DB responde
docker exec -it postgres_container psql -U postgres -l

# Checa las variables de entorno de tu contenedor
docker exec postgres_container env | grep POSTGRES
```

### El backup parece que se colgó

```bash
# Usa verbose para ver qué está pasando
python3 backup_orchestrator.py --verbose

# Checa los logs del contenedor
docker logs postgres_container -f
```

## Prácticas que nos funcionaron

### 1. Buenos nombres para backups

```bash
# Descriptivos y con fecha
--name "pre_sprint3_$(date +%Y%m%d)"
--name "antes_migracion_usuarios"  
--name "backup_demo_final"
--name "punto_estable_v1"

# Evita nombres genéricos
--name "backup"      # ¿cuál backup?
--name "test"        # ¿qué estas probando?
--name "temp"        # temporal para siempre
```

### 2. Estrategia de retención que usamos

```bash
# Configuración balanceada que probamos
python3 backup_orchestrator.py \
  --retention-daily 14 \    # 2 semanas diarias
  --retention-weekly 8 \    # 2 meses semanales  
  --retention-monthly 12 \  # 1 año mensuales
  --retention-full 5        # 5 puntos críticos
```

### 3. Verificación después de backups importantes

```bash
# Después de un backup crítico, siempre verifica
python3 backup_orchestrator.py --force-full --name "critico"
python3 backup_orchestrator.py --list

# Y prueba la restauración en un ambiente de pruebas
python3 backup_orchestrator.py \
  --restore \
  --restore-file backups/critico.sql \
  --container postgres_test
```

## Integración con docker-compose

Como desarrollamos con docker-compose, aquí está nuestro setup:

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    container_name: postgres_container  # Nombre que usa el script
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: 12345           # Hardcoded como pide el proyecto  
      POSTGRES_DB: pc_db                 # Base de datos por defecto
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups              # Para acceder a backups desde host
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

Con este setup, el comando básico funciona directo:

```bash
docker-compose up -d
python3 backup_orchestrator.py
```

## Variables de entorno útiles

```bash
# En tu .bashrc o .zshrc para no escribir siempre lo mismo
export BACKUP_DIR="/ruta/personalizada/backups"
export POSTGRES_CONTAINER="mi_postgres_container"

# Para diferentes ambientes
export BACKUP_CONFIG_DEV="--retention-daily 3"
export BACKUP_CONFIG_PROD="--retention-daily 30 --retention-full 10"

# Usar la configuración
python3 backup_orchestrator.py $BACKUP_CONFIG_DEV
```

## FAQ - Preguntas que nos surgieron

### ¿Cuándo usar backup full vs incremental?

- **Full**: Antes de cambios importantes, weekly, o si no tienes full reciente
- **Incremental**: Para backups diarios regulares
- **Auto**: Deja que el sistema decida (recomendado para uso normal)

### ¿Cómo sé si mi backup está bien?

El script valida automáticamente, pero puedes verificar manualmente:

```bash
# Ver info del archivo
file backups/mi_backup.sql
ls -lh backups/mi_backup.sql

# Ver las primeras líneas (debe parecer SQL válido)
head -20 backups/mi_backup.sql
```

### ¿Puedo usar diferente contenedor?

Si, especifica el nombre:

```bash
python3 backup_orchestrator.py --container mi_postgres_diferente
```

### ¿Funciona con Kubernetes en la nube?

Mientras tengas `kubectl` configurado y acceso al cluster, si. Usa:

```bash
python3 backup_orchestrator.py --pod nombre-pod --namespace mi-namespace
```

## Scripts útiles que creamos

### Backup múltiple

```bash
#!/bin/bash
# backup_all_envs.sh

envs=("development" "staging" "production")

for env in "${envs[@]}"; do
  echo "Backing up $env..."
  python3 backup_orchestrator.py \
    --pod postgres-0 \
    --namespace $env \
    --name "${env}_$(date +%Y%m%d)" \
    --verbose
done

echo "Backups completados"
```

### Monitoreo básico

```bash
#!/bin/bash
# check_backups.sh

backup_count=$(python3 backup_orchestrator.py --list 2>/dev/null | wc -l)

if [ $backup_count -lt 3 ]; then
  echo "ALERTA: Solo $backup_count backups disponibles"
  exit 1
else
  echo "OK: $backup_count backups disponibles"
  exit 0
fi
```

---

**Nota**: Esta guía está basada en nuestra experiencia desarrollando el proyecto. Si encuentras algo que no funciona o tienes dudas, revisa los logs con `--verbose` o consulta la [documentación técnica](architecture.md). 