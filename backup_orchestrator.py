#!/usr/bin/env python3

import os
import subprocess
import logging
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

class ProgressIndicator:
    """
    Simple progress indicator for command line operations
    """
    def __init__(self, message: str):
        self.message = message
        self.active = False
        
    def start(self):
        """Start showing progress"""
        self.active = True
        print(f"[INFO] {self.message}", end="", flush=True)
        
    def update(self, status: str = "."):
        """Update progress indicator"""
        if self.active:
            print(status, end="", flush=True)
            
    def complete(self, success: bool = True):
        """Complete progress indication"""
        if self.active:
            status = " [OK]" if success else " [FAILED]"
            print(status)
            self.active = False

class BackupOrchestrator:
    """
    Orquestador de backups para PostgreSQL con contenedores Docker
    """

    def __init__(self, container_name: str = "pc_db", backup_dir: str = "backups", show_progress: bool = True):
        self.container_name = container_name
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.show_progress = show_progress

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

    def create_backup(self, custom_name: str = None) -> bool:
        """
        Crea un backup de la base de datos usando docker exec y pg_dump
        """
        if custom_name:
            backup_filename = f"{custom_name}.sql"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.sql"
            
        backup_path = self.backup_dir / backup_filename

        # Progress indicators
        container_check = ProgressIndicator(f"Checking container '{self.container_name}'")
        backup_progress = ProgressIndicator(f"Creating backup '{backup_filename}'")
        
        try:
            # Check container availability
            if self.show_progress:
                container_check.start()
                time.sleep(0.5)  # Brief pause for visual feedback
                
            if not self._check_docker_container():
                if self.show_progress:
                    container_check.complete(False)
                self.logger.error(f"Container '{self.container_name}' not found or not running")
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
                    print(f"[INFO] Backup size: {self._format_file_size(file_size)}")
                    print(f"[INFO] Location: {backup_path.absolute()}")
                    
                return True
            else:
                self.logger.error(f"Error en pg_dump: {result.stderr}")
                if self.show_progress:
                    backup_progress.complete(False)
                    print(f"[ERROR] pg_dump failed: {result.stderr.strip()}")
                    
                if backup_path.exists():
                    backup_path.unlink()
                return False

        except subprocess.TimeoutExpired:
            error_msg = "Timeout en pg_dump - el proceso tomo mas de 5 minutos"
            self.logger.error(error_msg)
            if self.show_progress:
                backup_progress.complete(False)
                print(f"[ERROR] Backup timeout (>5 minutes)")
                
            if backup_path.exists():
                backup_path.unlink()
            return False

        except FileNotFoundError:
            error_msg = "Error: Docker no encontrado"
            self.logger.error(error_msg)
            if self.show_progress:
                backup_progress.complete(False)
                print(f"[ERROR] Docker command not found")
                
            return False
        except Exception as e:
            self.logger.error(f"Error inesperado durante el backup: {e}")
            if self.show_progress:
                backup_progress.complete(False)
                print(f"[ERROR] Unexpected error: {e}")
                
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
    
    return parser


def main():
    """
    Función principal con interfaz de línea de comandos
    """
    parser = create_parser()
    args = parser.parse_args()
    
    # Configure logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        orchestrator = BackupOrchestrator(
            container_name=args.container,
            backup_dir=args.dir,
            show_progress=not args.quiet
        )
        
        if not args.quiet:
            print("PostgreSQL Backup Orchestrator")
            print(f"Container: {orchestrator.container_name}")
            print(f"Backup directory: {orchestrator.backup_dir}")
            print("-" * 40)
        
        success = orchestrator.create_backup(custom_name=args.name)
        
        if success:
            if not args.quiet:
                print("[SUCCESS] Backup completed successfully")
            return 0
        else:
            if not args.quiet:
                print("[FAILED] Backup operation failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n[CANCELLED] Backup cancelled by user")
        return 1
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
