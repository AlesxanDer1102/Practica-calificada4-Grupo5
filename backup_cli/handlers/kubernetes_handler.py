import json
import logging
import subprocess
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class KubernetesHandler:
    """
    Maneja operaciones específicas de Kubernetes para backups de PostgreSQL
    """

    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.logger = logging.getLogger(__name__)

    def find_postgres_pods(self, labels: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """
        Encuentra pods de PostgreSQL usando labels
        """
        try:
            cmd = ["kubectl", "get", "pods", "-n", self.namespace, "-o", "json"]

            if labels:
                label_selector = ",".join([f"{k}={v}" for k, v in labels.items()])
                cmd.extend(["-l", label_selector])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                self.logger.error(f"Error al obtener pods: {result.stderr}")
                return []

            data = json.loads(result.stdout)
            pods = []

            for item in data.get("items", []):

                if self._is_postgres_pod(item):
                    pods.append(
                        {
                            "name": item["metadata"]["name"],
                            "namespace": item["metadata"]["namespace"],
                            "status": item["status"]["phase"],
                            "labels": item["metadata"].get("labels", {}),
                            "containers": [
                                c["name"] for c in item["spec"]["containers"]
                            ],
                        }
                    )

            return pods

        except Exception as e:
            self.logger.error(f"Error al buscar pods de PostgreSQL: {e}")
            return []

    def _is_postgres_pod(self, pod_data: Dict) -> bool:
        """
        Determina si un pod es de PostgreSQL basado en su configuración
        Adaptado para la configuración específica del proyecto
        """

        name = pod_data["metadata"]["name"].lower()
        if "postgres" in name or "postgresql" in name:
            return True

        labels = pod_data["metadata"].get("labels", {})

        if labels.get("app") == "postgres":
            return True

        for key, value in labels.items():
            if "postgres" in key.lower() or "postgres" in str(value).lower():
                return True

        containers = pod_data["spec"].get("containers", [])
        for container in containers:
            image = container.get("image", "").lower()
            if "postgres" in image or "custom-postgres" in image:
                return True

        return False

    def select_pod_interactive(self, labels: Dict[str, str] = None) -> Optional[str]:
        """
        Permite seleccionar un pod de forma interactiva
        """
        pods = self.find_postgres_pods(labels)

        if not pods:
            print("No se encontraron pods de PostgreSQL")
            return None

        if len(pods) == 1:
            pod_name = pods[0]["name"]
            print(f"Pod de PostgreSQL detectado automáticamente: {pod_name}")
            return pod_name

        print("\nPods de PostgreSQL encontrados:")
        print("-" * 60)

        for i, pod in enumerate(pods, 1):
            status_color = "🟢" if pod["status"] == "Running" else ""
            print(f"  {i}. {pod['name']} [{pod['namespace']}] {status_color}")
            print(f"     Estado: {pod['status']}")
            print(f"     Contenedores: {', '.join(pod['containers'])}")
            if pod["labels"]:
                print(
                    f"     Labels: {', '.join([f'{k}={v}' for k, v in pod['labels'].items()])}"
                )
            print()

        while True:
            try:
                selection = input(
                    "Seleccione el número del pod (0 para cancelar): "
                ).strip()

                if selection == "0":
                    return None

                index = int(selection) - 1
                if 0 <= index < len(pods):
                    return pods[index]["name"]
                else:
                    print("Por favor, ingrese un número válido.")

            except ValueError:
                print("Por favor, ingrese un número válido.")
            except KeyboardInterrupt:
                return None

    def check_pod_status(self, pod_name: str) -> bool:
        """
        Verifica si un pod está ejecutándose y listo
        """
        try:
            cmd = [
                "kubectl",
                "get",
                "pod",
                pod_name,
                "-n",
                self.namespace,
                "-o",
                "json",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode != 0:
                return False

            data = json.loads(result.stdout)
            status = data.get("status", {})

            if status.get("phase") != "Running":
                return False

            container_statuses = status.get("containerStatuses", [])
            for container_status in container_statuses:
                if not container_status.get("ready", False):
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error al verificar estado del pod {pod_name}: {e}")
            return False

    def execute_command(
        self,
        pod_name: str,
        command: List[str],
        container: str = None,
        stdin_data: str = None,
    ) -> subprocess.CompletedProcess:
        """
        Ejecuta un comando en un pod usando kubectl exec
        """
        cmd = ["kubectl", "exec", "-n", self.namespace]

        if container:
            cmd.extend(["-c", container])

        if stdin_data:
            cmd.extend(["-i"])

        cmd.extend([pod_name, "--"] + command)

        kwargs = {"capture_output": True, "text": True, "timeout": 300}

        if stdin_data:
            kwargs["input"] = stdin_data

        return subprocess.run(cmd, **kwargs)

    def get_postgres_container(self, pod_name: str) -> Optional[str]:
        """
        Encuentra el contenedor PostgreSQL en un pod
        Adaptado para la configuración específica del proyecto
        """
        try:
            cmd = [
                "kubectl",
                "get",
                "pod",
                pod_name,
                "-n",
                self.namespace,
                "-o",
                "json",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode != 0:
                return None

            data = json.loads(result.stdout)
            containers = data["spec"].get("containers", [])

            for container in containers:
                name = container.get("name", "").lower()
                image = container.get("image", "").lower()

                if name == "postgres":  # Del StatefulSet
                    return container["name"]

                if "custom-postgres" in image or "postgres" in image:
                    return container["name"]

            if containers:
                return containers[0]["name"]

            return None

        except Exception as e:
            self.logger.error(f"Error al obtener contenedor PostgreSQL: {e}")
            return None

    def copy_file_to_pod(
        self, local_path: Path, pod_name: str, remote_path: str, container: str = None
    ) -> bool:
        """
        Copia un archivo local a un pod
        """
        try:
            cmd = ["kubectl", "cp", "-n", self.namespace]

            if container:
                cmd.extend(["-c", container])

            cmd.extend([str(local_path), f"{pod_name}:{remote_path}"])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            return result.returncode == 0

        except Exception as e:
            self.logger.error(f"Error al copiar archivo al pod: {e}")
            return False

    def copy_file_from_pod(
        self, pod_name: str, remote_path: str, local_path: Path, container: str = None
    ) -> bool:
        """
        Copia un archivo desde un pod al sistema local
        """
        try:
            cmd = ["kubectl", "cp", "-n", self.namespace]

            if container:
                cmd.extend(["-c", container])

            cmd.extend([f"{pod_name}:{remote_path}", str(local_path)])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            return result.returncode == 0

        except Exception as e:
            self.logger.error(f"Error al copiar archivo desde pod: {e}")
            return False

    def _encrypt_backup(self, backup_path):
        """
        Encriptar usando OpenSSL
        """
        password_file = os.getenv(
            "ENCRYPTION_PASSWORD_FILE", "./scripts/secure/backup_key.txt"
        )
        encrypted_path = f"{backup_path}.enc"

        if not os.path.exists(password_file):
            self.logger.error(
                f"No se encontro un archivo de contraseña en {password_file}"
            )
            return None

        comando = [
            "openssl",
            "enc",
            "-aes-256-cbc",
            "-salt",
            "-pbkdf2",
            "-iter",
            "100000",
            "-in",
            backup_path,
            "-out",
            encrypted_path,
            "-pass",
            f"file:{password_file}",
        ]

        try:
            result = subprocess.run(comando, capture_output=True, text=True)
            self.logger.info(f"Backup encriptado exitosamente: {encrypted_path}")
            return encrypted_path
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error al encriptar backup con OpenSSL: {e.stderr}")
        except Exception as e:
            self.logger.error(f"Error inesperado durante la encriptación: {e}")
            return None
