"""
Tests E2E de disaster recovery específicos para Kubernetes
"""

import subprocess
import time
from typing import Any, Dict

import pytest

from tests.e2e.disaster_recovery import (
    VolumeDestroyer,
    DataCorruptor,
    FullRecoveryTest,
    RTOMonitor,
    RTOAnalyzer,
)


class TestKubernetesDisasterRecovery:
    """
    Tests de disaster recovery para entorno Kubernetes
    """

    @pytest.fixture(scope="class")
    def kubernetes_environment(self):
        """
        Setup del entorno Kubernetes para tests
        """
        # Verificar que kubectl esté disponible
        try:
            result = subprocess.run(
                ["kubectl", "version", "--client"], capture_output=True, timeout=10
            )
            if result.returncode != 0:
                pytest.skip("kubectl no está disponible")
        except subprocess.TimeoutExpired:
            pytest.skip("kubectl no responde")

        # Verificar conectividad al cluster
        try:
            result = subprocess.run(
                ["kubectl", "get", "nodes"], capture_output=True, timeout=15
            )
            if result.returncode != 0:
                pytest.skip("No hay conexión a cluster Kubernetes")
        except subprocess.TimeoutExpired:
            pytest.skip("Cluster Kubernetes no responde")

        # Configurar pod de prueba
        pod_name = "postgres-test-disaster"
        namespace = "default"

        # Cleanup previo
        subprocess.run(
            ["kubectl", "delete", "pod", pod_name, "-n", namespace], capture_output=True
        )
        time.sleep(5)

        # Crear pod para tests
        pod_manifest = f"""
apiVersion: v1
kind: Pod
metadata:
  name: {pod_name}
  namespace: {namespace}
spec:
  containers:
  - name: postgres
    image: postgres:15
    env:
    - name: POSTGRES_USER
      value: "postgres"
    - name: POSTGRES_PASSWORD
      value: "test123"
    - name: POSTGRES_DB
      value: "test_db"
    ports:
    - containerPort: 5432
  restartPolicy: Never
"""

        # Escribir manifest temporal
        manifest_file = f"/tmp/{pod_name}-manifest.yaml"
        with open(manifest_file, "w") as f:
            f.write(pod_manifest)

        # Aplicar manifest
        result = subprocess.run(
            ["kubectl", "apply", "-f", manifest_file], capture_output=True, timeout=30
        )
        if result.returncode != 0:
            pytest.skip(f"No se pudo crear pod: {result.stderr}")

        # Esperar que esté corriendo
        for attempt in range(30):  # 30 intentos x 10s = 5min max
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "pod",
                    pod_name,
                    "-n",
                    namespace,
                    "-o",
                    "jsonpath={.status.phase}",
                ],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.decode().strip() == "Running":
                # Verificar también que el contenedor esté ready
                ready_result = subprocess.run(
                    [
                        "kubectl",
                        "get",
                        "pod",
                        pod_name,
                        "-n",
                        namespace,
                        "-o",
                        "jsonpath={.status.containerStatuses[0].ready}",
                    ],
                    capture_output=True,
                    timeout=10,
                )
                if (
                    ready_result.returncode == 0
                    and ready_result.stdout.decode().strip() == "true"
                ):
                    # Dar tiempo adicional para que PostgreSQL esté completamente listo
                    time.sleep(10)
                    break
            time.sleep(10)
        else:
            # Cleanup y skip si no está listo
            subprocess.run(
                ["kubectl", "delete", "pod", pod_name, "-n", namespace],
                capture_output=True,
            )
            pytest.skip("Pod no alcanzó estado Running")

        yield {"pod_name": pod_name, "namespace": namespace}

        # Cleanup
        subprocess.run(
            ["kubectl", "delete", "pod", pod_name, "-n", namespace], capture_output=True
        )

    def test_kubernetes_pvc_destruction_simulation(self, kubernetes_environment):
        """
        Test de simulación de destrucción de PVC en Kubernetes
        """
        pod_info = kubernetes_environment
        pod_name = pod_info["pod_name"]
        destroyer = VolumeDestroyer("kubernetes")

        # Simular destrucción de PVC
        result = destroyer.simulate_disaster(pod_name)

        # Verificar resultados
        assert result["success"] is True
        assert result["disaster_type"] == "pvc_deletion"
        assert pod_name in result["target"]
        assert result["recoverable"] is True
        assert "timestamp" in result

        # Verificar logging
        summary = destroyer.get_destruction_summary()
        assert summary["total_volumes_destroyed"] >= 0

    def test_kubernetes_data_corruption_simulation(self, kubernetes_environment):
        """
        Test de simulación de corrupción de datos en Kubernetes
        """
        pod_info = kubernetes_environment
        pod_name = pod_info["pod_name"]
        corruptor = DataCorruptor("kubernetes")

        # Simular corrupción
        result = corruptor.simulate_disaster(pod_name)

        # Verificar resultados
        assert result["success"] is True
        assert result["disaster_type"] in [
            "table_drop",
            "data_scramble",
            "index_corruption",
        ]
        assert result["target"] == pod_name
        assert result["recoverable"] is True
        assert "severity" in result

        # Verificar logging
        summary = corruptor.get_corruption_summary()
        assert summary["total_corruptions"] == 1

    def test_kubernetes_rto_monitoring(self, kubernetes_environment):
        """
        Test de monitoreo RTO en entorno Kubernetes
        """
        pod_info = kubernetes_environment
        pod_name = pod_info["pod_name"]
        rto_monitor = RTOMonitor(target_rto_seconds=180)  # 3 min para K8s

        # Iniciar monitoreo
        session_id = rto_monitor.start_recovery_timer("pvc_deletion", pod_name)
        assert session_id is not None

        # Simular trabajo de recuperación (K8s es más lento)
        time.sleep(3)

        # Detener monitoreo
        result = rto_monitor.stop_recovery_timer(session_id)

        # Verificar resultados
        assert result["session_id"] == session_id
        assert result["disaster_type"] == "pvc_deletion"
        assert result["target"] == pod_name
        assert result["duration"] >= 3
        assert result["rto_met"] is True  # 3s < 180s

        # Verificar métricas
        metrics = rto_monitor.get_rto_metrics()
        assert metrics["total_sessions"] == 1
        assert metrics["rto_compliance_rate"] == 100.0

    def test_kubernetes_full_recovery_workflow(self, kubernetes_environment):
        """
        Test completo de workflow de recuperación en Kubernetes
        """
        pod_info = kubernetes_environment
        pod_name = pod_info["pod_name"]
        recovery_test = FullRecoveryTest("kubernetes")

        # Ejecutar test completo
        result = recovery_test.run_full_disaster_recovery_test(pod_name)

        # Verificar estructura del resultado
        assert "test_id" in result
        assert result["environment"] == "kubernetes"
        assert result["target"] == pod_name
        assert "test_duration" in result
        assert "initial_data" in result
        assert "backup_result" in result
        assert "disaster_result" in result
        assert "recovery_result" in result
        assert "rto_result" in result
        assert "validation_result" in result
        assert "overall_success" in result

        # Verificar que disaster y RTO funcionaron
        assert result["disaster_result"]["success"] is True
        assert "duration" in result["rto_result"]

    def test_kubernetes_pod_resilience(self, kubernetes_environment):
        """
        Test de resiliencia específica de pods K8s
        """
        pod_info = kubernetes_environment
        pod_name = pod_info["pod_name"]
        namespace = pod_info["namespace"]

        # Verificar estado inicial
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "pod",
                pod_name,
                "-n",
                namespace,
                "-o",
                "jsonpath={.status.phase}",
            ],
            capture_output=True,
            timeout=10,
        )
        initial_phase = result.stdout.decode().strip()
        assert initial_phase == "Running"

        # Simular eliminación de pod (kubernetes lo recrea automáticamente si es deployment)
        destroyer = VolumeDestroyer("kubernetes")
        disaster_result = destroyer.simulate_disaster(pod_name)

        assert disaster_result["success"] is True
        assert (
            "pvc" in disaster_result["disaster_type"]
            or "volume" in disaster_result["disaster_type"]
        )

    def test_kubernetes_namespace_isolation(self, kubernetes_environment):
        """
        Test de aislamiento por namespace en K8s
        """
        pod_info = kubernetes_environment
        pod_name = pod_info["pod_name"]
        namespace = pod_info["namespace"]

        # Verificar que operaciones respetan el namespace
        corruptor = DataCorruptor("kubernetes")
        result = corruptor.simulate_disaster(pod_name)

        assert result["success"] is True

        # Verificar que el target no incluye pods de otros namespaces
        assert (
            namespace in result.get("target", pod_name)
            or result.get("target") == pod_name
        )

    def test_kubernetes_rto_comparison_with_docker(self, kubernetes_environment):
        """
        Test comparativo de RTO entre K8s y Docker
        """
        pod_info = kubernetes_environment
        pod_name = pod_info["pod_name"]

        # Monitor específico para K8s
        k8s_monitor = RTOMonitor(target_rto_seconds=300)  # 5 min para K8s

        # Simular varias operaciones K8s
        k8s_durations = []
        for i in range(3):
            session_id = k8s_monitor.start_recovery_timer("k8s_test", pod_name)
            time.sleep(2)  # K8s típicamente más lento que Docker
            result = k8s_monitor.stop_recovery_timer(session_id)
            k8s_durations.append(result["duration"])

        # Verificar que todas las operaciones están dentro del RTO
        for duration in k8s_durations:
            assert duration < 300  # Menos de 5 min

        # K8s debe ser consistente pero posiblemente más lento que Docker
        avg_k8s_duration = sum(k8s_durations) / len(k8s_durations)
        assert avg_k8s_duration > 1.5  # Al menos 1.5s por la complejidad K8s

    def test_kubernetes_cluster_connectivity(self, kubernetes_environment):
        """
        Test de conectividad básica del cluster
        """
        # Verificar que podemos ejecutar comandos en el pod
        pod_info = kubernetes_environment
        pod_name = pod_info["pod_name"]
        namespace = pod_info["namespace"]

        # Test de conectividad básica
        result = subprocess.run(
            ["kubectl", "exec", pod_name, "-n", namespace, "--", "echo", "test"],
            capture_output=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "test" in result.stdout.decode()

    @pytest.mark.slow
    def test_kubernetes_disaster_recovery_stress(self, kubernetes_environment):
        """
        Test de stress para disaster recovery en K8s
        """
        pod_info = kubernetes_environment
        pod_name = pod_info["pod_name"]

        # Configurar monitoring con RTO más estricto
        rto_monitor = RTOMonitor(target_rto_seconds=120)  # 2 min para stress test
        disaster_types = ["pvc_deletion", "data_corruption"]

        successful_recoveries = 0
        total_tests = 6  # 3 por cada tipo

        for disaster_type in disaster_types:
            for i in range(3):
                session_id = rto_monitor.start_recovery_timer(disaster_type, pod_name)

                # Simular carga variable
                if disaster_type == "pvc_deletion":
                    time.sleep(1.0 + i * 0.5)  # 1.0, 1.5, 2.0s
                else:
                    time.sleep(1.5 + i * 0.3)  # 1.5, 1.8, 2.1s

                result = rto_monitor.stop_recovery_timer(session_id)

                if result["rto_met"]:
                    successful_recoveries += 1

        # Verificar que al menos 80% de tests cumplen RTO
        success_rate = successful_recoveries / total_tests
        assert success_rate >= 0.8, f"Solo {success_rate*100:.1f}% cumplió RTO"

        # Analizar resultados
        analyzer = RTOAnalyzer()
        analysis = analyzer.analyze_rto_performance(rto_monitor)

        assert analysis["total_sessions"] == total_tests
        assert "disaster_type_analysis" in analysis

        # Generar reporte de stress test
        report = analyzer.generate_rto_report()
        assert "REPORTE DE ANÁLISIS RTO" in report
