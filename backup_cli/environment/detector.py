import subprocess
import logging
import os
from enum import Enum
from typing import Optional, Dict, Any


class Environment(Enum):
    """Tipos de entorno soportados"""

    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    UNKNOWN = "unknown"


class EnvironmentDetector:
    """
    Detecta automáticamente el entorno de ejecución
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def detect_environment(self) -> Environment:
        """
        Detecta automáticamente el entorno basado en herramientas disponibles
        y variables de entorno
        """
        # Primero verificar si kubectl está disponible y funcionando
        if self._is_kubectl_working():
            self.logger.debug("kubectl funcionando - detectando Kubernetes")
            return Environment.KUBERNETES

        # Verificar si hay variables de Kubernetes
        if self._is_kubernetes_environment():
            return Environment.KUBERNETES

        # Luego verificar si Docker está disponible
        if self._is_docker_available():
            return Environment.DOCKER

        return Environment.UNKNOWN

    def _is_kubectl_working(self) -> bool:
        """
        Verifica si kubectl está disponible y puede conectarse al cluster
        """
        try:
            result = subprocess.run(
                ["kubectl", "cluster-info", "--request-timeout=5s"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and "running at" in result.stdout:
                self.logger.debug("kubectl cluster-info exitoso")
                return True

            result = subprocess.run(
                ["kubectl", "get", "pods", "--request-timeout=5s"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.logger.debug("kubectl get pods exitoso")
                return True

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.logger.debug(f"kubectl no disponible: {e}")

        return False

    def _is_kubernetes_environment(self) -> bool:
        """
        Verifica si estamos en un entorno Kubernetes
        """

        k8s_env_vars = [
            "KUBERNETES_SERVICE_HOST",
            "KUBERNETES_SERVICE_PORT",
            "KUBECTL_CONTEXT",
        ]

        for var in k8s_env_vars:
            if os.getenv(var):
                self.logger.debug(f"Variable de entorno Kubernetes detectada: {var}")
                return True

        if self._is_kubectl_available():
            return True

        return False

    def _is_kubectl_available(self) -> bool:
        """Verifica si kubectl está disponible y funcional"""
        try:
            result = subprocess.run(
                ["kubectl", "version", "--client", "--short"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return False

            test_commands = [
                ["kubectl", "get", "namespaces", "--request-timeout=5s"],
                ["kubectl", "get", "pods", "--request-timeout=5s"],
                ["kubectl", "cluster-info", "--request-timeout=5s"],
            ]

            for cmd in test_commands:
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        self.logger.debug(f"kubectl comando exitoso: {' '.join(cmd)}")
                        return True
                except subprocess.TimeoutExpired:
                    continue

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return False

    def _is_docker_available(self) -> bool:
        """
        Verifica si Docker está disponible y funcional
        """
        try:
            result = subprocess.run(
                ["docker", "version", "--format", "{{.Client.Version}}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return False

            result = subprocess.run(
                ["docker", "info"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                return True

            if "Cannot connect to the Docker daemon" in result.stderr:
                self.logger.debug("Docker comando disponible pero daemon no accesible")
                return not self._is_kubectl_working()

            return False

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return False

    def get_environment_info(self) -> Dict[str, Any]:
        """
        Obtiene información detallada del entorno
        """
        env = self.detect_environment()
        info = {
            "environment": env.value,
            "docker_available": self._is_docker_available(),
            "kubectl_available": self._is_kubectl_available(),
            "kubernetes_vars": self._get_kubernetes_vars(),
        }

        if env == Environment.KUBERNETES:
            info.update(self._get_kubernetes_info())
        elif env == Environment.DOCKER:
            info.update(self._get_docker_info())

        return info

    def _is_kubectl_available(self) -> bool:
        """Verifica si kubectl está disponible y funcional"""
        try:
            result = subprocess.run(
                ["kubectl", "version", "--client", "--short"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return False

            result = subprocess.run(
                ["kubectl", "get", "namespaces"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.logger.debug("kubectl disponible y conectado")
                return True

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return False

    def _get_kubernetes_info(self) -> Dict[str, Any]:
        """Obtiene información específica de Kubernetes"""
        info = {}
        try:
            result = subprocess.run(
                ["kubectl", "config", "current-context"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                info["current_context"] = result.stdout.strip()

            result = subprocess.run(
                ["kubectl", "cluster-info"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                info["cluster_info"] = result.stdout.strip()

        except:
            pass

        return info

    def _get_kubernetes_vars(self) -> Dict[str, str]:
        """Obtiene variables de entorno relacionadas con Kubernetes"""
        k8s_vars = {}
        for key, value in os.environ.items():
            if "KUBERNETES" in key or "KUBECTL" in key:
                k8s_vars[key] = value
        return k8s_vars

    def _get_kubernetes_info(self) -> Dict[str, Any]:
        """Obtiene información específica de Kubernetes"""
        info = {}
        try:
            result = subprocess.run(
                ["kubectl", "config", "current-context"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                info["current_context"] = result.stdout.strip()
        except:
            pass

        return info

    def _get_docker_info(self) -> Dict[str, Any]:
        """Obtiene información específica de Docker"""
        info = {}
        try:
            result = subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                info["docker_version"] = result.stdout.strip()
        except:
            pass

        return info
