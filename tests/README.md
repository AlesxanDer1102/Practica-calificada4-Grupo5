# Tests Unitarios del Orquestador de Backups

Este directorio contiene tests unitarios completos para las funciones core del orquestador de backups.

## Estructura de Tests

```
tests/
├── conftest.py                 # Fixtures compartidas
├── test_docker_connection.py   # Tests de conexión a Docker
├── test_filename_validation.py # Tests de validación de nombres
├── test_backup_orchestrator.py # Tests del orquestador principal
├── test_cli_utilities.py       # Tests de utilidades CLI
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

## Fixtures Disponibles

### `temp_backup_dir`
Crea un directorio temporal para backups durante las pruebas.

### `mock_docker_container`
Simula un contenedor Docker disponible.

### `mock_docker_container_not_found`
Simula un contenedor Docker no encontrado.

### `orchestrator_instance`
Crea una instancia configurada del BackupOrchestrator para tests.

## Técnicas de Testing Utilizadas

- **Mocking**: Simulación de llamadas a Docker y subprocess
- **Parametrización**: Tests con múltiples valores de entrada
- **Fixtures**: Configuración reutilizable entre tests
- **Patching**: Reemplazo temporal de funciones del sistema
- **Temporal files**: Manejo seguro de archivos temporales

## Comandos Útiles

```bash
# Instalar dependencias de testing
pip install -r requirements.txt

# Ejecutar solo tests que fallan
python -m pytest --lf

# Ejecutar con output verboso
python -m pytest -v
