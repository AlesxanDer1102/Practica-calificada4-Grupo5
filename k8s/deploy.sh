#!/usr/bin/env bash
set -e

echo "Desplegando aplicación..."
minikube start --driver=docker
eval $(minikube docker-env)

docker build -f k8s/postgres/Dockerfile -t custom-postgres:latest .
docker build -f k8s/backend/Dockerfile -t miapp:dev .

kubectl apply -f k8s/postgres/
kubectl apply -f k8s/backend/

echo "Esperando que PostgreSQL esté listo..."
kubectl wait --for=condition=Ready pod/postgres-0 --timeout=300s

echo "Verificando despliegue..."
kubectl get pods

echo "Configurando directorio de backups..."
mkdir -p backups

echo "Despliegue completado!"
echo "Para crear backup: python3 backup_orchestrator.py"
echo "Para ver pods: kubectl get pods"