#!/usr/bin/env python3

import os
import subprocess
import logging
import argparse
import sys
from datetime import datetime
from pathlib import Path

class BackupOrchestrator:
    """
    Orquestador de backups para PostgreSQL con contenedores Docker
    """

    def __init__(self, container_name: str = "pc_db", backup_dir: str = "backups"):
        self.container_name = container_name
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

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

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

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

        try:
            self.logger.info(f"Iniciando el backup: {backup_filename}")

            cmd = [
                "docker", "exec", self.container_name,
                "pg_dump",
                "-U", self.db_config["user"],
                "-d", self.db_config["database"],
                "--clean",
                "--create"
            ]

            self.logger.info("Conectando al contenedor Docker...")

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

            if result.returncode == 0:
                file_size = backup_path.stat().st_size
                self.logger.info(f"Backup completado exitosamente: {backup_filename} ({file_size} bytes)")
                return True
            else:
                self.logger.error(f"Error en pg_dump: {result.stderr}")
                if backup_path.exists():
                    backup_path.unlink()
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("Timeout en pg_dump - el proceso tomo mas de 5 minutos")
            if backup_path.exists():
                backup_path.unlink()
            return False

        except FileNotFoundError:
            self.logger.error("Error: Docker no encontrado")
            return False
        except Exception as e:
            self.logger.error(f"Error inesperado durante el backup: {e}")
            if backup_path.exists():
                backup_path.unlink()
            return False


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
            backup_dir=args.dir
        )
        
        print("PostgreSQL Backup Orchestrator")
        print(f"Container: {orchestrator.container_name}")
        print(f"Backup directory: {orchestrator.backup_dir}")
        print("-" * 40)
        
        success = orchestrator.create_backup(custom_name=args.name)
        
        if success:
            print("Backup completed successfully")
            return 0
        else:
            print("Error: Backup failed")
            return 1
            
    except KeyboardInterrupt:
        print("\nBackup cancelled by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
