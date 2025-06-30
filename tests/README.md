# Tests del Orquestador de Backups y Restauración

Este directorio contiene tests unitarios y de integración completos para las funciones core del orquestador de backups y restauración.

## Estructura de Tests

```
tests/
├── conftest.py                  # Fixtures compartidas
├── test_backup_orchestrator.py  # Tests del orquestador principal
├── test_cli_utilities.py        # Tests de utilidades CLI
├── test_docker_connection.py    # Tests de conexión a Docker
├── test_filename_validation.py  # Tests de validación de nombres
├── test_integration_docker.py   # Tests de integración para Docker
├── test_integration_k8s.py      # Tests de integración para Kubernetes
├── test_restore_integration.py  # Tests de integración de restauración
└── README.md                    # Esta documentación
```

## Ejecución de Tests

### Ejecutar todos los tests
```bash
python -m pytest
```

### Ejecutar con reporte de cobertura 
```bash
python -m pytest --cov
```

### Ejecutar tests específicos
```bash
# Solo tests de Docker
python -m pytest tests/test_docker_connection.py

# Solo tests de validación de nombres
python -m pytest tests/test_filename_validation.py

# Solo tests del orquestador principal
python -m pytest tests/test_backup_orchestrator.py

# Solo tests de utilidades CLI
python -m pytest tests/test_cli_utilities.py

# Solo tests de restauración e integración
python -m pytest tests/test_restore_integration.py

# Solo tests de integración Docker
python -m pytest tests/test_integration_docker.py

# Solo tests de integración Kubernetes
python -m pytest tests/test_integration_k8s.py
```

### Ejecutar tests por categorías
```bash
# Tests unitarios
python -m pytest tests/test_backup_orchestrator.py tests/test_cli_utilities.py tests/test_docker_connection.py tests/test_filename_validation.py

# Tests de integración
python -m pytest tests/test_integration_docker.py tests/test_integration_k8s.py tests/test_restore_integration.py

# Solo tests de Docker (conexión + integración)
python -m pytest tests/test_docker_connection.py tests/test_integration_docker.py

# Solo tests de Kubernetes
python -m pytest tests/test_integration_k8s.py
```

## Categorías de Tests

### 1. Tests de Conexión Docker (`test_docker_connection.py`)
- Verificación de contenedores existentes/no existentes
- Manejo de timeouts y errores de Docker
- Tests parametrizados para diferentes nombres de contenedores

### 2. Tests de Validación de Nombres (`test_filename_validation.py`)
- Validación de caracteres permitidos/prohibidos
- Manejo de nombres reservados del sistema
- Resolución de conflictos de archivos existentes
- Formateo de tamaños de archivo

### 3. Tests del Orquestador Principal (`test_backup_orchestrator.py`)
- Inicialización y configuración
- Listado de backups existentes
- Creación de backups (éxito y fallos)
- Manejo de errores de pg_dump y Docker

### 4. Tests de Utilidades CLI (`test_cli_utilities.py`)
- Funcionalidad de colores ANSI
- Indicadores de progreso
- Parser de argumentos de línea de comandos
- Configuración CLI derivada

### 5. Tests de Integración Docker (`test_integration_docker.py`)
**Suite completa de tests de integración para entornos Docker:**

- **Disponibilidad de contenedores**: Verificación de contenedores PostgreSQL
- **Creación de backups**: Tests de backup completo con validación de comandos
- **Simulación de pérdida de datos**: Eliminación de tablas para testing
- **Restauración de datos**: Flujo completo de restauración con confirmación de usuario
- **Verificación de integridad**: Validación de datos después de restauración
- **Estrategias de backup**: Testing de backups incrementales y full
- **Gestión de backups**: Listado y administración de archivos de backup
- **Detección de entorno**: Verificación automática de entorno Docker
- **Flujo de integración completo**: Backup → Pérdida → Restauración → Verificación
- **Manejo de errores**: Contenedores no encontrados, validación de backups
- **Manejo de concurrencia**: Tests de backups simultáneos

**Escenarios específicos cubiertos:**
- Backup y restauración con contenedores existentes/no existentes
- Validación de comandos Docker exec con pg_dump y psql
- Tests de integridad de datos con conteos de registros
- Manejo de backups concurrentes con nombres únicos
- Flujos de error y recuperación

### 6. Tests de Integración Kubernetes (`test_integration_k8s.py`)
**Suite completa de tests de integración para entornos Kubernetes:**

- **Disponibilidad de pods**: Verificación de pods PostgreSQL en namespace
- **Creación de backups**: Tests de backup en pods con kubectl exec
- **Simulación de pérdida de datos**: Eliminación de tablas en entorno K8s
- **Restauración de datos**: Flujo completo con manejo de contenedores específicos
- **Verificación de integridad**: Validación post-restauración en pods
- **Flujo de integración completo**: Workflow completo con mocking de respuestas JSON
- **Manejo de errores**: Pods no encontrados, namespaces incorrectos

**Características específicas de K8s:**
- Manejo de comandos envueltos en shell con variables de entorno
- Tests con contenedores específicos en pods multi-container
- Validación de comandos kubectl con namespaces y contenedores
- Mocking de respuestas JSON para status de pods
- Tests de detección automática de entorno Kubernetes

### 7. Tests de Integración de Restauración (`test_restore_integration.py`)
- Listado y selección interactiva de backups
- Validación de integridad de archivos de backup
- Confirmación de operaciones de restauración
- Ejecución completa de restauración con psql
- Manejo de errores durante restauración (timeouts, fallos de contenedor)
- Flujo completo de restauración desde selección hasta finalización
- Tests con mocks para subprocess y entrada de usuario
- Verificación de argumentos pasados a comandos Docker/psql

**Escenarios cubiertos:**
- Listado de backups vacío y con múltiples archivos
- Validación de archivos: válidos, inexistentes, vacíos, contenido inválido
- Selección interactiva: selección válida, cancelación, sin backups disponibles
- Confirmación de usuario: respuestas afirmativas y negativas
- Restauración exitosa con verificación de comandos psql
- Manejo de fallos: psql, contenedor no disponible, timeouts
- Cancelación por usuario y backups inválidos
- Flujo completo desde selección interactiva hasta restauración

## Fixtures Disponibles

### Fixtures Generales (`conftest.py`)

#### `temp_backup_dir`
Crea un directorio temporal para backups durante las pruebas.

#### `mock_docker_container`
Simula un contenedor Docker disponible.

#### `mock_docker_container_not_found`
Simula un contenedor Docker no encontrado.

#### `orchestrator_instance`
Crea una instancia configurada del UnifiedBackupOrchestrator para tests.

#### `mock_docker_handler_available`
Fixture que simula un handler Docker con contenedor disponible y métodos de estado mockeados.

#### `mock_k8s_handler_available`
Fixture que simula un handler Kubernetes con pod disponible y métodos de estado mockeados.

#### `mock_backup_strategy_state`
Fixture que simula el estado del backup strategy con archivo JSON válido para evitar errores de carga.

#### `sample_test_data`
Fixture que proporciona datos de prueba de ejemplo para validaciones.

### Fixtures específicas de tests de integración

Cada suite de integración incluye fixtures locales para:
- Configuración específica del entorno (Docker/K8s)
- Datos de prueba adaptados al contexto
- Directorios temporales aislados

## Técnicas de Testing Utilizadas

- **Mocking avanzado**: Simulación de llamadas a Docker, kubectl y subprocess
- **Parametrización**: Tests con múltiples valores de entrada
- **Fixtures compartidas**: Configuración reutilizable entre diferentes suites
- **Patching contextual**: Reemplazo temporal de funciones específicas por test
- **Temporal files**: Manejo seguro de archivos temporales
- **Mocking de handlers**: Simulación de estados de contenedores y pods
- **Assertions de comandos**: Verificación de argumentos pasados a comandos del sistema
- **Flujos de integración**: Tests end-to-end que cubren workflows completos

## Comandos Específicos por Suite

### Tests de Integración Docker
```bash
# Ejecutar todas las pruebas de integración Docker
python -m pytest tests/test_integration_docker.py -v

# Tests específicos de Docker
python -m pytest tests/test_integration_docker.py -k "backup_creation" -v
python -m pytest tests/test_integration_docker.py -k "restoration" -v
python -m pytest tests/test_integration_docker.py -k "concurrent" -v
python -m pytest tests/test_integration_docker.py -k "workflow" -v
```

### Tests de Integración Kubernetes
```bash
# Ejecutar todas las pruebas de integración K8s
python -m pytest tests/test_integration_k8s.py -v

# Tests específicos de K8s
python -m pytest tests/test_integration_k8s.py -k "pod_availability" -v
python -m pytest tests/test_integration_k8s.py -k "backup_creation" -v
python -m pytest tests/test_integration_k8s.py -k "restoration" -v
python -m pytest tests/test_integration_k8s.py -k "workflow" -v
```

### Tests de Restauración
```bash
# Ejecutar todas las pruebas de restauración
python -m pytest tests/test_restore_integration.py -v

# Ejecutar solo tests de validación de backups
python -m pytest tests/test_restore_integration.py -k "validate" -v

# Ejecutar solo tests de selección interactiva
python -m pytest tests/test_restore_integration.py -k "interactive" -v

# Ejecutar solo tests de confirmación de usuario
python -m pytest tests/test_restore_integration.py -k "confirm" -v

# Ejecutar prueba específica (ej: restauración exitosa)
python -m pytest tests/test_restore_integration.py::TestRestoreIntegration::test_restore_database_successful -v
```

## Comandos Útiles Generales

```bash
# Instalar dependencias de testing
pip install -r requirements.txt

# Ejecutar solo tests que fallan
python -m pytest --lf

# Ejecutar con output verboso
python -m pytest -v

# Ejecutar con reporte de cobertura específica
python -m pytest --cov=backup_orchestrator --cov-report=term-missing

# Ejecutar tests de integración completos
python -m pytest tests/test_integration_docker.py tests/test_integration_k8s.py tests/test_restore_integration.py -v

# Ejecutar con parada en primer fallo
python -m pytest -x

# Ejecutar tests en paralelo (si tienes pytest-xdist instalado)
python -m pytest -n auto
```
