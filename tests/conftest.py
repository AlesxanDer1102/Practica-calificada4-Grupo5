"""
Configuración compartida para todos los tests del proyecto.
Incluye fixtures y configuraciones globales de pytest.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from backup_orchestrator import BackupOrchestrator


@pytest.fixture
def temp_backup_dir():
    """
    Fixture que crea un directorio temporal para backups durante las pruebas.
    Se limpia automáticamente después de cada test.
    """
    temp_dir = tempfile.mkdtemp(prefix="test_backup_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_docker_container():
    """
    Fixture que simula un contenedor Docker disponible.
    """
    with patch('subprocess.run') as mock_run:
        # Simular que docker inspect retorna éxito (contenedor existe)
        mock_run.return_value = Mock(returncode=0)
        yield mock_run


@pytest.fixture
def mock_docker_container_not_found():
    """
    Fixture que simula un contenedor Docker no encontrado.
    """
    with patch('subprocess.run') as mock_run:
        # Simular que docker inspect falla (contenedor no existe)
        mock_run.return_value = Mock(returncode=1)
        yield mock_run


@pytest.fixture
def orchestrator_instance(temp_backup_dir):
    """
    Fixture que crea una instancia del BackupOrchestrator con configuración de test.
    """
    return BackupOrchestrator(
        container_name="test_db",
        backup_dir=str(temp_backup_dir),
        show_progress=False,  # Deshabilitar progreso en tests
        use_colors=False      # Deshabilitar colores en tests
    ) 