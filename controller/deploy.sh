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

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install it first:"
    echo "   brew install kubectl"
    exit 1
fi

# Skip cluster creation since you already have it
echo "🔧 Using existing cluster..."

if [[ "$MODE" == "dev" ]]; then
    echo "🛠 Development mode: will use host path mounting in Kubernetes"
    
    # Set source path for template substitution
    export CONTROLLER_SOURCE_PATH="$(pwd)"
    echo "📁 Using source path: $CONTROLLER_SOURCE_PATH"
fi

# Wait for cluster to be ready
echo "⏳ Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=60s

if [[ "$MODE" == "prod" ]]; then
    # Build Docker image
    echo "🔨 Building Docker image..."
    docker build -t roam-controller:latest .
    
    # Import image to k3d (if using k3d)
    echo "📥 Importing image to k3d..."
    k3d image import roam-controller:latest --cluster roam-controller
    
    # Apply production manifests in the right order
    echo "🔧 Deploying roam-controller (production mode)..."
    echo "📋 Applying manifests in order..."
    
    # Easy button alternative: kubectl apply -f k8s/
    if [[ -f k8s/namespace.yaml ]]; then
        kubectl apply -f k8s/namespace.yaml
    fi
    if [[ -f k8s/configmap.yaml ]]; then
        kubectl apply -f k8s/configmap.yaml
    fi
    kubectl apply -f k8s/deployment.yaml
    kubectl apply -f k8s/service.yaml
    if [[ -f k8s/ingress.yaml ]]; then
        kubectl apply -f k8s/ingress.yaml
    fi
    # Optional manifests
    if [[ -f k8s/hpa.yaml ]]; then
        kubectl apply -f k8s/hpa.yaml
    fi
    if [[ -f k8s/pdb.yaml ]]; then
        kubectl apply -f k8s/pdb.yaml
    fi
    
    # Wait for deployment
    kubectl wait --for=condition=Available deployment/roam-controller --timeout=120s
    
    echo "✅ Production deployment complete!"
    echo "🔍 To check logs:"
    echo "   kubectl logs -l app=roam-controller -f"
    
else
    # Apply development manifests in the right order
    echo "🔧 Deploying roam-controller (development mode)..."
    echo "📋 Applying manifests in order..."
    
    # Easy button alternative: kubectl apply -f k8s/
    if [[ -f k8s/namespace.yaml ]]; then
        kubectl apply -f k8s/namespace.yaml
    fi
    if [[ -f k8s/configmap.yaml ]]; then
        kubectl apply -f k8s/configmap.yaml
    fi
    kubectl apply -f k8s/deployment-dev.yaml
    if [[ -f k8s/service.yaml ]]; then
        kubectl apply -f k8s/service.yaml
    fi
    if [[ -f k8s/ingress.yaml ]]; then
        kubectl apply -f k8s/ingress.yaml
    fi
    # Optional manifests
    if [[ -f k8s/hpa.yaml ]]; then
        kubectl apply -f k8s/hpa.yaml
    fi
    if [[ -f k8s/pdb.yaml ]]; then
        kubectl apply -f k8s/pdb.yaml
    fi
    
    # Wait for deployment
    kubectl wait --for=condition=Available deployment/roam-controller-dev --namespace=roam-controller --timeout=120s
    
    echo "✅ Development deployment complete!"
    echo "🔥 Hot reloading enabled - changes to source files will be reflected!"
    echo "🔍 To check logs:"
    echo "   kubectl logs -l app=roam-controller-dev -f"
fi

echo ""
echo "🌐 Service information:"
kubectl get svc -n roam-controller
echo ""
echo "🏃 Controller should be accessible at:"
echo "   http://localhost:8001"
echo ""
echo "🧹 To clean up:"
echo "   k3d cluster delete roam-dev"