"""
Gestor principal de versionado de backups
Se integra con el sistema existente de BackupStrategy
"""

import hashlib
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .semantic_version import SemanticVersion, VersionBranch


class BackupVersionManager:
    """
    Gestor de versionado de backups que extiende el sistema existente
    """

    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

        # Directorio para metadatos de versionado
        self.version_dir = self.backup_dir / ".versions"
        self.version_dir.mkdir(exist_ok=True)

        # Archivos de control de versiones
        self.version_state_file = self.version_dir / "version_state.json"
        self.tags_file = self.version_dir / "tags.json"
        self.branches_file = self.version_dir / "branches.json"

        self.logger = logging.getLogger(__name__)

        # Estado inicial del sistema de versiones
        self._initialize_version_system()

    def _initialize_version_system(self):
        """Inicializa el sistema de versiones si no existe"""
        if not self.version_state_file.exists():
            initial_state = {
                "current_version": "1.0.0-main.20241201_000000",
                "latest_versions_by_branch": {
                    "main": "1.0.0-main.20241201_000000",
                    "develop": None,
                    "staging": None,
                    "hotfix": None,
                    "feature": None,
                    "release": None,
                    "manual": None,
                },
                "versioned_backups": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            self._save_version_state(initial_state)

        if not self.tags_file.exists():
            self._save_json_file(self.tags_file, {})

        if not self.branches_file.exists():
            initial_branches = {
                branch.value: {
                    "created_at": datetime.now().isoformat(),
                    "description": f"Rama {branch.value}",
                    "backup_count": 0,
                }
                for branch in VersionBranch
            }
            self._save_json_file(self.branches_file, initial_branches)

    def _load_version_state(self) -> Dict:
        """Carga el estado de versiones"""
        try:
            with open(self.version_state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error cargando estado de versiones: {e}")
            return {}

    def _save_version_state(self, state: Dict):
        """Guarda el estado de versiones"""
        try:
            state["updated_at"] = datetime.now().isoformat()
            with open(self.version_state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error guardando estado de versiones: {e}")

    def _save_json_file(self, file_path: Path, data: Dict):
        """Guarda datos JSON de forma segura"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error guardando archivo {file_path}: {e}")

    def _load_json_file(self, file_path: Path) -> Dict:
        """Carga archivo JSON de forma segura"""
        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Error cargando archivo {file_path}: {e}")
        return {}

    def create_versioned_backup(
        self,
        backup_name: str,
        version: Optional[SemanticVersion] = None,
        tags: Optional[List[str]] = None,
        description: str = "",
        auto_increment: str = "patch",
    ) -> Tuple[SemanticVersion, str]:
        """
        Crea un backup con versionado semántico

        Args:
            backup_name: Nombre del archivo de backup (sin .sql)
            version: Versión específica o None para auto-incrementar
            tags: Lista de etiquetas para el backup
            description: Descripción del backup
            auto_increment: Nivel de incremento automático (major, minor, patch)

        Returns:
            Tupla (version_objeto, backup_filename_versionado)
        """
        state = self._load_version_state()

        # Determinar versión a usar
        if version is None:
            if state.get("current_version"):
                current = SemanticVersion.parse(state["current_version"])
                version = current.increment(auto_increment)
            else:
                version = SemanticVersion()

        # Generar nombre de archivo versionado
        versioned_filename = f"{backup_name}_v{version}.sql"

        # Crear metadatos del backup versionado
        version_metadata = {
            "version": version.to_dict(),
            "backup_name": backup_name,
            "versioned_filename": versioned_filename,
            "original_filename": f"{backup_name}.sql",
            "tags": tags or [],
            "description": description,
            "created_at": datetime.now().isoformat(),
            "file_hash": None,  # Se calculará después de crear el archivo
            "file_size": None,  # Se calculará después de crear el archivo
            "backup_type": "full",  # Por defecto, se puede actualizar
            "branch_info": {
                "name": version.branch.value,
                "color": version.get_branch_color(),
            },
        }

        # Actualizar estado
        state["current_version"] = str(version)
        state["latest_versions_by_branch"][version.branch.value] = str(version)
        state["versioned_backups"].append(version_metadata)

        self._save_version_state(state)

        # Actualizar información de ramas
        self._update_branch_info(version.branch, version_metadata)

        # Procesar etiquetas si se proporcionaron
        if tags:
            self._add_tags_to_version(version, tags)

        self.logger.info(f"Versión creada: {version} -> {versioned_filename}")

        return version, versioned_filename

    def finalize_versioned_backup(self, version: SemanticVersion, backup_path: Path):
        """
        Finaliza el backup versionado calculando hash y tamaño
        """
        if not backup_path.exists():
            self.logger.error(f"Archivo de backup no encontrado: {backup_path}")
            return

        # Calcular hash del archivo
        file_hash = self._calculate_file_hash(backup_path)
        file_size = backup_path.stat().st_size

        # Actualizar metadatos
        state = self._load_version_state()
        for backup_meta in state["versioned_backups"]:
            if backup_meta["version"]["version_string"] == str(version):
                backup_meta["file_hash"] = file_hash
                backup_meta["file_size"] = file_size
                break

        self._save_version_state(state)

        # Crear enlace simbólico para fácil acceso
        latest_link = self.backup_dir / f"latest_{version.branch.value}.sql"
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(backup_path.name)

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calcula hash SHA256 del archivo"""
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculando hash: {e}")
            return ""

    def _update_branch_info(self, branch: VersionBranch, version_metadata: Dict):
        """Actualiza información de la rama"""
        branches_data = self._load_json_file(self.branches_file)

        if branch.value not in branches_data:
            branches_data[branch.value] = {
                "created_at": datetime.now().isoformat(),
                "description": f"Rama {branch.value}",
                "backup_count": 0,
            }

        branches_data[branch.value]["backup_count"] += 1
        branches_data[branch.value]["last_backup"] = datetime.now().isoformat()

        self._save_json_file(self.branches_file, branches_data)

    def _add_tags_to_version(self, version: SemanticVersion, tags: List[str]):
        """Agrega etiquetas a una versión"""
        tags_data = self._load_json_file(self.tags_file)

        for tag in tags:
            if tag not in tags_data:
                tags_data[tag] = []

            # Evitar duplicados
            version_str = str(version)
            if version_str not in [t["version"] for t in tags_data[tag]]:
                tags_data[tag].append(
                    {"version": version_str, "created_at": datetime.now().isoformat()}
                )

        self._save_json_file(self.tags_file, tags_data)

    def list_versions(
        self,
        branch: Optional[VersionBranch] = None,
        tag: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        Lista versiones con filtros opcionales
        """
        state = self._load_version_state()
        backups = state.get("versioned_backups", [])

        # Filtrar por rama
        if branch:
            backups = [b for b in backups if b["version"]["branch"] == branch.value]

        # Filtrar por etiqueta
        if tag:
            backups = [b for b in backups if tag in b.get("tags", [])]

        # Ordenar por fecha de creación (más recientes primero)
        # Manejar casos donde created_at podría ser None o tener formato incorrecto
        def safe_sort_key(backup):
            try:
                created_at = backup.get("created_at")
                if created_at:
                    return created_at
                else:
                    return "1900-01-01T00:00:00"  # Fecha por defecto para None
            except:
                return "1900-01-01T00:00:00"

        backups.sort(key=safe_sort_key, reverse=True)

        # Limitar resultados
        if limit:
            backups = backups[:limit]

        return backups

    def get_version_info(self, version_string: str) -> Optional[Dict]:
        """Obtiene información detallada de una versión específica"""
        state = self._load_version_state()

        for backup in state.get("versioned_backups", []):
            if backup["version"]["version_string"] == version_string:
                return backup

        return None

    def create_tag(self, version_string: str, tag_name: str, description: str = ""):
        """Crea una etiqueta para una versión específica"""
        tags_data = self._load_json_file(self.tags_file)

        if tag_name not in tags_data:
            tags_data[tag_name] = []

        # Verificar que la versión existe
        if not self.get_version_info(version_string):
            raise ValueError(f"Versión no encontrada: {version_string}")

        # Agregar etiqueta
        tag_entry = {
            "version": version_string,
            "description": description,
            "created_at": datetime.now().isoformat(),
        }

        # Evitar duplicados
        existing = [t for t in tags_data[tag_name] if t["version"] == version_string]
        if not existing:
            tags_data[tag_name].append(tag_entry)
            self._save_json_file(self.tags_file, tags_data)
            self.logger.info(
                f"Etiqueta '{tag_name}' agregada a versión {version_string}"
            )

    def list_tags(self) -> Dict:
        """Lista todas las etiquetas disponibles"""
        return self._load_json_file(self.tags_file)

    def list_branches(self) -> Dict:
        """Lista todas las ramas y su información"""
        return self._load_json_file(self.branches_file)

    def get_latest_version(
        self, branch: VersionBranch = VersionBranch.MAIN
    ) -> Optional[SemanticVersion]:
        """Obtiene la última versión de una rama específica"""
        state = self._load_version_state()
        latest_version_str = state.get("latest_versions_by_branch", {}).get(
            branch.value
        )

        if latest_version_str:
            try:
                return SemanticVersion.parse(latest_version_str)
            except ValueError:
                self.logger.error(f"Error parseando versión: {latest_version_str}")

        return None

    def compare_versions(self, version1_str: str, version2_str: str) -> Dict:
        """
        Compara dos versiones y retorna información de diferencias
        """
        try:
            v1 = SemanticVersion.parse(version1_str)
            v2 = SemanticVersion.parse(version2_str)

            info1 = self.get_version_info(version1_str)
            info2 = self.get_version_info(version2_str)

            # Manejar comparación de tamaños de archivo de forma segura
            size1 = 0
            size2 = 0
            if info1 and info1.get("file_size") is not None:
                size1 = info1["file_size"]
            if info2 and info2.get("file_size") is not None:
                size2 = info2["file_size"]

            return {
                "version1": {
                    "version": str(v1),
                    "info": info1,
                    "newer": v1.is_newer_than(v2),
                },
                "version2": {
                    "version": str(v2),
                    "info": info2,
                    "newer": v2.is_newer_than(v1),
                },
                "compatible": v1.is_compatible(v2),
                "same_branch": v1.branch == v2.branch,
                "file_size_diff": size1 - size2,
            }

        except ValueError as e:
            return {"error": str(e)}

    def rollback_to_version(
        self, target_version_str: str, create_backup: bool = True
    ) -> bool:
        """
        Hace rollback a una versión específica
        """
        target_info = self.get_version_info(target_version_str)
        if not target_info:
            self.logger.error(f"Versión no encontrada: {target_version_str}")
            return False

        versioned_file = self.backup_dir / target_info["versioned_filename"]
        if not versioned_file.exists():
            self.logger.error(f"Archivo de backup no encontrado: {versioned_file}")
            return False

        # Actualizar versión actual
        state = self._load_version_state()
        state["current_version"] = target_version_str

        # Crear entrada de rollback en el historial
        rollback_entry = {
            "action": "rollback",
            "target_version": target_version_str,
            "timestamp": datetime.now().isoformat(),
            "created_backup": create_backup,
        }

        if "rollback_history" not in state:
            state["rollback_history"] = []
        state["rollback_history"].append(rollback_entry)

        self._save_version_state(state)

        self.logger.info(f"Rollback completado a versión: {target_version_str}")
        return True

    def get_rollback_history(self) -> List[Dict]:
        """Obtiene el historial de rollbacks"""
        state = self._load_version_state()
        return state.get("rollback_history", [])

    def cleanup_old_versions(self, keep_count: int = 10, dry_run: bool = False) -> Dict:
        """
        Limpia versiones antiguas manteniendo las más recientes
        """
        state = self._load_version_state()
        backups = state.get("versioned_backups", [])

        # Agrupar por rama
        by_branch = {}
        for backup in backups:
            branch = backup["version"]["branch"]
            if branch not in by_branch:
                by_branch[branch] = []
            by_branch[branch].append(backup)

        cleanup_result = {"deleted_count": 0, "deleted_versions": [], "errors": []}

        # Limpiar cada rama por separado
        for branch, branch_backups in by_branch.items():
            # Ordenar por fecha de creación (más recientes primero)
            # Usar la misma función segura de ordenamiento
            def safe_sort_key(backup):
                try:
                    created_at = backup.get("created_at")
                    if created_at:
                        return created_at
                    else:
                        return "1900-01-01T00:00:00"
                except:
                    return "1900-01-01T00:00:00"

            branch_backups.sort(key=safe_sort_key, reverse=True)

            # Versiones a eliminar (las que exceden keep_count)
            to_delete = branch_backups[keep_count:]

            for backup_meta in to_delete:
                version_str = backup_meta["version"]["version_string"]
                versioned_file = self.backup_dir / backup_meta["versioned_filename"]

                if not dry_run:
                    try:
                        # Eliminar archivo
                        if versioned_file.exists():
                            versioned_file.unlink()

                        # Remover del estado
                        state["versioned_backups"] = [
                            b
                            for b in state["versioned_backups"]
                            if b["version"]["version_string"] != version_str
                        ]

                        cleanup_result["deleted_count"] += 1
                        cleanup_result["deleted_versions"].append(version_str)

                    except Exception as e:
                        error_msg = f"Error eliminando {version_str}: {e}"
                        cleanup_result["errors"].append(error_msg)
                        self.logger.error(error_msg)
                else:
                    # Solo simular para dry run
                    cleanup_result["deleted_versions"].append(version_str)

        if not dry_run:
            self._save_version_state(state)

        return cleanup_result
