# Deploy Workspace

Infrastructure as Code for ROAM system.

## Structure

```
deploy/
├── k8s/             # Kubernetes manifests
│   ├── namespace.yaml        # roam-controller namespace
│   ├── rbac.yaml            # Service accounts and permissions  
│   ├── redis.yaml           # Redis deployment and service
│   ├── deployment-dev.yaml  # Controller development deployment
│   ├── workers.yaml         # Persistent worker pool
│   ├── service.yaml         # Controller service
│   └── ingress.yaml         # Ingress for external access
├── scripts/         # Deployment and management scripts
└── README.md        # This file
```

## Deployment Options

### Simple Deployment (Existing Cluster)
```bash
# Deploy to existing k8s cluster
./scripts/deploy-all.sh

# Or manually in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/rbac.yaml  
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/deployment-dev.yaml
kubectl apply -f k8s/workers.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

### Full Deployment (Creates k3d Cluster)
```bash
# Development mode (hot reload)
./scripts/deploy-with-cluster.sh dev

# Production mode (Docker image)  
./scripts/deploy-with-cluster.sh prod
```
- Best for active development

### Default (Production Mode)
```bash
./deploy.sh
```

## Files

- `k3d-config.yaml` - k3d cluster configuration
- `Dockerfile` - Multi-stage Docker build
- `deploy.sh` - Deployment script with mode selection
- `k8s/deployment.yaml` - Production Kubernetes deployment
- `k8s/deployment-dev.yaml` - Development deployment with host mounts
- `k8s/service.yaml` - LoadBalancer service

## Access

Once deployed, the controller will be available at:
- http://localhost:8001

## Monitoring

```bash
# Check logs
kubectl logs -l app=roam-controller -f           # Production
kubectl logs -l app=roam-controller-dev -f       # Development

# Check status
kubectl get pods
kubectl get services
```

## Cleanup

```bash
k3d cluster delete roam-dev
```