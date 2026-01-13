# RCSB PDB Chatbot - K8s Deployment Commands Reference

This document contains all commands used for deploying the chatbot to RCSB Kubernetes.

## Prerequisites

```bash
# Verify kubectl context
kubectl config current-context
# Expected: rcsb-east

# Check namespace exists
kubectl get namespaces | grep vivek
# Expected: vivek-chithari

# Verify storage class
kubectl get storageclass
# Expected: csi-cephfs-sc

# Verify cert-manager cluster issuer
kubectl get clusterissuer
# Expected: rutgers-acme
```

---

## Step 1: Deploy RAGFlow

```bash
# Clone RAGFlow Helm chart (always get latest)
rm -rf /tmp/ragflow
git clone --depth 1 https://github.com/infiniflow/ragflow.git /tmp/ragflow

# Deploy RAGFlow with RCSB overrides (minimal values file)
helm upgrade --install ragflow /tmp/ragflow/helm \
  -f k8s/helm/rcsb-pdb-chatbot/ragflow-values.yaml \
  -n vivek-chithari \
  --timeout 10m \
  --wait

# Verify deployment
kubectl get pods -n vivek-chithari
kubectl get svc,pvc -n vivek-chithari
```

**Expected output:**
```
NAME                       READY   STATUS    RESTARTS   AGE
ragflow-xxxxxxxxx-xxxxx    1/1     Running   0          Xm
ragflow-infinity-0         1/1     Running   0          Xm
ragflow-minio-0            1/1     Running   0          Xm
ragflow-mysql-0            1/1     Running   0          Xm
ragflow-redis-0            1/1     Running   0          Xm
```

---

## Step 2: Access RAGFlow UI (Get API Key)

```bash
# Port forward to RAGFlow UI
kubectl port-forward svc/ragflow 8080:80 -n vivek-chithari &

# Open browser: http://localhost:8080
# 1. Register/Login (create account first time)
# 2. Go to Settings → API Keys (or User Profile → API Keys)
# 3. Generate new API key
# 4. Copy the key (format: ragflow-xxxx...)

# Kill port forward when done
pkill -f "port-forward svc/ragflow"
```

---

## Step 3: Create Kubernetes Secrets

```bash
# 1. Create application secrets (API keys)
kubectl create secret generic chatbot-secrets -n vivek-chithari \
  --from-literal='RAGFLOW_API_KEY=your-ragflow-api-key' \
  --from-literal='OPENAI_API_KEY=your-openai-api-key' \
  --from-literal='GOOGLE_DRIVE_FOLDER_URL=https://drive.google.com/drive/folders/YOUR_FOLDER_ID' \
  --from-literal='GOOGLE_DRIVE_EXPORT_FOLDER_ID='

# 2. Create Google Drive credentials secret
kubectl create secret generic gdrive-credentials -n vivek-chithari \
  --from-file=credentials.json=./credentials/google_drive_credentials.json

# 3. Create Harbor image pull secret
# IMPORTANT: Use your Harbor OIDC username and CLI secret (from Harbor User Profile)
kubectl create secret docker-registry harbor-docker-registry-conf \
  --docker-server=harbor.devops.k8s.rcsb.org \
  --docker-username='YOUR_OIDC_USERNAME' \
  --docker-password='YOUR_CLI_SECRET' \
  --docker-email='your.email@rcsb.org' \
  -n vivek-chithari

# Verify secrets created
kubectl get secrets -n vivek-chithari
```

**Expected secrets:**
```
NAME                            TYPE                             DATA   AGE
chatbot-secrets                 Opaque                           4      Xs
gdrive-credentials              Opaque                           1      Xs
harbor-docker-registry-conf     kubernetes.io/dockerconfigjson   1      Xs
ragflow-env-config              Opaque                           21     Xm
```

---

## Step 4: Build and Push Docker Image

**IMPORTANT: Build for AMD64 architecture (K8s cluster runs AMD64, not ARM)**

```bash
# Login to Harbor (use OIDC username and CLI secret)
docker login harbor.devops.k8s.rcsb.org

# Build for AMD64 (required for K8s cluster)
docker buildx build --platform linux/amd64 \
  -t harbor.devops.k8s.rcsb.org/vivek.chithari/rcsb-pdb-chatbot:1.0.0 \
  --push .

# OR build and push separately:
docker buildx build --platform linux/amd64 \
  -t harbor.devops.k8s.rcsb.org/vivek.chithari/rcsb-pdb-chatbot:1.0.0 .

docker push harbor.devops.k8s.rcsb.org/vivek.chithari/rcsb-pdb-chatbot:1.0.0
```

**Note:** If you build without `--platform linux/amd64` on an Apple Silicon Mac, you'll get `exec format error` in the pod.

---

## Step 5: Deploy Chatbot

```bash
# Deploy chatbot Helm chart
helm upgrade --install rcsb-pdb-chatbot k8s/helm/rcsb-pdb-chatbot \
  -n vivek-chithari \
  --wait \
  --timeout 5m

# Verify deployment
kubectl get pods -n vivek-chithari
kubectl get ingress -n vivek-chithari
```

---

## Step 6: Verify Deployment

```bash
# Check all resources
kubectl get all -n vivek-chithari

# Check TLS certificate (may take a few minutes to be ready)
kubectl get certificate -n vivek-chithari

# View pod logs
kubectl logs -f deploy/rcsb-pdb-chatbot -n vivek-chithari

# Test health endpoint (after ingress is ready)
curl https://pdb-chatbot.k8s.rcsb.org/_stcore/health
```

---

## Troubleshooting

### Image Pull Errors

```bash
# Check pod events
kubectl describe pod -l app.kubernetes.io/name=rcsb-pdb-chatbot -n vivek-chithari

# If "no basic auth credentials" error:
# 1. Verify Harbor image pull secret has correct credentials
kubectl get secret harbor-docker-registry-conf -n vivek-chithari -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d

# 2. Recreate with correct credentials
kubectl delete secret harbor-docker-registry-conf -n vivek-chithari
kubectl create secret docker-registry harbor-docker-registry-conf \
  --docker-server=harbor.devops.k8s.rcsb.org \
  --docker-username='YOUR_OIDC_USERNAME' \
  --docker-password='YOUR_CLI_SECRET' \
  --docker-email='your.email@rcsb.org' \
  -n vivek-chithari
```

### Exec Format Error

```bash
# This means image was built for wrong architecture (ARM instead of AMD64)
# Rebuild with correct platform:
docker buildx build --platform linux/amd64 \
  -t harbor.devops.k8s.rcsb.org/vivek.chithari/rcsb-pdb-chatbot:1.0.0 \
  --push .

# Then restart the deployment
kubectl rollout restart deployment/rcsb-pdb-chatbot -n vivek-chithari
```

### Pod CrashLoopBackOff

```bash
# Check logs
kubectl logs -l app.kubernetes.io/name=rcsb-pdb-chatbot -n vivek-chithari --tail=100

# Check events
kubectl get events -n vivek-chithari --sort-by='.lastTimestamp'
```

### Harbor Connection Issues

```bash
# Check if you can reach Harbor (need VPN)
curl -I https://harbor.devops.k8s.rcsb.org/v2/

# If DNS fails, flush DNS cache:
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder

# Reconnect VPN and retry
```

---

## Useful Commands

```bash
# Watch pods
watch kubectl get pods -n vivek-chithari

# Port forward to chatbot (for local testing)
kubectl port-forward svc/rcsb-pdb-chatbot 8501:8501 -n vivek-chithari

# Port forward to RAGFlow UI
kubectl port-forward svc/ragflow 8080:80 -n vivek-chithari

# Restart deployment
kubectl rollout restart deploy/rcsb-pdb-chatbot -n vivek-chithari

# View events
kubectl get events -n vivek-chithari --sort-by='.lastTimestamp'

# Execute command in pod
kubectl exec -it deploy/rcsb-pdb-chatbot -n vivek-chithari -- /bin/bash

# Test RAGFlow connectivity from chatbot pod
kubectl exec -it deploy/rcsb-pdb-chatbot -n vivek-chithari -- \
  curl -s http://ragflow-ragflow:9380/health
```

---

## Uninstall / Cleanup

```bash
# Uninstall chatbot
helm uninstall rcsb-pdb-chatbot -n vivek-chithari

# Uninstall RAGFlow
helm uninstall ragflow -n vivek-chithari

# Delete PVCs (WARNING: deletes all data)
kubectl delete pvc --all -n vivek-chithari

# Delete secrets
kubectl delete secret chatbot-secrets gdrive-credentials harbor-docker-registry-conf -n vivek-chithari
```

---

## Updating RAGFlow

When RAGFlow releases a new version:

```bash
# Get latest Helm chart
rm -rf /tmp/ragflow
git clone --depth 1 https://github.com/infiniflow/ragflow.git /tmp/ragflow

# Upgrade (our minimal overrides file will still work)
helm upgrade ragflow /tmp/ragflow/helm \
  -f k8s/helm/rcsb-pdb-chatbot/ragflow-values.yaml \
  -n vivek-chithari \
  --wait

# Verify upgrade
kubectl get pods -n vivek-chithari
```

---

## Updating Chatbot

```bash
# Build new image with new tag
docker buildx build --platform linux/amd64 \
  -t harbor.devops.k8s.rcsb.org/vivek.chithari/rcsb-pdb-chatbot:1.0.1 \
  --push .

# Upgrade with new tag
helm upgrade rcsb-pdb-chatbot k8s/helm/rcsb-pdb-chatbot \
  -n vivek-chithari \
  --set image.tag=1.0.1 \
  --wait
```
