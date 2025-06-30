#!/usr/bin/env bash
  set -e

  kubectl delete -f k8s/backend/ || true
  kubectl delete -f k8s/postgres/ || true

  minikube stop
  minikube delete