#!/usr/bin/env python3

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv no disponible, usar variables de entorno normales

from backup_cli.backup_strategy import BackupStrategy
from backup_cli.cli.parser import CLIConfig, create_cli_parser
from backup_cli.environment.detector import Environment, EnvironmentDetector
from backup_cli.handlers.docker_handler import DockerHandler
from backup_cli.handlers.kubernetes_handler import KubernetesHandler
from backup_cli.scheduling import CronManager, K8sCronJobManager, NotificationManager
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

        # Configuración de base de datos específica del proyecto
        self.db_config = {
            "user": "postgres",
            "password": "12345",  # Coincide con postgres-secret
            "database": "pc_db",  # Coincide con POSTGRES_DB del StatefulSet
        }

        # Detectar entorno
        self.env_detector = EnvironmentDetector()
        self.environment = self._determine_environment()

        # Inicializar handler apropiado
        self._initialize_handler()

        # Inicializar gestor de estrategias de backup
        self.backup_strategy = BackupStrategy(str(self.backup_dir))

        # Configurar políticas de retención si se especificaron
        retention_updates = {}
        if config.retention_daily:
            retention_updates["daily"] = config.retention_daily
        if config.retention_weekly:
            retention_updates["weekly"] = config.retention_weekly
        if config.retention_monthly:
            retention_updates["monthly"] = config.retention_monthly
        if config.retention_full:
            retention_updates["full"] = config.retention_full

        if retention_updates:
            self.backup_strategy.configure_retention_policy(**retention_updates)

        # Inicializar gestores de programación
        self._initialize_scheduling_managers()

        # Configurar logging
        self.setup_logging()

    def _initialize_scheduling_managers(self):
        """
        Inicializa los gestores de programación automática
        """
        # Gestor de notificaciones
        self.notification_manager = NotificationManager(str(self.backup_dir))
        
        # Gestor de cron local (Docker)
        script_path = Path(__file__).absolute()
        self.cron_manager = CronManager(str(script_path))
        
        # Gestor de CronJobs Kubernetes
        self.k8s_cronjob_manager = K8sCronJobManager(namespace=self.config.namespace)

    def _determine_environment(self) -> Environment:
        """
        Determina el entorno a usar basado en configuración y detección
        """
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
            # Auto-detectar
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

        # Buscar automáticamente o interactivamente
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

        # Buscar usando labels o interactivamente
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
        Crea un backup de la base de datos con estrategia automática
        """
        # Determinar tipo de backup
        backup_type = "full"
        if self.config.backup_type == "auto":
            backup_type = self.backup_strategy.determine_backup_type(
                self.config.force_full
            )
        elif self.config.backup_type in ["full", "incremental"]:
            backup_type = self.config.backup_type
        elif self.config.force_full:
            backup_type = "full"

        # Mostrar recomendación si es automático
        if self.config.backup_type == "auto" and self.config.show_progress:
            recommendation = self.backup_strategy.get_next_backup_recommendation()
            self._print_message(
                "INFO", f"Tipo de backup recomendado: {recommendation['type']}"
            )
            self._print_message("INFO", f"Razón: {recommendation['reason']}")

        start_time = time.time()

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

        # Añadir sufijo del tipo de backup
        if not custom_name:
            base_name = backup_filename.replace(".sql", "")
            backup_filename = f"{base_name}_{backup_type}.sql"

        backup_path = self.backup_dir / backup_filename

        # Mostrar advertencia de modificación de nombre
        if name_modified:
            self._print_message(
                "WARNING",
                f"Nombre de backup modificado para evitar conflicto: {backup_filename}",
            )

        # Resolver objetivo
        target = self._resolve_target()
        if not target:
            self._print_message("ERROR", "No se pudo resolver el objetivo del backup")
            return False

        # Indicadores de progreso
        target_type = "contenedor" if self.environment == Environment.DOCKER else "pod"
        target_check = ProgressIndicator(
            f"Verificando {target_type} '{target}'", self.config.use_colors
        )
        backup_progress = ProgressIndicator(
            f"Creando backup '{backup_filename}'", self.config.use_colors
        )

        try:
            # Verificar disponibilidad del objetivo
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

            self.logger.info(f"Iniciando backup {backup_type}: {backup_filename}")

            # Preparar comando pg_dump con estrategia específica
            cmd = [
                "pg_dump",
                "-U",
                self.db_config["user"],
                "-d",
                self.db_config["database"],
            ]
            cmd.extend(self.backup_strategy.get_backup_command_args(backup_type))

            # Iniciar progreso de backup
            if self.config.show_progress:
                backup_progress.start()

            # Configurar entorno
            env = os.environ.copy()
            env["PGPASSWORD"] = self.db_config["password"]

            # Ejecutar comando según el entorno
            if self.environment == Environment.DOCKER:
                result = self.handler.execute_command(target, cmd)
            elif self.environment == Environment.KUBERNETES:
                container = self._get_postgres_container_name(target)
                # Para Kubernetes, manejar variables de entorno directamente
                env_vars = [f"PGPASSWORD={self.db_config['password']}"]
                full_cmd = [
                    "sh",
                    "-c",
                    f"export {' '.join(env_vars)} && {' '.join(cmd)}",
                ]
                result = self.handler.execute_command(target, full_cmd, container)

            # Simular progreso
            if self.config.show_progress:
                backup_progress.simulate_work()

            if result.returncode == 0:
                # Escribir el backup al archivo
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(result.stdout)

                file_size = backup_path.stat().st_size
                duration = time.time() - start_time

                # Crear metadatos del backup
                metadata = self.backup_strategy.create_backup_metadata(
                    backup_filename.replace(".sql", ""),
                    backup_type,
                    file_size,
                    duration,
                )

                # Actualizar estado
                self.backup_strategy.update_backup_state(
                    backup_filename.replace(".sql", ""), backup_type, metadata
                )

                self.logger.info(
                    f"Backup {backup_type} completado exitosamente: {backup_filename} ({file_size} bytes)"
                )

                if self.config.show_progress:
                    backup_progress.complete(True)
                    self._print_message(
                        "INFO", f"Tipo de backup: {backup_type.upper()}"
                    )
                    self._print_message(
                        "INFO", f"Tamaño del backup: {format_file_size(file_size)}"
                    )
                    self._print_message("INFO", f"Duración: {duration:.1f} segundos")
                    self._print_message("INFO", f"Ubicación: {backup_path.absolute()}")

                # Enviar notificación si está configurado
                if (hasattr(self.config, 'notification_email') and self.config.notification_email) or \
                   (hasattr(self.config, 'slack_token') and self.config.slack_token and 
                    hasattr(self.config, 'slack_channel') and self.config.slack_channel):
                    self.notification_manager.notify_backup_status(
                        success=True,
                        backup_name=backup_filename,
                        environment=self.environment.value,
                        target=target,
                        email=getattr(self.config, 'notification_email', None),
                        slack_token=getattr(self.config, 'slack_token', None),
                        slack_channel=getattr(self.config, 'slack_channel', None),
                        details=f"Tipo: {backup_type.upper()}, Tamaño: {format_file_size(file_size)}, Duración: {duration:.1f}s"
                    )

                return True
            else:
                self.logger.error(f"Error en pg_dump: {result.stderr}")
                if self.config.show_progress:
                    backup_progress.complete(False)
                self._print_message("ERROR", f"pg_dump falló: {result.stderr.strip()}")

                # Enviar notificación de fallo si está configurado
                if (hasattr(self.config, 'notification_email') and self.config.notification_email) or \
                   (hasattr(self.config, 'slack_token') and self.config.slack_token and 
                    hasattr(self.config, 'slack_channel') and self.config.slack_channel):
                    self.notification_manager.notify_backup_status(
                        success=False,
                        backup_name=backup_filename,
                        environment=self.environment.value,
                        target=target,
                        email=getattr(self.config, 'notification_email', None),
                        slack_token=getattr(self.config, 'slack_token', None),
                        slack_channel=getattr(self.config, 'slack_channel', None),
                        details=f"Error en pg_dump: {result.stderr.strip()}"
                    )

                if backup_path.exists():
                    backup_path.unlink()
                return False

        except Exception as e:
            self.logger.error(f"Error inesperado durante el backup: {e}")
            if self.config.show_progress:
                backup_progress.complete(False)
            self._print_message("ERROR", f"Error inesperado: {e}")

            # Enviar notificación de error si está configurado
            if (hasattr(self.config, 'notification_email') and self.config.notification_email) or \
               (hasattr(self.config, 'slack_token') and self.config.slack_token and 
                hasattr(self.config, 'slack_channel') and self.config.slack_channel):
                self.notification_manager.notify_backup_status(
                    success=False,
                    backup_name=backup_filename if 'backup_filename' in locals() else "backup_unknown",
                    environment=self.environment.value,
                    target=target if 'target' in locals() else "unknown",
                    email=getattr(self.config, 'notification_email', None),
                    slack_token=getattr(self.config, 'slack_token', None),
                    slack_channel=getattr(self.config, 'slack_channel', None),
                    details=f"Error inesperado: {str(e)}"
                )

            if backup_path.exists():
                backup_path.unlink()
            return False

    def restore_database(self, backup_path: Path = None) -> bool:
        """
        Restaura la base de datos desde un archivo de backup
        """
        try:
            # Si no se proporciona un backup, seleccionar interactivamente
            if backup_path is None:
                backup_path = self.select_backup_interactive()

            # Validar integridad del backup
            if not self.validate_backup_integrity(backup_path):
                return False

            # Resolver objetivo
            target = self._resolve_target()
            if not target:
                self._print_message(
                    "ERROR", "No se pudo resolver el objetivo de la restauración"
                )
                return False

            # Solicitar confirmación
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

            # Preparar comando psql
            cmd = [
                "psql",
                "-U",
                self.db_config["user"],
                "-d",
                self.db_config["database"],
            ]

            # Iniciar progreso de restauración
            if self.config.show_progress:
                restore_progress.start()

            with open(backup_path, "r", encoding="utf-8") as f:
                backup_content = f.read()

            # Ejecutar restauración según el entorno
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

            # Simular progreso durante la restauración
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

    def schedule_automatic_backup(
        self,
        schedule: str,
        backup_name: str = None,
        notification_email: str = None,
    ) -> bool:
        """
        Programa un backup automático
        """
        try:
            target = self._resolve_target()
            if not target:
                self._print_message("ERROR", "No se pudo resolver el objetivo del backup")
                return False

            if self.environment == Environment.DOCKER:
                return self.cron_manager.add_scheduled_backup(
                    schedule=schedule,
                    container=target,
                    backup_name=backup_name,
                    notification_email=notification_email,
                )
            elif self.environment == Environment.KUBERNETES:
                return self.k8s_cronjob_manager.create_scheduled_backup(
                    name=backup_name or "scheduled",
                    schedule=schedule,
                    notification_email=notification_email,
                )

            return False

        except Exception as e:
            self._print_message("ERROR", f"Error programando backup: {e}")
            return False

    def list_scheduled_backups(self) -> bool:
        """
        Lista los backups programados activos
        """
        try:
            self._print_message("INFO", "Backups programados:")
            print()

            if self.environment == Environment.DOCKER:
                schedules = self.cron_manager.list_scheduled_backups()
                if not schedules:
                    print("  No hay backups programados en cron")
                else:
                    for i, schedule in enumerate(schedules, 1):
                        print(f"  {i}. {schedule}")

            elif self.environment == Environment.KUBERNETES:
                cronjobs = self.k8s_cronjob_manager.list_scheduled_backups()
                if not cronjobs:
                    print("  No hay CronJobs de backup activos")
                else:
                    for job in cronjobs:
                        status = "Activo" if job["active"] > 0 else "Inactivo"
                        print(f"  • {job['name']}: {job['schedule']} ({status})")
                        if job["last_schedule"]:
                            print(f"    Última ejecución: {job['last_schedule']}")

            return True

        except Exception as e:
            self._print_message("ERROR", f"Error listando programaciones: {e}")
            return False

    def remove_scheduled_backup(self, name: str) -> bool:
        """
        Elimina un backup programado
        """
        try:
            if self.environment == Environment.DOCKER:
                return self.cron_manager.remove_scheduled_backup(name)
            elif self.environment == Environment.KUBERNETES:
                return self.k8s_cronjob_manager.delete_scheduled_backup(name)

            return False

        except Exception as e:
            self._print_message("ERROR", f"Error eliminando programación: {e}")
            return False

    def test_notification_system(self) -> bool:
        """
        Prueba el sistema de notificaciones
        """
        email = getattr(self.config, 'notification_email', None)
        slack_token = getattr(self.config, 'slack_token', None)
        slack_channel = getattr(self.config, 'slack_channel', None)
        environment = self.environment.value  # docker o kubernetes
        return self.notification_manager.test_notification_system(email, slack_token, slack_channel, environment)


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

    # Encabezado
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


def handle_backup_strategy_commands(
    config: CLIConfig, orchestrator: UnifiedBackupOrchestrator, use_colors: bool
) -> int:
    """
    Maneja comandos relacionados con estrategias de backup y retención
    """
    backup_strategy = orchestrator.backup_strategy

    # Mostrar resumen de backups
    if config.backup_summary:
        print_colored_message(
            "INFO", "Resumen de backups y políticas de retención:", use_colors
        )

        # Obtener resumen de retención
        summary = backup_strategy.get_retention_summary()

        print(f"\n📊 POLÍTICAS DE RETENCIÓN")
        print("-" * 40)
        for category, count in summary["policies"].items():
            current = summary["current_counts"].get(category, 0)
            print(f"  {category.capitalize()}: {current}/{count} backups")

        print(f"\n📈 ESTADÍSTICAS")
        print("-" * 40)
        print(f"  Total de backups: {summary['total_backups']}")
        print(f"  Espacio utilizado: {summary['total_size_mb']} MB")

        # Mostrar backups por tipo
        backups_by_type = backup_strategy.list_backups_by_type()

        print(f"\n📋 BACKUPS POR TIPO")
        print("-" * 40)
        for backup_type, backups in backups_by_type.items():
            if backups:
                print(f"\n{backup_type.upper()} ({len(backups)}):")
                for backup in backups[:3]:  # Mostrar últimos 3
                    timestamp = datetime.fromisoformat(backup["timestamp"])
                    size_mb = backup.get("file_size", 0) / (1024 * 1024)
                    print(
                        f"  • {backup['name']} - {timestamp.strftime('%Y-%m-%d %H:%M')} ({size_mb:.1f} MB)"
                    )
                if len(backups) > 3:
                    print(f"  ... y {len(backups) - 3} más")

        # Mostrar recomendación para próximo backup
        recommendation = backup_strategy.get_next_backup_recommendation()
        print(f"\n💡 PRÓXIMO BACKUP RECOMENDADO")
        print("-" * 40)
        print(f"  Tipo: {recommendation['type'].upper()}")
        print(f"  Razón: {recommendation['reason']}")

        return 0

    # Aplicar políticas de retención
    if config.apply_retention or config.retention_dry_run:
        dry_run = config.retention_dry_run
        action = "Simulando" if dry_run else "Aplicando"

        print_colored_message("INFO", f"{action} políticas de retención...", use_colors)

        deleted_counts = backup_strategy.apply_retention_policy(dry_run=dry_run)

        total_deleted = sum(deleted_counts.values())

        if total_deleted == 0:
            print_colored_message(
                "INFO",
                "No hay backups que eliminar según las políticas actuales",
                use_colors,
            )
        else:
            print(f"\n🗑️  BACKUPS {'A ELIMINAR' if dry_run else 'ELIMINADOS'}")
            print("-" * 40)
            for category, count in deleted_counts.items():
                if count > 0:
                    print(f"  {category.capitalize()}: {count} backups")
            print(f"  Total: {total_deleted} backups")

            if dry_run:
                print_colored_message(
                    "INFO",
                    "Ejecutar sin --retention-dry-run para eliminar realmente",
                    use_colors,
                )
            else:
                print_colored_message(
                    "SUCCESS",
                    f"{total_deleted} backups eliminados exitosamente",
                    use_colors,
                )

        return 0

    return 0


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

    # Determinar si se deben usar colores
    use_colors = should_use_colors(config.no_color)
    if not use_colors:
        Colors.disable()

    # Configurar nivel de logging basado en flag verbose
    if config.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        orchestrator = UnifiedBackupOrchestrator(config)

        # Manejar comandos de estrategias de backup
        if config.backup_summary or config.apply_retention or config.retention_dry_run:
            return handle_backup_strategy_commands(config, orchestrator, use_colors)

        # Manejar comandos de programación automática
        if config.schedule or config.schedule_custom:
            schedule_str = None
            if config.schedule:
                predefined = CronManager.get_predefined_schedules()
                schedule_str = predefined.get(config.schedule)
                if not schedule_str:
                    print_colored_message("ERROR", f"Programación predefinida inválida: {config.schedule}", use_colors)
                    return 1
            elif config.schedule_custom:
                schedule_str = config.schedule_custom

            success = orchestrator.schedule_automatic_backup(
                schedule=schedule_str,
                backup_name=config.schedule_prefix,
                notification_email=config.notification_email
            )
            return 0 if success else 1

        if config.list_schedules:
            return 0 if orchestrator.list_scheduled_backups() else 1

        if config.remove_schedule:
            success = orchestrator.remove_scheduled_backup(config.remove_schedule)
            return 0 if success else 1

        if config.test_notifications:
            success = orchestrator.test_notification_system()
            return 0 if success else 1

        # Manejar comando de lista
        if config.list:
            return display_backup_list(orchestrator, use_colors)

        # Manejar comando de restauración
        if config.restore:
            if config.show_progress:
                display_header(orchestrator, use_colors)

            # Restaurar desde archivo específico o selección interactiva
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

        # Crear backup
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
