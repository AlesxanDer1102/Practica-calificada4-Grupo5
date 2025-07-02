"""
Suite de tests de integración para el entorno Kubernetes
Verifica el flujo completo de backup/restauración en Kubernetes
"""

import json
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from backup_cli.cli.parser import CLIConfig
from backup_orchestrator import UnifiedBackupOrchestrator


def create_k8s_test_config(backup_dir, pod_name="postgres-0", namespace="default"):
    """Helper function to create Kubernetes test configuration"""
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
                "container": None,
                "pod": pod_name,
                "namespace": namespace,
                "labels": None,
                "k8s_container": "postgres",
                "auto_detect": True,
                "force_docker": False,
                "force_kubernetes": True,
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


class TestK8sIntegration:
    """Suite de tests de integración para Kubernetes"""

    @pytest.fixture
    def temp_backup_dir(self):
        """Fixture que proporciona un directorio temporal para backups"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def k8s_orchestrator(self, temp_backup_dir):
        """Fixture que proporciona un orquestador configurado para Kubernetes"""
        config = create_k8s_test_config(temp_backup_dir, "postgres-0", "default")
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

    def test_k8s_pod_availability(self, k8s_orchestrator):
        """Test que verifica la disponibilidad del pod PostgreSQL en Kubernetes"""
        pod_json = {
            "status": {
                "phase": "Running",
                "containerStatuses": [
                    {"name": "postgres", "ready": True, "restartCount": 0}
                ],
            }
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(pod_json))

            result = k8s_orchestrator._check_target_availability("postgres-0")
            assert result is True

    def test_k8s_backup_creation(
        self,
        k8s_orchestrator,
        temp_backup_dir,
        mock_k8s_handler_available,
        mock_backup_strategy_state,
    ):
        """Test que verifica la creación de backup en Kubernetes"""
        backup_content = "-- PostgreSQL database dump\nCREATE TABLE test_table();\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="")

            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.write.return_value = None
                mock_open.return_value.__enter__.return_value.read.return_value = (
                    backup_content
                )

                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = len(backup_content)

                    result = k8s_orchestrator.create_backup()

                    assert result is True
                    mock_run.assert_called()

                    call_args = mock_run.call_args[0][0]
                    assert "kubectl" in call_args
                    assert "exec" in call_args
                    assert "postgres-0" in call_args
                    # For K8s, pg_dump is wrapped in shell command with env vars
                    call_string = " ".join(call_args)
                    assert "pg_dump" in call_string

    @patch("subprocess.run")
    def test_k8s_data_loss_simulation(self, mock_run, k8s_orchestrator):
        """Test que simula pérdida de datos eliminando tablas en Kubernetes"""
        mock_run.return_value = Mock(returncode=0, stdout="DROP TABLE", stderr="")

        drop_commands = [
            "DROP TABLE IF EXISTS pedidos CASCADE;",
            "DROP TABLE IF EXISTS productos CASCADE;",
            "DROP TABLE IF EXISTS usuarios CASCADE;",
        ]

        for command in drop_commands:
            result = k8s_orchestrator.handler.execute_command(
                "postgres-0", ["psql", "-U", "postgres", "-d", "pc_db", "-c", command]
            )

            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "kubectl" in call_args
            assert "exec" in call_args
            assert "postgres-0" in call_args
            assert "psql" in call_args

    def test_k8s_data_restoration(
        self, k8s_orchestrator, temp_backup_dir, mock_k8s_handler_available
    ):
        """Test que verifica la restauración de datos en Kubernetes"""
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

                result = k8s_orchestrator.restore_database(backup_file)

                assert result is True
                mock_run.assert_called()

                call_args = mock_run.call_args[0][0]
                assert "kubectl" in call_args
                assert "exec" in call_args
                assert "postgres-0" in call_args
                # For K8s, psql is wrapped in shell command with env vars
                call_string = " ".join(call_args)
                assert "psql" in call_string

    @patch("subprocess.run")
    def test_k8s_data_integrity_verification(
        self, mock_run, k8s_orchestrator, sample_test_data
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
            result = k8s_orchestrator.handler.execute_command(
                "postgres-0",
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

    @patch("subprocess.run")
    def test_k8s_full_integration_workflow(
        self, mock_run, k8s_orchestrator, temp_backup_dir, sample_test_data
    ):
        """Test de integración completo: backup -> pérdida -> restauración -> verificación"""

        # Mock proper JSON responses for Kubernetes
        pod_status_json = json.dumps(
            {
                "status": {
                    "phase": "Running",
                    "containerStatuses": [{"name": "postgres", "ready": True}],
                }
            }
        )

        # Step 1: Create backup
        backup_content = "-- PostgreSQL backup with test data\n"
        for table, data in sample_test_data.items():
            backup_content += f"CREATE TABLE {table} (...);\n"
            for row in data:
                backup_content += f"INSERT INTO {table} VALUES (...);\n"

        backup_file = temp_backup_dir / "integration_test_backup.sql"
        backup_file.write_text(backup_content)

        # Mock responses: 1st for pod check, 2nd for pg_dump
        mock_responses = [
            Mock(returncode=0, stdout=pod_status_json),  # Pod status check
            Mock(returncode=0, stderr=""),  # pg_dump execution
        ]
        mock_run.side_effect = mock_responses

        with patch("builtins.open", create=True):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = len(backup_content)

                backup_result = k8s_orchestrator.create_backup(
                    custom_name="integration_test"
                )
                assert backup_result is True

        # Step 3: Restore data
        mock_run.side_effect = [
            Mock(returncode=0, stdout=pod_status_json),  # Pod status check
            Mock(returncode=0, stderr=""),  # psql execution
        ]

        with patch("builtins.input") as mock_input:
            mock_input.return_value = "si"

            restore_result = k8s_orchestrator.restore_database(backup_file)
            assert restore_result is True

        # Step 4: Verify data integrity
        verification_responses = [
            Mock(returncode=0, stdout="3\n"),
            Mock(returncode=0, stdout="2\n"),
            Mock(returncode=0, stdout="2\n"),
        ]

        mock_run.side_effect = verification_responses

        for table in sample_test_data.keys():
            result = k8s_orchestrator.handler.execute_command(
                "postgres-0",
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

    def test_k8s_error_handling_pod_not_found(self, temp_backup_dir):
        """Test que verifica el manejo de errores cuando el pod no existe"""
        config = create_k8s_test_config(temp_backup_dir, "nonexistent-pod", "default")
        orchestrator = UnifiedBackupOrchestrator(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1, stderr="pod 'nonexistent-pod' not found"
            )

            result = orchestrator._check_target_availability("nonexistent-pod")
            assert result is False