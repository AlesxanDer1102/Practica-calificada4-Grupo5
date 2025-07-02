"""
Módulo de programación automática de backups
Soporta cron jobs locales y CronJobs de Kubernetes
Refactorizado aplicando SRP y Factory Pattern
"""

from .cron_manager import CronManager
from .k8s_cronjob import K8sCronJobManager
from .notifications import NotificationManager
from .backup_logger import BackupLogger
from .notifiers import INotifier, EmailNotifier, SlackNotifier
from .notification_factory import NotificationFactory, NotifierType

__all__ = [
    "CronManager", 
    "K8sCronJobManager",
    "NotificationManager",
    "BackupLogger",
    "INotifier", 
    "EmailNotifier", 
    "SlackNotifier",
    "NotificationFactory",
    "NotifierType"
] 