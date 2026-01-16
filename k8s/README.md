# Kubernetes & Helm Deployment

This directory contains Kubernetes and Helm deployment configurations for the RCSB PDB Chatbot application.

---

## Helm Chart

| File | Purpose |
|------|---------|
| `helm/rcsb-pdb-chatbot/Chart.yaml` | Chart metadata (name, version, maintainer) |
| `helm/rcsb-pdb-chatbot/values.yaml` | Main configuration - replicas, resources, ingress, storage, RAGFlow settings |
| `helm/rcsb-pdb-chatbot/ragflow-values.yaml` | RAGFlow subchart overrides |

## Kubernetes Templates

**Core Resources:**

| File | Type | Purpose |
|------|------|---------|
| `helm/rcsb-pdb-chatbot/templates/deployment.yaml` | Deployment | Main app pod with security context, probes, volumes |
| `helm/rcsb-pdb-chatbot/templates/service.yaml` | Service | ClusterIP on port 8501 |
| `helm/rcsb-pdb-chatbot/templates/ingress.yaml` | Ingress | HAProxy with TLS at `pdb-chatbot.k8s.rcsb.org` |
| `helm/rcsb-pdb-chatbot/templates/serviceaccount.yaml` | ServiceAccount | RBAC identity |

**Storage:**

| File | Type | Size |
|------|------|------|
| `helm/rcsb-pdb-chatbot/templates/pvc-user-data.yaml` | PVC | 10Gi (user sessions) |
| `helm/rcsb-pdb-chatbot/templates/pvc-knowledge-base.yaml` | PVC | 20Gi (RAGFlow docs) |
| `helm/rcsb-pdb-chatbot/templates/pvc-credentials.yaml` | PVC | 100Mi (disabled) |

**Configuration:**

| File | Type |
|------|------|
| `helm/rcsb-pdb-chatbot/templates/configmap.yaml` | ConfigMap |

**Jobs/CronJobs:**

| File | Schedule | Purpose |
|------|----------|---------|
| `helm/rcsb-pdb-chatbot/templates/job-kb-init.yaml` | Post-install hook | Initialize RAGFlow KB |
| `helm/rcsb-pdb-chatbot/templates/cronjob-gdrive-sync.yaml` | Every 6 hours | Sync Google Drive |
| `helm/rcsb-pdb-chatbot/templates/cronjob-feedback-export.yaml` | Weekly Sunday | Export feedback |

## Container & Deployment Scripts

| File | Purpose |
|------|---------|
| `../Dockerfile` | Multi-stage build (python:3.10-slim) |
| `../docker-compose.yml` | Local development |
| `deploy.sh` | Deployment automation script |

---

## Infrastructure Details

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

## Directory Structure

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
