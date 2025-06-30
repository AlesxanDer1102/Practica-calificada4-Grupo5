#!/usr/bin/env bash
  set -e
  minikube start --driver=docker
  eval $(minikube docker-env)

  docker build -f k8s/postgres/Dockerfile-postgres -t custom-postgres:latest .
  docker build -f Dockerfile-backend -t python-backend:dev .

  kubectl apply -f k8s/postgres/
  kubectl apply -f k8s/backend/