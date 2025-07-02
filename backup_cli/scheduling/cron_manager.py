"""
Gestor de cron jobs para programación automática de backups en Docker
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from ..utils.colors import print_colored_message


class CronManager:
    """
    Gestiona la programación de backups usando cron del sistema
    """

    def __init__(self, script_path: str):
        self.script_path = Path(script_path).absolute()
        self.backup_prefix = "auto_backup"

    def add_scheduled_backup(
        self,
        schedule: str,
        container: str = None,
        backup_name: str = None,
        notification_email: str = None,
    ) -> bool:
        """
        Agrega un backup programado al cron del usuario
        """
        try:
            # Construir comando de backup
            cmd_parts = [
                "cd",
                str(self.script_path.parent),
                "&&",
                "python3",
                str(self.script_path.name),
                "--force-docker",
                "--quiet",
            ]

            if container:
                cmd_parts.extend(["--container", container])

            if backup_name:
                cmd_parts.extend(["--name", f"{backup_name}_$(date +%Y%m%d_%H%M)"])
            else:
                cmd_parts.extend(
                    ["--name", f"{self.backup_prefix}_$(date +%Y%m%d_%H%M)"]
                )

            # Agregar logging
            log_file = self.script_path.parent / "backups" / "scheduled_backups.log"
            cmd_parts.extend([">>", str(log_file), "2>&1"])

            command = " ".join(cmd_parts)

            # Crear entrada de cron
            cron_entry = f"{schedule} {command}"

            # Agregar al crontab
            return self._add_cron_entry(cron_entry, notification_email)

        except Exception as e:
            print_colored_message("ERROR", f"Error programando backup: {e}")
            return False

    def _add_cron_entry(self, cron_entry: str, notification_email: str = None) -> bool:
        """
        Agrega una entrada al crontab del usuario
        """
        try:
            # Obtener crontab actual
            result = subprocess.run(
                ["crontab", "-l"], capture_output=True, text=True, timeout=10
            )

            current_cron = result.stdout if result.returncode == 0 else ""

            # Verificar si ya existe una entrada similar
            if cron_entry.split(" ", 5)[-1] in current_cron:
                print_colored_message("WARNING", "Ya existe una programación similar")
                return True

            # Agregar nueva entrada
            new_cron = current_cron + "\n" + cron_entry + "\n"

            # Configurar notificaciones por email si se especifica
            if notification_email and "MAILTO=" not in current_cron:
                new_cron = f"MAILTO={notification_email}\n" + new_cron

            # Escribir nuevo crontab
            with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
                f.write(new_cron)
                temp_file = f.name

            result = subprocess.run(
                ["crontab", temp_file], capture_output=True, text=True, timeout=10
            )

            os.unlink(temp_file)

            if result.returncode == 0:
                print_colored_message("SUCCESS", "Backup programado exitosamente")
                return True
            else:
                print_colored_message(
                    "ERROR", f"Error configurando cron: {result.stderr}"
                )
                return False

        except Exception as e:
            print_colored_message("ERROR", f"Error manejando crontab: {e}")
            return False

    def list_scheduled_backups(self) -> List[str]:
        """
        Lista los backups programados actualmente
        """
        try:
            result = subprocess.run(
                ["crontab", "-l"], capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                return []

            lines = result.stdout.strip().split("\n")
            backup_entries = []

            for line in lines:
                if "backup_orchestrator.py" in line and not line.startswith("#"):
                    backup_entries.append(line.strip())

            return backup_entries

        except Exception as e:
            print_colored_message("ERROR", f"Error listando programaciones: {e}")
            return []

    def remove_scheduled_backup(self, schedule_pattern: str) -> bool:
        """
        Elimina un backup programado del cron
        """
        try:
            result = subprocess.run(
                ["crontab", "-l"], capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                print_colored_message("WARNING", "No hay crontab configurado")
                return True

            lines = result.stdout.strip().split("\n")
            new_lines = []

            for line in lines:
                if schedule_pattern not in line:
                    new_lines.append(line)

            new_cron = "\n".join(new_lines) + "\n"

            with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
                f.write(new_cron)
                temp_file = f.name

            result = subprocess.run(
                ["crontab", temp_file], capture_output=True, text=True, timeout=10
            )

            os.unlink(temp_file)

            if result.returncode == 0:
                print_colored_message("SUCCESS", "Programación eliminada")
                return True
            else:
                print_colored_message(
                    "ERROR", f"Error eliminando programación: {result.stderr}"
                )
                return False

        except Exception as e:
            print_colored_message("ERROR", f"Error eliminando programación: {e}")
            return False

    @staticmethod
    def get_predefined_schedules() -> Dict[str, str]:
        """
        Retorna programaciones predefinidas comunes
        """
        return {
            "hourly": "0 * * * *",  # Cada hora
            "daily": "0 2 * * *",  # Diario a las 2 AM
            "weekly": "0 2 * * 0",  # Semanal los domingos a las 2 AM
            "monthly": "0 2 1 * *",  # Mensual el día 1 a las 2 AM
            "workdays": "0 2 * * 1-5",  # Días laborables a las 2 AM
        }
