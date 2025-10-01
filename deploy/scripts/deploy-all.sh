#!/bin/bash
# Deploy all ROAM components to k8s cluster

set -e

echo "🚀 Deploying ROAM system to k8s..."

# Deploy in order
echo "📦 Creating namespace..."
kubectl apply -f k8s/namespace.yaml

echo "🔐 Setting up RBAC..."  
kubectl apply -f k8s/rbac.yaml

echo "📊 Deploying Redis..."
kubectl apply -f k8s/redis.yaml

echo "🎯 Deploying Controller..."
kubectl apply -f k8s/deployment-dev.yaml
kubectl apply -f k8s/service.yaml

echo "⚙️ Deploying Workers..."
kubectl apply -f k8s/workers.yaml

echo "🌐 Setting up Ingress..."
kubectl apply -f k8s/ingress.yaml

echo "✅ ROAM deployment complete!"
echo "🔗 Access at: http://roam.localtest.me/healthz"