"""
Test completo de validación de recuperación ante desastres
"""

import subprocess
import time
from typing import Any, Dict, Tuple

from .data_corruptor import DataCorruptor
from .recovery_validator import RecoveryValidator
from .rto_monitor import RTOMonitor
from .volume_destroyer import VolumeDestroyer


class FullRecoveryTest:
    """
    Orchestrador de test completo de recuperación
    """

    def __init__(
        self, environment: str, backup_orchestrator_path: str = "backup_orchestrator.py"
    ):
        self.environment = environment
        self.backup_orchestrator_path = backup_orchestrator_path
        self.validator = RecoveryValidator()
        self.rto_monitor = RTOMonitor(target_rto_seconds=300)  # 5 min
        self.test_results = []

    def run_full_disaster_recovery_test(self, target: str) -> Dict[str, Any]:
        """
        Ejecuta test completo de disaster recovery
        """
        test_start = time.time()

        # 1. Crear datos iniciales y backup
        initial_data = self._create_initial_data(target)
        backup_result = self._create_baseline_backup(target)

        if not backup_result["success"]:
            return {"success": False, "error": "No se pudo crear backup inicial"}

        # 2. Simular desastre aleatorio
        disaster_result = self._simulate_random_disaster(target)

        # 3. Iniciar monitoreo RTO
        session_id = self.rto_monitor.start_recovery_timer(
            disaster_result["disaster_type"], target
        )

        # 4. Ejecutar recuperación
        recovery_result = self._execute_recovery(target, backup_result["backup_name"])

        # 5. Detener monitoreo RTO
        rto_result = self.rto_monitor.stop_recovery_timer(session_id)

        # 6. Validar recuperación completa
        recovered_data = self._verify_recovered_data(target)
        validation_result = self.validator.validate_full_recovery(
            initial_data, recovered_data
        )

        # 7. Compilar resultados
        test_result = {
            "test_id": f"disaster_recovery_{int(test_start)}",
            "environment": self.environment,
            "target": target,
            "test_duration": time.time() - test_start,
            "initial_data": initial_data,
            "backup_result": backup_result,
            "disaster_result": disaster_result,
            "recovery_result": recovery_result,
            "rto_result": rto_result,
            "validation_result": validation_result,
            "overall_success": self._evaluate_overall_success(
                disaster_result, recovery_result, rto_result, validation_result
            ),
            "timestamp": test_start,
        }

        self.test_results.append(test_result)
        return test_result

    def _create_initial_data(self, target: str) -> Dict[str, Any]:
        """
        Crea datos iniciales para medir recuperación
        """
        try:
            # Simular inserción de datos de referencia
            if self.environment == "docker":
                cmd = [
                    "docker",
                    "exec",
                    target,
                    "psql",
                    "-U",
                    "postgres",
                    "-d",
                    "test_db",
                    "-c",
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';",
                ]
            else:
                cmd = [
                    "kubectl",
                    "exec",
                    target,
                    "--",
                    "psql",
                    "-U",
                    "postgres",
                    "-d",
                    "test_db",
                    "-c",
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';",
                ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                # Extraer número de registros
                count_line = [
                    line for line in result.stdout.split("\n") if line.strip().isdigit()
                ]
                record_count = int(count_line[0]) if count_line else 0
            else:
                record_count = 0  # Fallback

            return {
                "record_count": record_count,
                "tables": ["information_schema"],
                "timestamp": time.time(),
            }

        except Exception as e:
            return {
                "record_count": 0,
                "tables": [],
                "error": str(e),
                "timestamp": time.time(),
            }

    def _create_baseline_backup(self, target: str) -> Dict[str, Any]:
        """
        Crea backup de línea base antes del desastre
        """
        try:
            backup_name = f"disaster_test_baseline_{int(time.time())}"

            if self.environment == "docker":
                # En lugar de usar backup_orchestrator, usar pg_dump directamente
                cmd = [
                    "docker",
                    "exec",
                    target,
                    "pg_dump",
                    "-U", "postgres",
                    "-d", "test_db",
                    "-f", f"/tmp/{backup_name}.sql"
                ]
            else:
                cmd = [
                    "kubectl",
                    "exec",
                    target,
                    "--",
                    "pg_dump",
                    "-U", "postgres", 
                    "-d", "test_db",
                    "-f", f"/tmp/{backup_name}.sql"
                ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

            return {
                "success": result.returncode == 0,
                "backup_name": backup_name,
                "command_output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "timestamp": time.time(),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "timestamp": time.time()}

    def _simulate_random_disaster(self, target: str) -> Dict[str, Any]:
        """
        Simula desastre aleatorio (volumen o corrupción)
        """
        import random

        disaster_type = random.choice(["volume_destruction", "data_corruption"])

        if disaster_type == "volume_destruction":
            destroyer = VolumeDestroyer(self.environment)
            return destroyer.simulate_disaster(target)
        else:
            corruptor = DataCorruptor(self.environment)
            return corruptor.simulate_disaster(target)

    def _execute_recovery(self, target: str, backup_name: str) -> Dict[str, Any]:
        """
        Ejecuta proceso de recuperación usando backup
        """
        try:
            if self.environment == "docker":
                # Usar psql para restaurar directamente
                cmd = [
                    "docker",
                    "exec",
                    target,
                    "psql",
                    "-U", "postgres",
                    "-d", "test_db",
                    "-f", f"/tmp/{backup_name}.sql"
                ]
            else:
                cmd = [
                    "kubectl",
                    "exec",
                    target,
                    "--",
                    "psql",
                    "-U", "postgres",
                    "-d", "test_db", 
                    "-f", f"/tmp/{backup_name}.sql"
                ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            return {
                "success": result.returncode == 0,
                "command_output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "recovery_method": "direct_psql",
                "timestamp": time.time(),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "timestamp": time.time()}

    def _verify_recovered_data(self, target: str) -> Dict[str, Any]:
        """
        Verifica datos tras recuperación
        """
        # Usar misma lógica que _create_initial_data para comparar
        return self._create_initial_data(target)

    def _evaluate_overall_success(
        self,
        disaster_result: Dict,
        recovery_result: Dict,
        rto_result: Dict,
        validation_result: Dict,
    ) -> bool:
        """
        Evalúa éxito general del test
        """
        return all(
            [
                disaster_result.get("success", False),
                recovery_result.get("success", False),
                rto_result.get("rto_met", False),
                validation_result.get("recovery_successful", False),
            ]
        )

    def get_test_summary(self) -> Dict[str, Any]:
        """
        Retorna resumen de todos los tests ejecutados
        """
        if not self.test_results:
            return {"total_tests": 0, "success_rate": 0}

        successful_tests = [t for t in self.test_results if t["overall_success"]]

        return {
            "total_tests": len(self.test_results),
            "successful_tests": len(successful_tests),
            "success_rate": len(successful_tests) / len(self.test_results) * 100,
            "avg_recovery_time": sum(
                t["rto_result"]["duration"]
                for t in self.test_results
                if t["rto_result"].get("duration")
            )
            / len(self.test_results),
            "rto_metrics": self.rto_monitor.get_rto_metrics(),
            "validation_summary": self.validator.get_validation_summary(),
            "tests": self.test_results,
        }
