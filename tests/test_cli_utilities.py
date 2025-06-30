"""
Tests unitarios para las utilidades CLI del proyecto.
"""

import sys
from io import StringIO
from unittest.mock import Mock, patch

import pytest

from backup_cli.cli.parser import CLIConfig, create_cli_parser
from backup_cli.utils.colors import Colors, print_colored_message, should_use_colors
from backup_cli.utils.progress import ProgressIndicator


class TestColors:
    """
    Clase de tests para la funcionalidad de colores ANSI.
    """

    def test_colors_constants_exist(self):
        """
        Test que verifica que todas las constantes de colores están definidas.
        """
        expected_colors = [
            "RESET",
            "BOLD",
            "RED",
            "GREEN",
            "YELLOW",
            "BLUE",
            "MAGENTA",
            "CYAN",
            "WHITE",
            "BRIGHT_RED",
            "BRIGHT_GREEN",
            "BRIGHT_YELLOW",
            "BRIGHT_BLUE",
            "BRIGHT_MAGENTA",
            "BRIGHT_CYAN",
        ]

        for color in expected_colors:
            assert hasattr(Colors, color)
            assert isinstance(getattr(Colors, color), str)

    def test_colors_disable(self):
        """
        Test que verifica que Colors.disable() elimina todos los códigos de color.
        """
        # Guardar valores originales
        original_red = Colors.RED
        original_green = Colors.GREEN
        original_reset = Colors.RESET

        # Deshabilitar colores
        Colors.disable()

        # Verificar que se vaciaron
        assert Colors.RED == ""
        assert Colors.GREEN == ""
        assert Colors.RESET == ""

        # Restaurar valores originales para otros tests
        Colors.RED = original_red
        Colors.GREEN = original_green
        Colors.RESET = original_reset

    @pytest.mark.parametrize(
        "no_color_flag,isatty_result,expected",
        [
            (False, True, True),  # Terminal TTY sin flag no_color
            (True, True, False),  # Terminal TTY con flag no_color
            (False, False, False),  # No es TTY sin flag no_color
            (True, False, False),  # No es TTY con flag no_color
        ],
    )
    def test_should_use_colors(self, no_color_flag, isatty_result, expected):
        """
        Test parametrizado para verificar should_use_colors() en diferentes escenarios.
        """
        with patch("sys.stdout.isatty", return_value=isatty_result):
            result = should_use_colors(no_color_flag)
            assert result == expected

    def test_print_colored_message_with_colors(self):
        """
        Test que verifica print_colored_message() con colores habilitados.
        """
        with patch("builtins.print") as mock_print:
            print_colored_message("INFO", "Test message", use_colors=True)

            # Verificar que se llamó print con colores
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "[INFO]" in call_args
            assert "Test message" in call_args
            assert Colors.BLUE in call_args  # INFO usa color azul
            assert Colors.RESET in call_args

    def test_print_colored_message_without_colors(self):
        """
        Test que verifica print_colored_message() sin colores.
        """
        with patch("builtins.print") as mock_print:
            print_colored_message("ERROR", "Error message", use_colors=False)

            # Verificar que se llamó print sin colores
            mock_print.assert_called_once_with("[ERROR] Error message")

    @pytest.mark.parametrize(
        "level",
        ["INFO", "SUCCESS", "WARNING", "ERROR", "FAILED", "CANCELLED", "UNKNOWN"],
    )
    def test_print_colored_message_different_levels(self, level):
        """
        Test parametrizado para diferentes niveles de mensaje.
        """
        with patch("builtins.print") as mock_print:
            print_colored_message(level, "Test message", use_colors=True)

            # Verificar que se llamó print y que contiene el nivel y el mensaje
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert f"[{level}]" in call_args
            assert "Test message" in call_args


class TestProgressIndicator:
    """
    Clase de tests para el indicador de progreso.
    """

    def test_progress_indicator_initialization(self):
        """
        Test que verifica la inicialización del indicador de progreso.
        """
        progress = ProgressIndicator("Test operation", use_colors=True)

        assert progress.message == "Test operation"
        assert progress.active is False
        assert progress.use_colors is True

    def test_progress_indicator_start_with_colors(self):
        """
        Test que verifica el inicio del progreso con colores.
        """
        progress = ProgressIndicator("Testing", use_colors=True)

        with patch("builtins.print") as mock_print:
            progress.start()

            assert progress.active is True
            mock_print.assert_called_once()
            call_args = mock_print.call_args
            assert "Testing" in str(call_args)
            assert call_args[1]["end"] == ""  # No debe terminar en newline
            assert call_args[1]["flush"] is True

    def test_progress_indicator_start_without_colors(self):
        """
        Test que verifica el inicio del progreso sin colores.
        """
        progress = ProgressIndicator("Testing", use_colors=False)

        with patch("builtins.print") as mock_print:
            progress.start()

            assert progress.active is True
            mock_print.assert_called_once_with("[INFO] Testing", end="", flush=True)

    def test_progress_indicator_update(self):
        """
        Test que verifica la actualización del progreso.
        """
        progress = ProgressIndicator("Testing", use_colors=True)
        progress.active = True  # Simular que está activo

        with patch("builtins.print") as mock_print:
            progress.update(".")
            progress.update("#")

            assert mock_print.call_count == 2
            calls = mock_print.call_args_list
            assert "." in str(calls[0])
            assert "#" in str(calls[1])

    def test_progress_indicator_update_inactive(self):
        """
        Test que verifica que update() no hace nada si no está activo.
        """
        progress = ProgressIndicator("Testing", use_colors=True)
        # progress.active es False por defecto

        with patch("builtins.print") as mock_print:
            progress.update(".")

            mock_print.assert_not_called()

    @pytest.mark.parametrize(
        "success,expected_status",
        [
            (True, "[OK]"),
            (False, "[FAILED]"),
        ],
    )
    def test_progress_indicator_complete(self, success, expected_status):
        """
        Test parametrizado para completar el progreso con éxito/fallo.
        """
        progress = ProgressIndicator("Testing", use_colors=False)
        progress.active = True

        with patch("builtins.print") as mock_print:
            progress.complete(success)

            assert progress.active is False
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert expected_status in call_args

    def test_progress_indicator_simulate_work(self):
        """
        Test que verifica simulate_work() funciona correctamente.
        """
        progress = ProgressIndicator("Testing", use_colors=True)
        progress.active = True

        with patch("builtins.print") as mock_print:
            with patch("time.sleep") as mock_sleep:
                progress.simulate_work(duration=0.3, steps=3)

                # Verificar que se llamó sleep y print las veces correctas
                assert mock_sleep.call_count == 3
                assert mock_print.call_count == 3


class TestCLIParser:
    """
    Clase de tests para el parser CLI.
    """

    def test_create_cli_parser_returns_parser(self):
        """
        Test que verifica que create_cli_parser() retorna un parser válido.
        """
        parser = create_cli_parser()

        assert parser is not None
        assert hasattr(parser, "parse_args")
        assert hasattr(parser, "add_argument")

    def test_cli_parser_default_arguments(self):
        """
        Test que verifica los argumentos por defecto del parser.
        """
        parser = create_cli_parser()
        args = parser.parse_args([])  # Sin argumentos

        assert args.name is None
        assert args.container is None  # Container doesn't have a default value
        assert args.dir == "backups"
        assert args.verbose is False
        assert args.quiet is False
        assert args.force is False
        assert args.list is False
        assert args.restore is False
        assert args.restore_file is None
        assert args.no_color is False
        assert args.pod is None
        assert args.namespace == "default"
        assert args.labels is None
        assert args.k8s_container is None
        assert args.auto_detect is False
        assert args.force_docker is False
        assert args.force_kubernetes is False

    def test_cli_parser_with_arguments(self):
        """
        Test que verifica el parsing con argumentos específicos.
        """
        parser = create_cli_parser()
        args = parser.parse_args(
            [
                "--name",
                "test_backup",
                "--container",
                "my_db",
                "--dir",
                "/tmp/backups",
                "--verbose",
                "--quiet",
                "--force",
                "--list",
                "--no-color",
            ]
        )

        assert args.name == "test_backup"
        assert args.container == "my_db"
        assert args.dir == "/tmp/backups"
        assert args.verbose is True
        assert args.quiet is True
        assert args.force is True
        assert args.list is True
        assert args.no_color is True

    def test_cli_parser_short_arguments(self):
        """
        Test que verifica los argumentos cortos del parser.
        """
        parser = create_cli_parser()
        args = parser.parse_args(
            [
                "-n",
                "backup_short",
                "-c",
                "container_short",
                "-d",
                "dir_short",
                "-v",
                "-q",
                "-f",
                "-l",
            ]
        )

        assert args.name == "backup_short"
        assert args.container == "container_short"
        assert args.dir == "dir_short"
        assert args.verbose is True
        assert args.quiet is True
        assert args.force is True
        assert args.list is True


class TestCLIConfig:
    """
    Clase de tests para la configuración CLI.
    """

    def test_cli_config_initialization(self):
        """
        Test que verifica la inicialización de CLIConfig.
        """
        # Crear mock args
        mock_args = Mock()
        mock_args.name = "test"
        mock_args.container = "test_db"
        mock_args.dir = "test_dir"
        mock_args.verbose = True
        mock_args.quiet = False
        mock_args.force = True
        mock_args.list = False
        mock_args.no_color = False

        # Add missing required attributes for CLIConfig
        mock_args.restore = False
        mock_args.restore_file = None
        mock_args.pod = None
        mock_args.namespace = "default"
        mock_args.labels = None  # This needs to be None or string, not Mock
        mock_args.k8s_container = None
        mock_args.auto_detect = False
        mock_args.force_docker = False
        mock_args.force_kubernetes = False
        mock_args.backup_type = "auto"
        mock_args.force_full = False
        mock_args.retention_daily = None
        mock_args.retention_weekly = None
        mock_args.retention_monthly = None
        mock_args.retention_full = None
        mock_args.apply_retention = False
        mock_args.retention_dry_run = False
        mock_args.backup_summary = False
        mock_args.schedule = None
        mock_args.schedule_custom = None
        mock_args.schedule_prefix = "auto"
        mock_args.retention_days = 7
        mock_args.notification_email = None
        mock_args.list_schedules = False
        mock_args.remove_schedule = None
        mock_args.test_notifications = False

        config = CLIConfig(mock_args)

        assert config.name == "test"
        assert config.container == "test_db"
        assert config.backup_dir == "test_dir"
        assert config.verbose is True
        assert config.quiet is False
        assert config.force is True
        assert config.list is False
        assert config.no_color is False
        assert config.show_progress is True  # derivado: not quiet
        assert config.use_colors is True  # derivado: not no_color

    def test_cli_config_derived_properties(self):
        """
        Test que verifica las propiedades derivadas de CLIConfig.
        """
        # Test con quiet=True, no_color=True
        mock_args = Mock()
        mock_args.name = None
        mock_args.container = "db"
        mock_args.dir = "backups"
        mock_args.verbose = False
        mock_args.quiet = True
        mock_args.force = False
        mock_args.list = False
        mock_args.no_color = True

        # Add missing required attributes for CLIConfig
        mock_args.restore = False
        mock_args.restore_file = None
        mock_args.pod = None
        mock_args.namespace = "default"
        mock_args.labels = None
        mock_args.k8s_container = None
        mock_args.auto_detect = False
        mock_args.force_docker = False
        mock_args.force_kubernetes = False
        mock_args.backup_type = "auto"
        mock_args.force_full = False
        mock_args.retention_daily = None
        mock_args.retention_weekly = None
        mock_args.retention_monthly = None
        mock_args.retention_full = None
        mock_args.apply_retention = False
        mock_args.retention_dry_run = False
        mock_args.backup_summary = False
        mock_args.schedule = None
        mock_args.schedule_custom = None
        mock_args.schedule_prefix = "auto"
        mock_args.retention_days = 7
        mock_args.notification_email = None
        mock_args.list_schedules = False
        mock_args.remove_schedule = None
        mock_args.test_notifications = False

        config = CLIConfig(mock_args)

        assert config.show_progress is False  # derivado: not quiet
        assert config.use_colors is False  # derivado: not no_color

    def test_cli_config_repr(self):
        """
        Test que verifica la representación en string de CLIConfig.
        """
        mock_args = Mock()
        mock_args.name = None
        mock_args.container = "test_container"
        mock_args.dir = "test_backups"
        mock_args.verbose = False
        mock_args.quiet = True
        mock_args.force = False
        mock_args.list = False
        mock_args.no_color = False

        # Add missing required attributes for CLIConfig
        mock_args.restore = False
        mock_args.restore_file = None
        mock_args.pod = None
        mock_args.namespace = "default"
        mock_args.labels = None
        mock_args.k8s_container = None
        mock_args.auto_detect = False
        mock_args.force_docker = False
        mock_args.force_kubernetes = False
        mock_args.backup_type = "auto"
        mock_args.force_full = False
        mock_args.retention_daily = None
        mock_args.retention_weekly = None
        mock_args.retention_monthly = None
        mock_args.retention_full = None
        mock_args.apply_retention = False
        mock_args.retention_dry_run = False
        mock_args.backup_summary = False
        mock_args.schedule = None
        mock_args.schedule_custom = None
        mock_args.schedule_prefix = "auto"
        mock_args.retention_days = 7
        mock_args.notification_email = None
        mock_args.list_schedules = False
        mock_args.remove_schedule = None
        mock_args.test_notifications = False

        config = CLIConfig(mock_args)
        repr_str = repr(config)

        assert "CLIConfig" in repr_str
        assert "test_container" in repr_str
        assert "test_backups" in repr_str
        assert "quiet=True" in repr_str
