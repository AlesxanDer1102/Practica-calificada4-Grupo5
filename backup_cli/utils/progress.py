"""
Utilidades para indicadores de progreso en terminal
"""

import time
from .colors import Colors


class ProgressIndicator:
    """
    Indicador de progreso simple para operaciones de línea de comandos
    """

    def __init__(self, message: str, use_colors: bool = True):
        self.message = message
        self.active = False
        self.use_colors = use_colors

    def start(self):
        """Inicia el indicador de progreso"""
        self.active = True
        if self.use_colors:
            print(
                f"{Colors.BLUE}[INFO]{Colors.RESET} {self.message}", end="", flush=True
            )
        else:
            print(f"[INFO] {self.message}", end="", flush=True)

    def update(self, status: str = "."):
        """Actualiza el indicador de progreso"""
        if self.active:
            if self.use_colors:
                print(f"{Colors.CYAN}{status}{Colors.RESET}", end="", flush=True)
            else:
                print(status, end="", flush=True)

    def complete(self, success: bool = True):
        """Completa la indicación de progreso"""
        if self.active:
            if success:
                status = (
                    f" {Colors.BRIGHT_GREEN}[OK]{Colors.RESET}"
                    if self.use_colors
                    else " [OK]"
                )
            else:
                status = (
                    f" {Colors.BRIGHT_RED}[FAILED]{Colors.RESET}"
                    if self.use_colors
                    else " [FAILED]"
                )
            print(status)
            self.active = False

    def simulate_work(self, duration: float = 0.9, steps: int = 3):
        """
        Simula trabajo con actualizaciones de progreso
        """
        if self.active:
            for i in range(steps):
                time.sleep(duration / steps)
                self.update(".")
