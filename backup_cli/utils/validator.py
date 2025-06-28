"""
Utilidades para validación de nombres de backup
"""

import re
from datetime import datetime
from pathlib import Path


class BackupNameValidator:
    """
    Validador de nombres de archivos de backup
    """
    
    # Nombres reservados del sistema
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
        'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 
        'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    # Caracteres inválidos para nombres de archivo
    INVALID_CHARS_PATTERN = r'[<>:"/\\|?*]'
    
    # Longitud máxima del nombre
    MAX_NAME_LENGTH = 200

    @classmethod
    def validate_backup_name(cls, name: str) -> tuple[bool, str]:
        """
        Valida que el nombre del backup sea válido para el sistema de archivos
        """
        if not name:
            return False, "El nombre del backup no puede estar vacío"
            
        # Verificar caracteres inválidos
        if re.search(cls.INVALID_CHARS_PATTERN, name):
            return False, f"El nombre contiene caracteres inválidos: {cls.INVALID_CHARS_PATTERN}"
            
        # Verificar longitud
        if len(name) > cls.MAX_NAME_LENGTH:
            return False, f"El nombre es muy largo (máximo {cls.MAX_NAME_LENGTH} caracteres)"
            
        # Verificar nombres reservados
        if name.upper() in cls.RESERVED_NAMES:
            return False, f"'{name}' es un nombre reservado del sistema"
            
        return True, "Nombre de backup válido"

    @classmethod
    def resolve_backup_filename(cls, backup_dir: Path, custom_name: str = None, 
                              force_overwrite: bool = False) -> tuple[str, bool]:
        """
        Resuelve el nombre final del backup, manejando conflictos si es necesario
        """
        if custom_name:
            is_valid, message = cls.validate_backup_name(custom_name)
            if not is_valid:
                raise ValueError(f"Nombre de backup inválido: {message}")
                
            backup_filename = f"{custom_name}.sql"
            backup_path = backup_dir / backup_filename
            
            # Verificar si el archivo existe
            if backup_path.exists() and not force_overwrite:
                # Generar nombre alternativo con timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"{custom_name}_{timestamp}.sql"
                return backup_filename, True  # True indica que el nombre fue modificado
            else:
                return backup_filename, False  # False indica que se usó el nombre original
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.sql"
            return backup_filename, False


def format_file_size(size_bytes: int) -> str:
    """
    Formatea el tamaño del archivo en unidades legibles
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB" 