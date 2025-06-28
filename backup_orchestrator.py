#!/usr/bin/env python3

import os
import subprocess
import logging
import argparse
import sys
import time
import re
from datetime import datetime
from pathlib import Path

class Colors:
    """
    ANSI color codes for terminal output
    """
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Basic colors
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    
    @classmethod
    def disable(cls):
        """Disable all colors"""
        for attr in dir(cls):
            if not attr.startswith('_') and attr != 'disable':
                setattr(cls, attr, '')

class ProgressIndicator:
    """
    Simple progress indicator for command line operations with color support
    """
    def __init__(self, message: str, use_colors: bool = True):
        self.message = message
        self.active = False
        self.use_colors = use_colors
        
    def start(self):
        """Start showing progress"""
        self.active = True
        if self.use_colors:
            print(f"{Colors.BLUE}[INFO]{Colors.RESET} {self.message}", end="", flush=True)
        else:
            print(f"[INFO] {self.message}", end="", flush=True)
        
    def update(self, status: str = "."):
        """Update progress indicator"""
        if self.active:
            if self.use_colors:
                print(f"{Colors.CYAN}{status}{Colors.RESET}", end="", flush=True)
            else:
                print(status, end="", flush=True)
            
    def complete(self, success: bool = True):
        """Complete progress indication"""
        if self.active:
            if success:
                status = f" {Colors.BRIGHT_GREEN}[OK]{Colors.RESET}" if self.use_colors else " [OK]"
            else:
                status = f" {Colors.BRIGHT_RED}[FAILED]{Colors.RESET}" if self.use_colors else " [FAILED]"
            print(status)
            self.active = False

class BackupOrchestrator:
    """
    Orquestador de backups para PostgreSQL con contenedores Docker
    """

    def __init__(self, container_name: str = "pc_db", backup_dir: str = "backups", 
                 show_progress: bool = True, use_colors: bool = True):
        self.container_name = container_name
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.show_progress = show_progress
        self.use_colors = use_colors
        
        if not use_colors:
            Colors.disable()

        self.db_config = {
            "user": "postgres",
            "password": "12345",
            "database": "pc_db",
        }

        self.setup_logging()

    def setup_logging(self):
        """
        Configura el sistema de logging
        """
        log_file = self.backup_dir / "backup_orchestrator.log"

        # Set up file logging only, console output handled by progress indicator
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)

    def _print_message(self, level: str, message: str):
        """Print colored message based on level"""
        if not self.show_progress:
            return
            
        color_map = {
            'INFO': Colors.BLUE,
            'SUCCESS': Colors.BRIGHT_GREEN,
            'WARNING': Colors.BRIGHT_YELLOW,
            'ERROR': Colors.BRIGHT_RED,
            'FAILED': Colors.BRIGHT_RED,
            'CANCELLED': Colors.YELLOW
        }
        
        if self.use_colors:
            color = color_map.get(level, Colors.WHITE)
            print(f"{color}[{level}]{Colors.RESET} {message}")
        else:
            print(f"[{level}] {message}")

    def _validate_backup_name(self, name: str) -> tuple[bool, str]:
        """
        Valida que el nombre del backup sea válido para el sistema de archivos
        """
        if not name:
            return False, "Backup name cannot be empty"
            
        # Check for invalid characters
        invalid_chars = r'[<>:"/\\|?*]'
        if re.search(invalid_chars, name):
            return False, f"Backup name contains invalid characters: {invalid_chars}"
            
        # Check length
        if len(name) > 200:
            return False, "Backup name too long (max 200 characters)"
            
        # Check for reserved names (Windows compatibility)
        reserved_names = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                         'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 
                         'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
        if name.upper() in reserved_names:
            return False, f"'{name}' is a reserved system name"
            
        return True, "Valid backup name"

    def _resolve_backup_filename(self, custom_name: str = None, force_overwrite: bool = False) -> tuple[str, bool]:
        """
        Resuelve el nombre final del backup, manejando conflictos si es necesario
        """
        if custom_name:
            is_valid, message = self._validate_backup_name(custom_name)
            if not is_valid:
                raise ValueError(f"Invalid backup name: {message}")
                
            backup_filename = f"{custom_name}.sql"
            backup_path = self.backup_dir / backup_filename
            
            # Check if file exists
            if backup_path.exists() and not force_overwrite:
                # Generate alternative name with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"{custom_name}_{timestamp}.sql"
                return backup_filename, True  # True indicates name was modified
            else:
                return backup_filename, False  # False indicates original name was used
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.sql"
            return backup_filename, False

    def _check_docker_container(self) -> bool:
        """
        Verifica si el contenedor Docker está disponible
        """
        try:
            result = subprocess.run(
                ["docker", "inspect", self.container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def list_backups(self) -> list[dict]:
        """
        Lista todos los backups disponibles en el directorio
        """
        backups = []
        for backup_file in self.backup_dir.glob("*.sql"):
            stat = backup_file.stat()
            backups.append({
                'name': backup_file.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'path': backup_file
            })
        return sorted(backups, key=lambda x: x['modified'], reverse=True)

    def create_backup(self, custom_name: str = None, force_overwrite: bool = False) -> bool:
        """
        Crea un backup de la base de datos usando docker exec y pg_dump
        """
        try:
            backup_filename, name_modified = self._resolve_backup_filename(custom_name, force_overwrite)
        except ValueError as e:
            self._print_message('ERROR', str(e))
            self.logger.error(str(e))
            return False
            
        backup_path = self.backup_dir / backup_filename

        # Show name modification warning
        if name_modified:
            self._print_message('WARNING', f"Backup name modified to avoid conflict: {backup_filename}")

        # Progress indicators
        container_check = ProgressIndicator(f"Checking container '{self.container_name}'", self.use_colors)
        backup_progress = ProgressIndicator(f"Creating backup '{backup_filename}'", self.use_colors)
        
        try:
            # Check container availability
            if self.show_progress:
                container_check.start()
                time.sleep(0.5)  # Brief pause for visual feedback
                
            if not self._check_docker_container():
                if self.show_progress:
                    container_check.complete(False)
                error_msg = f"Container '{self.container_name}' not found or not running"
                self._print_message('ERROR', error_msg)
                self.logger.error(error_msg)
                return False
                
            if self.show_progress:
                container_check.complete(True)

            self.logger.info(f"Iniciando el backup: {backup_filename}")

            cmd = [
                "docker", "exec", self.container_name,
                "pg_dump",
                "-U", self.db_config["user"],
                "-d", self.db_config["database"],
                "--clean",
                "--create"
            ]

            # Start backup progress
            if self.show_progress:
                backup_progress.start()

            env = os.environ.copy()
            env["PGPASSWORD"] = self.db_config["password"]

            with open(backup_path, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                    timeout=300
                )
                
                # Simulate progress updates during backup
                if self.show_progress:
                    for i in range(3):
                        time.sleep(0.3)
                        backup_progress.update(".")

            if result.returncode == 0:
                file_size = backup_path.stat().st_size
                self.logger.info(f"Backup completado exitosamente: {backup_filename} ({file_size} bytes)")
                
                if self.show_progress:
                    backup_progress.complete(True)
                    self._print_message('INFO', f"Backup size: {self._format_file_size(file_size)}")
                    self._print_message('INFO', f"Location: {backup_path.absolute()}")
                    
                return True
            else:
                self.logger.error(f"Error en pg_dump: {result.stderr}")
                if self.show_progress:
                    backup_progress.complete(False)
                self._print_message('ERROR', f"pg_dump failed: {result.stderr.strip()}")
                    
                if backup_path.exists():
                    backup_path.unlink()
                return False

        except subprocess.TimeoutExpired:
            error_msg = "Timeout en pg_dump - el proceso tomo mas de 5 minutos"
            self.logger.error(error_msg)
            if self.show_progress:
                backup_progress.complete(False)
            self._print_message('ERROR', "Backup timeout (>5 minutes)")
                
            if backup_path.exists():
                backup_path.unlink()
            return False

        except FileNotFoundError:
            error_msg = "Error: Docker no encontrado"
            self.logger.error(error_msg)
            if self.show_progress:
                backup_progress.complete(False)
            self._print_message('ERROR', "Docker command not found")
                
            return False
        except Exception as e:
            self.logger.error(f"Error inesperado durante el backup: {e}")
            if self.show_progress:
                backup_progress.complete(False)
            self._print_message('ERROR', f"Unexpected error: {e}")
                
            if backup_path.exists():
                backup_path.unlink()
            return False

    def _format_file_size(self, size_bytes: int) -> str:
        """
        Formatea el tamaño del archivo en unidades legibles
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


def create_parser():
    """
    Crea el parser de argumentos de línea de comandos
    """
    parser = argparse.ArgumentParser(
        description='PostgreSQL Database Backup Orchestrator for Docker containers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Create backup with timestamp
  %(prog)s --name my_backup          # Create backup with custom name
  %(prog)s --container my_db         # Backup from different container
  %(prog)s --dir /path/to/backups    # Use different backup directory
  %(prog)s --quiet                   # Run without progress indicators
  %(prog)s --list                    # List existing backups
  %(prog)s --name test --force       # Overwrite existing backup
  %(prog)s --no-color                # Disable colored output
        """
    )
    
    parser.add_argument(
        '--name', '-n',
        type=str,
        help='Custom name for the backup file (without .sql extension)'
    )
    
    parser.add_argument(
        '--container', '-c',
        type=str,
        default='pc_db',
        help='Docker container name (default: pc_db)'
    )
    
    parser.add_argument(
        '--dir', '-d',
        type=str,
        default='backups',
        help='Backup directory path (default: backups)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Disable progress indicators'
    )
    
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Overwrite existing backup files'
    )
    
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List existing backup files and exit'
    )
    
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )
    
    return parser


def main():
    """
    Función principal con interfaz de línea de comandos
    """
    parser = create_parser()
    args = parser.parse_args()
    
    # Determine if colors should be used
    use_colors = not args.no_color and sys.stdout.isatty()
    if not use_colors:
        Colors.disable()
    
    # Configure logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        orchestrator = BackupOrchestrator(
            container_name=args.container,
            backup_dir=args.dir,
            show_progress=not args.quiet,
            use_colors=use_colors
        )
        
        # Handle list command
        if args.list:
            backups = orchestrator.list_backups()
            if not backups:
                if use_colors:
                    print(f"{Colors.YELLOW}No backup files found{Colors.RESET}")
                else:
                    print("No backup files found")
                return 0
                
            # Header
            if use_colors:
                print(f"{Colors.CYAN}{Colors.BOLD}Backup files in {orchestrator.backup_dir}:{Colors.RESET}")
                print(f"{Colors.CYAN}{'-' * 60}{Colors.RESET}")
            else:
                print(f"Backup files in {orchestrator.backup_dir}:")
                print("-" * 60)
                
            for backup in backups:
                size_str = orchestrator._format_file_size(backup['size'])
                if use_colors:
                    print(f"{Colors.WHITE}{backup['name']:<30}{Colors.RESET} "
                          f"{Colors.BRIGHT_BLUE}{size_str:>10}{Colors.RESET} "
                          f"{Colors.MAGENTA}{backup['modified']}{Colors.RESET}")
                else:
                    print(f"{backup['name']:<30} {size_str:>10} {backup['modified']}")
            return 0
        
        if not args.quiet:
            if use_colors:
                print(f"{Colors.CYAN}{Colors.BOLD}PostgreSQL Backup Orchestrator{Colors.RESET}")
                print(f"{Colors.WHITE}Container: {Colors.BRIGHT_YELLOW}{orchestrator.container_name}{Colors.RESET}")
                print(f"{Colors.WHITE}Backup directory: {Colors.BRIGHT_YELLOW}{orchestrator.backup_dir}{Colors.RESET}")
                print(f"{Colors.CYAN}{'-' * 40}{Colors.RESET}")
            else:
                print("PostgreSQL Backup Orchestrator")
                print(f"Container: {orchestrator.container_name}")
                print(f"Backup directory: {orchestrator.backup_dir}")
                print("-" * 40)
        
        success = orchestrator.create_backup(
            custom_name=args.name,
            force_overwrite=args.force
        )
        
        if success:
            if not args.quiet:
                if use_colors:
                    print(f"{Colors.BRIGHT_GREEN}[SUCCESS]{Colors.RESET} Backup completed successfully")
                else:
                    print("[SUCCESS] Backup completed successfully")
            return 0
        else:
            if not args.quiet:
                if use_colors:
                    print(f"{Colors.BRIGHT_RED}[FAILED]{Colors.RESET} Backup operation failed")
                else:
                    print("[FAILED] Backup operation failed")
            return 1
            
    except KeyboardInterrupt:
        if use_colors:
            print(f"\n{Colors.YELLOW}[CANCELLED]{Colors.RESET} Backup cancelled by user")
        else:
            print("\n[CANCELLED] Backup cancelled by user")
        return 1
    except Exception as e:
        if use_colors:
            print(f"{Colors.BRIGHT_RED}[ERROR]{Colors.RESET} Unexpected error: {e}")
        else:
            print(f"[ERROR] Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
