"""
Tests unitarios para las funciones principales del BackupOrchestrator.
"""

import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from backup_orchestrator import UnifiedBackupOrchestrator
from backup_cli.cli.parser import CLIConfig


def create_test_config(backup_dir, container_name="test_db"):
    """Helper function to create test configuration"""
    return CLIConfig(type('Args', (), {
        'dir': str(backup_dir),
        'verbose': False,
        'quiet': True,
        'force': False,
        'name': None,
        'list': False,
        'restore': False,
        'restore_file': None,
        'no_color': True,
        'container': container_name,
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


class TestBackupOrchestrator:
    """
    Clase de tests para las funciones principales del orquestador de backups.
    """

    def test_orchestrator_initialization(self, temp_backup_dir):
        """
        Test que verifica la inicialización correcta del orquestador.
        """
        config = create_test_config(temp_backup_dir, "test_container")
        orchestrator = UnifiedBackupOrchestrator(config)

        assert orchestrator.config.container == "test_container"
        assert orchestrator.backup_dir == temp_backup_dir
        assert orchestrator.config.show_progress is False
        assert orchestrator.config.use_colors is False
        assert orchestrator.db_config["user"] == "postgres"
        assert orchestrator.db_config["password"] == "12345"
        assert orchestrator.db_config["database"] == "pc_db"

    def test_list_backups_empty_directory(self, orchestrator_instance):
        """
        Test que verifica list_backups() con directorio vacío.
        """
        backups = orchestrator_instance.list_backups()
        assert backups == []

    def test_list_backups_with_files(self, orchestrator_instance, temp_backup_dir):
        """
        Test que verifica list_backups() con archivos de backup.
        """
        # Crear archivos de backup de prueba
        backup1 = temp_backup_dir / "backup_20240101_120000.sql"
        backup2 = temp_backup_dir / "backup_20240102_120000.sql"
        backup3 = temp_backup_dir / "other_file.txt"  # No es archivo SQL

        backup1.write_text("-- SQL backup content")
        backup2.write_text("-- SQL backup content 2")
        backup3.write_text("not a backup")

        # Ejecutar list_backups
        backups = orchestrator_instance.list_backups()

        # Verificaciones
        assert len(backups) == 2
        backup_names = [backup["name"] for backup in backups]
        assert "backup_20240101_120000.sql" in backup_names
        assert "backup_20240102_120000.sql" in backup_names
        assert "other_file.txt" not in backup_names

        # Verificar que tienen las claves correctas
        for backup in backups:
            assert "name" in backup
            assert "size" in backup
            assert "modified" in backup
            assert "path" in backup

    def test_list_backups_sorted_by_modified_date(
        self, orchestrator_instance, temp_backup_dir
    ):
        """
        Test que verifica que list_backups() devuelve archivos ordenados por fecha de modificación.
        """
        import time

        # Crear archivos con diferentes tiempos
        backup1 = temp_backup_dir / "backup_old.sql"
        backup1.write_text("old backup")

        # Esperar un poco para diferencia de tiempo
        time.sleep(0.1)

        backup2 = temp_backup_dir / "backup_new.sql"
        backup2.write_text("new backup")

        backups = orchestrator_instance.list_backups()

        # El más reciente debe estar primero
        assert len(backups) == 2
        assert backups[0]["name"] == "backup_new.sql"
        assert backups[1]["name"] == "backup_old.sql"

    @patch("backup_orchestrator.UnifiedBackupOrchestrator._check_target_availability")
    def test_create_backup_container_not_found(
        self, mock_check_container, orchestrator_instance
    ):
        """
        Test que verifica create_backup() cuando el contenedor no existe.
        """
        # Configurar mock para contenedor no encontrado
        mock_check_container.return_value = False

        # Ejecutar create_backup
        result = orchestrator_instance.create_backup()

        # Verificaciones
        assert result is False
        mock_check_container.assert_called_once()

    @patch("backup_orchestrator.UnifiedBackupOrchestrator._check_target_availability")
    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_backup_success(
        self,
        mock_file,
        mock_subprocess,
        mock_check_container,
        orchestrator_instance,
        temp_backup_dir,
    ):
        """
        Test que verifica create_backup() exitoso.
        """
        # Configurar mocks
        mock_check_container.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stderr="")

        # Mock del archivo de backup creado
        backup_file = temp_backup_dir / "backup_test.sql"
        backup_file.write_text("-- Mock backup content")

        with patch(
            "backup_cli.utils.validator.BackupNameValidator.resolve_backup_filename"
        ) as mock_resolve:
            mock_resolve.return_value = ("backup_test.sql", False)

            # Ejecutar create_backup
            result = orchestrator_instance.create_backup(custom_name="test")

            # Verificaciones
            assert result is True
            mock_check_container.assert_called_once()
            mock_subprocess.assert_called_once()

            # Verificar que se llamó con los argumentos correctos
            call_args = mock_subprocess.call_args
            assert "docker" in call_args[0][0]
            assert "exec" in call_args[0][0]
            assert "test_db" in call_args[0][0]
            assert "pg_dump" in call_args[0][0]

    @patch("backup_orchestrator.UnifiedBackupOrchestrator._check_target_availability")
    @patch("subprocess.run")
    def test_create_backup_pg_dump_failure(
        self, mock_subprocess, mock_check_container, orchestrator_instance
    ):
        """
        Test que verifica create_backup() cuando pg_dump falla.
        """
        # Configurar mocks
        mock_check_container.return_value = True
        mock_subprocess.return_value = Mock(returncode=1, stderr="Error en pg_dump")

        with patch(
            "backup_cli.utils.validator.BackupNameValidator.resolve_backup_filename"
        ) as mock_resolve:
            mock_resolve.return_value = ("backup_failed.sql", False)

            with patch("builtins.open", new_callable=mock_open):
                # Ejecutar create_backup
                result = orchestrator_instance.create_backup()

                # Verificaciones
                assert result is False
                mock_check_container.assert_called_once()
                mock_subprocess.assert_called_once()

    @patch("backup_orchestrator.UnifiedBackupOrchestrator._check_target_availability")
    @patch("subprocess.run")
    def test_create_backup_timeout(
        self, mock_subprocess, mock_check_container, orchestrator_instance
    ):
        """
        Test que verifica create_backup() cuando hay timeout.
        """
        # Configurar mocks
        mock_check_container.return_value = True
        mock_subprocess.side_effect = subprocess.TimeoutExpired(
            cmd=["pg_dump"], timeout=300
        )

        with patch(
            "backup_cli.utils.validator.BackupNameValidator.resolve_backup_filename"
        ) as mock_resolve:
            mock_resolve.return_value = ("backup_timeout.sql", False)

            with patch("builtins.open", new_callable=mock_open):
                # Ejecutar create_backup
                result = orchestrator_instance.create_backup()

                # Verificaciones
                assert result is False

    @patch("backup_orchestrator.UnifiedBackupOrchestrator._check_target_availability")
    def test_create_backup_docker_not_found(
        self, mock_check_container, orchestrator_instance
    ):
        """
        Test que verifica create_backup() cuando Docker no está disponible.
        """
        # Configurar mocks
        mock_check_container.return_value = True

        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.side_effect = FileNotFoundError("docker command not found")

            with patch(
                "backup_cli.utils.validator.BackupNameValidator.resolve_backup_filename"
            ) as mock_resolve:
                mock_resolve.return_value = ("backup_no_docker.sql", False)

                with patch("builtins.open", new_callable=mock_open):
                    # Ejecutar create_backup
                    result = orchestrator_instance.create_backup()

                    # Verificaciones
                    assert result is False

    def test_create_backup_invalid_custom_name(self, orchestrator_instance):
        """
        Test que verifica create_backup() con nombre personalizado inválido.
        """
        with patch(
            "backup_cli.utils.validator.BackupNameValidator.resolve_backup_filename"
        ) as mock_resolve:
            mock_resolve.side_effect = ValueError("Nombre de backup inválido")

            # Ejecutar create_backup
            result = orchestrator_instance.create_backup(custom_name="invalid<name>")

            # Verificaciones
            assert result is False

    @pytest.mark.parametrize(
        "custom_name,force_overwrite,expected_name",
        [
            (None, False, "backup_timestamp.sql"),
            ("mi_backup", False, "mi_backup.sql"),
            ("backup_existente", True, "backup_existente.sql"),
        ],
    )
    def test_create_backup_different_scenarios(
        self, orchestrator_instance, custom_name, force_overwrite, expected_name
    ):
        """
        Test parametrizado para diferentes escenarios de create_backup().
        """
        with patch(
            "backup_orchestrator.UnifiedBackupOrchestrator._check_target_availability"
        ) as mock_check:
            mock_check.return_value = True

            with patch("subprocess.run") as mock_subprocess:
                mock_subprocess.return_value = Mock(returncode=0, stderr="")

                with patch(
                    "backup_cli.utils.validator.BackupNameValidator.resolve_backup_filename"
                ) as mock_resolve:
                    mock_resolve.return_value = (expected_name, False)

                    with patch("builtins.open", new_callable=mock_open):
                        # Simular archivo creado
                        with patch.object(Path, "stat") as mock_stat:
                            mock_stat.return_value.st_size = 1024

                            # Ejecutar create_backup
                            result = orchestrator_instance.create_backup(
                                custom_name=custom_name, force_overwrite=force_overwrite
                            )

                            # Verificaciones
                            assert result is True
                            mock_resolve.assert_called_once_with(
                                orchestrator_instance.backup_dir,
                                custom_name,
                                force_overwrite,
                            )
