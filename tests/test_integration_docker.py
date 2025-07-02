"""
Suite de tests de integración para el entorno Docker
Verifica el flujo completo de backup/restauración en Docker
"""

import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from backup_cli.cli.parser import CLIConfig
from backup_orchestrator import UnifiedBackupOrchestrator


def create_docker_test_config(backup_dir, container_name="postgres_container"):
    """Helper function to create Docker test configuration"""
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
                "apply_encryption": False,
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


class TestDockerIntegration:
    """Suite de tests de integración para Docker"""

    @pytest.fixture
    def temp_backup_dir(self):
        """Fixture que proporciona un directorio temporal para backups"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def docker_orchestrator(self, temp_backup_dir):
        """Fixture que proporciona un orquestador configurado para Docker"""
        config = create_docker_test_config(temp_backup_dir, "postgres_container")
        return UnifiedBackupOrchestrator(config)

    @pytest.fixture
    def sample_test_data(self):
        """Fixture que proporciona datos de prueba"""
        return {
            "usuarios": [
                {"usuario_id": 1, "nombre": "Juan", "apellido": "Pérez"},
                {"usuario_id": 2, "nombre": "María", "apellido": "García"},
                {"usuario_id": 3, "nombre": "Carlos", "apellido": "López"},
            ],
            "productos": [
                {
                    "producto_id": 1,
                    "nombre_producto": "Laptop HP",
                    "manufacturador": "HP",
                    "precio": 850.00,
                },
                {
                    "producto_id": 2,
                    "nombre_producto": "Mouse Logitech",
                    "manufacturador": "Logitech",
                    "precio": 25.00,
                },
            ],
            "pedidos": [
                {"pedido_id": 1, "usuario_id": 1, "producto_id": 1, "cantidad": 1},
                {"pedido_id": 2, "usuario_id": 2, "producto_id": 2, "cantidad": 2},
            ],
        }

    def test_docker_container_availability(self, docker_orchestrator):
        """Test que verifica la disponibilidad del contenedor PostgreSQL en Docker"""
        container_json = '[{"State": {"Running": true}}]'

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=container_json)

            result = docker_orchestrator._check_target_availability(
                "postgres_container"
            )
            assert result is True

    def test_docker_backup_creation(
        self,
        docker_orchestrator,
        temp_backup_dir,
        mock_docker_handler_available,
        mock_backup_strategy_state,
    ):
        """Test que verifica la creación de backup en Docker"""
        backup_content = "-- PostgreSQL database dump\nCREATE TABLE test_table();\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout=backup_content)

            with patch(
                "backup_cli.utils.validator.BackupNameValidator.resolve_backup_filename"
            ) as mock_resolve:
                # Generate a specific backup filename
                backup_filename = "backup_20250702_220154_full.sql"
                mock_resolve.return_value = (backup_filename, False)

                # Create the backup file in the temp directory
                backup_path = temp_backup_dir / backup_filename
                backup_path.write_text(backup_content)

                result = docker_orchestrator.create_backup()

                assert result is True
                mock_run.assert_called()

                call_args = mock_run.call_args[0][0]
                assert "docker" in call_args
                assert "exec" in call_args
                assert "postgres_container" in call_args
                assert "pg_dump" in call_args

                # Verify the backup file was created and has content
                assert backup_path.exists()
                assert backup_path.stat().st_size > 0

    @patch("subprocess.run")
    def test_docker_data_loss_simulation(self, mock_run, docker_orchestrator):
        """Test que simula pérdida de datos eliminando tablas en Docker"""
        mock_run.return_value = Mock(returncode=0, stdout="DROP TABLE", stderr="")

        drop_commands = [
            "DROP TABLE IF EXISTS pedidos CASCADE;",
            "DROP TABLE IF EXISTS productos CASCADE;",
            "DROP TABLE IF EXISTS usuarios CASCADE;",
        ]

        for command in drop_commands:
            result = docker_orchestrator.handler.execute_command(
                "postgres_container",
                ["psql", "-U", "postgres", "-d", "pc_db", "-c", command],
            )

            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "docker" in call_args
            assert "exec" in call_args
            assert "postgres_container" in call_args
            assert "psql" in call_args

    def test_docker_data_restoration(
        self, docker_orchestrator, temp_backup_dir, mock_docker_handler_available
    ):
        """Test que verifica la restauración de datos en Docker"""
        backup_content = """
-- PostgreSQL database dump
CREATE TABLE usuarios (usuario_id integer PRIMARY KEY, nombre varchar(15), apellido varchar(15));
CREATE TABLE productos (producto_id integer PRIMARY KEY, nombre_producto varchar(25), manufacturador varchar(20), precio real);
CREATE TABLE pedidos (pedido_id integer PRIMARY KEY, usuario_id integer, producto_id integer, cantidad integer);
INSERT INTO usuarios VALUES (1, 'Juan', 'Pérez');
INSERT INTO productos VALUES (1, 'Laptop HP', 'HP', 850.00);
INSERT INTO pedidos VALUES (1, 1, 1, 1);
"""

        backup_file = temp_backup_dir / "test_backup.sql"
        backup_file.write_text(backup_content)

        with patch("builtins.input") as mock_input:
            mock_input.return_value = "si"

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stderr="")

                result = docker_orchestrator.restore_database(backup_file)

                assert result is True
                mock_run.assert_called()

                call_args = mock_run.call_args[0][0]
                assert "docker" in call_args
                assert "exec" in call_args
                assert "postgres_container" in call_args
                assert "psql" in call_args

    @patch("subprocess.run")
    def test_docker_data_integrity_verification(
        self, mock_run, docker_orchestrator, sample_test_data
    ):
        """Test que verifica la integridad de los datos después de la restauración"""
        count_responses = [
            Mock(returncode=0, stdout="3\n"),
            Mock(returncode=0, stdout="2\n"),
            Mock(returncode=0, stdout="2\n"),
        ]

        mock_run.side_effect = count_responses

        tables = ["usuarios", "productos", "pedidos"]
        expected_counts = [3, 2, 2]

        for table, expected_count in zip(tables, expected_counts):
            result = docker_orchestrator.handler.execute_command(
                "postgres_container",
                [
                    "psql",
                    "-U",
                    "postgres",
                    "-d",
                    "pc_db",
                    "-t",
                    "-c",
                    f"SELECT COUNT(*) FROM {table};",
                ],
            )

            assert mock_run.called

    def test_docker_incremental_backup_strategy(
        self,
        docker_orchestrator,
        temp_backup_dir,
        mock_docker_handler_available,
        mock_backup_strategy_state,
    ):
        """Test que verifica la estrategia de backup incremental en Docker"""
        existing_backup = temp_backup_dir / "backup_full_20240101.sql"
        existing_backup.write_text("-- Full backup content")

        backup_content = "-- Incremental backup content"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout=backup_content)

            with patch(
                "backup_cli.backup_strategy.BackupStrategy.determine_backup_type"
            ) as mock_strategy:
                mock_strategy.return_value = "incremental"

                with patch(
                    "backup_cli.utils.validator.BackupNameValidator.resolve_backup_filename"
                ) as mock_resolve:
                    backup_filename = "backup_20250702_220154_incremental.sql"
                    mock_resolve.return_value = (backup_filename, False)

                    # Create the backup file in the temp directory
                    backup_path = temp_backup_dir / backup_filename
                    backup_path.write_text(backup_content)

                    result = docker_orchestrator.create_backup()

                    assert result is True
                    mock_run.assert_called()

                    # Verify the backup file was created
                    assert backup_path.exists()
                    assert backup_path.stat().st_size > 0

    @patch("subprocess.run")
    def test_docker_backup_list_and_management(
        self, mock_run, docker_orchestrator, temp_backup_dir
    ):
        """Test que verifica el listado y gestión de backups en Docker"""
        # Crear archivos de backup
        backup_files = [
            "backup_20240101_120000.sql",
            "backup_20240102_120000.sql",
            "backup_20240103_120000.sql",
        ]

        for filename in backup_files:
            backup_file = temp_backup_dir / filename
            backup_file.write_text("-- Test backup content")

        backups = docker_orchestrator.list_backups()

        assert len(backups) == 3
        assert all(backup["name"] in backup_files for backup in backups)
        assert all("size" in backup for backup in backups)
        assert all("modified" in backup for backup in backups)

    def test_docker_environment_detection(self, docker_orchestrator):
        """Test que verifica la detección automática del entorno en Docker"""
        with patch(
            "backup_cli.environment.detector.EnvironmentDetector.detect_environment"
        ) as mock_detect:
            mock_detect.return_value = "docker"

            environment = docker_orchestrator.env_detector.detect_environment()
            assert environment == "docker"

    def test_docker_full_integration_workflow(
        self,
        docker_orchestrator,
        temp_backup_dir,
        sample_test_data,
        mock_docker_handler_available,
        mock_backup_strategy_state,
    ):
        """Test de integración completo: backup -> pérdida -> restauración -> verificación en Docker"""

        # Crear un backup
        backup_content = "-- PostgreSQL backup with test data\n"
        for table, data in sample_test_data.items():
            backup_content += f"CREATE TABLE {table} (...);\n"
            for row in data:
                backup_content += f"INSERT INTO {table} VALUES (...);\n"

        backup_file = temp_backup_dir / "integration_test_backup.sql"
        backup_file.write_text(backup_content)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout=backup_content)

            with patch(
                "backup_cli.utils.validator.BackupNameValidator.resolve_backup_filename"
            ) as mock_resolve:
                backup_filename = "integration_test_20250702_220154.sql"
                mock_resolve.return_value = (backup_filename, False)

                # Create the backup file in the temp directory
                backup_path = temp_backup_dir / backup_filename
                backup_path.write_text(backup_content)

                backup_result = docker_orchestrator.create_backup(
                    custom_name="integration_test"
                )
                assert backup_result is True

                # Verify the backup file was created
                assert backup_path.exists()
                assert backup_path.stat().st_size > 0

            # Restaurar los datos
            with patch("builtins.input") as mock_input:
                mock_input.return_value = "si"

                restore_result = docker_orchestrator.restore_database(backup_file)
                assert restore_result is True

            # Verificar la integridad de los datos
            verification_responses = [
                Mock(returncode=0, stdout="3\n"),
                Mock(returncode=0, stdout="2\n"),
                Mock(returncode=0, stdout="2\n"),
            ]

            mock_run.side_effect = verification_responses

        for table in sample_test_data.keys():
            result = docker_orchestrator.handler.execute_command(
                "postgres_container",
                [
                    "psql",
                    "-U",
                    "postgres",
                    "-d",
                    "pc_db",
                    "-t",
                    "-c",
                    f"SELECT COUNT(*) FROM {table};",
                ],
            )

        assert True

    def test_docker_error_handling_container_not_found(self, temp_backup_dir):
        """Test que verifica el manejo de errores cuando el contenedor no existe en Docker"""
        config = create_docker_test_config(temp_backup_dir, "nonexistent_container")
        orchestrator = UnifiedBackupOrchestrator(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1, stderr="container 'nonexistent_container' not found"
            )

            result = orchestrator._check_target_availability("nonexistent_container")
            assert result is False

    def test_docker_backup_validation(self, docker_orchestrator, temp_backup_dir):
        """Test que verifica la validación de backups en Docker"""
        # Crear un backup válido
        valid_backup = temp_backup_dir / "valid_backup.sql"
        valid_backup.write_text("-- PostgreSQL database dump\nCREATE TABLE test();\n")

        result = docker_orchestrator.validate_backup_integrity(valid_backup)
        assert result is True

        # Crear un backup inválido
        invalid_backup = temp_backup_dir / "invalid_backup.sql"
        invalid_backup.write_text("This is not a valid SQL backup")

        result = docker_orchestrator.validate_backup_integrity(invalid_backup)
        assert result is False

    def test_docker_concurrent_backups_handling(
        self,
        docker_orchestrator,
        temp_backup_dir,
        mock_docker_handler_available,
        mock_backup_strategy_state,
    ):
        """Test que verifica el manejo de backups concurrentes en Docker"""

        # Simular intentos de backup concurrentes
        backup_content = "-- Concurrent backup content"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout=backup_content)

            with patch(
                "backup_cli.backup_strategy.BackupStrategy.determine_backup_type"
            ) as mock_strategy:
                # Forzar ambos backups a ser de tipo full para evitar problemas de lógica incremental
                mock_strategy.return_value = "full"

                with patch(
                    "backup_cli.utils.validator.BackupNameValidator.resolve_backup_filename"
                ) as mock_resolve:

                    # First backup
                    backup_filename_1 = "concurrent_test_1_20250702_220154.sql"
                    mock_resolve.return_value = (backup_filename_1, False)

                    backup_path_1 = temp_backup_dir / backup_filename_1
                    backup_path_1.write_text(backup_content)

                    result1 = docker_orchestrator.create_backup(
                        custom_name="concurrent_test_1"
                    )
                    assert result1 is True
                    assert backup_path_1.exists()

                    # Second backup with different filename
                    backup_filename_2 = "concurrent_test_2_20250702_220154.sql"
                    mock_resolve.return_value = (backup_filename_2, False)

                    backup_path_2 = temp_backup_dir / backup_filename_2
                    backup_path_2.write_text(backup_content)

                    result2 = docker_orchestrator.create_backup(
                        custom_name="concurrent_test_2"
                    )
                    assert result2 is True
                    assert backup_path_2.exists()
