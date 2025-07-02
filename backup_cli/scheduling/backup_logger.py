"""
Módulo de logging para backups automáticos
Responsabilidad única: manejo de logs y archivos de estado
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from ..utils.colors import print_colored_message


class BackupLogger:
    """
    Responsable únicamente del logging y manejo de estado de backups
    """

    def __init__(self, backup_dir: str):
        self.backup_dir = Path(backup_dir)
        self.log_file = self.backup_dir / "scheduled_backups.log"
        self.status_file = self.backup_dir / ".metadata" / "last_status.json"

    def log_backup_status(
        self,
        success: bool,
        backup_name: str,
        environment: str,
        target: str,
        details: str = None,
    ):
        """
        Registra el estado del backup en el archivo de log
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "ÉXITO" if success else "FALLO"

        log_message = f"[{timestamp}] {status} - {backup_name} ({environment}:{target})"

        if details:
            log_message += f" - {details}"

        log_message += "\n"

        try:
            self.log_file.parent.mkdir(exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_message)
        except Exception as e:
            print_colored_message("ERROR", f"Error escribiendo log: {e}")

    def update_status_file(
        self,
        success: bool,
        backup_name: str,
        environment: str,
        target: str,
        details: str = None,
    ):
        """
        Actualiza el archivo de estado con la información del último backup
        """
        status_data = {
            "last_backup": {
                "timestamp": datetime.now().isoformat(),
                "success": success,
                "backup_name": backup_name,
                "environment": environment,
                "target": target,
                "details": details,
            }
        }

        try:
            self.status_file.parent.mkdir(exist_ok=True)
            with open(self.status_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print_colored_message("ERROR", f"Error actualizando estado: {e}")

    def get_last_backup_status(self) -> Optional[Dict]:
        """
        Obtiene el estado del último backup realizado
        """
        try:
            if not self.status_file.exists():
                return None

            with open(self.status_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            return data.get("last_backup")

        except Exception as e:
            print_colored_message("ERROR", f"Error leyendo estado: {e}")
            return None

    def get_backup_history(self, lines: int = 50) -> list:
        """
        Obtiene el historial de backups del archivo de log
        """
        try:
            if not self.log_file.exists():
                return []

            with open(self.log_file, "r", encoding="utf-8") as f:
                all_lines = f.readlines()

            # Retornar las últimas 'lines' líneas
            return [line.strip() for line in all_lines[-lines:] if line.strip()]

        except Exception as e:
            print_colored_message("ERROR", f"Error leyendo historial: {e}")
            return [] 