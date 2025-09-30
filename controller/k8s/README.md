# Roam Controller Kubernetes Deployment

This directory contains everything needed to deploy the roam-controller to a k3d Kubernetes cluster.

## Quick Start

### Production Mode (Docker Image)
```bash
./deploy.sh prod
```
- Builds a Docker image from source
- Deploys using the built image
- Best for production-like testing

### Development Mode (Host Mount)
```bash
./deploy.sh dev
```
- Mounts your local source directory
- Changes are reflected immediately (hot reload)
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
k3d cluster delete roam-controller
```