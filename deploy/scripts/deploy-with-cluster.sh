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

# Check if required tools are installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install it first:"
    echo "   brew install kubectl"
    exit 1
fi

if ! command -v k3d &> /dev/null; then
    echo "❌ k3d is not installed. Please install it first:"
    echo "   brew install k3d"
    exit 1
fi

# Check if cluster exists, create if it doesn't
if ! k3d cluster list | grep -q "roam-dev"; then
    echo "🏗️  Creating k3d cluster..."
    k3d cluster create roam-dev \
        --agents 1 --servers 1 \
        -p "80:80@loadbalancer" \
        -p "443:443@loadbalancer" \
        -p "8001:8001@loadbalancer" \
        --volume "$(pwd):/app/controller@server:*;agent:*"
    
    echo "✅ k3d cluster created successfully"
else
    echo "📋 Using existing k3d cluster 'roam-dev'"
fi

# Ensure we're using the right context
kubectl config use-context k3d-roam-dev

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
    if [[ -f k8s/rbac.yaml ]]; then
        kubectl apply -f k8s/rbac.yaml
    fi
    if [[ -f k8s/redis.yaml ]]; then
        kubectl apply -f k8s/redis.yaml
    fi
    kubectl apply -f k8s/deployment-dev.yaml
    if [[ -f k8s/workers.yaml ]]; then
        kubectl apply -f k8s/workers.yaml
    fi
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
echo ""
echo "🔄 To recreate cluster:"
echo "   k3d cluster delete roam-dev && ./deploy.sh $MODE"