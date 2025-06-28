#!/usr/bin/env python3

import os
import subprocess
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Importar módulos separados
from backup_cli.utils.colors import Colors, should_use_colors, print_colored_message
from backup_cli.utils.progress import ProgressIndicator
from backup_cli.utils.validator import BackupNameValidator, format_file_size
from backup_cli.cli.parser import create_cli_parser, CLIConfig


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

        # Configurar logging solo a archivo, la salida de consola la maneja el indicador de progreso
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)

    def _print_message(self, level: str, message: str):
        """Imprime mensaje con color si el progreso está habilitado"""
        if self.show_progress:
            print_colored_message(level, message, self.use_colors)

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

    def select_backup_interactive(self) -> Path:
        """
        Permite al usuario seleccionar un backup de forma interactiva
        """
        backups = self.list_backups()
        
        if not backups:
            self._print_message('ERROR', "No se encontraron backups disponibles")
            raise ValueError("No hay backups disponibles para restaurar")
        
        self._print_message('INFO', "Backups disponibles:")
        print()
        
        for i, backup in enumerate(backups, 1):
            size_formatted = format_file_size(backup['size'])
            modified_str = backup['modified'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"  {i}. {backup['name']}")
            print(f"     Tamaño: {size_formatted}")
            print(f"     Modificado: {modified_str}")
            print()
        
        while True:
            try:
                selection = input("Seleccione el número del backup a restaurar (0 para cancelar): ").strip()
                
                if selection == '0':
                    self._print_message('INFO', "Operación cancelada por el usuario")
                    raise KeyboardInterrupt("Restauración cancelada")
                
                index = int(selection) - 1
                if 0 <= index < len(backups):
                    selected_backup = backups[index]['path']
                    self._print_message('INFO', f"Backup seleccionado: {selected_backup.name}")
                    return selected_backup
                else:
                    print("Por favor, ingrese un número válido.")
                    
            except ValueError:
                print("Por favor, ingrese un número válido.")
            except KeyboardInterrupt:
                raise

    def create_backup(self, custom_name: str = None, force_overwrite: bool = False) -> bool:
        """
        Crea un backup de la base de datos usando docker exec y pg_dump
        """
        try:
            backup_filename, name_modified = BackupNameValidator.resolve_backup_filename(
                self.backup_dir, custom_name, force_overwrite
            )
        except ValueError as e:
            self._print_message('ERROR', str(e))
            self.logger.error(str(e))
            return False
            
        backup_path = self.backup_dir / backup_filename

        # Mostrar advertencia de modificación de nombre
        if name_modified:
            self._print_message('WARNING', f"Nombre de backup modificado para evitar conflicto: {backup_filename}")

        # Indicadores de progreso
        container_check = ProgressIndicator(f"Verificando contenedor '{self.container_name}'", self.use_colors)
        backup_progress = ProgressIndicator(f"Creando backup '{backup_filename}'", self.use_colors)
        
        try:
            # Verificar disponibilidad del contenedor
            if self.show_progress:
                container_check.start()
                time.sleep(0.5)  # Pausa breve para feedback visual
                
            if not self._check_docker_container():
                if self.show_progress:
                    container_check.complete(False)
                error_msg = f"Contenedor '{self.container_name}' no encontrado o no está ejecutándose"
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

            # Iniciar progreso de backup
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
                
                # Simular actualizaciones de progreso durante el backup
                if self.show_progress:
                    backup_progress.simulate_work()

            if result.returncode == 0:
                file_size = backup_path.stat().st_size
                self.logger.info(f"Backup completado exitosamente: {backup_filename} ({file_size} bytes)")
                
                if self.show_progress:
                    backup_progress.complete(True)
                    self._print_message('INFO', f"Tamaño del backup: {format_file_size(file_size)}")
                    self._print_message('INFO', f"Ubicación: {backup_path.absolute()}")
                    
                return True
            else:
                self.logger.error(f"Error en pg_dump: {result.stderr}")
                if self.show_progress:
                    backup_progress.complete(False)
                self._print_message('ERROR', f"pg_dump falló: {result.stderr.strip()}")
                    
                if backup_path.exists():
                    backup_path.unlink()
                return False

        except subprocess.TimeoutExpired:
            error_msg = "Timeout en pg_dump - el proceso tomó más de 5 minutos"
            self.logger.error(error_msg)
            if self.show_progress:
                backup_progress.complete(False)
            self._print_message('ERROR', "Timeout del backup (>5 minutos)")
                
            if backup_path.exists():
                backup_path.unlink()
            return False

        except FileNotFoundError:
            error_msg = "Error: Docker no encontrado"
            self.logger.error(error_msg)
            if self.show_progress:
                backup_progress.complete(False)
            self._print_message('ERROR', "Comando docker no encontrado")
                
            return False
        except Exception as e:
            self.logger.error(f"Error inesperado durante el backup: {e}")
            if self.show_progress:
                backup_progress.complete(False)
            self._print_message('ERROR', f"Error inesperado: {e}")
                
            if backup_path.exists():
                backup_path.unlink()
            return False


def display_backup_list(orchestrator: BackupOrchestrator, use_colors: bool):
    """
    Muestra la lista de backups disponibles
    """
    backups = orchestrator.list_backups()
    if not backups:
        if use_colors:
            print(f"{Colors.YELLOW}No se encontraron archivos de backup{Colors.RESET}")
        else:
            print("No se encontraron archivos de backup")
        return 0
        
    # Encabezado
    if use_colors:
        print(f"{Colors.CYAN}{Colors.BOLD}Archivos de backup en {orchestrator.backup_dir}:{Colors.RESET}")
        print(f"{Colors.CYAN}{'-' * 60}{Colors.RESET}")
    else:
        print(f"Archivos de backup en {orchestrator.backup_dir}:")
        print("-" * 60)
        
    for backup in backups:
        size_str = format_file_size(backup['size'])
        if use_colors:
            print(f"{Colors.WHITE}{backup['name']:<30}{Colors.RESET} "
                  f"{Colors.BRIGHT_BLUE}{size_str:>10}{Colors.RESET} "
                  f"{Colors.MAGENTA}{backup['modified']}{Colors.RESET}")
        else:
            print(f"{backup['name']:<30} {size_str:>10} {backup['modified']}")
    return 0


def display_header(orchestrator: BackupOrchestrator, use_colors: bool):
    """
    Muestra el encabezado de la aplicación
    """
    if use_colors:
        print(f"{Colors.CYAN}{Colors.BOLD}Orquestador de Backup PostgreSQL{Colors.RESET}")
        print(f"{Colors.WHITE}Contenedor: {Colors.BRIGHT_YELLOW}{orchestrator.container_name}{Colors.RESET}")
        print(f"{Colors.WHITE}Directorio de backup: {Colors.BRIGHT_YELLOW}{orchestrator.backup_dir}{Colors.RESET}")
        print(f"{Colors.CYAN}{'-' * 40}{Colors.RESET}")
    else:
        print("Orquestador de Backup PostgreSQL")
        print(f"Contenedor: {orchestrator.container_name}")
        print(f"Directorio de backup: {orchestrator.backup_dir}")
        print("-" * 40)


def main():
    """
    Función principal con interfaz de línea de comandos
    """
    parser = create_cli_parser()
    args = parser.parse_args()
    config = CLIConfig(args)
    
    # Determinar si se deben usar colores
    use_colors = should_use_colors(config.no_color)
    if not use_colors:
        Colors.disable()
    
    # Configurar nivel de logging basado en flag verbose
    if config.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        orchestrator = BackupOrchestrator(
            container_name=config.container,
            backup_dir=config.backup_dir,
            show_progress=config.show_progress,
            use_colors=use_colors
        )
        
        # Manejar comando de lista
        if config.list:
            return display_backup_list(orchestrator, use_colors)
        
        if config.show_progress:
            display_header(orchestrator, use_colors)
        
        success = orchestrator.create_backup(
            custom_name=config.name,
            force_overwrite=config.force
        )
        
        if success:
            if config.show_progress:
                print_colored_message('SUCCESS', 'Backup completado exitosamente', use_colors)
            return 0
        else:
            if config.show_progress:
                print_colored_message('FAILED', 'La operación de backup falló', use_colors)
            return 1
            
    except KeyboardInterrupt:
        print_colored_message('CANCELLED', 'Backup cancelado por el usuario', use_colors)
        return 1
    except Exception as e:
        print_colored_message('ERROR', f'Error inesperado: {e}', use_colors)
        return 1


if __name__ == "__main__":
    sys.exit(main())
