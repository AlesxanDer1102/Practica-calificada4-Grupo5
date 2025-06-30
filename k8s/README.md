# Despliegue Local: PostgreSQL + Aplicación Python en Minikube

Este repositorio contiene todo lo necesario para construir y orquestar **localmente** en Minikube:

- Una base de datos PostgreSQL empaquetada en una imagen Docker propia, con scripts de inicialización.
- Una aplicación Python (backend + orquestador de backups) en su propia imagen Docker.
- Manifiestos Kubernetes (StatefulSet, PVC, Deployments, Services) organizados de forma clara.

---

## Estructura de tu proyecto

```

Practica-calificada4-Grupo5/
├── pos\_db/
│   ├── 01-init.sql
│   └── 02-seed\_data.sql
├── src/                         # Código del backend Python
├── backup\_cli/                  # Código del orquestador de backups
├── app.py
├── backup\_orchestrator.py
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
├── deploy.sh                    # Script para build + apply
└── cleanup.sh                   # Script para borrar recursos

````

---

## Prerrequisitos

- **Minikube** instalado (v1.30+).
- **kubectl** configurado.
- **Docker** local para construir imágenes.

---

## Primeros pasos

1. **Arrancar Minikube**
   ```bash
   minikube start --driver=docker
````

2. **Enviar tu terminal Docker al daemon de Minikube**

   ```bash
   eval $(minikube docker-env)
   ```

---

## Construir imágenes Docker

Desde la raíz del proyecto:

```bash
# 1. Imagen de PostgreSQL con scripts embebidos
docker build -f k8s/postgres/Dockerfile-postgres \
  -t custom-postgres:latest .

# 2. Imagen del backend Python (app + backup orchestrator)
docker build -f Dockerfile-backend \
  -t python-backend:dev .
```

Verifica que ambas imágenes existen:

```bash
docker images | grep -E "custom-postgres|python-backend"
```

---

## Despliegue en Kubernetes

### 1. Desplegar PostgreSQL

```bash
kubectl apply -f k8s/postgres/postgres-secret.yaml
kubectl apply -f k8s/postgres/postgres-service.yaml
kubectl apply -f k8s/postgres/postgres-statefulset.yaml
```

### 2. Desplegar el backend Python

```bash
kubectl apply -f k8s/backend/backend-deployment.yaml
kubectl apply -f k8s/backend/backend-service.yaml
```

---

## Verificaciones

```bash
# Estado general
kubectl get pods,svc,pvc

# Logs de Postgres para confirmar init/seed
kubectl logs statefulset/postgres-0

# Logs del backend
kubectl logs deployment/backend
```

---

## Acceso a la aplicación

```bash
# Exponer puerto 3000 a localhost
kubectl port-forward svc/backend-svc 3000:3000

# Probar endpoint (e.g. /health)
curl http://localhost:3000/health
```

---

## Scripts de conveniencia
# Dar permisos de ejecucion
```bash
chmod +x deploy.sh cleanup.sh
```

# Deploy

```bash
./deploy.sh
```

# Limpieza
```bash
./cleanup.sh
```

---

## 🩺 Solución de problemas

1. **Pods en CrashLoop / ConfigError**

   ```bash
   kubectl describe pod <POD_NAME>
   ```

2. **Reiniciar un Deployment**

   ```bash
   kubectl rollout restart deployment/backend
   ```

3. **Eliminar todo y recomenzar**

   ```bash
   ./cleanup.sh
   ./deploy.sh
   ```

---

## 🔑 Variables de entorno inyectadas al backend

El Deployment Python define:

* `DB_HOST=postgres-0.postgres`
* `DB_PORT=5432`
* `DB_NAME=pc_db`
* `DB_USER=postgres`
* `DB_PASSWORD` (desde `postgres-secret`)

¡Listo! Con esta documentación actualizada tienes un flujo claro para construir y orquestar tu base de datos Postgres y tu aplicación Python con Minikube.
