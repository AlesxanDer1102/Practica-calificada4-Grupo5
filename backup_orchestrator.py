#!/usr/bin/env python3

import os
import subprocess
import logging
from datetime import datetime
from pathlib import Path

class BackupOrchestrator:
    """
    Orquestador de backups para PostgreSQL con conternedores Docker
    """

    def  __init__(self,container_name:str="pc_db",backup_dir:str="backups"):

        self.container_name=container_name
        self.backup_dir=Path(backup_dir)
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

        log_file=self.backup_dir/"backup_orchestrator.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file,encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def create_backup(self) -> bool:
        """
        Crea un backup de la base de datos usando docker exec y pg_dump
        """

        timestamp =datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename=f"backup_{timestamp}.sql"
        backup_path = self.backup_dir / backup_filename

        try:
            self.logger.info(f"Iniciando el backup: {backup_filename}")


            cmd = [
                "docker","exec",self.container_name,
                "pg_dump",
                "-U",self.db_config["user"],
                "-d",self.db_config["database"],
                "--clean",
                "--create"
            ]

            self.logger.info("Conectando al contenedor Docker...")

            env=os.environ.copy()
            env["PGPASSWORD"] = self.db_config["password"]

            with open(backup_path,'w',encoding='utf-8') as f:
                result =subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                    timeout=300
                )

            if result.returncode == 0:
                file_size = backup_path.stat().st_size
                self.logger.info(f"Bacup completado exitosamente: {backup_filename} ({file_size}) bytes")
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

def main():
    """ Funcion principal"""
    orchestator=BackupOrchestrator()

    print("=== ORQUESTADOR DE BACKUPS POSTGRESQL ===")
    print(f"Contenedor: {orchestator.container_name}")
    print(f"Directorio de backups: {orchestator.backup_dir}")
    print("==========================================")

    success = orchestator.create_backup()

    if success:
        print("Backup completado exitosamente")
    else:
        print(" Error al crear el backup")
        return 1

    return 0

if __name__== "__main__":
    import sys
    sys.exit(main())
