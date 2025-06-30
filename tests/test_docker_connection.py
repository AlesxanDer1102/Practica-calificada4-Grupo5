"""
Tests unitarios para la funcionalidad de conexión a Docker del BackupOrchestrator.
"""

import subprocess
from unittest.mock import Mock, patch

import pytest

from backup_orchestrator import UnifiedBackupOrchestrator
from backup_cli.cli.parser import CLIConfig


def create_test_config(backup_dir, container_name="test_db"):
    """Helper function to create test configuration"""
    return CLIConfig(
        type(
            "Args",
            (),
            {
                "dir": str(backup_dir),
                "verbose": False,
                "quiet": True,
                "force": False,
                "name": None,
                "list": False,
                "restore": False,
                "restore_file": None,
                "no_color": True,
                "container": container_name,
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
                "list_schedules": False,
                "remove_schedule": None,
                "test_notifications": False,
            },
        )()
    )


class TestDockerConnection:
    """
    Clase de tests para verificar la conexión y verificación de contenedores Docker.
    """

    def test_check_docker_container_exists(self, orchestrator_instance):
        """
        Test que verifica que _check_target_availability() retorna True cuando el contenedor existe.
        """
        container_json = '[{"State": {"Running": true}}]'

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=container_json)

            # Ejecutar la verificación
            result = orchestrator_instance._check_target_availability("test_db")

            # Verificaciones
            assert result is True

    def test_check_docker_container_not_found(self, orchestrator_instance):
        """
        Test que verifica que _check_target_availability() retorna False cuando el contenedor no existe.
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1, stdout="", stderr="No such container"
            )

            # Ejecutar la verificación
            result = orchestrator_instance._check_target_availability("test_db")

            # Verificaciones
            assert result is False

    def test_check_docker_container_timeout(self, orchestrator_instance):
        """
        Test que verifica el manejo de timeout en la verificación del contenedor.
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["docker", "inspect", "test_db"], timeout=10
            )

            # Ejecutar la verificación
            result = orchestrator_instance._check_target_availability("test_db")

            # Verificaciones
            assert result is False

    def test_check_docker_container_docker_not_found(self, orchestrator_instance):
        """
        Test que verifica el manejo cuando Docker no está instalado.
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("docker command not found")

            # Ejecutar la verificación
            result = orchestrator_instance._check_target_availability("test_db")

            # Verificaciones
            assert result is False

    @pytest.mark.parametrize(
        "container_name,expected_call",
        [
            ("postgres_db", "postgres_db"),
            ("mysql_container", "mysql_container"),
            ("custom-db-123", "custom-db-123"),
        ],
    )
    def test_check_docker_container_different_names(
        self, temp_backup_dir, container_name, expected_call
    ):
        """
        Test parametrizado para verificar diferentes nombres de contenedores.
        """
        # Crear orchestrator con nombre personalizado
        config = create_test_config(temp_backup_dir, container_name)
        orchestrator = UnifiedBackupOrchestrator(config)

        container_json = '[{"State": {"Running": true}}]'

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=container_json)

            # Ejecutar la verificación
            result = orchestrator._check_target_availability(expected_call)

            # Verificaciones
            assert result is True
