"""
Sistema de notificaciones para backups automáticos refactorizado
Aplicando SRP y Factory Pattern
"""

from typing import Dict, Optional, List

from .backup_logger import BackupLogger
from .notification_factory import NotificationFactory
from .notifiers import INotifier
from ..utils.colors import print_colored_message


class NotificationManager:
    """
    Orquestador principal de notificaciones
    Responsabilidad única: coordinar logging y notificadores
    """

    def __init__(self, backup_dir: str):
        self.backup_logger = BackupLogger(backup_dir)
        self.notifiers: List[INotifier] = []

    def notify_backup_status(
        self,
        success: bool,
        backup_name: str,
        environment: str,
        target: str,
        email: str = None,
        slack_token: str = None,
        slack_channel: str = None,
        details: str = None,
    ) -> bool:
        """
        Notifica el estado de un backup automático usando el patrón refactorizado
        """
        try:
            # 1. Logging (siempre se hace)
            self.backup_logger.log_backup_status(
                success, backup_name, environment, target, details
            )
            self.backup_logger.update_status_file(
                success, backup_name, environment, target, details
            )

            # 2. Crear configuración para notificadores
            config = {
                "email": email,
                "slack_token": slack_token,
                "slack_channel": slack_channel,
            }

            # 3. Crear notificadores basado en configuración
            notifiers = NotificationFactory.create_notifiers_from_config(config)

            # 4. Enviar notificaciones
            all_results = []
            for notifier in notifiers:
                try:
                    result = notifier.send_notification(
                        success,
                        backup_name,
                        environment,
                        target,
                        details,
                        email=email,
                        slack_token=slack_token,
                        slack_channel=slack_channel,
                    )
                    all_results.append(result)
                except Exception as e:
                    print_colored_message(
                        "ERROR", f"Error con notificador {type(notifier).__name__}: {e}"
                    )
                    all_results.append(False)

            # Retornar True si al menos un notificador funcionó, o si no hay notificadores
            return len(all_results) == 0 or any(all_results)

        except Exception as e:
            print_colored_message("ERROR", f"Error general en notificación: {e}")
            return False

    def get_last_backup_status(self) -> Optional[Dict]:
        """
        Obtiene el estado del último backup realizado
        Delega al BackupLogger
        """
        return self.backup_logger.get_last_backup_status()

    def get_backup_history(self, lines: int = 50) -> list:
        """
        Obtiene el historial de backups del archivo de log
        Delega al BackupLogger
        """
        return self.backup_logger.get_backup_history(lines)

    def test_notification_system(
        self,
        email: str = None,
        slack_token: str = None,
        slack_channel: str = None,
        environment: str = "docker",
    ) -> bool:
        """
        Prueba el sistema de notificaciones usando la arquitectura refactorizada
        """
        print_colored_message(
            "INFO",
            f"Probando sistema de notificaciones en entorno {environment.upper()}...",
        )

        # Determinar target según entorno
        test_target = (
            "test_container" if environment.lower() == "docker" else "test_postgres_pod"
        )
        test_log = f"Prueba del sistema de notificaciones en {environment.upper()}"

        # Usar el método refactorizado
        success = self.notify_backup_status(
            success=True,
            backup_name="test_backup",
            environment=environment,
            target=test_target,
            email=email,
            slack_token=slack_token,
            slack_channel=slack_channel,
            details=test_log,
        )

        if not email and not (slack_token and slack_channel):
            print_colored_message(
                "SUCCESS", "Sistema de notificaciones funcionando (solo logging)"
            )
        elif success:
            print_colored_message(
                "SUCCESS", "Todas las notificaciones enviadas exitosamente"
            )
        else:
            print_colored_message("WARNING", "Algunas notificaciones fallaron")

        return success
