#!/usr/bin/env python3

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from backup_cli.cli.parser import CLIConfig, create_cli_parser
from backup_cli.environment.detector import Environment, EnvironmentDetector
from backup_cli.handlers.docker_handler import DockerHandler
from backup_cli.handlers.kubernetes_handler import KubernetesHandler
from backup_cli.utils.colors import Colors, print_colored_message, should_use_colors
from backup_cli.utils.progress import ProgressIndicator
from backup_cli.utils.validator import BackupNameValidator, format_file_size


class UnifiedBackupOrchestrator:
    """
    Orquestador unificado de backups para PostgreSQL
    Soporta tanto Docker como Kubernetes con detección automática
    """

    def __init__(self, config: CLIConfig):
        self.config = config
        self.backup_dir = Path(config.backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

        if not config.use_colors:
            Colors.disable()

        self.db_config = {
            "user": "postgres",
            "password": "12345",  # Coincide con postgres-secret
            "database": "pc_db",  # Coincide con POSTGRES_DB del StatefulSet
        }

        self.env_detector = EnvironmentDetector()
        self.environment = self._determine_environment()

        self._initialize_handler()

        self.setup_logging()

    def _determine_environment(self) -> Environment:

        preferred = self.config.get_preferred_environment()

        if preferred == "docker":
            if self.config.verbose:
                self._print_message("INFO", "Forzando uso de Docker")
            return Environment.DOCKER
        elif preferred == "kubernetes":
            if self.config.verbose:
                self._print_message("INFO", "Forzando uso de Kubernetes")
            return Environment.KUBERNETES
        else:
            if self.config.verbose:
                self._print_message("INFO", "Detectando entorno automáticamente...")

            detected = self.env_detector.detect_environment()

            if self.config.verbose:
                env_info = self.env_detector.get_environment_info()
                self._print_message(
                    "INFO", f'Docker disponible: {env_info["docker_available"]}'
                )
                self._print_message(
                    "INFO", f'kubectl disponible: {env_info["kubectl_available"]}'
                )
                if "current_context" in env_info:
                    self._print_message(
                        "INFO", f'Contexto kubectl: {env_info["current_context"]}'
                    )

            if detected == Environment.UNKNOWN:
                # Fallback a Docker si no se puede detectar
                self._print_message(
                    "WARNING",
                    "No se pudo detectar el entorno, usando Docker como predeterminado",
                )
                return Environment.DOCKER

            if self.config.verbose:
                self._print_message("INFO", f"Entorno detectado: {detected.value}")

            return detected

    def _initialize_handler(self):
        """
        Inicializa el handler apropiado según el entorno
        """
        if self.environment == Environment.DOCKER:
            self.handler = DockerHandler()
            self._print_message("INFO", f"Usando entorno Docker")
        elif self.environment == Environment.KUBERNETES:
            self.handler = KubernetesHandler(namespace=self.config.namespace)
            self._print_message(
                "INFO",
                f"Usando entorno Kubernetes (namespace: {self.config.namespace})",
            )
        else:
            raise ValueError(f"Entorno no soportado: {self.environment}")

    def setup_logging(self):
        """
        Configura el sistema de logging
        """
        log_file = self.backup_dir / "backup_orchestrator.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(file_formatter)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)

    def _print_message(self, level: str, message: str):
        """Imprime mensaje con color si el progreso está habilitado"""
        if self.config.show_progress:
            print_colored_message(level, message, self.config.use_colors)
        # También log a archivo para debugging
        if hasattr(self, "logger"):
            if level == "ERROR":
                self.logger.error(message)
            elif level == "WARNING":
                self.logger.warning(message)
            else:
                self.logger.info(message)

    def _resolve_target(self) -> Optional[str]:
        """
        Resuelve el objetivo del backup (contenedor o pod) según el entorno
        """
        if self.environment == Environment.DOCKER:
            return self._resolve_docker_target()
        elif self.environment == Environment.KUBERNETES:
            return self._resolve_kubernetes_target()

        return None

    def _resolve_docker_target(self) -> Optional[str]:
        """
        Resuelve el contenedor Docker objetivo
        """
        if self.config.container:
            return self.config.container

        return self.handler.select_container_interactive()

    def _resolve_kubernetes_target(self) -> Optional[str]:
        """
        Resuelve el pod Kubernetes objetivo
        Adaptado para la configuración específica del proyecto
        """
        if self.config.pod:
            return self.config.pod

        default_labels = {"app": "postgres"}  # Label del StatefulSet
        labels_to_use = self.config.labels if self.config.labels else default_labels

        return self.handler.select_pod_interactive(labels_to_use)

    def _check_target_availability(self, target: str) -> bool:
        """
        Verifica que el objetivo esté disponible
        """
        if self.environment == Environment.DOCKER:
            return self.handler.check_container_status(target)
        elif self.environment == Environment.KUBERNETES:
            return self.handler.check_pod_status(target)

        return False

    def _get_postgres_container_name(self, target: str) -> Optional[str]:
        """
        Obtiene el nombre del contenedor PostgreSQL (solo relevante para K8s)
        """
        if self.environment == Environment.KUBERNETES:
            if self.config.k8s_container:
                return self.config.k8s_container
            return self.handler.get_postgres_container(target)

        return None  # Para Docker no es necesario

    def list_backups(self) -> list[dict]:
        """
        Lista todos los backups disponibles en el directorio
        """
        backups = []
        for backup_file in self.backup_dir.glob("*.sql"):
            stat = backup_file.stat()
            backups.append(
                {
                    "name": backup_file.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                    "path": backup_file,
                }
            )
        return sorted(backups, key=lambda x: x["modified"], reverse=True)

    def select_backup_interactive(self) -> Path:
        """
        Permite al usuario seleccionar un backup de forma interactiva
        """
        backups = self.list_backups()

        if not backups:
            self._print_message("ERROR", "No se encontraron backups disponibles")
            raise ValueError("No hay backups disponibles para restaurar")

        self._print_message("INFO", "Backups disponibles:")
        print()

        for i, backup in enumerate(backups, 1):
            size_formatted = format_file_size(backup["size"])
            modified_str = backup["modified"].strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {i}. {backup['name']}")
            print(f"     Tamaño: {size_formatted}")
            print(f"     Modificado: {modified_str}")
            print()

        while True:
            try:
                selection = input(
                    "Seleccione el número del backup a restaurar (0 para cancelar): "
                ).strip()

                if selection == "0":
                    self._print_message("INFO", "Operación cancelada por el usuario")
                    raise KeyboardInterrupt("Restauración cancelada")

                index = int(selection) - 1
                if 0 <= index < len(backups):
                    selected_backup = backups[index]["path"]
                    self._print_message(
                        "INFO", f"Backup seleccionado: {selected_backup.name}"
                    )
                    return selected_backup
                else:
                    print("Por favor, ingrese un número válido.")

            except ValueError:
                print("Por favor, ingrese un número válido.")
            except KeyboardInterrupt:
                raise

    def validate_backup_integrity(self, backup_path: Path) -> bool:
        """
        Valida la integridad básica del archivo de backup
        """
        try:
            if not backup_path.exists():
                self._print_message(
                    "ERROR", f"El archivo de backup no existe: {backup_path}"
                )
                return False

            if backup_path.stat().st_size == 0:
                self._print_message("ERROR", "El archivo de backup está vacío")
                return False

            with open(backup_path, "r", encoding="utf-8") as f:
                content = f.read(1000)  # Leer primeros 1000 caracteres

            required_patterns = ["CREATE", "INSERT", "--"]
            found_patterns = [
                pattern for pattern in required_patterns if pattern in content.upper()
            ]

            if len(found_patterns) < 2:
                self._print_message(
                    "WARNING", "El archivo no parece ser un backup válido de PostgreSQL"
                )
                return False

            self._print_message("INFO", "Validación de integridad del backup: EXITOSA")
            return True

        except Exception as e:
            self._print_message("ERROR", f"Error al validar backup: {str(e)}")
            return False

    def confirm_restore_operation(self, backup_path: Path, target: str) -> bool:
        """
        Solicita confirmación al usuario antes de proceder con la restauración
        """
        self._print_message(
            "WARNING",
            "ADVERTENCIA: Esta operación sobrescribirá TODOS los datos existentes",
        )
        print()
        print(f"Backup a restaurar: {backup_path.name}")
        print(f"Base de datos objetivo: {self.db_config['database']}")

        if self.environment == Environment.DOCKER:
            print(f"Contenedor: {target}")
        elif self.environment == Environment.KUBERNETES:
            print(f"Pod: {target}")
            print(f"Namespace: {self.config.namespace}")

        print()

        while True:
            confirmation = (
                input("¿Está seguro que desea continuar? (si/no): ").lower().strip()
            )

            if confirmation in ["si", "sí", "s", "yes", "y"]:
                self._print_message(
                    "INFO", "Confirmación recibida, procediendo con la restauración"
                )
                return True
            elif confirmation in ["no", "n"]:
                self._print_message("INFO", "Restauración cancelada por el usuario")
                return False
            else:
                print("Por favor, responda 'si' o 'no'")

    def create_backup(
        self, custom_name: str = None, force_overwrite: bool = False
    ) -> bool:
        """
        Crea un backup de la base de datos
        """
        try:
            backup_filename, name_modified = (
                BackupNameValidator.resolve_backup_filename(
                    self.backup_dir, custom_name, force_overwrite
                )
            )
        except ValueError as e:
            self._print_message("ERROR", str(e))
            self.logger.error(str(e))
            return False

        backup_path = self.backup_dir / backup_filename

        if name_modified:
            self._print_message(
                "WARNING",
                f"Nombre de backup modificado para evitar conflicto: {backup_filename}",
            )

        target = self._resolve_target()
        if not target:
            self._print_message("ERROR", "No se pudo resolver el objetivo del backup")
            return False

        target_type = "contenedor" if self.environment == Environment.DOCKER else "pod"
        target_check = ProgressIndicator(
            f"Verificando {target_type} '{target}'", self.config.use_colors
        )
        backup_progress = ProgressIndicator(
            f"Creando backup '{backup_filename}'", self.config.use_colors
        )

        try:
            if self.config.show_progress:
                target_check.start()
                time.sleep(0.5)

            if not self._check_target_availability(target):
                if self.config.show_progress:
                    target_check.complete(False)
                error_msg = f"{target_type.capitalize()} '{target}' no encontrado o no está ejecutándose"
                self._print_message("ERROR", error_msg)
                self.logger.error(error_msg)
                return False

            if self.config.show_progress:
                target_check.complete(True)

            self.logger.info(f"Iniciando el backup: {backup_filename}")

            cmd = [
                "pg_dump",
                "-U",
                self.db_config["user"],
                "-d",
                self.db_config["database"],
                "--clean",
                "--create",
            ]

            if self.config.show_progress:
                backup_progress.start()

            env = os.environ.copy()
            env["PGPASSWORD"] = self.db_config["password"]

            if self.environment == Environment.DOCKER:
                result = self.handler.execute_command(target, cmd)
            elif self.environment == Environment.KUBERNETES:
                container = self._get_postgres_container_name(target)

                env_vars = [f"PGPASSWORD={self.db_config['password']}"]
                full_cmd = [
                    "sh",
                    "-c",
                    f"export {' '.join(env_vars)} && {' '.join(cmd)}",
                ]
                result = self.handler.execute_command(target, full_cmd, container)

            if self.config.show_progress:
                backup_progress.simulate_work()

            if result.returncode == 0:

                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(result.stdout)

                file_size = backup_path.stat().st_size
                self.logger.info(
                    f"Backup completado exitosamente: {backup_filename} ({file_size} bytes)"
                )

                if self.config.show_progress:
                    backup_progress.complete(True)
                    self._print_message(
                        "INFO", f"Tamaño del backup: {format_file_size(file_size)}"
                    )
                    self._print_message("INFO", f"Ubicación: {backup_path.absolute()}")

                return True
            else:
                self.logger.error(f"Error en pg_dump: {result.stderr}")
                if self.config.show_progress:
                    backup_progress.complete(False)
                self._print_message("ERROR", f"pg_dump falló: {result.stderr.strip()}")

                if backup_path.exists():
                    backup_path.unlink()
                return False

        except Exception as e:
            self.logger.error(f"Error inesperado durante el backup: {e}")
            if self.config.show_progress:
                backup_progress.complete(False)
            self._print_message("ERROR", f"Error inesperado: {e}")

            if backup_path.exists():
                backup_path.unlink()
            return False

    def restore_database(self, backup_path: Path = None) -> bool:
        """
        Restaura la base de datos desde un archivo de backup
        """
        try:
            if backup_path is None:
                backup_path = self.select_backup_interactive()

            if not self.validate_backup_integrity(backup_path):
                return False

            target = self._resolve_target()
            if not target:
                self._print_message(
                    "ERROR", "No se pudo resolver el objetivo de la restauración"
                )
                return False

            if not self.confirm_restore_operation(backup_path, target):
                return False

            target_type = (
                "contenedor" if self.environment == Environment.DOCKER else "pod"
            )
            target_check = ProgressIndicator(
                f"Verificando {target_type} '{target}'", self.config.use_colors
            )
            restore_progress = ProgressIndicator(
                f"Restaurando desde '{backup_path.name}'", self.config.use_colors
            )

            if self.config.show_progress:
                target_check.start()
                time.sleep(0.5)

            if not self._check_target_availability(target):
                if self.config.show_progress:
                    target_check.complete(False)
                error_msg = f"{target_type.capitalize()} '{target}' no encontrado o no está ejecutándose"
                self._print_message("ERROR", error_msg)
                self.logger.error(error_msg)
                return False

            if self.config.show_progress:
                target_check.complete(True)

            self.logger.info(f"Iniciando restauración desde: {backup_path.name}")

            cmd = [
                "psql",
                "-U",
                self.db_config["user"],
                "-d",
                self.db_config["database"],
            ]

            if self.config.show_progress:
                restore_progress.start()

            with open(backup_path, "r", encoding="utf-8") as f:
                backup_content = f.read()

            if self.environment == Environment.DOCKER:
                result = self.handler.execute_command(
                    target, cmd, stdin_data=backup_content
                )
            elif self.environment == Environment.KUBERNETES:
                container = self._get_postgres_container_name(target)
                # Para Kubernetes, configurar entorno y ejecutar
                env_vars = [f"PGPASSWORD={self.db_config['password']}"]
                full_cmd = [
                    "sh",
                    "-c",
                    f"export {' '.join(env_vars)} && {' '.join(cmd)}",
                ]
                result = self.handler.execute_command(
                    target, full_cmd, container, stdin_data=backup_content
                )

            if self.config.show_progress:
                restore_progress.simulate_work()

            if result.returncode == 0:
                self.logger.info(
                    f"Restauración completada exitosamente desde: {backup_path.name}"
                )

                if self.config.show_progress:
                    restore_progress.complete(True)
                    self._print_message(
                        "INFO", f"Base de datos restaurada exitosamente"
                    )
                    self._print_message("INFO", f"Backup utilizado: {backup_path.name}")

                return True
            else:
                self.logger.error(f"Error en restauración: {result.stderr}")
                if self.config.show_progress:
                    restore_progress.complete(False)
                self._print_message(
                    "ERROR", f"Falló la restauración: {result.stderr.strip()}"
                )
                return False

        except FileNotFoundError:
            error_msg = "Error: Herramientas de contenedor no encontradas"
            self.logger.error(error_msg)
            if self.config.show_progress:
                restore_progress.complete(False)
            self._print_message(
                "ERROR", "Herramientas de contenedor no están disponibles"
            )
            return False

        except KeyboardInterrupt:
            self._print_message("INFO", "Restauración cancelada por el usuario")
            return False

        except Exception as e:
            error_msg = f"Error inesperado durante la restauración: {str(e)}"
            self.logger.error(error_msg)
            self._print_message("ERROR", error_msg)
            return False


def display_backup_list(orchestrator: UnifiedBackupOrchestrator, use_colors: bool):
    """
    Muestra la lista de backups disponibles
    """
    backups = orchestrator.list_backups()
    if not backups:
        if use_colors:
            print(f"{Colors.YELLOW}No se encontraron archivos de backup{Colors.RESET}")
        else:
            print("No se encontraron archivos de backup")
        return 0

    if use_colors:
        print(
            f"{Colors.CYAN}{Colors.BOLD}Archivos de backup en {orchestrator.backup_dir}:{Colors.RESET}"
        )
        print(f"{Colors.CYAN}{'-' * 60}{Colors.RESET}")
    else:
        print(f"Archivos de backup en {orchestrator.backup_dir}:")
        print("-" * 60)

    for backup in backups:
        size_str = format_file_size(backup["size"])
        if use_colors:
            print(
                f"{Colors.WHITE}{backup['name']:<30}{Colors.RESET} "
                f"{Colors.BRIGHT_BLUE}{size_str:>10}{Colors.RESET} "
                f"{Colors.MAGENTA}{backup['modified']}{Colors.RESET}"
            )
        else:
            print(f"{backup['name']:<30} {size_str:>10} {backup['modified']}")
    return 0


def display_header(orchestrator: UnifiedBackupOrchestrator, use_colors: bool):
    """
    Muestra el encabezado de la aplicación
    """
    env_info = orchestrator.env_detector.get_environment_info()

    if use_colors:
        print(
            f"{Colors.CYAN}{Colors.BOLD}Orquestador de Backup PostgreSQL Unificado{Colors.RESET}"
        )
        print(
            f"{Colors.WHITE}Entorno: {Colors.BRIGHT_YELLOW}{env_info['environment'].upper()}{Colors.RESET}"
        )

        if orchestrator.environment == Environment.KUBERNETES:
            print(
                f"{Colors.WHITE}Namespace: {Colors.BRIGHT_YELLOW}{orchestrator.config.namespace}{Colors.RESET}"
            )

        print(
            f"{Colors.WHITE}Directorio de backup: {Colors.BRIGHT_YELLOW}{orchestrator.backup_dir}{Colors.RESET}"
        )
        print(f"{Colors.CYAN}{'-' * 50}{Colors.RESET}")
    else:
        print("Orquestador de Backup PostgreSQL Unificado")
        print(f"Entorno: {env_info['environment'].upper()}")

        if orchestrator.environment == Environment.KUBERNETES:
            print(f"Namespace: {orchestrator.config.namespace}")

        print(f"Directorio de backup: {orchestrator.backup_dir}")
        print("-" * 50)


def main():
    """
    Función principal con interfaz de línea de comandos unificada
    """
    parser = create_cli_parser()
    args = parser.parse_args()

    try:
        config = CLIConfig(args)
    except ValueError as e:
        print(f"Error en argumentos: {e}")
        return 1

    use_colors = should_use_colors(config.no_color)
    if not use_colors:
        Colors.disable()

    if config.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        orchestrator = UnifiedBackupOrchestrator(config)

        if config.list:
            return display_backup_list(orchestrator, use_colors)

        if config.restore:
            if config.show_progress:
                display_header(orchestrator, use_colors)

            restore_path = None
            if config.restore_file:
                restore_path = Path(config.restore_file)
                if not restore_path.exists():
                    print_colored_message(
                        "ERROR",
                        f"Archivo de backup no encontrado: {config.restore_file}",
                        use_colors,
                    )
                    return 1

            success = orchestrator.restore_database(restore_path)

            if success:
                if config.show_progress:
                    print_colored_message(
                        "SUCCESS", "Restauración completada exitosamente", use_colors
                    )
                return 0
            else:
                if config.show_progress:
                    print_colored_message(
                        "FAILED", "La operación de restauración falló", use_colors
                    )
                return 1

        if config.show_progress:
            display_header(orchestrator, use_colors)

        success = orchestrator.create_backup(
            custom_name=config.name, force_overwrite=config.force
        )

        if success:
            if config.show_progress:
                print_colored_message(
                    "SUCCESS", "Backup completado exitosamente", use_colors
                )
            return 0
        else:
            if config.show_progress:
                print_colored_message(
                    "FAILED", "La operación de backup falló", use_colors
                )
            return 1

    except KeyboardInterrupt:
        print_colored_message(
            "CANCELLED", "Operación cancelada por el usuario", use_colors
        )
        return 1
    except Exception as e:
        print_colored_message("ERROR", f"Error inesperado: {e}", use_colors)
        return 1


if __name__ == "__main__":
    sys.exit(main())
