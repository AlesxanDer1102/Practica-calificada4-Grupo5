#!/bin/bash

# Script de despliegue para recursos de Kubernetes
set -e
echo "Desplegando PostgreSQL + Aplicación Python en Kubernetes..."

kubectl apply -f k8s/postgres/postgres-secret.yaml
kubectl apply -f k8s/postgres/postgres-service.yaml
kubectl apply -f k8s/postgres/postgres-statefulset.yaml

echo "Esperando a que PostgreSQL esté listo..."
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s

echo "6. Desplegando aplicación Python..."
kubectl apply -f k8s/backend/backend-deployment.yaml
kubectl apply -f k8s/backend/backend-service.yaml

echo "Despliegue completado!"

echo ""
echo "Verificar estado con:"
echo "  kubectl get pods"
echo "  kubectl get services"

echo ""
echo "Ver logs con:"
echo "  kubectl logs statefulset/postgres-0"
echo "  kubectl logs deployment/backend"
