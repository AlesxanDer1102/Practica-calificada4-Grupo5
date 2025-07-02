"""
Gestor de CronJobs de Kubernetes para programación automática de backups
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from ..utils.colors import print_colored_message


class K8sCronJobManager:
    """
    Gestiona CronJobs de Kubernetes para backups automáticos
    """

    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.cronjob_template = self._get_cronjob_template()

    def create_scheduled_backup(
        self,
        name: str,
        schedule: str,
        pod_selector: str = "app=postgres",
        container: str = "postgres",
        backup_prefix: str = "auto_backup",
        notification_email: str = None,
    ) -> bool:
        """
        Crea un CronJob para backups automáticos en Kubernetes
        """
        try:
            # Generar nombre único para el CronJob
            cronjob_name = f"backup-{name.lower().replace('_', '-')}"

            # Crear ConfigMap con configuración
            if not self._create_backup_configmap(
                cronjob_name, pod_selector, container, backup_prefix, notification_email
            ):
                return False

            # Crear CronJob
            cronjob_manifest = self._generate_cronjob_manifest(
                cronjob_name, schedule, pod_selector
            )

            return self._apply_manifest(cronjob_manifest, "cronjob")

        except Exception as e:
            print_colored_message("ERROR", f"Error creando CronJob: {e}")
            return False

    def _create_backup_configmap(
        self,
        name: str,
        pod_selector: str,
        container: str,
        backup_prefix: str,
        notification_email: str = None,
    ) -> bool:
        """
        Crea ConfigMap con la configuración del backup
        """
        config_data = {
            "pod_selector": pod_selector,
            "container": container,
            "backup_prefix": backup_prefix,
            "namespace": self.namespace,
        }

        if notification_email:
            config_data["notification_email"] = notification_email

        configmap_manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": f"{name}-config", "namespace": self.namespace},
            "data": {"config.json": json.dumps(config_data, indent=2)},
        }

        return self._apply_manifest(configmap_manifest, "configmap")

    def _generate_cronjob_manifest(
        self, name: str, schedule: str, pod_selector: str
    ) -> Dict:
        """
        Genera el manifest del CronJob
        """
        return {
            "apiVersion": "batch/v1",
            "kind": "CronJob",
            "metadata": {"name": name, "namespace": self.namespace},
            "spec": {
                "schedule": schedule,
                "jobTemplate": {
                    "spec": {
                        "template": {
                            "spec": {
                                "restartPolicy": "OnFailure",
                                "serviceAccountName": "backup-service-account",
                                "containers": [
                                    {
                                        "name": "backup-runner",
                                        "image": "python:3.10-slim",
                                        "command": ["/bin/bash"],
                                        "args": ["-c", self._get_backup_script()],
                                        "env": [
                                            {
                                                "name": "NAMESPACE",
                                                "value": self.namespace,
                                            },
                                            {
                                                "name": "POD_SELECTOR",
                                                "value": pod_selector,
                                            },
                                        ],
                                        "volumeMounts": [
                                            {
                                                "name": "config",
                                                "mountPath": "/config",
                                            },
                                            {
                                                "name": "backup-storage",
                                                "mountPath": "/backups",
                                            },
                                        ],
                                    }
                                ],
                                "volumes": [
                                    {
                                        "name": "config",
                                        "configMap": {"name": f"{name}-config"},
                                    },
                                    {
                                        "name": "backup-storage",
                                        "persistentVolumeClaim": {"claimName": "backup-pvc"},
                                    },
                                ],
                            }
                        }
                    }
                },
            },
        }

    def _get_backup_script(self) -> str:
        """
        Genera el script de backup que se ejecutará en el CronJob
        """
        return """
# Instalar kubectl en el contenedor
apt-get update && apt-get install -y curl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && mv kubectl /usr/local/bin/

# Cargar configuración
CONFIG=$(cat /config/config.json)
POD_SELECTOR=$(echo $CONFIG | python3 -c "import sys, json; print(json.load(sys.stdin)['pod_selector'])")
CONTAINER=$(echo $CONFIG | python3 -c "import sys, json; print(json.load(sys.stdin)['container'])")
BACKUP_PREFIX=$(echo $CONFIG | python3 -c "import sys, json; print(json.load(sys.stdin)['backup_prefix'])")

# Encontrar pod PostgreSQL
POD_NAME=$(kubectl get pods -n $NAMESPACE -l $POD_SELECTOR -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD_NAME" ]; then
    echo "ERROR: No se encontró pod con selector $POD_SELECTOR"
    exit 1
fi

# Crear backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="${BACKUP_PREFIX}_${TIMESTAMP}.sql"

echo "Creando backup: $BACKUP_NAME desde pod: $POD_NAME"

# Ejecutar pg_dump
kubectl exec -n $NAMESPACE -c $CONTAINER $POD_NAME -- pg_dump \\
    -U postgres \\
    -d pc_db \\
    --clean --create --verbose > /backups/$BACKUP_NAME

if [ $? -eq 0 ]; then
    echo "Backup exitoso: $BACKUP_NAME"
    # Aquí se podría agregar notificación de éxito
else
    echo "ERROR: Falló el backup"
    exit 1
fi
        """.strip()

    def _apply_manifest(self, manifest: Dict, resource_type: str) -> bool:
        """
        Aplica un manifest de Kubernetes usando kubectl
        """
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                if resource_type == "configmap" or resource_type == "cronjob":
                    # Convertir dict a YAML usando kubectl
                    import yaml

                    yaml.dump(manifest, f, default_flow_style=False)
                else:
                    json.dump(manifest, f, indent=2)

                temp_file = f.name

            # Aplicar usando kubectl
            result = subprocess.run(
                ["kubectl", "apply", "-f", temp_file, "-n", self.namespace],
                capture_output=True,
                text=True,
                timeout=30,
            )

            Path(temp_file).unlink()

            if result.returncode == 0:
                print_colored_message(
                    "SUCCESS", f"{resource_type.title()} aplicado exitosamente"
                )
                return True
            else:
                print_colored_message(
                    "ERROR", f"Error aplicando {resource_type}: {result.stderr}"
                )
                return False

        except ImportError:
            print_colored_message("ERROR", "PyYAML requerido para CronJobs de Kubernetes")
            return False
        except Exception as e:
            print_colored_message("ERROR", f"Error aplicando manifest: {e}")
            return False

    def list_scheduled_backups(self) -> List[Dict]:
        """
        Lista los CronJobs de backup activos
        """
        try:
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "cronjobs",
                    "-n",
                    self.namespace,
                    "-l",
                    "app=backup-orchestrator",
                    "-o",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )

            if result.returncode != 0:
                print_colored_message("ERROR", f"Error listando CronJobs: {result.stderr}")
                return []

            data = json.loads(result.stdout)
            cronjobs = []

            for item in data.get("items", []):
                cronjobs.append(
                    {
                        "name": item["metadata"]["name"],
                        "schedule": item["spec"]["schedule"],
                        "active": len(item.get("status", {}).get("active", [])),
                        "last_schedule": item.get("status", {}).get("lastScheduleTime"),
                    }
                )

            return cronjobs

        except Exception as e:
            print_colored_message("ERROR", f"Error listando CronJobs: {e}")
            return []

    def delete_scheduled_backup(self, name: str) -> bool:
        """
        Elimina un CronJob de backup programado
        """
        try:
            # Eliminar CronJob
            result = subprocess.run(
                ["kubectl", "delete", "cronjob", name, "-n", self.namespace],
                capture_output=True,
                text=True,
                timeout=20,
            )

            # Eliminar ConfigMap asociado
            subprocess.run(
                ["kubectl", "delete", "configmap", f"{name}-config", "-n", self.namespace],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                print_colored_message("SUCCESS", f"CronJob {name} eliminado")
                return True
            else:
                print_colored_message("ERROR", f"Error eliminando CronJob: {result.stderr}")
                return False

        except Exception as e:
            print_colored_message("ERROR", f"Error eliminando CronJob: {e}")
            return False

    def _get_cronjob_template(self) -> str:
        """
        Retorna el template base para CronJobs
        """
        return "backup-cronjob-template"

    @staticmethod
    def ensure_rbac_permissions() -> bool:
        """
        Verifica/crea los permisos RBAC necesarios para CronJobs
        """
        try:
            # Verificar si existe ServiceAccount
            result = subprocess.run(
                ["kubectl", "get", "serviceaccount", "backup-service-account"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                print_colored_message(
                    "WARNING", "ServiceAccount backup-service-account no encontrado"
                )
                print_colored_message(
                    "INFO", "Crear manualmente: kubectl create serviceaccount backup-service-account"
                )
                return False

            return True

        except Exception as e:
            print_colored_message("ERROR", f"Error verificando RBAC: {e}")
            return False 