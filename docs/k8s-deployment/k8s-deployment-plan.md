# RCSB PDB Chatbot - Kubernetes Deployment Plan

## Overview
Deploy the RCSB PDB multi-user research chatbot to RCSB Kubernetes cluster using:
- **RAGFlow**: Official Helm chart for RAG backend
- **Chatbot**: Custom Helm chart for Streamlit application

## Architecture Summary
```
                    EXTERNAL
                        |
            ┌───────────┴───────────┐
            │  HAProxy Ingress      │
            │  (TLS via cert-mgr)   │
            └───────────┬───────────┘
                        │
    ┌───────────────────┴───────────────────┐
    │    NAMESPACE: vivek.chithari          │
    │                                        │
    │  ┌─────────────┐    ┌──────────────┐  │
    │  │   Chatbot   │───→│   RAGFlow    │  │
    │  │ (Streamlit) │    │ (API :9380)  │  │
    │  │   :8501     │    ├──────────────┤  │
    │  └─────────────┘    │ + Infinity   │  │
    │        │            │ + MySQL      │  │
    │        ↓            │ + MinIO      │  │
    │  ┌─────────────┐    │ + Redis      │  │
    │  │ PVC: user_  │    └──────────────┘  │
    │  │ data, creds │                      │
    │  └─────────────┘                      │
    └───────────────────────────────────────┘
```

## Configuration Decisions
| Setting | Value |
|---------|-------|
| Namespace | `vivek.chithari` |
| Domain | `pdb-chatbot.k8s.rcsb.org` |
| Authentication | None (keep research ID system) |
| Secrets | Manual K8s Secrets |
| Storage | `csi-cephfs-sc` |
| RAGFlow Location | Same namespace |
| Google Drive | Enabled |

---

## Implementation Steps

### Phase 1: Create Helm Chart Structure
Create `k8s/helm/rcsb-pdb-chatbot/` directory with:

```
k8s/helm/
├── rcsb-pdb-chatbot/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── ragflow-values.yaml    # RAGFlow configuration
│   └── templates/
│       ├── _helpers.tpl
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── ingress.yaml
│       ├── configmap.yaml
│       ├── pvc-user-data.yaml
│       ├── pvc-credentials.yaml
│       ├── job-kb-init.yaml
│       └── cronjob-gdrive-sync.yaml
└── deploy.sh                   # Deployment script
```

### Phase 2: Create Kubernetes Secrets

```bash
# 1. Harbor image pull secret
kubectl create secret docker-registry harbor-docker-registry-conf \
  --docker-server=harbor.devops.k8s.rcsb.org \
  --docker-username=<OIDC_USERNAME> \
  --docker-password=<CLI_SECRET> \
  -n vivek.chithari

# 2. Application secrets
kubectl create secret generic chatbot-secrets \
  --from-literal=RAGFLOW_API_KEY=<key> \
  --from-literal=OPENAI_API_KEY=<key> \
  -n vivek.chithari

# 3. Google Drive credentials
kubectl create secret generic gdrive-credentials \
  --from-file=credentials.json=./credentials/google_drive_credentials.json \
  --from-file=token.pickle=./credentials/google_drive_token.pickle \
  -n vivek.chithari
```

### Phase 3: Deploy RAGFlow Stack

```bash
# Clone RAGFlow Helm chart
git clone --depth 1 https://github.com/infiniflow/ragflow.git /tmp/ragflow

# Deploy RAGFlow
helm upgrade --install ragflow /tmp/ragflow/helm \
  -f k8s/helm/rcsb-pdb-chatbot/ragflow-values.yaml \
  -n vivek.chithari \
  --wait --timeout 15m
```

### Phase 4: Build and Push Docker Image

```bash
# Login to Harbor
docker login harbor.devops.k8s.rcsb.org

# Build image
docker build -t harbor.devops.k8s.rcsb.org/vivek.chithari/rcsb-pdb-chatbot:1.0.0 .

# Push to Harbor
docker push harbor.devops.k8s.rcsb.org/vivek.chithari/rcsb-pdb-chatbot:1.0.0
```

### Phase 5: Deploy Chatbot Helm Chart

```bash
helm upgrade --install rcsb-pdb-chatbot k8s/helm/rcsb-pdb-chatbot \
  -n vivek.chithari \
  --wait --timeout 5m
```

### Phase 6: Initialize Knowledge Base

```bash
# Run KB init job
kubectl create job kb-init-$(date +%s) \
  --from=cronjob/kb-init \
  -n vivek.chithari

# Monitor progress
kubectl logs -f job/kb-init-<name> -n vivek.chithari
```

---

## Verification Checklist

```bash
# 1. Check all pods running
kubectl get pods -n vivek.chithari

# 2. Verify RAGFlow connectivity
kubectl exec -it deploy/rcsb-pdb-chatbot -n vivek.chithari -- \
  curl http://ragflow-ragflow:9380/health

# 3. Check TLS certificate
kubectl get certificate -n vivek.chithari

# 4. Test health endpoint
curl https://pdb-chatbot.k8s.rcsb.org/_stcore/health

# 5. Verify PVC bindings
kubectl get pvc -n vivek.chithari

# 6. View application logs
kubectl logs -f deploy/rcsb-pdb-chatbot -n vivek.chithari
```

**Functional Tests:**
- [ ] UI loads at https://pdb-chatbot.k8s.rcsb.org
- [ ] User can login with research ID
- [ ] Chat creation works
- [ ] Messages persist across refreshes
- [ ] RAGFlow returns responses
- [ ] Google Drive sync runs (CronJob)

---

## Rollback Procedure

```bash
# View release history
helm history rcsb-pdb-chatbot -n vivek.chithari

# Rollback to previous version
helm rollback rcsb-pdb-chatbot 1 -n vivek.chithari

# Full uninstall if needed
helm uninstall rcsb-pdb-chatbot -n vivek.chithari
helm uninstall ragflow -n vivek.chithari
```
