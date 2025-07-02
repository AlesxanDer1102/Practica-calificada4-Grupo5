"""
Configuración compartida para todos los tests del proyecto.
Incluye fixtures y configuraciones globales de pytest.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from backup_cli.cli.parser import CLIConfig
from backup_orchestrator import UnifiedBackupOrchestrator


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
    test_config = CLIConfig(
        type(
            "Args",
            (),
            {
                "dir": str(temp_backup_dir),
                "verbose": False,
                "quiet": True,
                "force": False,
                "name": None,
                "list": False,
                "restore": False,
                "restore_file": None,
                "no_color": True,
                "container": "test_db",
                "pod": None,
                "namespace": "default",
                "labels": None,
                "k8s_container": None,
                "auto_detect": True,
                "force_docker": True,
                "force_kubernetes": False,
                "backup_type": "auto",
                "force_full": False,
                "retention_daily": None,
                "retention_weekly": None,
                "retention_monthly": None,
                "retention_full": None,
                "apply_retention": False,
                "retention_dry_run": False,
                "backup_summary": False,
                "schedule": None,
                "schedule_custom": None,
                "schedule_prefix": "auto",
                "retention_days": 7,
                "notification_email": None,
                "slack_token": None,
                "slack_channel": None,
                "list_schedules": False,
                "remove_schedule": None,
                "test_notifications": False,
            },
        )()
    )

    return UnifiedBackupOrchestrator(test_config)


@pytest.fixture
def mock_docker_handler_available():
    """
    Fixture que simula un handler Docker con contenedor disponible.
    Mock the Docker handler methods to return proper status.
    """
    with patch(
        "backup_cli.handlers.docker_handler.DockerHandler.check_container_status"
    ) as mock_status:
        "Retorna True para indicar que el contenedor está disponible"
        mock_status.return_value = True
        yield mock_status


@pytest.fixture
def mock_k8s_handler_available():
    """
    Fixture que simula un handler Kubernetes con pod disponible.
    Mock the Kubernetes handler methods to return proper status.
    """
    with patch(
        "backup_cli.handlers.kubernetes_handler.KubernetesHandler.check_pod_status"
    ) as mock_status:
        mock_status.return_value = True
        yield mock_status


@pytest.fixture
def mock_backup_strategy_state():
    """
    Fixture que simula el estado del backup strategy con archivo JSON válido.
    """
    with patch(
        "backup_cli.backup_strategy.BackupStrategy.load_backup_state"
    ) as mock_load:
        mock_load.return_value = {
            "last_full_backup": None,
            "last_incremental_backup": None,
            "schema_hash": None,
            "backups": [],
        }
        with patch(
            "backup_cli.backup_strategy.BackupStrategy.save_backup_state"
        ) as mock_save:
            mock_save.return_value = None
            yield mock_load, mock_save


@pytest.fixture
def sample_test_data():
    """
    Fixture que proporciona datos de prueba de ejemplo.
    """
    return {
        "test_table": [
            {"id": 1, "name": "Test Item 1", "value": "test_value_1"},
            {"id": 2, "name": "Test Item 2", "value": "test_value_2"},
        ]
    }
