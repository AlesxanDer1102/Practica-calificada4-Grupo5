"""
Tests de integración para la funcionalidad de restauración de backups
"""

import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

from backup_cli.cli.parser import CLIConfig
from backup_orchestrator import UnifiedBackupOrchestrator


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


class TestRestoreIntegration:
    """
    Tests de integración para el sistema de restauración de backups
    """

    @pytest.fixture
    def temp_backup_dir(self):
        """Fixture que proporciona un directorio temporal para backups"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def sample_backup_content(self):
        """Fixture que proporciona contenido de backup de ejemplo"""
        return """--
-- PostgreSQL database dump
--

-- Dumped from database version 15.0
-- Dumped by pg_dump version 15.0

SET statement_timeout = 0;

CREATE DATABASE pc_db;

CREATE TABLE usuarios (
    usuario_id integer PRIMARY KEY,
    nombre varchar(15) NOT NULL,
    apellido varchar(15) NOT NULL
);

INSERT INTO usuarios VALUES (1, 'Juan', 'Pérez');
INSERT INTO usuarios VALUES (2, 'María', 'García');

CREATE TABLE productos (
    producto_id integer PRIMARY KEY,
    nombre_producto varchar(25) NOT NULL,
    manufacturador varchar(20) NOT NULL,
    precio real NOT NULL
);

INSERT INTO productos VALUES (1, 'Laptop HP', 'HP', 850.00);
"""

    @pytest.fixture
    def orchestrator(self, temp_backup_dir):
        """Fixture que proporciona un orquestador configurado"""
        config = create_test_config(temp_backup_dir, "test_db")
        return UnifiedBackupOrchestrator(config)

    def create_sample_backup(self, backup_dir: Path, filename: str, content: str):
        """Helper para crear un archivo de backup de prueba"""
        backup_path = backup_dir / filename
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(content)
        return backup_path

    def test_list_backups_when_empty(self, orchestrator):
        """Test que verifica el listado cuando no hay backups"""
        backups = orchestrator.list_backups()
        assert backups == []

    def test_list_backups_with_multiple_files(
        self, orchestrator, temp_backup_dir, sample_backup_content
    ):
        """Test que verifica el listado de múltiples backups"""
        # Crear archivos de backup de prueba
        backup1 = self.create_sample_backup(
            temp_backup_dir, "backup_2024_01_01.sql", sample_backup_content
        )
        backup2 = self.create_sample_backup(
            temp_backup_dir, "backup_2024_01_02.sql", sample_backup_content
        )

        # Simular timestamps diferentes
        import time

        time.sleep(0.1)  # Pequeña diferencia de tiempo
        backup2.touch()  # Actualizar timestamp del segundo backup

        backups = orchestrator.list_backups()

        assert len(backups) == 2
        assert backups[0]["name"] == "backup_2024_01_02.sql"  # Más reciente primero
        assert backups[1]["name"] == "backup_2024_01_01.sql"
        assert all("size" in backup for backup in backups)
        assert all("modified" in backup for backup in backups)
        assert all("path" in backup for backup in backups)

    def test_validate_backup_integrity_valid_file(
        self, orchestrator, temp_backup_dir, sample_backup_content
    ):
        """Test que verifica validación de backup válido"""
        backup_path = self.create_sample_backup(
            temp_backup_dir, "valid_backup.sql", sample_backup_content
        )

        result = orchestrator.validate_backup_integrity(backup_path)
        assert result is True

    def test_validate_backup_integrity_nonexistent_file(
        self, orchestrator, temp_backup_dir
    ):
        """Test que verifica validación de archivo inexistente"""
        nonexistent_path = temp_backup_dir / "nonexistent.sql"

        result = orchestrator.validate_backup_integrity(nonexistent_path)
        assert result is False

    def test_validate_backup_integrity_empty_file(self, orchestrator, temp_backup_dir):
        """Test que verifica validación de archivo vacío"""
        empty_backup = self.create_sample_backup(temp_backup_dir, "empty.sql", "")

        result = orchestrator.validate_backup_integrity(empty_backup)
        assert result is False

    def test_validate_backup_integrity_invalid_content(
        self, orchestrator, temp_backup_dir
    ):
        """Test que verifica validación de contenido inválido"""
        invalid_content = "This is not a SQL backup file"
        invalid_backup = self.create_sample_backup(
            temp_backup_dir, "invalid.sql", invalid_content
        )

        result = orchestrator.validate_backup_integrity(invalid_backup)
        assert result is False

    @patch("builtins.input")
    def test_select_backup_interactive_valid_selection(
        self, mock_input, orchestrator, temp_backup_dir, sample_backup_content
    ):
        """Test de selección interactiva con selección válida"""
        # Crear backup de prueba
        backup_path = self.create_sample_backup(
            temp_backup_dir, "test_backup.sql", sample_backup_content
        )

        # Simular entrada del usuario
        mock_input.return_value = "1"

        result = orchestrator.select_backup_interactive()
        assert result == backup_path

    @patch("builtins.input")
    def test_select_backup_interactive_cancel(
        self, mock_input, orchestrator, temp_backup_dir, sample_backup_content
    ):
        """Test de selección interactiva con cancelación"""
        # Crear backup de prueba
        self.create_sample_backup(
            temp_backup_dir, "test_backup.sql", sample_backup_content
        )

        # Simular cancelación del usuario
        mock_input.return_value = "0"

        with pytest.raises(KeyboardInterrupt):
            orchestrator.select_backup_interactive()

    def test_select_backup_interactive_no_backups(self, orchestrator):
        """Test de selección interactiva sin backups disponibles"""
        with pytest.raises(ValueError, match="No hay backups disponibles"):
            orchestrator.select_backup_interactive()

    @patch("builtins.input")
    def test_confirm_restore_operation_yes(
        self, mock_input, orchestrator, temp_backup_dir, sample_backup_content
    ):
        """Test de confirmación de restauración con respuesta afirmativa"""
        backup_path = self.create_sample_backup(
            temp_backup_dir, "test_backup.sql", sample_backup_content
        )

        mock_input.return_value = "si"

        result = orchestrator.confirm_restore_operation(backup_path, "pc_db")
        assert result is True

    @patch("builtins.input")
    def test_confirm_restore_operation_no(
        self, mock_input, orchestrator, temp_backup_dir, sample_backup_content
    ):
        """Test de confirmación de restauración con respuesta negativa"""
        backup_path = self.create_sample_backup(
            temp_backup_dir, "test_backup.sql", sample_backup_content
        )

        mock_input.return_value = "no"

        result = orchestrator.confirm_restore_operation(backup_path, "pc_db")
        assert result is False

    @patch("subprocess.run")
    @patch("builtins.input")
    def test_restore_database_successful(
        self,
        mock_input,
        mock_subprocess,
        orchestrator,
        temp_backup_dir,
        sample_backup_content,
    ):
        """Test de restauración exitosa de base de datos"""
        # Crear backup de prueba
        backup_path = self.create_sample_backup(
            temp_backup_dir, "test_backup.sql", sample_backup_content
        )

        # Configurar mocks
        mock_input.return_value = "si"  # Confirmar restauración
        mock_subprocess.side_effect = [
            Mock(returncode=0),  # docker inspect (verificar contenedor)
            Mock(returncode=0, stderr=""),  # psql (restaurar)
        ]

        with patch.object(
            orchestrator, "_check_target_availability", return_value=True
        ):
            result = orchestrator.restore_database(backup_path)

        assert result is True

        # Verificar que se llamó psql correctamente
        assert mock_subprocess.call_count == 1
        psql_call = mock_subprocess.call_args_list[0]
        assert "psql" in psql_call[0][0]
        assert "-U" in psql_call[0][0]
        assert "postgres" in psql_call[0][0]

    @patch("subprocess.run")
    @patch("builtins.input")
    def test_restore_database_psql_failure(
        self,
        mock_input,
        mock_subprocess,
        orchestrator,
        temp_backup_dir,
        sample_backup_content,
    ):
        """Test de restauración con fallo en psql"""
        # Crear backup de prueba
        backup_path = self.create_sample_backup(
            temp_backup_dir, "test_backup.sql", sample_backup_content
        )

        # Configurar mocks
        mock_input.return_value = "si"  # Confirmar restauración
        mock_subprocess.return_value = Mock(
            returncode=1, stderr="Database connection failed"
        )

        with patch.object(
            orchestrator, "_check_target_availability", return_value=True
        ):
            result = orchestrator.restore_database(backup_path)

        assert result is False

    @patch("builtins.input")
    def test_restore_database_container_not_found(
        self, mock_input, orchestrator, temp_backup_dir, sample_backup_content
    ):
        """Test de restauración con contenedor no disponible"""
        # Crear backup de prueba
        backup_path = self.create_sample_backup(
            temp_backup_dir, "test_backup.sql", sample_backup_content
        )

        # Configurar mocks
        mock_input.return_value = "si"  # Confirmar restauración

        with patch.object(
            orchestrator, "_check_target_availability", return_value=False
        ):
            result = orchestrator.restore_database(backup_path)

        assert result is False

    @patch("builtins.input")
    def test_restore_database_user_cancellation(
        self, mock_input, orchestrator, temp_backup_dir, sample_backup_content
    ):
        """Test de restauración cancelada por el usuario"""
        # Crear backup de prueba
        backup_path = self.create_sample_backup(
            temp_backup_dir, "test_backup.sql", sample_backup_content
        )

        # Simular cancelación del usuario
        mock_input.return_value = "no"

        result = orchestrator.restore_database(backup_path)
        assert result is False

    def test_restore_database_invalid_backup(self, orchestrator, temp_backup_dir):
        """Test de restauración con backup inválido"""
        # Crear backup inválido
        invalid_backup = self.create_sample_backup(
            temp_backup_dir, "invalid.sql", "invalid content"
        )

        result = orchestrator.restore_database(invalid_backup)
        assert result is False

    @patch("subprocess.run")
    @patch("builtins.input")
    def test_restore_database_timeout(
        self,
        mock_input,
        mock_subprocess,
        orchestrator,
        temp_backup_dir,
        sample_backup_content,
    ):
        """Test de restauración con timeout"""
        # Crear backup de prueba
        backup_path = self.create_sample_backup(
            temp_backup_dir, "test_backup.sql", sample_backup_content
        )

        # Configurar mocks
        mock_input.return_value = "si"  # Confirmar restauración
        mock_subprocess.side_effect = subprocess.TimeoutExpired(
            cmd=["psql"], timeout=300
        )

        with patch.object(
            orchestrator, "_check_target_availability", return_value=True
        ):
            result = orchestrator.restore_database(backup_path)

        assert result is False

    @patch("builtins.input")
    def test_full_restore_workflow(
        self, mock_input, orchestrator, temp_backup_dir, sample_backup_content
    ):
        """Test del flujo completo de restauración desde selección interactiva"""
        # Crear múltiples backups
        backup1 = self.create_sample_backup(
            temp_backup_dir, "backup1.sql", sample_backup_content
        )
        backup2 = self.create_sample_backup(
            temp_backup_dir, "backup2.sql", sample_backup_content
        )

        # Simular selección del usuario: seleccionar backup 1 y confirmar
        mock_input.side_effect = ["1", "si"]

        with patch("subprocess.run", return_value=Mock(returncode=0, stderr="")):
            with patch.object(
                orchestrator, "_check_target_availability", return_value=True
            ):
                result = orchestrator.restore_database()

        assert result is True
