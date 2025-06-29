# Tests del Orquestador de Backups y Restauración

Este directorio contiene tests unitarios y de integración completos para las funciones core del orquestador de backups y restauración.

## Estructura de Tests

```
tests/
├── conftest.py                 # Fixtures compartidas
├── test_docker_connection.py   # Tests de conexión a Docker
├── test_filename_validation.py # Tests de validación de nombres
├── test_backup_orchestrator.py # Tests del orquestador principal
├── test_cli_utilities.py       # Tests de utilidades CLI
├── test_restore_integration.py # Tests de integración de restauración
└── README.md                   # Esta documentación
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

### 5. Tests de Integración de Restauración (`test_restore_integration.py`)
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

### `temp_backup_dir`
Crea un directorio temporal para backups durante las pruebas.

### `mock_docker_container`
Simula un contenedor Docker disponible.

### `mock_docker_container_not_found`
Simula un contenedor Docker no encontrado.

### `orchestrator_instance`
Crea una instancia configurada del BackupOrchestrator para tests.

### Fixtures específicas de Restauración (`test_restore_integration.py`)

#### `sample_backup_content`
Proporciona contenido SQL válido de ejemplo para archivos de backup de prueba.

#### `temp_backup_dir`  
Crea un directorio temporal aislado para archivos de backup durante las pruebas.

#### `orchestrator`
Instancia del BackupOrchestrator configurada específicamente para tests de restauración (sin progreso visual ni colores).

## Técnicas de Testing Utilizadas

- **Mocking**: Simulación de llamadas a Docker y subprocess
- **Parametrización**: Tests con múltiples valores de entrada
- **Fixtures**: Configuración reutilizable entre tests
- **Patching**: Reemplazo temporal de funciones del sistema
- **Temporal files**: Manejo seguro de archivos temporales

## Tests de Restauración - Comandos Específicos

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

# Ejecutar con cobertura específica del módulo de restauración
python -m pytest tests/test_restore_integration.py --cov=backup_orchestrator --cov-report=term-missing
```

## Comandos Útiles Generales

```bash
# Instalar dependencias de testing
pip install -r requirements.txt

# Ejecutar solo tests que fallan
python -m pytest --lf

# Ejecutar con output verboso
python -m pytest -v
