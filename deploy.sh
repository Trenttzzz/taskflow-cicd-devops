#!/bin/bash
set -e

echo "Membuat namespace..."
kubectl apply -f kubernetes/namespace-dev.yaml
kubectl apply -f kubernetes/namespace-prod.yaml

echo "Deploy ke production..."
kubectl apply -f kubernetes/deployment.yaml -n taskflow-prod
kubectl apply -f kubernetes/service.yaml -n taskflow-prod

echo "Menunggu deployment selesai..."
kubectl rollout status deployment/taskflow-api -n taskflow-prod --timeout=180s

echo "Selesai."
echo "Cek resource: kubectl get all -n taskflow-prod"