# Despliegue Local: PostgreSQL + Aplicación Python en Minikube

Este repositorio contiene todo lo necesario para construir y orquestar **localmente** en Minikube:

- Una base de datos PostgreSQL empaquetada en una imagen Docker propia, con scripts de inicialización.
- Una aplicación Python (backend + **orquestador de backups unificado**) en su propia imagen Docker.
- Manifiestos Kubernetes (StatefulSet, PVC, Deployments, Services) organizados de forma clara.
- **Sistema de backup/restore que detecta automáticamente Docker vs Kubernetes**.

---

## Estructura del proyecto

```
Practica-calificada4-Grupo5/
├── pos_db/
│   ├── init.sql
│   └── seed_data.sql
├── src/                         # Código del backend Python
├── backup_cli/                  # Código del orquestador de backups UNIFICADO
│   ├── cli/                     # Parser de línea de comandos
│   ├── utils/                   # Utilidades (colores, progreso, validación)
│   ├── environment/             # Detección automática de entorno
│   └── handlers/                # Handlers para Docker y Kubernetes
├── app.py
├── backup_orchestrator.py       # ⭐ ORQUESTADOR UNIFICADO (detecta entorno)
├── requirements.txt
├── Dockerfile-backend           # Imagen de la app Python
├── k8s/
│   ├── postgres/
│   │   ├── Dockerfile-postgres
│   │   ├── postgres-secret.yaml
│   │   ├── postgres-service.yaml
│   │   └── postgres-statefulset.yaml
│   └── backend/
│       ├── backend-deployment.yaml
│       └── backend-service.yaml
├── check_database.sh            # Verificar estado de la base de datos
├── backup_dayly.sh              # Crea un backup con timestamp
├── deploy.sh                    # Script para build + apply
├── cleanup.sh                   # Script para borrar recursos
└── backups/                     # Directorio de backups (auto-creado)
```

---

## Prerrequisitos

- **Minikube** instalado (v1.30+).
- **kubectl** configurado.
- **Docker** local para construir imágenes.
- **Python 3.10+** para el orquestador de backups.

---

## Despliegue Rápido

### 1. Desplegar toda la infraestructura
```bash
# Dar permisos de ejecución
chmod +x k8s/deploy.sh k8s/cleanup.sh

# Deploy completo
k8s/deploy.sh
```

### 2. Verificar despliegue
```bash
# Estado general
kubectl get pods,svc,pvc

# Debería mostrar:
# NAME             READY   STATUS    RESTARTS   AGE
# pod/backend-xxx  1/1     Running   0          2m
# pod/postgres-0   1/1     Running   0          2m

# Logs de Postgres para confirmar init/seed
kubectl logs postgres-0

# Logs del backend
kubectl logs deployment/backend
```

### 3. Acceso a la aplicación
```bash
# Exponer puerto 3000 a localhost
kubectl port-forward svc/backend-svc 3000:3000

# Probar endpoint (e.g. /health)
curl http://localhost:3000/health
```

---

## Sistema de Backup Unificado

### Nueva Funcionalidad: Detección Automática de Entorno

El orquestador de backup ahora **detecta automáticamente** si estás en:
- **Docker** (contenedores locales)
- **Kubernetes** (pods en Minikube)

### Uso Básico (Recomendado)

```bash
# Detección automática - encuentra postgres-0 automáticamente
python3 backup_orchestrator.py

# Backup con nombre personalizado
python3 backup_orchestrator.py --name mi_backup_$(date +%Y%m%d)

# Listar backups existentes
python3 backup_orchestrator.py --list

# Restaurar (selección interactiva)
python3 backup_orchestrator.py --restore
```

### Comandos Específicos de Kubernetes

```bash
# Forzar uso de Kubernetes
python3 backup_orchestrator.py --force-kubernetes

# Pod específico
python3 backup_orchestrator.py --pod postgres-0

# Con namespace (si no es default)
python3 backup_orchestrator.py --pod postgres-0 --namespace production

# Buscar por labels
python3 backup_orchestrator.py --labels app=postgres

# Contenedor específico en pod
python3 backup_orchestrator.py --pod postgres-0 --k8s-container postgres
```

### Comandos Específicos de Docker

```bash
# Forzar uso de Docker
python3 backup_orchestrator.py --force-docker

# Contenedor específico
python3 backup_orchestrator.py --container mi_postgres_container
```

### Restauración

```bash
# Restauración interactiva (recomendado)
python3 backup_orchestrator.py --restore

# Restaurar archivo específico
python3 backup_orchestrator.py --restore --restore-file backups/backup_20241230.sql

# Restaurar en pod específico
python3 backup_orchestrator.py --restore --pod postgres-0
```

### Opciones Avanzadas

```bash
# Backup silencioso (para scripts/cron)
python3 backup_orchestrator.py --quiet --name automated_backup

# Sobrescribir backup existente
python3 backup_orchestrator.py --name important_backup --force

# Directorio personalizado
python3 backup_orchestrator.py --dir /ruta/custom/backups

# Modo verbose para debugging
python3 backup_orchestrator.py --verbose

# Sin colores (para logs)
python3 backup_orchestrator.py --no-color
```

---


##  Build Manual

Si prefieres buildear paso a paso:

### 1. Arrancar Minikube
```bash
minikube start --driver=docker
eval $(minikube docker-env)
```

### 2. Construir imágenes Docker
```bash
# Imagen de PostgreSQL con scripts embebidos
docker build -f k8s/postgres/Dockerfile -t custom-postgres:latest .

# Imagen del backend Python
docker build -f k8s/backend/Dockerfile -t miapp:dev .

# Verificar imágenes
docker images | grep -E "miapp|custom-postgres"
```

### 3. Desplegar en Kubernetes

```bash
# PostgreSQL
kubectl apply -f k8s/postgres/
# Backend Python
kubectl apply -f k8s/backend/
```

---

## Solución de Problemas

### Problemas con Backups
```bash
# Verificar que el orquestrador detecta el entorno
python3 backup_orchestrator.py --verbose

# Ver logs del orquestrador
tail -f backups/backup_orchestrator.log

# Probar conexión manual
kubectl exec -it postgres-0 -- psql -U postgres -d pc_db -c "SELECT version();"

# Forzar entorno específico
python3 backup_orchestrator.py --force-kubernetes --pod postgres-0
```

### Problemas de Conectividad
```bash
# Verificar servicios
kubectl get svc

# Verificar secrets
kubectl get secret postgres-secret -o yaml

# Port forward para debug
kubectl port-forward pod/postgres-0 5432:5432
```

### Reiniciar Todo
```bash
# Limpieza completa
k8s/cleanup.sh

# Redespliegue
k8s/deploy.sh

# Verificar
kubectl get pods
python3 backup_orchestrator.py --list
```

---

## Variables de Entorno

El Deployment Python define:
- `DB_HOST=postgres-0.postgres`
- `DB_PORT=5432`
- `DB_NAME=pc_db`
- `DB_USER=postgres`
- `DB_PASSWORD` (desde `postgres-secret`)

El orquestador de backup usa automáticamente:
- **Database**: `pc_db`
- **Usuario**: `postgres`
- **Password**: `12345` (coincide con el secret)
- **Pod objetivo**: `postgres-0` (detectado por label `app=postgres`)

---

## Monitoreo y Mantenimiento

### Verificar Estado del Sistema
```bash
# Estado general
kubectl get all

# Uso de recursos
kubectl top pods

# Persistencia de datos
kubectl get pvc

# Verificar backups
ls -la backups/
python3 backup_orchestrator.py --list
```

### Automatización con Cron
```bash
# Editar crontab
crontab -e

# Backup diario a las 2 AM
0 2 * * * cd /ruta/a/tu/proyecto && ./backup_daily.sh >> /var/log/postgres_backup.log 2>&1

# Verificación cada hora durante horario laboral
0 9-17 * * 1-5 cd /ruta/a/tu/proyecto && kubectl get pod postgres-0 || echo "PostgreSQL down" | mail admin@empresa.com
```

### Scripts de Monitoreo
```bash
# Verificar salud del cluster
kubectl get nodes
kubectl get pods --all-namespaces

# Verificar logs de sistema
kubectl logs -n kube-system -l component=kube-apiserver

# Verificar espacio en disco
kubectl exec postgres-0 -- df -h
```

---

## Procedimientos de Emergencia

### Backup de Emergencia
```bash
# Crear backup inmediato antes de mantenimiento
python3 backup_orchestrator.py --name "emergency_$(date +%Y%m%d_%H%M%S)" --force

# Verificar integridad
python3 backup_orchestrator.py --list
```

### Recuperación de Desastres
```bash
# 1. Verificar estado
kubectl get pods

# 2. Si PostgreSQL está corrupto, recrear
kubectl delete statefulset postgres
kubectl delete pvc data-postgres-0

# 3. Redesplegar
kubectl apply -f k8s/postgres/

# 4. Esperar que esté listo
kubectl wait --for=condition=Ready pod/postgres-0 --timeout=300s

# 5. Restaurar desde backup más reciente
python3 backup_orchestrator.py --restore
```
