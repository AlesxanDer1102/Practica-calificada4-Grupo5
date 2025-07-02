"""
Utilidades para mostrar información de versionado en CLI
"""

from datetime import datetime
from typing import Dict, List

from ..utils.colors import Colors, print_colored_message
from .semantic_version import VersionBranch


class VersionDisplayFormatter:
    """Formateador para mostrar información de versionado en CLI"""

    @staticmethod
    def format_file_size(size_bytes) -> str:
        """Formatea el tamaño de archivo de forma legible"""
        # Manejar valores None o no numéricos
        if size_bytes is None:
            return "N/A"

        try:
            size_bytes = float(size_bytes)
            if size_bytes < 0:
                return "N/A"
            if size_bytes == 0:
                return "0 B"

            for unit in ["B", "KB", "MB", "GB"]:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f} TB"
        except (ValueError, TypeError):
            return "N/A"

    @staticmethod
    def format_timestamp(iso_timestamp) -> str:
        """Formatea timestamp ISO a formato legible"""
        if iso_timestamp is None:
            return "N/A"

        try:
            # Asegurar que sea string
            iso_str = str(iso_timestamp)
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            # Si no se puede parsear, devolver el valor original o N/A
            return str(iso_timestamp) if iso_timestamp else "N/A"

    @staticmethod
    def display_version_list(versions: List[Dict], use_colors: bool = True):
        """Muestra lista de versiones formateada"""
        if not versions:
            print_colored_message("INFO", "No se encontraron versiones.", use_colors)
            return

        print(
            f"\n{'Version':<25} {'Rama':<12} {'Tamaño':<10} {'Fecha':<20} {'Etiquetas'}"
        )
        print("─" * 80)

        for version_data in versions:
            version_info = version_data["version"]
            branch_indicator = VersionDisplayFormatter._get_branch_indicator(
                version_info["branch"]
            )

            # Información básica
            version_str = version_info["version_string"]
            branch = f"{branch_indicator} {version_info['branch']}"
            size = VersionDisplayFormatter.format_file_size(
                version_data.get("file_size", 0)
            )
            date = VersionDisplayFormatter.format_timestamp(version_data["created_at"])
            tags = ", ".join(version_data.get("tags", [])) or "─"

            print(f"{version_str:<25} {branch:<12} {size:<10} {date:<20} {tags}")

        print()

    @staticmethod
    def display_version_info(version_data: Dict, use_colors: bool = True):
        """Muestra información detallada de una versión"""
        if not version_data:
            print_colored_message("ERROR", "Versión no encontrada.", use_colors)
            return

        version_info = version_data["version"]
        branch_indicator = VersionDisplayFormatter._get_branch_indicator(
            version_info["branch"]
        )

        print_colored_message(
            "INFO",
            f"Información de Versión: {version_info['version_string']}",
            use_colors,
        )
        print()

        # Información de versión
        print(f"Versión:        {version_info['version_string']}")
        print(f"Rama:           {branch_indicator} {version_info['branch']}")
        print(f"Build:          {version_info.get('build', 'N/A')}")
        if version_info.get("pre_release"):
            print(f"Pre-release:    {version_info['pre_release']}")
        if version_info.get("metadata"):
            print(f"Metadata:       {version_info['metadata']}")

        print()

        # Información del backup
        print(f"Archivo:        {version_data['versioned_filename']}")
        print(f"Tipo:           {version_data.get('backup_type', 'full').upper()}")
        if version_data.get("file_size"):
            print(
                f"Tamaño:         {VersionDisplayFormatter.format_file_size(version_data['file_size'])}"
            )
        print(
            f"Creado:         {VersionDisplayFormatter.format_timestamp(version_data['created_at'])}"
        )

        # Hash de archivo
        if version_data.get("file_hash"):
            print(f"SHA256:         {version_data['file_hash'][:16]}...")

        # Descripción
        if version_data.get("description"):
            print(f"Descripción:    {version_data['description']}")

        # Etiquetas
        tags = version_data.get("tags", [])
        if tags:
            print(f"Etiquetas:      {', '.join(tags)}")

        print()

    @staticmethod
    def display_branches_info(branches: Dict, use_colors: bool = True):
        """Muestra información de ramas"""
        if not branches:
            print_colored_message("INFO", "No se encontraron ramas.", use_colors)
            return

        print_colored_message("INFO", "Ramas de Versionado", use_colors)
        print()

        print(f"{'Rama':<12} {'Backups':<8} {'Último Backup':<20} {'Descripción'}")
        print("─" * 65)

        for branch_name, branch_info in branches.items():
            indicator = VersionDisplayFormatter._get_branch_indicator(branch_name)
            count = branch_info.get("backup_count", 0)
            last_backup = branch_info.get("last_backup", "Nunca")
            if last_backup != "Nunca":
                last_backup = VersionDisplayFormatter.format_timestamp(last_backup)
            description = branch_info.get("description", "")

            print(
                f"{indicator} {branch_name:<10} {count:<8} {last_backup:<20} {description}"
            )

        print()

    @staticmethod
    def display_tags_info(tags: Dict, use_colors: bool = True):
        """Muestra información de etiquetas"""
        if not tags:
            print_colored_message("INFO", "No se encontraron etiquetas.", use_colors)
            return

        print_colored_message("INFO", "Etiquetas Disponibles", use_colors)
        print()

        for tag_name, tag_versions in tags.items():
            print(f"[TAG] {tag_name}")
            for tag_entry in tag_versions:
                version = tag_entry["version"]
                created = VersionDisplayFormatter.format_timestamp(
                    tag_entry["created_at"]
                )
                description = tag_entry.get("description", "")

                print(f"   ├─ {version} ({created})")
                if description:
                    print(f"   │  {description}")
            print()

    @staticmethod
    def display_version_comparison(comparison: Dict, use_colors: bool = True):
        """Muestra comparación entre versiones"""
        if comparison.get("error"):
            print_colored_message("ERROR", comparison["error"], use_colors)
            return

        v1 = comparison["version1"]
        v2 = comparison["version2"]

        print_colored_message("INFO", "Comparación de Versiones", use_colors)
        print()

        # Información básica
        print(f"Versión 1:      {v1['version']} {'(más nueva)' if v1['newer'] else ''}")
        print(f"Versión 2:      {v2['version']} {'(más nueva)' if v2['newer'] else ''}")
        print()

        # Compatibilidad
        compatible_icon = "SI" if comparison["compatible"] else "NO"
        same_branch_icon = "SI" if comparison["same_branch"] else "NO"

        print(f"Compatible:     {compatible_icon}")
        print(f"Misma rama:     {same_branch_icon}")

        # Diferencia de tamaño
        size_diff = comparison.get("file_size_diff", 0)
        if size_diff != 0:
            sign = "+" if size_diff > 0 else ""
            print(
                f"Diff. tamaño:   {sign}{VersionDisplayFormatter.format_file_size(abs(size_diff))}"
            )

        print()

    @staticmethod
    def display_rollback_history(history: List[Dict], use_colors: bool = True):
        """Muestra historial de rollbacks"""
        if not history:
            print_colored_message("INFO", "No hay historial de rollbacks.", use_colors)
            return

        print_colored_message("INFO", "Historial de Rollbacks", use_colors)
        print()

        print(f"{'Fecha':<20} {'Versión Objetivo':<25} {'Backup Creado'}")
        print("─" * 65)

        for entry in history:
            timestamp = VersionDisplayFormatter.format_timestamp(entry["timestamp"])
            target = entry["target_version"]
            backup_created = "SI" if entry.get("created_backup") else "NO"

            print(f"{timestamp:<20} {target:<25} {backup_created}")

        print()

    @staticmethod
    def display_cleanup_result(
        result: Dict, dry_run: bool = False, use_colors: bool = True
    ):
        """Muestra resultado de limpieza de versiones"""
        action = "Se eliminarían" if dry_run else "Eliminadas"

        if result["deleted_count"] == 0:
            print_colored_message("INFO", "No hay versiones para eliminar.", use_colors)
            return

        print_colored_message(
            "INFO", f"{action}: {result['deleted_count']} versiones", use_colors
        )

        if result["deleted_versions"]:
            print("\nVersiones:")
            for version in result["deleted_versions"]:
                status = "[DEL]" if not dry_run else "[SIM]"
                print(f"  {status} {version}")

        if result["errors"]:
            print_colored_message(
                "WARNING", f"Errores: {len(result['errors'])}", use_colors
            )
            for error in result["errors"]:
                print(f"  [ERR] {error}")

        print()

    @staticmethod
    def _get_branch_indicator(branch_name: str) -> str:
        """Obtiene indicador para la rama"""
        indicator_map = {
            "main": "[M]",
            "develop": "[D]",
            "staging": "[S]",
            "hotfix": "[H]",
            "feature": "[F]",
            "release": "[R]",
            "manual": "[N]",
        }
        return indicator_map.get(branch_name, "[?]")
