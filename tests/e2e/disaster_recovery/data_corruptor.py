"""
Simulador de corrupción de datos para tests de desastre
"""

import random
import subprocess
import time
from typing import Any, Dict, List

from .disaster_simulator import DisasterSimulator


class DataCorruptor(DisasterSimulator):
    """
    Simula corrupción de datos en la base de datos
    """

    def __init__(self, environment: str):
        super().__init__(environment)
        self.corruption_types = ["table_drop", "data_scramble", "index_corruption"]
        self.corrupted_objects = []

    def simulate_disaster(self, target: str) -> Dict[str, Any]:
        """
        Simula corrupción de datos según tipo aleatorio
        """
        corruption_type = random.choice(self.corruption_types)

        if corruption_type == "table_drop":
            return self._simulate_table_drop(target)
        elif corruption_type == "data_scramble":
            return self._simulate_data_scramble(target)
        elif corruption_type == "index_corruption":
            return self._simulate_index_corruption(target)

    def _simulate_table_drop(self, target: str) -> Dict[str, Any]:
        """
        Simula eliminación accidental de tabla crítica
        """
        try:
            # Obtener tablas de la DB
            tables = self._get_database_tables(target)

            if not tables:
                return {
                    "success": False,
                    "error": "No se encontraron tablas para corromper",
                    "timestamp": time.time(),
                }

            # Seleccionar tabla aleatoria para "eliminar"
            target_table = random.choice(tables)

            # En test real sería: DROP TABLE, aquí solo simulamos
            corruption_event = {
                "corruption_type": "table_drop",
                "target": target,
                "affected_table": target_table,
                "timestamp": time.time(),
                "simulated": True,  # No eliminamos realmente
            }

            self.corrupted_objects.append(corruption_event)
            self.log_disaster("table_drop", target, time.time())

            return {
                "success": True,
                "disaster_type": "table_drop",
                "target": target,
                "affected_table": target_table,
                "timestamp": time.time(),
                "recoverable": True,
                "severity": "high",
            }

        except Exception as e:
            return {"success": False, "error": str(e), "timestamp": time.time()}

    def _simulate_data_scramble(self, target: str) -> Dict[str, Any]:
        """
        Simula corrupción de datos (scrambling)
        """
        try:
            tables = self._get_database_tables(target)

            if not tables:
                return {"success": False, "error": "No se encontraron tablas"}

            affected_tables = random.sample(tables, min(3, len(tables)))  # Max 3 tablas
            corrupted_records = random.randint(100, 1000)

            corruption_event = {
                "corruption_type": "data_scramble",
                "target": target,
                "affected_tables": affected_tables,
                "estimated_corrupted_records": corrupted_records,
                "timestamp": time.time(),
                "simulated": True,
            }

            self.corrupted_objects.append(corruption_event)
            self.log_disaster("data_scramble", target, time.time())

            return {
                "success": True,
                "disaster_type": "data_scramble",
                "target": target,
                "affected_tables": affected_tables,
                "corrupted_records": corrupted_records,
                "timestamp": time.time(),
                "recoverable": True,
                "severity": "medium",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _simulate_index_corruption(self, target: str) -> Dict[str, Any]:
        """
        Simula corrupción de índices
        """
        try:
            corruption_event = {
                "corruption_type": "index_corruption",
                "target": target,
                "affected_indexes": [
                    "idx_users_email",
                    "idx_orders_date",
                    "idx_products_sku",
                ],
                "timestamp": time.time(),
                "simulated": True,
            }

            self.corrupted_objects.append(corruption_event)
            self.log_disaster("index_corruption", target, time.time())

            return {
                "success": True,
                "disaster_type": "index_corruption",
                "target": target,
                "affected_indexes": corruption_event["affected_indexes"],
                "timestamp": time.time(),
                "recoverable": True,
                "severity": "low",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_database_tables(self, target: str) -> List[str]:
        """
        Obtiene lista de tablas de la base de datos
        """
        try:
            if self.environment == "docker":
                cmd = [
                    "docker",
                    "exec",
                    target,
                    "psql",
                    "-U",
                    "postgres",
                    "-d",
                    "pc_db",
                    "-t",
                    "-c",
                    "SELECT tablename FROM pg_tables WHERE schemaname='public';",
                ]
            else:  # kubernetes
                cmd = [
                    "kubectl",
                    "exec",
                    target,
                    "--",
                    "psql",
                    "-U",
                    "postgres",
                    "-d",
                    "pc_db",
                    "-t",
                    "-c",
                    "SELECT tablename FROM pg_tables WHERE schemaname='public';",
                ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                tables = [
                    line.strip() for line in result.stdout.split("\n") if line.strip()
                ]
                return (
                    tables if tables else ["usuarios", "productos", "pedidos"]
                )  # Fallback
            else:
                # Fallback con tablas por defecto del sistema
                return ["pg_type", "pg_attribute", "pg_class"]

        except Exception:
            # Fallback en caso de error
            return ["pg_type", "pg_attribute", "pg_class"]

    def is_recoverable(self) -> bool:
        """
        La corrupción de datos es recuperable con backup
        """
        return True

    def get_corruption_summary(self) -> Dict[str, Any]:
        """
        Retorna resumen de corrupciones realizadas
        """
        corruption_by_type = {}
        for corruption in self.corrupted_objects:
            corruption_type = corruption["corruption_type"]
            if corruption_type not in corruption_by_type:
                corruption_by_type[corruption_type] = 0
            corruption_by_type[corruption_type] += 1

        return {
            "total_corruptions": len(self.corrupted_objects),
            "corruption_by_type": corruption_by_type,
            "corrupted_objects": self.corrupted_objects,
            "disaster_summary": self.get_disaster_summary(),
        }
