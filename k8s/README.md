# Kubernetes & Helm Deployment Documentation

This directory contains all Kubernetes and Helm deployment configurations for the RCSB PDB Chatbot application.

---

## Files to Share with DevOps Team

### 1. Helm Chart (Primary - Share First)

| File | Purpose |
|------|---------|
| `k8s/helm/rcsb-pdb-chatbot/Chart.yaml` | Chart metadata (name, version, maintainer) |
| `k8s/helm/rcsb-pdb-chatbot/values.yaml` | **Main configuration** - replicas, resources, ingress, storage, RAGFlow settings |
| `k8s/helm/rcsb-pdb-chatbot/ragflow-values.yaml` | RAGFlow subchart overrides |

### 2. Kubernetes Templates

**Core Resources:**

| File | Type | Purpose |
|------|------|---------|
| `k8s/helm/rcsb-pdb-chatbot/templates/deployment.yaml` | Deployment | Main app pod with security context, probes, volumes |
| `k8s/helm/rcsb-pdb-chatbot/templates/service.yaml` | Service | ClusterIP on port 8501 |
| `k8s/helm/rcsb-pdb-chatbot/templates/ingress.yaml` | Ingress | HAProxy with TLS at `pdb-chatbot.k8s.rcsb.org` |
| `k8s/helm/rcsb-pdb-chatbot/templates/serviceaccount.yaml` | ServiceAccount | RBAC identity |

**Storage:**

| File | Type | Size |
|------|------|------|
| `k8s/helm/rcsb-pdb-chatbot/templates/pvc-user-data.yaml` | PVC | 10Gi (user sessions) |
| `k8s/helm/rcsb-pdb-chatbot/templates/pvc-knowledge-base.yaml` | PVC | 20Gi (RAGFlow docs) |
| `k8s/helm/rcsb-pdb-chatbot/templates/pvc-credentials.yaml` | PVC | 100Mi (disabled) |

**Configuration:**

| File | Type |
|------|------|
| `k8s/helm/rcsb-pdb-chatbot/templates/configmap.yaml` | ConfigMap |

**Jobs/CronJobs:**

| File | Schedule | Purpose |
|------|----------|---------|
| `k8s/helm/rcsb-pdb-chatbot/templates/job-kb-init.yaml` | Post-install hook | Initialize RAGFlow KB |
| `k8s/helm/rcsb-pdb-chatbot/templates/cronjob-gdrive-sync.yaml` | Every 6 hours | Sync Google Drive |
| `k8s/helm/rcsb-pdb-chatbot/templates/cronjob-feedback-export.yaml` | Weekly Sunday | Export feedback |

### 3. Container & Deployment Scripts

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build (python:3.10-slim) |
| `docker-compose.yml` | Local development |
| `k8s/deploy.sh` | Deployment automation script |

---

## Key Infrastructure Details

| Component | Value |
|-----------|-------|
| **Registry** | `harbor.devops.k8s.rcsb.org/vivek.chithari/rcsb-pdb-chatbot` |
| **Storage Class** | `csi-cephfs-sc` (Ceph) |
| **Ingress** | HAProxy + cert-manager (`rutgers-acme`) |
| **Namespace** | `vivek-chithari` |
| **Port** | 8501 (Streamlit) |

---

## Resource Limits

| Resource | Request | Limit |
|----------|---------|-------|
| CPU | 500m | 2 |
| Memory | 1Gi | 4Gi |

---

## Security Features

- Non-root user (UID 1000)
- Read-only root filesystem
- Secrets via K8s secrets (not in config)
- Custom ServiceAccount

---

## Deployment Commands

### Deploy with Helm

```bash
# Install/upgrade the chart
helm upgrade --install rcsb-pdb-chatbot ./k8s/helm/rcsb-pdb-chatbot \
  --namespace vivek-chithari \
  --create-namespace \
  -f k8s/helm/rcsb-pdb-chatbot/values.yaml

# Check deployment status
kubectl get pods -n vivek-chithari

# View logs
kubectl logs -f deployment/rcsb-pdb-chatbot -n vivek-chithari
```

### Using the Deploy Script

```bash
# Run the deployment script
./k8s/deploy.sh
```

### Helm Operations

```bash
# Template rendering (dry-run)
helm template rcsb-pdb-chatbot ./k8s/helm/rcsb-pdb-chatbot

# Uninstall
helm uninstall rcsb-pdb-chatbot -n vivek-chithari

# List releases
helm list -n vivek-chithari
```

---

## Quick Share Command

```bash
# List all files for DevOps review
find k8s/ -type f \( -name "*.yaml" -o -name "*.sh" \) | sort

# Or share the whole k8s/ directory
```

---

## File Summary

**Total: 16 K8s/Helm files + Dockerfile + docker-compose.yml**

```
k8s/
├── deploy.sh
├── README.md
└── helm/
    └── rcsb-pdb-chatbot/
        ├── Chart.yaml
        ├── values.yaml
        ├── ragflow-values.yaml
        └── templates/
            ├── NOTES.txt
            ├── _helpers.tpl
            ├── configmap.yaml
            ├── cronjob-feedback-export.yaml
            ├── cronjob-gdrive-sync.yaml
            ├── deployment.yaml
            ├── ingress.yaml
            ├── job-kb-init.yaml
            ├── pvc-credentials.yaml
            ├── pvc-knowledge-base.yaml
            ├── pvc-user-data.yaml
            ├── service.yaml
            └── serviceaccount.yaml
```
