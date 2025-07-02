"""
Módulo de notificadores específicos
Aplicando SRP y patrón Strategy
"""

import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
from email.mime.text import MIMEText
from typing import Any, Dict

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False

from ..utils.colors import print_colored_message


class INotifier(ABC):
    """
    Interface común para todos los notificadores
    """

    @abstractmethod
    def send_notification(
        self,
        success: bool,
        backup_name: str,
        environment: str,
        target: str,
        details: str = None,
        **kwargs,
    ) -> bool:
        """
        Envía una notificación
        """
        pass


class EmailNotifier(INotifier):
    """
    Notificador específico para email vía sendmail
    Responsabilidad única: envío de emails
    """

    def send_notification(
        self,
        success: bool,
        backup_name: str,
        environment: str,
        target: str,
        details: str = None,
        **kwargs,
    ) -> bool:
        """
        Envía notificación por email
        """
        email = kwargs.get("email")
        if not email:
            print_colored_message("ERROR", "Email no proporcionado para EmailNotifier")
            return False

        try:
            status = "ÉXITO" if success else "FALLO"
            subject = f"Backup Automático - {status}: {backup_name}"

            body = self._create_email_body(
                status, backup_name, environment, target, details
            )

            # Crear mensaje
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = "backup-orchestrator@localhost"
            msg["To"] = email

            # Enviar usando sendmail
            return self._send_via_sendmail(msg, email)

        except Exception as e:
            print_colored_message("ERROR", f"Error preparando notificación email: {e}")
            return False

    def _create_email_body(
        self, status: str, backup_name: str, environment: str, target: str, details: str
    ) -> str:
        """
        Crea el cuerpo del email
        """
        return f"""
Estado del Backup Automático

Resultado: {status}
Backup: {backup_name}
Entorno: {environment}
Objetivo: {target}
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{details if details else ''}

Este es un mensaje automático del Orquestador de Backups.
        """.strip()

    def _send_via_sendmail(self, msg: MIMEText, email: str) -> bool:
        """
        Envía email usando sendmail local
        """
        try:
            # Verificar si sendmail está disponible
            result = subprocess.run(
                ["which", "sendmail"], capture_output=True, timeout=5
            )

            if result.returncode != 0:
                print_colored_message(
                    "WARNING", "sendmail no disponible, notificación email omitida"
                )
                return True

            # Enviar usando sendmail
            process = subprocess.Popen(
                ["sendmail", email], stdin=subprocess.PIPE, text=True
            )

            process.communicate(input=msg.as_string())

            if process.returncode == 0:
                print_colored_message("SUCCESS", f"Notificación enviada a {email}")
                return True
            else:
                print_colored_message("ERROR", "Error enviando email")
                return False

        except Exception as e:
            print_colored_message("ERROR", f"Error con sendmail: {e}")
            return False


class SlackNotifier(INotifier):
    """
    Notificador específico para Slack
    Responsabilidad única: envío de mensajes Slack
    """

    def send_notification(
        self,
        success: bool,
        backup_name: str,
        environment: str,
        target: str,
        details: str = None,
        **kwargs,
    ) -> bool:
        """
        Envía notificación vía Slack bot
        """
        slack_token = kwargs.get("slack_token")
        slack_channel = kwargs.get("slack_channel")

        if not slack_token or not slack_channel:
            print_colored_message("ERROR", "Token o canal de Slack no proporcionados")
            return False

        try:
            if not SLACK_AVAILABLE:
                print_colored_message(
                    "WARNING", "slack-sdk no disponible, notificación Slack omitida"
                )
                return True

            # Inicializar cliente Slack
            client = WebClient(token=slack_token)

            # Crear mensaje estructurado
            message = self._create_slack_message(
                slack_channel, success, backup_name, environment, target, details
            )

            # Enviar mensaje
            response = client.chat_postMessage(**message)

            if response["ok"]:
                print_colored_message(
                    "SUCCESS", f"Notificación Slack enviada al canal {slack_channel}"
                )
                return True
            else:
                print_colored_message(
                    "ERROR",
                    f"Error enviando a Slack: {response.get('error', 'Unknown error')}",
                )
                return False

        except SlackApiError as e:
            print_colored_message("ERROR", f"Error Slack API: {e.response['error']}")
            return False
        except Exception as e:
            print_colored_message("ERROR", f"Error inesperado con Slack: {e}")
            return False

    def _create_slack_message(
        self,
        slack_channel: str,
        success: bool,
        backup_name: str,
        environment: str,
        target: str,
        details: str = None,
    ) -> Dict[str, Any]:
        """
        Crea el mensaje estructurado para Slack
        """
        # Preparar mensaje con emojis específicos por entorno
        status = " ÉXITO" if success else " FALLO"
        emoji = "" if success else ""
        color = "good" if success else "danger"

        # Emoji específico del entorno
        env_emoji = "" if environment.lower() == "docker" else "️"
        env_name = f"{env_emoji} {environment.upper()}"

        # Crear mensaje estructurado
        message = {
            "channel": slack_channel,
            "text": f"{emoji} Backup Automático [{env_name}] - {status}",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {"title": "Estado", "value": status, "short": True},
                        {"title": "Backup", "value": backup_name, "short": True},
                        {
                            "title": "Entorno",
                            "value": f"{env_emoji} {environment.upper()}",
                            "short": True,
                        },
                        {"title": "Objetivo", "value": target, "short": True},
                        {
                            "title": "Fecha",
                            "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "short": True,
                        },
                    ],
                    "footer": "Orquestador de Backups",
                    "ts": int(datetime.now().timestamp()),
                }
            ],
        }

        # Agregar detalles si están disponibles
        if details:
            message["attachments"][0]["fields"].append(
                {"title": "Detalles", "value": details, "short": False}
            )

        return message
