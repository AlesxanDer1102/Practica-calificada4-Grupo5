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

   # Construir imagen localmente
   docker build -t db_app:latest .

   # Verificar imagen
   docker images | grep db_app
   ```

3. **Verificar configuración del deployment**:
  El archivo `python/deployment.yaml` debe tener:
  ```yaml
  yamlcontainers:
    - name: python-app
      image: db_app:latest
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

# Específico de PostgreSQL
kubectl get pods -l app=postgres

# Específico de la aplicación Python
kubectl get pods -l app=python-app
```

### Ver Registros
```bash
# Registros de PostgreSQL
kubectl logs -l app=postgres

# Registros de la aplicación Python
kubectl logs -l app=python-app

# Seguir registros en tiempo real
kubectl logs -f -l app=python-app
```

### Acceso a la Base de Datos
```bash
# Conectar directamente a PostgreSQL
kubectl exec -it deployment/postgres-deployment -- psql -U postgres -d pc_db
```

### Acceso a la aplicación
```bash
# Conectar directamente a la aplicación de Python
kubectl exec -it deployment/python-app-deployment -- bash -c "python3 app.py"
```

## Variables de Entorno Disponibles para la Aplicación Python

Tu aplicación Python recibirá estas variables de entorno automáticamente:

- `POSTGRES_HOST=postgres-service`
- `POSTGRES_PORT=5432`
- `POSTGRES_USER=postgres`
- `POSTGRES_PASSWORD=12345`
- `POSTGRES_DB=pc_db`
