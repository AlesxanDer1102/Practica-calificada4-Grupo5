#!/bin/bash

echo "Limpiando recursos de Kubernetes..."

echo "Eliminando recursos de la aplicación Python..."
kubectl delete -f python/deployment.yaml --ignore-not-found=true

echo "Eliminando recursos de PostgreSQL..."
kubectl delete -f postgres/service.yaml --ignore-not-found=true
kubectl delete -f postgres/deployment.yaml --ignore-not-found=true
kubectl delete -f postgres/pvc.yaml --ignore-not-found=true
kubectl delete -f postgres/configmap.yaml --ignore-not-found=true
kubectl delete -f postgres/secret.yaml --ignore-not-found=true

echo "¡Limpieza completada!"
