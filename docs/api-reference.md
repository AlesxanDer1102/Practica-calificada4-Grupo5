# Comandos disponibles

## Comando principal

```bash
python3 backup_orchestrator.py [OPCIONES]
```

## Comandos básicos

### Crear backup

```bash
# Backup automático (recomendado)
python3 backup_orchestrator.py

# Con información detallada
python3 backup_orchestrator.py --verbose

# Silencioso (solo errores)
python3 backup_orchestrator.py --quiet
```

### Parámetros para backup

| Opción | Qué hace | Ejemplo |
|--------|----------|---------|
| `--name` | Nombre personalizado | `--name "backup_examen"` |
| `--dir` | Donde guardar backups | `--dir /mi/carpeta/backups` |
| `--container` | Contenedor Docker específico | `--container mi_postgres` |
| `--pod` | Pod de Kubernetes | `--pod postgres-0` |
| `--namespace` | Namespace de K8s | `--namespace production` |

### Tipos de backup

```bash
# Forzar backup completo
python3 backup_orchestrator.py --force-full

# Especificar tipo manualmente
python3 backup_orchestrator.py --backup-type full
python3 backup_orchestrator.py --backup-type incremental
python3 backup_orchestrator.py --backup-type auto

# Ejemplo completo
python3 backup_orchestrator.py \
  --force-full \
  --name "backup_importante" \
  --verbose
```

## Restaurar datos

### Restauración básica

```bash
# Restauración interactiva (te deja elegir)
python3 backup_orchestrator.py --restore

# Restaurar archivo específico
python3 backup_orchestrator.py --restore \
  --restore-file backups/backup_importante.sql

# Restauración silenciosa
python3 backup_orchestrator.py --restore --quiet
```

| Opción | Qué hace | Ejemplo |
|--------|----------|---------|
| `--restore` | Activar modo restauración | `--restore` |
| `--restore-file` | Archivo específico | `--restore-file mi_backup.sql` |

## Gestión de backups

### Ver backups

```bash
# Listar todos los backups
python3 backup_orchestrator.py --list

# Con más información
python3 backup_orchestrator.py --list --verbose
```

### Limpieza

```bash
# Ver qué se eliminaría (sin borrar nada)
python3 backup_orchestrator.py --retention-dry-run

# Aplicar limpieza de backups viejos
python3 backup_orchestrator.py --apply-retention

# Ver resumen de backups y políticas
python3 backup_orchestrator.py --backup-summary
```

## Configurar retención

### Límites de backups

```bash
# Configurar cuántos backups mantener
python3 backup_orchestrator.py --retention-daily 10
python3 backup_orchestrator.py --retention-weekly 6  
python3 backup_orchestrator.py --retention-monthly 12
python3 backup_orchestrator.py --retention-full 5

# Configurar varios a la vez
python3 backup_orchestrator.py \
  --retention-daily 15 \
  --retention-weekly 8 \
  --retention-monthly 24 \
  --retention-full 10
```

### Límites por defecto

| Categoría | Cuántos mantiene | Cuándo se crean |
|-----------|------------------|-----------------|
| Daily | 7 backups | Días regulares |
| Weekly | 4 backups | Domingos |  
| Monthly | 12 backups | Día 1 del mes |
| Full | 3 backups | Backups completos |

## Opciones por entorno

### Para Docker

```bash
# Especificar contenedor
python3 backup_orchestrator.py --container postgres_container

# Forzar Docker (si la detección falla)
python3 backup_orchestrator.py --force-docker
```

### Para Kubernetes

```bash
# Pod y namespace
python3 backup_orchestrator.py \
  --pod postgres-0 \
  --namespace production

# Buscar por labels
python3 backup_orchestrator.py --labels app=postgres

# Contenedor específico dentro del pod
python3 backup_orchestrator.py \
  --pod postgres-0 \
  --k8s-container postgres

# Forzar Kubernetes
python3 backup_orchestrator.py --force-kubernetes
```

### Detección automática

```bash
# Detecta automáticamente (por defecto)
python3 backup_orchestrator.py --auto-detect

# El sistema detecta:
# - Docker: si encuentra /var/run/docker.sock
# - Kubernetes: si encuentra KUBERNETES_SERVICE_HOST
```

## Usar desde Python

Si quieres usar el sistema desde otro script Python:

```python
from backup_orchestrator import UnifiedBackupOrchestrator
from backup_cli.cli.parser import CLIConfig
import argparse

# Crear configuración simulada
mock_args = argparse.Namespace(
    container="postgres_container",
    dir="./backups",
    verbose=False,
    quiet=True,
    # ... otros parámetros necesarios según CLIConfig
)

config = CLIConfig(mock_args)
orchestrator = UnifiedBackupOrchestrator(config)

# Crear backup
success = orchestrator.create_backup()
if success:
    print("Backup creado exitosamente")

# Listar backups
backups = orchestrator.list_backups()
for backup in backups:
    print(f"Backup: {backup['name']} - {backup['size']} bytes")
```

### Métodos principales

**create_backup()**
```python
# Backup básico
success = orchestrator.create_backup()

# Con nombre personalizado  
success = orchestrator.create_backup(custom_name="mi_backup")

# Con sobrescritura
success = orchestrator.create_backup(
    custom_name="backup_importante",
    force_overwrite=True
)
```

**restore_database()**
```python
from pathlib import Path

# Restaurar archivo específico
backup_file = Path("backups/mi_backup.sql")
success = orchestrator.restore_database(backup_file)

# Restauración interactiva
success = orchestrator.restore_database()
```

**list_backups()**
```python
backups = orchestrator.list_backups()
for backup in backups:
    print(f"Archivo: {backup['name']}")
    print(f"Tamaño: {backup['size']}")
    print(f"Fecha: {backup['modified']}")
```

## Variables de entorno

### Para PostgreSQL
```bash
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=mi_password  
export POSTGRES_DB=mi_base_datos
```

### Para Kubernetes
```bash
export KUBE_NAMESPACE=default
export KUBECONFIG=/ruta/al/kubeconfig
```

### Para backups
```bash
export BACKUP_DIR=/mi/directorio/backups
export RETENTION_DAILY=7
export RETENTION_WEEKLY=4
```

## Códigos de salida

| Código | Significado |
|--------|-------------|
| 0 | Todo salió bien |
| 1 | Algo falló |

## Ejemplos completos

### Flujo típico de desarrollo

```bash
# 1. Ver qué backups tienes
python3 backup_orchestrator.py --list

# 2. Crear backup antes de cambios
python3 backup_orchestrator.py \
  --name "antes_cambios_$(date +%Y%m%d)" \
  --verbose

# 3. Verificar que se creó
python3 backup_orchestrator.py --list
```

### Migración entre entornos

```bash
# 1. Backup en origen
python3 backup_orchestrator.py \
  --force-full \
  --name "migracion_datos" \
  --container postgres_desarrollo

# 2. Restaurar en destino  
python3 backup_orchestrator.py \
  --restore \
  --restore-file backups/migracion_datos.sql \
  --container postgres_staging
```

### Restauración de emergencia

```bash
# 1. Ver backups disponibles
python3 backup_orchestrator.py --list

# 2. Restaurar el más reciente
python3 backup_orchestrator.py \
  --restore \
  --restore-file backups/backup_mas_reciente.sql \
  --verbose
```

## Para automatización (cron)

```bash
# Backup diario silencioso
0 2 * * * cd /ruta/proyecto && python3 backup_orchestrator.py --quiet

# Backup completo semanal  
0 1 * * 0 cd /ruta/proyecto && python3 backup_orchestrator.py --force-full --quiet

# Limpieza mensual
0 3 1 * * cd /ruta/proyecto && python3 backup_orchestrator.py --apply-retention --quiet
```

---

**Nota**: Todos estos comandos los probamos durante el desarrollo. Si algo no funciona, usa `--verbose` para ver qué está pasando. 