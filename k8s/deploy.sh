#!/usr/bin/env bash
  set -e
  minikube start --driver=docker
  eval $(minikube docker-env)

  docker build -f k8s/postgres/Dockerfile -t custom-postgres:latest .
  docker build -f k8s/backend/Dockerfile -t miapp:dev .

  kubectl apply -f k8s/postgres/
  kubectl apply -f k8s/backend/