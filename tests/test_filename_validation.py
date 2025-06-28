"""
Tests unitarios para la funcionalidad de validación y generación de nombres de archivo.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
from backup_cli.utils.validator import BackupNameValidator, format_file_size


class TestBackupNameValidator:
    """
    Clase de tests para validar la funcionalidad de nombres de backup.
    """

    def test_validate_backup_name_valid_names(self):
        """
        Test que verifica nombres válidos de backup.
        """
        valid_names = [
            "backup_test",
            "mi_backup_2024",
            "proyecto-final",
            "test_123",
            "backup.daily"
        ]
        
        for name in valid_names:
            is_valid, message = BackupNameValidator.validate_backup_name(name)
            assert is_valid is True, f"Nombre '{name}' debería ser válido: {message}"
            assert message == "Nombre de backup válido"

    def test_validate_backup_name_empty_name(self):
        """
        Test que verifica el rechazo de nombres vacíos.
        """
        is_valid, message = BackupNameValidator.validate_backup_name("")
        assert is_valid is False
        assert "no puede estar vacío" in message

    def test_validate_backup_name_invalid_characters(self):
        """
        Test que verifica el rechazo de caracteres inválidos.
        """
        invalid_names = [
            "backup<test>",
            "backup:test",
            'backup"test',
            "backup/test",
            "backup\\test",
            "backup|test",
            "backup?test",
            "backup*test"
        ]
        
        for name in invalid_names:
            is_valid, message = BackupNameValidator.validate_backup_name(name)
            assert is_valid is False, f"Nombre '{name}' debería ser inválido"
            assert "caracteres inválidos" in message

    def test_validate_backup_name_too_long(self):
        """
        Test que verifica el rechazo de nombres muy largos.
        """
        long_name = "a" * 201  # Excede el límite de 200 caracteres
        is_valid, message = BackupNameValidator.validate_backup_name(long_name)
        assert is_valid is False
        assert "muy largo" in message

    @pytest.mark.parametrize("reserved_name", [
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "LPT1", "LPT9"
    ])
    def test_validate_backup_name_reserved_names(self, reserved_name):
        """
        Test parametrizado que verifica el rechazo de nombres reservados del sistema.
        """
        is_valid, message = BackupNameValidator.validate_backup_name(reserved_name)
        assert is_valid is False
        assert "nombre reservado" in message

    def test_resolve_backup_filename_no_custom_name(self):
        """
        Test que verifica la generación automática de nombres con timestamp.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)
            
            # Mock datetime para timestamp predecible
            with patch('backup_cli.utils.validator.datetime') as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20240115_143000"
                
                filename, name_modified = BackupNameValidator.resolve_backup_filename(backup_dir)
                
                assert filename == "backup_20240115_143000.sql"
                assert name_modified is False

    def test_resolve_backup_filename_custom_name_no_conflict(self):
        """
        Test que verifica el uso de nombre personalizado sin conflictos.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)
            custom_name = "mi_backup_test"
            
            filename, name_modified = BackupNameValidator.resolve_backup_filename(
                backup_dir, custom_name
            )
            
            assert filename == "mi_backup_test.sql"
            assert name_modified is False

    def test_resolve_backup_filename_custom_name_with_conflict(self):
        """
        Test que verifica la resolución de conflictos de nombres.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)
            custom_name = "backup_conflicto"
            
            # Crear archivo existente
            existing_file = backup_dir / f"{custom_name}.sql"
            existing_file.touch()
            
            # Mock datetime para timestamp predecible
            with patch('backup_cli.utils.validator.datetime') as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20240115_143000"
                
                filename, name_modified = BackupNameValidator.resolve_backup_filename(
                    backup_dir, custom_name, force_overwrite=False
                )
                
                assert filename == "backup_conflicto_20240115_143000.sql"
                assert name_modified is True

    def test_resolve_backup_filename_force_overwrite(self):
        """
        Test que verifica la sobrescritura forzada de archivos existentes.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)
            custom_name = "backup_sobrescribir"
            
            # Crear archivo existente
            existing_file = backup_dir / f"{custom_name}.sql"
            existing_file.touch()
            
            filename, name_modified = BackupNameValidator.resolve_backup_filename(
                backup_dir, custom_name, force_overwrite=True
            )
            
            assert filename == "backup_sobrescribir.sql"
            assert name_modified is False

    def test_resolve_backup_filename_invalid_custom_name(self):
        """
        Test que verifica el manejo de nombres personalizados inválidos.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)
            invalid_name = "backup<invalid>"
            
            with pytest.raises(ValueError) as exc_info:
                BackupNameValidator.resolve_backup_filename(backup_dir, invalid_name)
            
            assert "Nombre de backup inválido" in str(exc_info.value)


class TestFormatFileSize:
    """
    Clase de tests para la función de formateo de tamaños de archivo.
    """

    @pytest.mark.parametrize("size_bytes,expected", [
        (0, "0.0 B"),
        (512, "512.0 B"),
        (1023, "1023.0 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1048576, "1.0 MB"),
        (1073741824, "1.0 GB"),
        (1099511627776, "1.0 TB"),
    ])
    def test_format_file_size_various_sizes(self, size_bytes, expected):
        """
        Test parametrizado para verificar el formateo correcto de diferentes tamaños.
        """
        result = format_file_size(size_bytes)
        assert result == expected

    def test_format_file_size_large_number(self):
        """
        Test que verifica el manejo de números muy grandes.
        """
        very_large = 1024 ** 5  # Más de 1 TB
        result = format_file_size(very_large)
        assert result.endswith(" TB")
        assert "1024.0" in result 