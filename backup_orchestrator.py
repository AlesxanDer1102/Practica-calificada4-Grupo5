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

    def validate_backup_integrity(self, backup_path: Path) -> bool:
        """
        Valida la integridad básica del archivo de backup
        """
        try:
            if not backup_path.exists():
                self._print_message('ERROR', f"El archivo de backup no existe: {backup_path}")
                return False
            
            if backup_path.stat().st_size == 0:
                self._print_message('ERROR', "El archivo de backup está vacío")
                return False
            
            # Verificar que el archivo contiene comandos SQL básicos
            with open(backup_path, 'r', encoding='utf-8') as f:
                content = f.read(1000)  # Leer primeros 1000 caracteres
                
            # Verificar que contiene elementos típicos de un dump de PostgreSQL
            required_patterns = ['CREATE', 'INSERT', '--']
            found_patterns = [pattern for pattern in required_patterns if pattern in content.upper()]
            
            if len(found_patterns) < 2:
                self._print_message('WARNING', "El archivo no parece ser un backup válido de PostgreSQL")
                return False
            
            self._print_message('INFO', "Validación de integridad del backup: EXITOSA")
            return True
            
        except Exception as e:
            self._print_message('ERROR', f"Error al validar backup: {str(e)}")
            return False

    def confirm_restore_operation(self, backup_path: Path) -> bool:
        """
        Solicita confirmación al usuario antes de proceder con la restauración
        """
        self._print_message('WARNING', "ADVERTENCIA: Esta operación sobrescribirá TODOS los datos existentes")
        print()
        print(f"Backup a restaurar: {backup_path.name}")
        print(f"Base de datos objetivo: {self.db_config['database']}")
        print(f"Contenedor: {self.container_name}")
        print()
        
        while True:
            confirmation = input("¿Está seguro que desea continuar? (si/no): ").lower().strip()
            
            if confirmation in ['si', 'sí', 's', 'yes', 'y']:
                self._print_message('INFO', "Confirmación recibida, procediendo con la restauración")
                return True
            elif confirmation in ['no', 'n']:
                self._print_message('INFO', "Restauración cancelada por el usuario")
                return False
            else:
                print("Por favor, responda 'si' o 'no'")

    def restore_database(self, backup_path: Path = None) -> bool:
        """
        Restaura la base de datos desde un archivo de backup
        """
        try:
            # Si no se proporciona un backup, seleccionar interactivamente
            if backup_path is None:
                backup_path = self.select_backup_interactive()
            
            # Validar integridad del backup
            if not self.validate_backup_integrity(backup_path):
                return False
            
            # Solicitar confirmación
            if not self.confirm_restore_operation(backup_path):
                return False
            
            # Verificar disponibilidad del contenedor
            container_check = ProgressIndicator(f"Verificando contenedor '{self.container_name}'", self.use_colors)
            restore_progress = ProgressIndicator(f"Restaurando desde '{backup_path.name}'", self.use_colors)
            
            if self.show_progress:
                container_check.start()
                time.sleep(0.5)
                
            if not self._check_docker_container():
                if self.show_progress:
                    container_check.complete(False)
                error_msg = f"Contenedor '{self.container_name}' no encontrado o no está ejecutándose"
                self._print_message('ERROR', error_msg)
                self.logger.error(error_msg)
                return False
                
            if self.show_progress:
                container_check.complete(True)

            self.logger.info(f"Iniciando restauración desde: {backup_path.name}")

            # Comando para restaurar usando psql
            cmd = [
                "docker", "exec", "-i", self.container_name,
                "psql",
                "-U", self.db_config["user"],
                "-d", self.db_config["database"]
            ]

            # Iniciar progreso de restauración
            if self.show_progress:
                restore_progress.start()

            env = os.environ.copy()
            env["PGPASSWORD"] = self.db_config["password"]

            # Ejecutar restauración
            with open(backup_path, 'r', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdin=f,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                    timeout=300
                )
                
                # Simular progreso durante la restauración
                if self.show_progress:
                    restore_progress.simulate_work()

            if result.returncode == 0:
                self.logger.info(f"Restauración completada exitosamente desde: {backup_path.name}")
                
                if self.show_progress:
                    restore_progress.complete(True)
                    self._print_message('INFO', f"Base de datos restaurada exitosamente")
                    self._print_message('INFO', f"Backup utilizado: {backup_path.name}")
                    
                return True
            else:
                self.logger.error(f"Error en restauración: {result.stderr}")
                if self.show_progress:
                    restore_progress.complete(False)
                self._print_message('ERROR', f"Falló la restauración: {result.stderr.strip()}")
                return False

        except subprocess.TimeoutExpired:
            error_msg = "Timeout en restauración - el proceso tomó más de 5 minutos"
            self.logger.error(error_msg)
            if self.show_progress:
                restore_progress.complete(False)
            self._print_message('ERROR', "Timeout de la restauración (>5 minutos)")
            return False

        except FileNotFoundError:
            error_msg = "Error: Docker no encontrado"
            self.logger.error(error_msg)
            if self.show_progress:
                restore_progress.complete(False)
            self._print_message('ERROR', "Docker no está disponible")
            return False
            
        except KeyboardInterrupt:
            self._print_message('INFO', "Restauración cancelada por el usuario")
            return False
            
        except Exception as e:
            error_msg = f"Error inesperado durante la restauración: {str(e)}"
            self.logger.error(error_msg)
            self._print_message('ERROR', error_msg)
            return False

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
        
        # Manejar comando de restauración
        if config.restore:
            if config.show_progress:
                display_header(orchestrator, use_colors)
            
            # Restaurar desde archivo específico o selección interactiva
            restore_path = None
            if config.restore_file:
                restore_path = Path(config.restore_file)
                if not restore_path.exists():
                    print_colored_message('ERROR', f"Archivo de backup no encontrado: {config.restore_file}", use_colors)
                    return 1
            
            success = orchestrator.restore_database(restore_path)
            
            if success:
                if config.show_progress:
                    print_colored_message('SUCCESS', 'Restauración completada exitosamente', use_colors)
                return 0
            else:
                if config.show_progress:
                    print_colored_message('FAILED', 'La operación de restauración falló', use_colors)
                return 1
        
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
