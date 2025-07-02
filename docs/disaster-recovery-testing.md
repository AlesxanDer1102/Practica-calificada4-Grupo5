# 🔥 Tests E2E de Recuperación ante Desastres

## 📋 Descripción General

Este módulo implementa tests End-to-End (E2E) completos para validar la capacidad del sistema de backup/restauración para recuperarse de escenarios de desastre catastróficos.

### 🎯 Objetivos

- **Simular pérdidas catastróficas** de datos y volúmenes
- **Validar recuperación completa** desde backups
- **Medir tiempo de recuperación** (RTO - Recovery Time Objective)
- **Verificar integridad** de datos tras recuperación

## 🏗️ Arquitectura de Testing

### Componentes Principales

```
tests/e2e/disaster_recovery/
├── __init__.py                    # Módulo principal
├── disaster_simulator.py         # Clase base abstracta
├── volume_destroyer.py           # Simulador destrucción volúmenes
├── data_corruptor.py             # Simulador corrupción datos
├── recovery_validator.py         # Validador de recuperación
├── rto_monitor.py                # Monitor de RTO
├── rto_analyzer.py               # Análisis avanzado RTO
└── full_recovery_test.py         # Orchestrador completo
```

### Tests Específicos por Entorno

```
tests/e2e/
├── test_docker_disaster_recovery.py      # Tests Docker
└── test_kubernetes_disaster_recovery.py  # Tests Kubernetes
```

## 🔥 Tipos de Desastres Simulados

### 1. Eliminación Completa de Volúmenes

#### Docker
- Detiene contenedor PostgreSQL
- Identifica volúmenes montados
- Simula eliminación de volúmenes de datos
- Registra eventos para auditoría

#### Kubernetes
- Identifica PersistentVolumeClaims del pod
- Elimina pod y PVCs asociados
- Simula pérdida de almacenamiento persistente

```python
from tests.e2e.disaster_recovery import VolumeDestroyer

# Ejemplo de uso
destroyer = VolumeDestroyer("docker")
result = destroyer.simulate_disaster("postgres_container")

# Resultado incluye:
# - success: bool
# - disaster_type: "volume_deletion" | "pvc_deletion"
# - target: nombre del objetivo
# - volumes_destroyed: lista de volúmenes afectados
# - recoverable: True (con backup)
```

### 2. Corrupción de Datos

#### Tipos de Corrupción
- **Table Drop**: Eliminación accidental de tabla crítica
- **Data Scramble**: Corrupción de registros existentes
- **Index Corruption**: Corrupción de índices de base de datos

```python
from tests.e2e.disaster_recovery import DataCorruptor

# Ejemplo de uso
corruptor = DataCorruptor("kubernetes")
result = corruptor.simulate_disaster("postgres-pod")

# Resultado incluye:
# - disaster_type: "table_drop" | "data_scramble" | "index_corruption"
# - affected_tables/indexes: objetos afectados
# - severity: "high" | "medium" | "low"
# - estimated_corrupted_records: número estimado
```

## ⏱️ Medición de RTO (Recovery Time Objective)

### Monitor Básico

```python
from tests.e2e.disaster_recovery import RTOMonitor

# Configurar objetivo RTO
rto_monitor = RTOMonitor(target_rto_seconds=300)  # 5 minutos

# Medir tiempo de recuperación
session_id = rto_monitor.start_recovery_timer("volume_deletion", "target_name")
# ... ejecutar recuperación ...
result = rto_monitor.stop_recovery_timer(session_id)

print(f"Duración: {result['duration']}s")
print(f"RTO cumplido: {result['rto_met']}")
```

### Análisis Avanzado

```python
from tests.e2e.disaster_recovery import RTOAnalyzer

analyzer = RTOAnalyzer()
analysis = analyzer.analyze_rto_performance(rto_monitor)

# Métricas incluidas:
# - Estadísticas descriptivas (media, mediana, percentiles)
# - Categorización de performance (excelente/bueno/aceptable/deficiente)
# - Análisis por tipo de desastre
# - Tendencias temporales
# - Recomendaciones automáticas
```

## 🔄 Flujo Completo de Testing

### Test Workflow Automatizado

```python
from tests.e2e.disaster_recovery import FullRecoveryTest

# Inicializar test completo
recovery_test = FullRecoveryTest("docker")

# Ejecutar workflow completo
result = recovery_test.run_full_disaster_recovery_test("postgres_container")

# El workflow incluye:
# 1. Crear datos iniciales de referencia
# 2. Crear backup de línea base
# 3. Simular desastre aleatorio
# 4. Iniciar monitoreo RTO
# 5. Ejecutar recuperación desde backup
# 6. Validar integridad de datos recuperados
# 7. Generar reporte completo
```

### Resultado del Test

```json
{
  "test_id": "disaster_recovery_1234567890",
  "environment": "docker",
  "target": "postgres_container",
  "test_duration": 125.5,
  "initial_data": {
    "record_count": 1500,
    "tables": ["usuarios", "productos", "pedidos"]
  },
  "backup_result": {
    "success": true,
    "backup_name": "disaster_test_baseline_1234567890"
  },
  "disaster_result": {
    "success": true,
    "disaster_type": "volume_deletion",
    "severity": "high"
  },
  "rto_result": {
    "duration": 95.2,
    "rto_met": true
  },
  "validation_result": {
    "recovery_successful": true,
    "data_integrity": true,
    "service_available": true
  },
  "overall_success": true
}
```

## 🐳 Tests Docker

### Ejecutar Tests

```bash
# Tests específicos Docker
pytest tests/e2e/test_docker_disaster_recovery.py -v

# Test específico
pytest tests/e2e/test_docker_disaster_recovery.py::TestDockerDisasterRecovery::test_docker_volume_destruction_simulation -v

# Tests de benchmark (marcados como lentos)
pytest tests/e2e/test_docker_disaster_recovery.py -m slow -v
```

### Prerrequisitos Docker

- Docker engine corriendo
- Imagen `postgres:15` disponible
- Contenedor de prueba será creado/eliminado automáticamente

### Tests Incluidos

1. **test_docker_volume_destruction_simulation**: Simulación destrucción volúmenes
2. **test_docker_data_corruption_simulation**: Simulación corrupción datos
3. **test_docker_rto_monitoring**: Monitoreo básico RTO
4. **test_docker_full_recovery_workflow**: Workflow completo
5. **test_docker_rto_analysis**: Análisis avanzado RTO
6. **test_docker_multiple_disaster_types**: Múltiples tipos de desastre
7. **test_docker_performance_benchmark**: Benchmark de performance

## ☸️ Tests Kubernetes

### Ejecutar Tests

```bash
# Tests específicos Kubernetes
pytest tests/e2e/test_kubernetes_disaster_recovery.py -v

# Test específico
pytest tests/e2e/test_kubernetes_disaster_recovery.py::TestKubernetesDisasterRecovery::test_kubernetes_pvc_destruction_simulation -v

# Tests de stress
pytest tests/e2e/test_kubernetes_disaster_recovery.py -m slow -v
```

### Prerrequisitos Kubernetes

- `kubectl` instalado y configurado
- Conexión activa a cluster Kubernetes (Minikube/Kind/etc.)
- Permisos para crear/eliminar pods en namespace `default`
- Imagen `postgres:15` disponible en el cluster

### Tests Incluidos

1. **test_kubernetes_pvc_destruction_simulation**: Simulación destrucción PVC
2. **test_kubernetes_data_corruption_simulation**: Simulación corrupción datos
3. **test_kubernetes_rto_monitoring**: Monitoreo RTO específico K8s
4. **test_kubernetes_full_recovery_workflow**: Workflow completo K8s
5. **test_kubernetes_pod_resilience**: Resiliencia específica pods
6. **test_kubernetes_namespace_isolation**: Aislamiento por namespace
7. **test_kubernetes_rto_comparison_with_docker**: Comparación Docker vs K8s
8. **test_kubernetes_cluster_connectivity**: Conectividad básica cluster
9. **test_kubernetes_disaster_recovery_stress**: Test de stress

## 📊 Métricas y Reportes

### Categorías de Performance RTO

- **Excelente**: ≤ 50% del RTO objetivo
- **Bueno**: 50-80% del RTO objetivo  
- **Aceptable**: 80-100% del RTO objetivo
- **Deficiente**: > 100% del RTO objetivo

### Reporte de Ejemplo

```
=== REPORTE DE ANÁLISIS RTO ===

📊 MÉTRICAS GENERALES:
- Total de sesiones: 10
- RTO objetivo: 300s (5.0 min)
- Tasa de cumplimiento: 90.0%

⏱️ ESTADÍSTICAS DE DURACIÓN:
- Promedio: 145.2s
- Mediana: 142.0s
- Mínimo: 89.5s
- Máximo: 287.3s
- P95: 275.1s

📈 CATEGORÍAS DE PERFORMANCE:
- Excelente: 3 (30.0%)
- Bueno: 4 (40.0%)
- Aceptable: 2 (20.0%)
- Deficiente: 1 (10.0%)

🔍 TENDENCIA: IMPROVING
- Cambio: +12.5%

💡 RECOMENDACIONES:
  1. Performance RTO dentro de parámetros aceptables.
  2. Considerar optimización para casos excepcionales.
```

## 🚀 Ejecución Completa

### Script de Ejecución

```bash
#!/bin/bash
# Ejecutar todos los tests de disaster recovery

echo "🔥 Ejecutando Tests E2E de Disaster Recovery"

# Tests Docker
echo "🐳 Tests Docker..."
pytest tests/e2e/test_docker_disaster_recovery.py -v --tb=short

# Tests Kubernetes (si está disponible)
echo "☸️ Tests Kubernetes..."
pytest tests/e2e/test_kubernetes_disaster_recovery.py -v --tb=short

# Tests de benchmark (opcional)
echo "📊 Tests de Benchmark..."
pytest tests/e2e/ -m slow -v --tb=short

echo "✅ Tests completados"
```

### Configuración pytest.ini

```ini
[tool:pytest]
markers =
    slow: tests que tardan más tiempo en ejecutar
    docker: tests específicos para Docker
    kubernetes: tests específicos para Kubernetes
    e2e: tests end-to-end
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

## 🔧 Solución de Problemas

### Docker

**Error**: "Docker no está disponible"
- **Solución**: Verificar que Docker engine esté corriendo: `docker ps`

**Error**: "No se pudo crear contenedor"
- **Solución**: Verificar permisos Docker y que imagen postgres:15 esté disponible

### Kubernetes

**Error**: "kubectl no está disponible"  
- **Solución**: Instalar kubectl y configurar conexión al cluster

**Error**: "No hay conexión a cluster Kubernetes"
- **Solución**: Verificar cluster activo: `kubectl get nodes`

**Error**: "Pod no alcanzó estado Running"
- **Solución**: Verificar recursos del cluster y imagen disponible

### Tests

**Error**: "No hay sesiones RTO para analizar"
- **Solución**: Ejecutar al menos un test de monitoreo RTO antes del análisis

**Error**: Tests fallan por timeout
- **Solución**: Aumentar timeouts en configuración de tests según recursos disponibles

## 📈 Futuras Mejoras

### Funcionalidades Planificadas

1. **Chaos Engineering**: Integración con herramientas como Chaos Monkey
2. **Métricas Avanzadas**: RPO (Recovery Point Objective), MTTR (Mean Time To Recovery)
3. **Tests Multi-AZ**: Simulación fallos de disponibilidad de zona
4. **Automatización CI/CD**: Integración en pipelines de testing
5. **Dashboard Web**: Visualización en tiempo real de métricas RTO
6. **Alertas**: Notificaciones automáticas cuando RTO no se cumple

### Extensiones Posibles

- Soporte para otros motores de BD (MySQL, MongoDB)
- Tests de red (particiones, latencia)
- Simulación de fallos de hardware
- Tests de escalabilidad durante recuperación
- Integración con herramientas de monitoring (Prometheus, Grafana)

## 📚 Referencias

- [Kubernetes Disaster Recovery Best Practices](https://kubernetes.io/docs/concepts/cluster-administration/backup-restore/)
- [Docker Volume Management](https://docs.docker.com/storage/volumes/)
- [PostgreSQL Backup & Recovery](https://www.postgresql.org/docs/current/backup.html)
- [RTO/RPO Concepts](https://en.wikipedia.org/wiki/Disaster_recovery#Recovery_Time_Objective)
- [Chaos Engineering Principles](https://principlesofchaos.org/)

---

**Nota**: Estos tests están diseñados para entornos de desarrollo/testing. **NO ejecutar en producción** sin las debidas precauciones y aprobaciones. 