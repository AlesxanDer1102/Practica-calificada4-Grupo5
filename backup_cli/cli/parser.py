"""
Parser de argumentos de línea de comandos para el orquestador de backup
"""

import argparse


def create_cli_parser():
    """
    Crea el parser de argumentos de línea de comandos
    """
    parser = argparse.ArgumentParser(
        description='Orquestador de Backup de PostgreSQL para contenedores Docker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  %(prog)s                           # Crear backup con timestamp
  %(prog)s --name mi_backup          # Crear backup con nombre personalizado
  %(prog)s --container mi_db         # Backup desde contenedor diferente
  %(prog)s --dir /ruta/a/backups     # Usar directorio diferente
  %(prog)s --quiet                   # Ejecutar sin indicadores de progreso
  %(prog)s --list                    # Listar backups existentes
  %(prog)s --name test --force       # Sobrescribir backup existente
  %(prog)s --no-color                # Deshabilitar salida coloreada
        """
    )
    
    parser.add_argument(
        '--name', '-n',
        type=str,
        help='Nombre personalizado para el archivo de backup (sin extensión .sql)'
    )
    
    parser.add_argument(
        '--container', '-c',
        type=str,
        default='pc_db',
        help='Nombre del contenedor Docker (predeterminado: pc_db)'
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
        '--no-color',
        action='store_true',
        help='Deshabilitar salida coloreada'
    )
    
    return parser


class CLIConfig:
    """
    Configuración derivada de los argumentos de línea de comandos
    """
    
    def __init__(self, args):
        self.name = args.name
        self.container = args.container
        self.backup_dir = args.dir
        self.verbose = args.verbose
        self.quiet = args.quiet
        self.force = args.force
        self.list = args.list
        self.no_color = args.no_color
        
        # Configuraciones derivadas
        self.show_progress = not args.quiet
        self.use_colors = not args.no_color
        
    def __repr__(self):
        return f"CLIConfig(container={self.container}, backup_dir={self.backup_dir}, quiet={self.quiet})" 