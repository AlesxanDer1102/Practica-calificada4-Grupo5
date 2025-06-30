"""
Configuración compartida para todos los tests del proyecto.
Incluye fixtures y configuraciones globales de pytest.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from backup_orchestrator import UnifiedBackupOrchestrator
from backup_cli.cli.parser import CLIConfig


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
    with patch("subprocess.run") as mock_run:
        # Simular que docker inspect retorna éxito (contenedor existe)
        mock_run.return_value = Mock(returncode=0)
        yield mock_run


@pytest.fixture
def mock_docker_container_not_found():
    """
    Fixture que simula un contenedor Docker no encontrado.
    """
    with patch("subprocess.run") as mock_run:
        # Simular que docker inspect falla (contenedor no existe)
        mock_run.return_value = Mock(returncode=1)
        yield mock_run


@pytest.fixture
def orchestrator_instance(temp_backup_dir):
    """
    Fixture que crea una instancia del UnifiedBackupOrchestrator con configuración de test.
    """
    # Crear configuración CLI para tests
    test_config = CLIConfig(type('Args', (), {
        'dir': str(temp_backup_dir),
        'verbose': False,
        'quiet': True,
        'force': False,
        'name': None,
        'list': False,
        'restore': False,
        'restore_file': None,
        'no_color': True,
        'container': 'test_db',
        'pod': None,
        'namespace': 'default',
        'labels': None,
        'k8s_container': None,
        'auto_detect': True,
        'force_docker': True,
        'force_kubernetes': False,
        'backup_type': 'auto',
        'force_full': False,
        'retention_daily': None,
        'retention_weekly': None,
        'retention_monthly': None,
        'retention_full': None,
        'apply_retention': False,
        'retention_dry_run': False,
        'backup_summary': False,
        'schedule': None,
        'schedule_custom': None,
        'schedule_prefix': 'auto',
        'retention_days': 7,
        'notification_email': None,
        'list_schedules': False,
        'remove_schedule': None,
        'test_notifications': False
    })())
    
    return UnifiedBackupOrchestrator(test_config)
