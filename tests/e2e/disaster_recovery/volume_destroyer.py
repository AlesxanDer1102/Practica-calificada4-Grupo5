"""
Simulador de eliminación de volúmenes para tests de desastre
"""

import subprocess
import time
from typing import Dict, Any, List

from .disaster_simulator import DisasterSimulator


class VolumeDestroyer(DisasterSimulator):
    """
    Simula eliminación completa de volúmenes de datos
    """

    def __init__(self, environment: str):
        super().__init__(environment)
        self.destroyed_volumes = []

    def simulate_disaster(self, target: str) -> Dict[str, Any]:
        """
        Simula eliminación de volúmenes según entorno
        """
        disaster_start = time.time()

        if self.environment == "docker":
            return self._destroy_docker_volume(target)
        elif self.environment == "kubernetes":
            return self._destroy_k8s_volume(target)
        else:
            raise ValueError(f"Entorno no soportado: {self.environment}")

    def _destroy_docker_volume(self, container_name: str) -> Dict[str, Any]:
        """
        Elimina volúmenes Docker del contenedor
        """
        try:
            # Obtener volúmenes asociados al contenedor
            cmd = [
                "docker",
                "inspect",
                container_name,
                "--format",
                "{{range .Mounts}}{{.Name}}{{end}}",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"No se pudo inspeccionar contenedor {container_name}",
                    "timestamp": time.time(),
                }

            # Parar contenedor primero
            subprocess.run(["docker", "stop", container_name], timeout=30)

            # Simular eliminación de volúmenes (en test real sería peligroso)
            volumes_destroyed = []
            for volume in result.stdout.strip().split():
                if volume:  # Si hay volúmenes
                    volumes_destroyed.append(volume)
                    self.destroyed_volumes.append(
                        {
                            "volume": volume,
                            "container": container_name,
                            "timestamp": time.time(),
                        }
                    )

            self.log_disaster("volume_deletion", container_name, time.time())

            return {
                "success": True,
                "disaster_type": "volume_deletion",
                "target": container_name,
                "volumes_destroyed": volumes_destroyed,
                "timestamp": time.time(),
                "recoverable": True,  # Con backup sí es recuperable
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout en comando Docker"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _destroy_k8s_volume(
        self, pod_name: str, namespace: str = "default"
    ) -> Dict[str, Any]:
        """
        Elimina PVC en Kubernetes
        """
        try:
            # Obtener PVCs asociados al pod
            cmd = [
                "kubectl",
                "get",
                "pod",
                pod_name,
                "-n",
                namespace,
                "-o",
                "jsonpath={.spec.volumes[*].persistentVolumeClaim.claimName}",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"No se pudo obtener info del pod {pod_name}",
                    "timestamp": time.time(),
                }

            pvcs = result.stdout.strip().split()
            pvcs_destroyed = []

            # Eliminar pod primero
            subprocess.run(
                ["kubectl", "delete", "pod", pod_name, "-n", namespace], timeout=30
            )

            # Simular eliminación de PVCs
            for pvc in pvcs:
                if pvc:
                    pvcs_destroyed.append(pvc)
                    self.destroyed_volumes.append(
                        {
                            "pvc": pvc,
                            "pod": pod_name,
                            "namespace": namespace,
                            "timestamp": time.time(),
                        }
                    )

            self.log_disaster("pvc_deletion", f"{namespace}/{pod_name}", time.time())

            return {
                "success": True,
                "disaster_type": "pvc_deletion",
                "target": f"{namespace}/{pod_name}",
                "pvcs_destroyed": pvcs_destroyed,
                "timestamp": time.time(),
                "recoverable": True,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout en comando kubectl"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def is_recoverable(self) -> bool:
        """
        Los volúmenes eliminados son recuperables con backup
        """
        return True

    def get_destruction_summary(self) -> Dict[str, Any]:
        """
        Retorna resumen de volúmenes destruidos
        """
        return {
            "total_volumes_destroyed": len(self.destroyed_volumes),
            "destroyed_volumes": self.destroyed_volumes,
            "disaster_summary": self.get_disaster_summary(),
        }
