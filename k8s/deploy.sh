#!/bin/bash

# Script de despliegue para recursos de Kubernetes
set -e
echo "Desplegando PostgreSQL + Aplicación Python en Kubernetes..."

kubectl apply -f postgres/secret.yaml
kubectl apply -f postgres/configmap.yaml
kubectl apply -f postgres/pvc.yaml
kubectl apply -f postgres/deployment.yaml
kubectl apply -f postgres/service.yaml

echo "Esperando a que PostgreSQL esté listo..."
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s

echo "6. Desplegando aplicación Python..."
kubectl apply -f python/deployment.yaml

echo "Despliegue completado!"

echo ""
echo "Verificar estado con:"
echo "  kubectl get pods"
echo "  kubectl get services"

echo ""
echo "Ver logs con:"
echo "  kubectl logs -l app=postgres"
echo "  kubectl logs -l app=python-app"
