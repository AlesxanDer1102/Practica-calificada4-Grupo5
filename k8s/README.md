# PostgreSQL + Aplicación Python en Kubernetes

Este directorio contiene todos los archivos YAML necesarios para desplegar una base de datos PostgreSQL junto con una aplicación Python en Kubernetes, organizados por tipo de servicio.

## Estructura del Directorio

```
k8s/
├── postgres/                 # Recursos relacionados con PostgreSQL
│   ├── secret.yaml           # Credenciales de la base de datos
│   ├── configmap.yaml        # Scripts de inicialización SQL
│   ├── pvc.yaml              # Almacenamiento persistente
│   ├── deployment.yaml       # Configuración del pod PostgreSQL
│   └── service.yaml          # Servicio de PostgreSQL
├── python/                   # Recursos de la aplicación Python
│   └── deployment.yaml       # Pod de la aplicación Python
├── deploy.sh                 # Desplegar todo
├── cleanup.sh                # Eliminar todos los recursos
└── README.md                 # Este archivo
```

## Antes del Despliegue

1. **Verificar que minikube está ejecutándose**:

   ```bash
   # Ejecutamos primeramente
   minikube start

   # Verificamos el estado actual
   minikube status

   # En caso de error podemos detenerlo y volverlo a iniciar
   minikube stop
   ```

2. **Construir y preparar la imagen Docker de Python**:

   ```bash
   # Configurar Docker para minikube
   eval $(minikube docker-env)

   # Construir imagen localmente de la bd
   docker build -f k8s/postgres/Dockerfile-postgres -t custom-postgres:latest .

   # Construimos la imagen localmente del backend en pthon

   docker build -f Dockerfile-backend -t miapp:latest .

   # Verificar imagenes
   docker images | grep -E "custom-postgres|miapp"
   ```

3. **Verificar configuración del deployment**:
   El archivo `backend/deployment.yaml` debe tener:

```yaml
yamlcontainers:
  - name: backend
    image: miapp:latest
    imagePullPolicy: Never
```

**Nota importante**: La línea `imagePullPolicy: Never` es esencial para evitar que Kubernetes trate de descargar la imagen desde un registro remoto.

## Instrucciones de despliegue

Podemos desplegar todo automáticamente usando el script `deploy.sh`:

```bash
chmod +x ./deploy.sh
./deploy.sh
```

Para eliminar lo creado podemos igualmente usar el script `cleanup.sh`:

```bash
chmod +x ./cleanup.sh
./cleanup.sh
```

## Monitoreo y Solución de Problemas

### Verificar Estado

```bash
# Todos los pods
kubectl get pods

# Todos los servicios
kubectl get services

# Todos los PVCs
kubectl get pvc

# Revisa logs de Postgres para confirmar init/seed
kubectl logs statefulset/postgres-0

# Revisa logs de tu backend
kubectl logs deployment/backend
```

### Ver Registros

```bash
# Logs de PostgreSQL (StatefulSet)
kubectl logs statefulset/postgres-0

# Logs del backend Python (Deployment)
kubectl logs deployment/backend

# Seguir los logs en tiempo real del backend
kubectl logs -f deployment/backend
```

### Acceso a la Base de Datos

```bash
# Abrir un shell psql dentro del pod de Postgres
kubectl exec -it statefulset/postgres-0 -- psql -U postgres -d pc_db
```

### Acceso a la aplicación

```bash
# Forward del puerto 3000 de tu servicio al localhost
kubectl port-forward svc/backend-svc 3000:3000

# En otra terminal, probar un endpoint (por ejemplo /health)
curl http://localhost:3000/health

kubectl exec -it deployment/backend -- bash
# dentro del pod:
python3 app.py
```

## Variables de Entorno Disponibles para el Backend Python
Estas variables se inyectan automáticamente desde el Secret y el StatefulSet:

-`DB_HOST=postgres-0.postgres`

-`DB_PORT=5432`

-`DB_USER=postgres`

-`DB_PASSWORD (desde el Secret postgres-secret)`

-`DB_NAME=pc_db`