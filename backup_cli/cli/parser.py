import argparse
from typing import Dict, Optional

def create_cli_parser():
    """
    Crea el parser de argumentos de línea de comandos con soporte para K8s
    """
    parser = argparse.ArgumentParser(
        description='Orquestador de Backup de PostgreSQL para Docker y Kubernetes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

Docker:
  %(prog)s                                    # Crear backup con timestamp
  %(prog)s --name mi_backup                   # Crear backup con nombre personalizado
  %(prog)s --container mi_db                  # Backup desde contenedor diferente
  %(prog)s --restore --container mi_db        # Restaurar desde contenedor

Kubernetes:
  %(prog)s --pod postgres-0                   # Backup desde pod específico
  %(prog)s --namespace production             # Usar namespace diferente
  %(prog)s --labels app=postgres              # Seleccionar pod por labels
  %(prog)s --restore --pod postgres-0         # Restaurar en pod específico
  %(prog)s --container postgres --pod pg-0    # Especificar contenedor en pod

Opciones generales:
  %(prog)s --dir /ruta/a/backups              # Usar directorio diferente
  %(prog)s --quiet                            # Ejecutar sin indicadores de progreso
  %(prog)s --list                             # Listar backups existentes
  %(prog)s --force                            # Sobrescribir backup existente
  %(prog)s --no-color                         # Deshabilitar salida coloreada
  %(prog)s --auto-detect                      # Detectar entorno automáticamente
        """
    )

    parser.add_argument(
        '--name', '-n',
        type=str,
        help='Nombre personalizado para el archivo de backup (sin extensión .sql)'
    )

    parser.add_argument(
        '--dir', '-d',
        type=str,
        default='backups',
        help='Ruta del directorio de backups (predeterminado: backups)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Habilitar salida detallada'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Deshabilitar indicadores de progreso'
    )

    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Sobrescribir archivos de backup existentes'
    )

    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='Listar archivos de backup existentes y salir'
    )

    parser.add_argument(
        '--restore', '-r',
        action='store_true',
        help='Restaurar base de datos desde un backup seleccionado'
    )

    parser.add_argument(
        '--restore-file',
        type=str,
        help='Ruta específica del archivo de backup a restaurar (omite selección interactiva)'
    )

    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Deshabilitar salida coloreada'
    )

    docker_group = parser.add_argument_group('Opciones de Docker')
    docker_group.add_argument(
        '--container', '-c',
        type=str,
        help='Nombre del contenedor Docker (para entorno Docker)'
    )

    k8s_group = parser.add_argument_group('Opciones de Kubernetes')
    k8s_group.add_argument(
        '--pod', '-p',
        type=str,
        help='Nombre del pod (para entorno Kubernetes)'
    )

    k8s_group.add_argument(
        '--namespace', '-ns',
        type=str,
        default='default',
        help='Namespace de Kubernetes (predeterminado: default)'
    )

    k8s_group.add_argument(
        '--labels',
        type=str,
        help='Selector de labels para encontrar pods (formato: key1=value1,key2=value2)'
    )

    k8s_group.add_argument(
        '--k8s-container',
        type=str,
        help='Nombre del contenedor específico dentro del pod'
    )

    env_group = parser.add_argument_group('Detección de entorno')
    env_group.add_argument(
        '--auto-detect',
        action='store_true',
        help='Detectar automáticamente el entorno (Docker o Kubernetes)'
    )

    env_group.add_argument(
        '--force-docker',
        action='store_true',
        help='Forzar uso de Docker (ignora detección automática)'
    )

    env_group.add_argument(
        '--force-kubernetes',
        action='store_true',
        help='Forzar uso de Kubernetes (ignora detección automática)'
    )

    return parser

def parse_labels(labels_str: str) -> Dict[str, str]:

    if not labels_str:
        return {}

    labels = {}
    for label_pair in labels_str.split(','):
        if '=' in label_pair:
            key, value = label_pair.split('=', 1)
            labels[key.strip()] = value.strip()

    return labels

class CLIConfig:

    def __init__(self, args):
        # Argumentos generales
        self.name = args.name
        self.backup_dir = args.dir
        self.verbose = args.verbose
        self.quiet = args.quiet
        self.force = args.force
        self.list = args.list
        self.restore = args.restore
        self.restore_file = args.restore_file
        self.no_color = args.no_color

        # Argumentos de Docker
        self.container = args.container

        # Argumentos de Kubernetes
        self.pod = args.pod
        self.namespace = args.namespace
        self.labels = parse_labels(args.labels) if args.labels else {}
        self.k8s_container = args.k8s_container

        # Opciones de entorno
        self.auto_detect = args.auto_detect
        self.force_docker = args.force_docker
        self.force_kubernetes = args.force_kubernetes

        # Configuraciones derivadas
        self.show_progress = not args.quiet
        self.use_colors = not args.no_color

        # Validación de argumentos
        self._validate_arguments()

    def _validate_arguments(self):

        # No se pueden forzar ambos entornos
        if self.force_docker and self.force_kubernetes:
            raise ValueError("No se pueden especificar --force-docker y --force-kubernetes al mismo tiempo")

        # Si se especifica un pod, debería ser Kubernetes
        if self.pod and self.force_docker:
            raise ValueError("--pod no es compatible con --force-docker")

        # Si se especifica un contenedor sin pod, debería ser Docker
        if self.container and not self.pod and self.force_kubernetes:
            raise ValueError("--container sin --pod no es compatible con --force-kubernetes")

    def get_preferred_environment(self) -> Optional[str]:

        if self.force_docker:
            return "docker"
        elif self.force_kubernetes:
            return "kubernetes"
        elif self.pod or self.labels or self.k8s_container:
            return "kubernetes"
        elif self.container:
            return "docker"
        else:
            return None  # Auto-detectar

    def __repr__(self):
        env_info = []
        if self.container:
            env_info.append(f"container={self.container}")
        if self.pod:
            env_info.append(f"pod={self.pod}")
        if self.namespace != "default":
            env_info.append(f"namespace={self.namespace}")

        env_str = ", ".join(env_info) if env_info else "auto-detect"

        return f"CLIConfig({env_str}, backup_dir={self.backup_dir}, quiet={self.quiet})"