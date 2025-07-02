# Guía de Versionado de Backups

El sistema de versionado de backups implementa un control de versiones semántico similar a Git, permitiendo gestionar múltiples versiones de backups de base de datos con ramas, etiquetas y funcionalidades avanzadas.

## Características Principales

- **Versionado Semántico**: Usa formato `MAJOR.MINOR.PATCH-BRANCH.BUILD`
- **Ramas de Backup**: Diferentes entornos (main, develop, staging, hotfix, etc.)
- **Etiquetas**: Marcadores para versiones importantes
- **Comparación de Versiones**: Analiza diferencias entre backups
- **Rollback**: Restauración a versiones específicas
- **Limpieza Automática**: Gestión de retención por rama

## Conceptos Básicos

### Estructura de Versiones

```
1.2.3-main.20241201_143052
│ │ │  │    └─ Build timestamp
│ │ │  └─ Rama de versionado
│ │ └─ PATCH (bug fixes, cambios menores)
│ └─ MINOR (nuevas características)
└─ MAJOR (cambios incompatibles)
```

### Ramas de Versionado

| Rama | Descripción | Uso Típico |
|------|-------------|------------|
| `main` | Producción principal | Backups de producción |
| `develop` | Desarrollo | Backups de desarrollo |
| `staging` | Pruebas | Backups de staging/QA |
| `hotfix` | Correcciones urgentes | Backups de emergencia |
| `feature` | Características específicas | Backups de features |
| `release` | Versiones de release | Release candidates |
| `manual` | Backups manuales | Operaciones manuales |

## Uso Básico

### Habilitar Versionado

```bash
# Backup con versionado básico (rama main)
python3 backup_orchestrator.py --enable-versioning

# Backup en rama específica
python3 backup_orchestrator.py --enable-versioning --branch develop

# Backup con versión específica
python3 backup_orchestrator.py --enable-versioning --version "2.1.0-staging"
```

### Crear Backups Versionados

```bash
# Backup automático con incremento patch
python3 backup_orchestrator.py --enable-versioning --name "production_backup"

# Backup con incremento minor
python3 backup_orchestrator.py --enable-versioning --version-increment minor

# Backup con etiquetas y descripción
python3 backup_orchestrator.py --enable-versioning \
  --tags stable production v1.0 \
  --description "Backup estable para release 1.0"

# Backup en rama develop con incremento major
python3 backup_orchestrator.py --enable-versioning \
  --branch develop \
  --version-increment major \
  --description "Breaking changes en desarrollo"
```

## Gestión de Versiones

### Listar Versiones

```bash
# Listar todas las versiones
python3 backup_orchestrator.py --list-versions

# Filtrar por rama
python3 backup_orchestrator.py --list-versions --filter-branch main

# Filtrar por etiqueta
python3 backup_orchestrator.py --list-versions --filter-tag production

# Limitar resultados
python3 backup_orchestrator.py --list-versions --limit 10

# Combinar filtros
python3 backup_orchestrator.py --list-versions \
  --filter-branch staging \
  --filter-tag release \
  --limit 5
```

### Información Detallada

```bash
# Ver información de una versión específica
python3 backup_orchestrator.py --version-info "1.2.3-main.20241201_143052"

# Comparar dos versiones
python3 backup_orchestrator.py --compare-versions \
  "1.2.0-main.20241201_120000" \
  "1.2.3-main.20241201_143052"
```

### Gestión de Ramas

```bash
# Listar todas las ramas y su información
python3 backup_orchestrator.py --list-branches
```

**Salida esperada:**
```
Ramas de Versionado

Rama         Backups  Último Backup        Descripción
─────────────────────────────────────────────────────────────
 main       5        2024-12-01 14:30:52  Rama main
 develop    3        2024-12-01 10:15:30  Rama develop
 staging    2        2024-11-30 16:45:20  Rama staging
 hotfix     1        2024-11-29 09:30:15  Rama hotfix
```

## ️ Gestión de Etiquetas

### Crear Etiquetas

```bash
# Crear etiqueta simple
python3 backup_orchestrator.py --create-tag \
  "1.2.3-main.20241201_143052" "stable"

# Crear etiqueta con descripción
python3 backup_orchestrator.py --create-tag \
  "1.2.3-main.20241201_143052" "release-1.2.3" \
  --description "Release candidato para versión 1.2.3"
```

### Listar Etiquetas

```bash
# Ver todas las etiquetas
python3 backup_orchestrator.py --list-tags
```

**Salida esperada:**
```
Etiquetas Disponibles

️  stable
   ├─ 1.2.3-main.20241201_143052 (2024-12-01 14:30:52)
   ├─ 1.1.5-main.20241130_090000 (2024-11-30 09:00:00)

️  production
   ├─ 1.2.3-main.20241201_143052 (2024-12-01 14:30:52)
   │  Backup de producción estable

️  release-1.2.3
   ├─ 1.2.3-main.20241201_143052 (2024-12-01 14:30:52)
   │  Release candidato para versión 1.2.3
```

## Rollback y Restauración

### Rollback a Versión Específica

```bash
# Rollback automático (crea backup de respaldo)
python3 backup_orchestrator.py --rollback-to "1.2.0-main.20241130_120000"

# Ver historial de rollbacks
python3 backup_orchestrator.py --rollback-history
```

**Ejemplo de historial:**
```
Historial de Rollbacks

Fecha                Versión Objetivo          Backup Creado
─────────────────────────────────────────────────────────────
2024-12-01 15:30:00  1.2.0-main.20241130...   
2024-11-30 10:15:00  1.1.5-main.20241129...   
```

## Limpieza y Mantenimiento

### Limpieza de Versiones Antiguas

```bash
# Simular limpieza (dry run)
python3 backup_orchestrator.py --cleanup-versions 5 --cleanup-dry-run

# Aplicar limpieza (mantener 5 versiones por rama)
python3 backup_orchestrator.py --cleanup-versions 5

# Limpieza conservadora (mantener 10 versiones)
python3 backup_orchestrator.py --cleanup-versions 10
```

**Salida de ejemplo:**
```
Eliminadas: 8 versiones

Versiones:
  ️ 1.0.1-develop.20241115_100000
  ️ 1.0.2-develop.20241116_100000
  ️ 1.1.0-staging.20241120_140000
  [...]
```

##  Ejemplos de Flujos de Trabajo

### Flujo de Desarrollo

```bash
# 1. Backup en desarrollo
python3 backup_orchestrator.py --enable-versioning \
  --branch develop \
  --description "Nueva funcionalidad de usuarios"

# 2. Backup de staging para testing
python3 backup_orchestrator.py --enable-versioning \
  --branch staging \
  --tags testing qa \
  --description "Deploy a staging para QA"

# 3. Release candidate
python3 backup_orchestrator.py --enable-versioning \
  --branch release \
  --version-increment minor \
  --tags rc candidate \
  --description "Release candidate v1.3.0"

# 4. Backup de producción
python3 backup_orchestrator.py --enable-versioning \
  --branch main \
  --version-increment minor \
  --tags stable production v1.3.0 \
  --description "Release estable v1.3.0"
```

### Gestión de Hotfixes

```bash
# 1. Backup de emergencia
python3 backup_orchestrator.py --enable-versioning \
  --branch hotfix \
  --version-increment patch \
  --tags emergency hotfix \
  --description "Backup antes de hotfix crítico"

# 2. Después del hotfix
python3 backup_orchestrator.py --enable-versioning \
  --branch main \
  --version-increment patch \
  --tags stable hotfix-applied \
  --description "Hotfix aplicado exitosamente"
```

### Comparación de Entornos

```bash
# Comparar versiones entre entornos
python3 backup_orchestrator.py --compare-versions \
  "1.2.3-main.20241201_143052" \
  "1.2.1-staging.20241201_100000"

# Listar diferencias por rama
python3 backup_orchestrator.py --list-versions --filter-branch main --limit 3
python3 backup_orchestrator.py --list-versions --filter-branch staging --limit 3
```

### Integración con CI/CD

```bash
# Script para CI/CD
#!/bin/bash
BRANCH_NAME=${CI_COMMIT_REF_NAME:-"develop"}
BUILD_NUMBER=${CI_PIPELINE_ID:-"local"}

python3 backup_orchestrator.py --enable-versioning \
  --branch "$BRANCH_NAME" \
  --tags "ci" "build-$BUILD_NUMBER" \
  --description "Backup automático de CI/CD - Build $BUILD_NUMBER"
```

##  Mejores Prácticas

### Convenciones de Nomenclatura

- **main**: Solo para backups de producción estables
- **develop**: Backups de desarrollo diario
- **staging**: Backups de staging/QA antes de deployments
- **hotfix**: Solo para emergencias
- **feature**: Backups específicos de características
- **release**: Release candidates y preparación de releases

### Gestión de Etiquetas

```bash
# Etiquetas semánticas posibles
--tags stable production        # Para production estable
--tags rc candidate            # Para release candidates  
--tags testing qa              # Para staging/QA
--tags emergency hotfix        # Para hotfixes
--tags feature-xxx             # Para features específicas
--tags migration               # Para backups pre/post migración
```

### Limpieza Periódica

```bash
# Configurar limpieza automática en cron
# Mantener 10 versiones por rama, limpiar semanalmente
0 2 * * 0 cd /path/to/project && python3 backup_orchestrator.py --cleanup-versions 10
```

## Solución de Problemas

### Problemas Comunes

**Error: "Versión no encontrada"**
```bash
# Verificar versiones disponibles
python3 backup_orchestrator.py --list-versions
```

**Error: "Rama inválida"**
```bash
# Verificar ramas disponibles
python3 backup_orchestrator.py --list-branches
```

**Conflictos de versión**
```bash
# Usar versión específica para evitar conflictos
python3 backup_orchestrator.py --enable-versioning --version "1.2.4-hotfix"
```

### Recuperación de Metadatos

Si los metadatos de versiones se corrompen:

```bash
# Los archivos de metadatos están en:
ls -la backups/.versions/
# - version_state.json
# - tags.json  
# - branches.json

# Backup manual de metadatos
cp -r backups/.versions/ backups/.versions.backup/
```

##  Monitoring y Estadísticas

### Ver Estado del Sistema

```bash
# Resumen completo
python3 backup_orchestrator.py --backup-summary

# Información específica de versionado
python3 backup_orchestrator.py --list-branches
python3 backup_orchestrator.py --list-versions --limit 10
```
