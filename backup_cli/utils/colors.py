"""
Utilidades para manejo de colores ANSI en terminal
"""

import sys


class Colors:
    """
    Códigos de colores ANSI para salida en terminal
    """

    RESET = "\033[0m"
    BOLD = "\033[1m"

    # Colores básicos
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Colores brillantes
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"

    @classmethod
    def disable(cls):
        """Deshabilita todos los colores"""
        for attr in dir(cls):
            if not attr.startswith("_") and attr != "disable":
                setattr(cls, attr, "")


def should_use_colors(no_color_flag: bool = False) -> bool:
    """
    Determina si se deben usar colores basado en la capacidad del terminal
    """
    return not no_color_flag and sys.stdout.isatty()


def print_colored_message(level: str, message: str, use_colors: bool = True):
    """
    Imprime un mensaje con color basado en el nivel
    """
    color_map = {
        "INFO": Colors.BLUE,
        "SUCCESS": Colors.BRIGHT_GREEN,
        "WARNING": Colors.BRIGHT_YELLOW,
        "ERROR": Colors.BRIGHT_RED,
        "FAILED": Colors.BRIGHT_RED,
        "CANCELLED": Colors.YELLOW,
    }

    if use_colors:
        color = color_map.get(level, Colors.WHITE)
        print(f"{color}[{level}]{Colors.RESET} {message}")
    else:
        print(f"[{level}] {message}")
