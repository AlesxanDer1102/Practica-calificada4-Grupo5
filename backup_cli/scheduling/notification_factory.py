"""
Factory Pattern para notificadores
Responsabilidad única: crear instancias de notificadores
"""

from enum import Enum
from typing import List, Dict, Any

from .notifiers import INotifier, EmailNotifier, SlackNotifier
from ..utils.colors import print_colored_message


class NotifierType(Enum):
    """
    Tipos de notificadores disponibles
    """
    EMAIL = "email"
    SLACK = "slack"


class NotificationFactory:
    """
    Factory para crear instancias de notificadores
    Aplica Factory Pattern
    """

    @staticmethod
    def create_notifier(notifier_type: NotifierType) -> INotifier:
        """
        Crea una instancia del notificador especificado
        """
        if notifier_type == NotifierType.EMAIL:
            return EmailNotifier()
        elif notifier_type == NotifierType.SLACK:
            return SlackNotifier()
        else:
            raise ValueError(f"Tipo de notificador no soportado: {notifier_type}")

    @staticmethod
    def create_notifiers_from_config(config: Dict[str, Any]) -> List[INotifier]:
        """
        Crea notificadores basado en configuración
        """
        notifiers = []

        # Agregar EmailNotifier si email está configurado
        if config.get('email'):
            try:
                email_notifier = NotificationFactory.create_notifier(NotifierType.EMAIL)
                notifiers.append(email_notifier)
                print_colored_message("INFO", "EmailNotifier configurado")
            except Exception as e:
                print_colored_message("ERROR", f"Error creando EmailNotifier: {e}")

        # Agregar SlackNotifier si Slack está configurado
        if config.get('slack_token') and config.get('slack_channel'):
            try:
                slack_notifier = NotificationFactory.create_notifier(NotifierType.SLACK)
                notifiers.append(slack_notifier)
                print_colored_message("INFO", "SlackNotifier configurado")
            except Exception as e:
                print_colored_message("ERROR", f"Error creando SlackNotifier: {e}")

        if not notifiers:
            print_colored_message("WARNING", "Ningún notificador configurado")

        return notifiers

    @staticmethod
    def get_available_notifiers() -> List[str]:
        """
        Retorna lista de notificadores disponibles
        """
        return [notifier_type.value for notifier_type in NotifierType] 