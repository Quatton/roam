#!/usr/bin/env bash

set -euo pipefail

# Default mode
MODE="${1:-prod}"

if [[ "$MODE" != "prod" && "$MODE" != "dev" ]]; then
    echo "Usage: $0 [prod|dev]"
    echo ""
    echo "Modes:"
    echo "  prod - Build Docker image and deploy (default)"
    echo "  dev  - Mount host directory for development"
    exit 1
fi

echo "🚀 Setting up roam-controller on k3d (mode: $MODE)..."

# Check if k3d is installed
if ! command -v k3d &> /dev/null; then
    echo "❌ k3d is not installed. Please install it first:"
    echo "   brew install k3d"
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install it first:"
    echo "   brew install kubectl"
    exit 1
fi

# Create k3d cluster
echo "📦 Creating k3d cluster..."
k3d cluster create roam-controller \
    --port "8001:8001@loadbalancer" \
    --agents 1 \
    --wait

if [[ "$MODE" == "dev" ]]; then
    echo "� Development mode: will use host path mounting in Kubernetes"
fi

# Wait for cluster to be ready
echo "⏳ Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=60s

if [[ "$MODE" == "prod" ]]; then
    # Build Docker image
    echo "🔨 Building Docker image..."
    docker build -t roam-controller:latest .
    
    # Import image to k3d
    echo "📥 Importing image to k3d..."
    k3d image import roam-controller:latest --cluster roam-controller
    
    # Apply production manifests
    echo "🔧 Deploying roam-controller (production mode)..."
    kubectl apply -f k8s/deployment.yaml
    kubectl apply -f k8s/service.yaml
    
    # Wait for deployment
    kubectl wait --for=condition=Available deployment/roam-controller --timeout=120s
    
    echo "✅ Production deployment complete!"
    echo "🔍 To check logs:"
    echo "   kubectl logs -l app=roam-controller -f"
    
else
    # Apply development manifests
    echo "🔧 Deploying roam-controller (development mode)..."
    kubectl apply -f k8s/deployment-dev.yaml
    
    # Wait for deployment
    kubectl wait --for=condition=Available deployment/roam-controller-dev --timeout=120s
    
    echo "✅ Development deployment complete!"
    echo "🔥 Hot reloading enabled - changes to source files will be reflected!"
    echo "🔍 To check logs:"
    echo "   kubectl logs -l app=roam-controller-dev -f"
fi

echo ""
echo "🌐 Service information:"
kubectl get svc
echo ""
echo "🏃 Controller should be accessible at:"
echo "   http://localhost:8001"
echo ""
echo "🧹 To clean up:"
echo "   k3d cluster delete roam-controller"