import json
import logging
import subprocess
from typing import Any, Dict, List, Optional


class DockerHandler:
    """
    Maneja operaciones específicas de Docker para backups de PostgreSQL
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def find_postgres_containers(self, name_filter: str = None) -> List[Dict[str, Any]]:

        try:
            cmd = ["docker", "ps", "--format", "json"]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                self.logger.error(f"Error al obtener contenedores: {result.stderr}")
                return []

            containers = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    container_data = json.loads(line)

                    # Filtrar contenedores que parezcan ser PostgreSQL
                    if self._is_postgres_container(container_data, name_filter):
                        containers.append(
                            {
                                "id": container_data["ID"],
                                "name": container_data["Names"],
                                "image": container_data["Image"],
                                "status": container_data["Status"],
                                "ports": container_data.get("Ports", ""),
                            }
                        )

            return containers

        except Exception as e:
            self.logger.error(f"Error al buscar contenedores de PostgreSQL: {e}")
            return []

    def _is_postgres_container(
        self, container_data: Dict, name_filter: str = None
    ) -> bool:

        name = container_data.get("Names", "").lower()
        image = container_data.get("Image", "").lower()

        if name_filter:
            return name_filter.lower() in name

        postgres_indicators = ["postgres", "postgresql", "pg_", "db"]

        for indicator in postgres_indicators:
            if indicator in name or indicator in image:
                return True

        return False

    def select_container_interactive(self, name_filter: str = None) -> Optional[str]:

        containers = self.find_postgres_containers(name_filter)

        if not containers:
            print("No se encontraron contenedores de PostgreSQL")
            return None

        if len(containers) == 1:
            container_name = containers[0]["name"]
            print(
                f"Contenedor de PostgreSQL detectado automáticamente: {container_name}"
            )
            return container_name

        print("\nContenedores de PostgreSQL encontrados:")
        print("-" * 80)

        for i, container in enumerate(containers, 1):
            status_color = "🟢" if "Up" in container["status"] else ""
            print(f"  {i}. {container['name']} {status_color}")
            print(f"     ID: {container['id'][:12]}")
            print(f"     Imagen: {container['image']}")
            print(f"     Estado: {container['status']}")
            if container["ports"]:
                print(f"     Puertos: {container['ports']}")
            print()

        while True:
            try:
                selection = input(
                    "Seleccione el número del contenedor (0 para cancelar): "
                ).strip()

                if selection == "0":
                    return None

                index = int(selection) - 1
                if 0 <= index < len(containers):
                    return containers[index]["name"]
                else:
                    print("Por favor, ingrese un número válido.")

            except ValueError:
                print("Por favor, ingrese un número válido.")
            except KeyboardInterrupt:
                return None

    def check_container_status(self, container_name: str) -> bool:
        """
        Verifica si un contenedor está ejecutándose
        """
        try:
            result = subprocess.run(
                ["docker", "inspect", container_name],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return False

            data = json.loads(result.stdout)
            if not data:
                return False

            state = data[0].get("State", {})
            return state.get("Running", False)

        except Exception as e:
            self.logger.error(
                f"Error al verificar estado del contenedor {container_name}: {e}"
            )
            return False

    def execute_command(
        self, container_name: str, command: List[str], stdin_data: str = None
    ) -> subprocess.CompletedProcess:
        """
        Ejecuta un comando en un contenedor usando docker exec
        """
        cmd = ["docker", "exec"]

        if stdin_data:
            cmd.append("-i")

        cmd.extend([container_name] + command)

        kwargs = {"capture_output": True, "text": True, "timeout": 300}

        if stdin_data:
            kwargs["input"] = stdin_data

        return subprocess.run(cmd, **kwargs)

    def get_container_info(self, container_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información detallada de un contenedor
        """
        try:
            result = subprocess.run(
                ["docker", "inspect", container_name],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode != 0:
                return None

            data = json.loads(result.stdout)
            if not data:
                return None

            container_info = data[0]

            return {
                "id": container_info["Id"][:12],
                "name": container_info["Name"].lstrip("/"),
                "image": container_info["Config"]["Image"],
                "state": container_info["State"],
                "ports": container_info["NetworkSettings"]["Ports"],
                "env": container_info["Config"]["Env"],
                "mounts": container_info["Mounts"],
            }

        except Exception as e:
            self.logger.error(f"Error al obtener información del contenedor: {e}")
            return None
