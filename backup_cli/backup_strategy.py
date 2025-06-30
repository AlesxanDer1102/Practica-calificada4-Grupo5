"""
Gestor de estrategias de backup y políticas de retención
Implementación sencilla que soporta backups completos e incrementales
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import hashlib


class BackupStrategy:
    """
    Gestiona diferentes estrategias de backup y políticas de retención
    """

    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

        # Directorio para metadatos
        self.metadata_dir = self.backup_dir / ".metadata"
        self.metadata_dir.mkdir(exist_ok=True)

        self.logger = logging.getLogger(__name__)

        # Archivo de estado para backups incrementales
        self.state_file = self.metadata_dir / "backup_state.json"

        # Configuración por defecto de retención
        self.retention_policies = {
            "daily": 7,  # Mantener 7 backups diarios
            "weekly": 4,  # Mantener 4 backups semanales
            "monthly": 12,  # Mantener 12 backups mensuales
            "full": 3,  # Mantener 3 backups completos
        }

    def load_backup_state(self) -> Dict:
        """
        Carga el estado de los backups desde archivo
        """
        if not self.state_file.exists():
            return {
                "last_full_backup": None,
                "last_incremental_backup": None,
                "schema_hash": None,
                "backups": [],
            }

        try:
            with open(self.state_file, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error cargando estado de backup: {e}")
            return {
                "last_full_backup": None,
                "last_incremental_backup": None,
                "schema_hash": None,
                "backups": [],
            }

    def save_backup_state(self, state: Dict):
        """
        Guarda el estado de los backups
        """
        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Error guardando estado de backup: {e}")

    def determine_backup_type(self, force_full: bool = False) -> str:
        """
        Determina si el backup debe ser completo o incremental
        """
        if force_full:
            return "full"

        state = self.load_backup_state()

        # Si no hay backup completo previo, hacer completo
        if not state.get("last_full_backup"):
            return "full"

        # Si el último backup completo fue hace más de 7 días, hacer completo
        last_full = datetime.fromisoformat(state["last_full_backup"])
        if datetime.now() - last_full > timedelta(days=7):
            return "full"

        # Si hay más de 5 backups incrementales, hacer completo
        incremental_count = len(
            [
                b
                for b in state.get("backups", [])
                if b.get("type") == "incremental"
                and datetime.fromisoformat(b["timestamp"]) > last_full
            ]
        )

        if incremental_count >= 5:
            return "full"

        return "incremental"

    def create_backup_metadata(
        self, backup_name: str, backup_type: str, file_size: int, duration: float
    ) -> Dict:
        """
        Crea metadatos para el backup
        """
        metadata = {
            "name": backup_name,
            "type": backup_type,
            "timestamp": datetime.now().isoformat(),
            "file_size": file_size,
            "duration": duration,
            "retention_category": self._get_retention_category(backup_type),
        }

        # Guardar metadatos individuales
        metadata_file = self.metadata_dir / f"{backup_name}.json"
        try:
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error guardando metadatos: {e}")

        return metadata

    def _get_retention_category(self, backup_type: str) -> str:
        """
        Determina la categoría de retención basada en el tipo y fecha
        """
        now = datetime.now()

        if backup_type == "full":
            return "full"
        elif now.weekday() == 6:  # Domingo
            return "weekly"
        elif now.day == 1:  # Primer día del mes
            return "monthly"
        else:
            return "daily"

    def update_backup_state(self, backup_name: str, backup_type: str, metadata: Dict):
        """
        Actualiza el estado después de crear un backup
        """
        state = self.load_backup_state()

        # Actualizar timestamps
        if backup_type == "full":
            state["last_full_backup"] = metadata["timestamp"]
        else:
            state["last_incremental_backup"] = metadata["timestamp"]

        # Agregar backup a la lista
        state["backups"].append(metadata)

        # Guardar estado
        self.save_backup_state(state)

    def get_backup_command_args(self, backup_type: str) -> List[str]:
        """
        Obtiene argumentos específicos para pg_dump según el tipo de backup
        """
        if backup_type == "full":
            # Backup completo con esquema y datos
            return ["--clean", "--create", "--verbose"]

        elif backup_type == "incremental":
            # Backup incremental - solo datos sin limpiar
            # Para simplificar, hacemos un backup completo pero más ligero
            return ["--verbose", "--no-owner", "--no-privileges"]

        # Fallback para cualquier otro tipo
        return ["--clean", "--create", "--verbose"]

    def apply_retention_policy(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Aplica las políticas de retención eliminando backups antiguos
        """
        state = self.load_backup_state()
        backups = state.get("backups", [])

        # Agrupar backups por categoría de retención
        categorized_backups = {}
        for backup in backups:
            category = backup.get("retention_category", "daily")
            if category not in categorized_backups:
                categorized_backups[category] = []
            categorized_backups[category].append(backup)

        deleted_counts = {}

        # Aplicar política para cada categoría
        for category, category_backups in categorized_backups.items():
            max_count = self.retention_policies.get(category, 7)

            # Ordenar por timestamp (más recientes primero)
            category_backups.sort(
                key=lambda x: datetime.fromisoformat(x["timestamp"]), reverse=True
            )

            # Marcar para eliminación los que excedan el límite
            to_delete = category_backups[max_count:]
            deleted_counts[category] = len(to_delete)

            for backup in to_delete:
                if not dry_run:
                    self._delete_backup(backup["name"])
                    # Remover del estado
                    state["backups"] = [
                        b for b in state["backups"] if b["name"] != backup["name"]
                    ]

        # Guardar estado actualizado
        if not dry_run:
            self.save_backup_state(state)

        return deleted_counts

    def _delete_backup(self, backup_name: str):
        """
        Elimina un backup y sus metadatos
        """
        try:
            # Eliminar archivo de backup
            backup_file = self.backup_dir / f"{backup_name}.sql"
            if backup_file.exists():
                backup_file.unlink()
                self.logger.info(f"Backup eliminado: {backup_name}")

            # Eliminar metadatos
            metadata_file = self.metadata_dir / f"{backup_name}.json"
            if metadata_file.exists():
                metadata_file.unlink()

        except Exception as e:
            self.logger.error(f"Error eliminando backup {backup_name}: {e}")

    def list_backups_by_type(self) -> Dict[str, List[Dict]]:
        """
        Lista backups agrupados por tipo
        """
        state = self.load_backup_state()
        backups = state.get("backups", [])

        result = {"full": [], "incremental": []}

        for backup in backups:
            backup_type = backup.get("type", "full")
            if backup_type in result:
                result[backup_type].append(backup)

        # Ordenar por timestamp
        for backup_list in result.values():
            backup_list.sort(
                key=lambda x: datetime.fromisoformat(x["timestamp"]), reverse=True
            )

        return result

    def get_retention_summary(self) -> Dict:
        """
        Obtiene resumen de la política de retención actual
        """
        state = self.load_backup_state()
        backups = state.get("backups", [])

        # Contar backups por categoría
        category_counts = {}
        for backup in backups:
            category = backup.get("retention_category", "daily")
            category_counts[category] = category_counts.get(category, 0) + 1

        # Crear resumen
        summary = {
            "policies": self.retention_policies.copy(),
            "current_counts": category_counts,
            "total_backups": len(backups),
        }

        # Calcular espacio usado
        total_size = sum(backup.get("file_size", 0) for backup in backups)
        summary["total_size_bytes"] = total_size
        summary["total_size_mb"] = round(total_size / (1024 * 1024), 2)

        return summary

    def configure_retention_policy(self, **policies):
        """
        Configura las políticas de retención
        """
        for category, count in policies.items():
            if category in self.retention_policies and count > 0:
                self.retention_policies[category] = count
                self.logger.info(
                    f"Política de retención actualizada: {category} = {count}"
                )

    def get_next_backup_recommendation(self) -> Dict:
        """
        Recomienda el tipo de backup y razón
        """
        backup_type = self.determine_backup_type()
        state = self.load_backup_state()

        recommendation = {"type": backup_type, "reason": ""}

        if backup_type == "full":
            if not state.get("last_full_backup"):
                recommendation["reason"] = "No existe backup completo previo"
            else:
                last_full = datetime.fromisoformat(state["last_full_backup"])
                days_since = (datetime.now() - last_full).days
                if days_since >= 7:
                    recommendation["reason"] = (
                        f"Último backup completo hace {days_since} días"
                    )
                else:
                    incremental_count = len(
                        [
                            b
                            for b in state.get("backups", [])
                            if b.get("type") == "incremental"
                            and datetime.fromisoformat(b["timestamp"]) > last_full
                        ]
                    )
                    recommendation["reason"] = (
                        f"Demasiados backups incrementales ({incremental_count})"
                    )
        else:
            recommendation["reason"] = "Backup incremental recomendado"

        return recommendation
