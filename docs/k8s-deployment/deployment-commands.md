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

## Step 2: Access RAGFlow UI and Configure

```bash
# Port forward to RAGFlow UI
kubectl port-forward svc/ragflow 8080:80 -n vivek-chithari &

# Open browser: http://localhost:8080
```

### 2.1 Register/Login
1. Create an account (first time) or login
2. Note your username for later

### 2.2 Generate RAGFlow API Key
1. Go to **User Profile** (top right) → **API Keys**
2. Click **Generate new API key**
3. Copy the key (format: `ragflow-xxxx...`)
4. Save this for Step 3

### 2.3 Configure OpenAI Model Provider (CRITICAL)
This step is required for the knowledge base and chat to work:

1. Go to **User Profile** → **Model Providers** (or **Settings** → **Model Management**)
2. Click **Add Model Provider**
3. Select **OpenAI**
4. Enter your **OpenAI API Key**
5. Click **Save**

**Important:** Ensure BOTH embedding models AND chat models (LLM) are enabled:
- **Embedding models**: `text-embedding-3-large` (for document processing)
- **Chat models**: `gpt-4-turbo`, `gpt-4`, etc. (for assistant responses)

**Note:** Without embedding model, KB init fails with `Unauthorized model: text-embedding-3-large@OpenAI`
**Note:** Without LLM model, chat responses show `Model(@None) not authorized`

```bash
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

# Build for AMD64 and push with 'latest' tag (recommended approach)
docker buildx build --platform linux/amd64 \
  -t harbor.devops.k8s.rcsb.org/vivek.chithari/rcsb-pdb-chatbot:latest \
  --push .

# OR build and push separately:
docker buildx build --platform linux/amd64 \
  -t harbor.devops.k8s.rcsb.org/vivek.chithari/rcsb-pdb-chatbot:latest .

docker push harbor.devops.k8s.rcsb.org/vivek.chithari/rcsb-pdb-chatbot:latest
```

**Notes:**
- If you build without `--platform linux/amd64` on an Apple Silicon Mac, you'll get `exec format error` in the pod.
- We use `latest` tag with `imagePullPolicy: Always` in values.yaml to avoid version tag management headaches.

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

## Step 6: Verify KB Init Job

The Helm chart automatically runs a Knowledge Base initialization job that:
1. Creates the RAGFlow dataset (`rcsb_pdb_knowledge_base`)
2. Uploads and processes documents from `knowledge_base/` directory
3. Creates the RAGFlow assistant (`RCSB ChatBot v2`)

```bash
# Check KB init job status
kubectl get jobs -n vivek-chithari | grep kb-init

# View KB init logs
kubectl logs job/rcsb-pdb-chatbot-kb-init -n vivek-chithari

# Expected output (successful):
# - "Dataset created successfully"
# - "Successfully uploaded X documents"
# - "Created new assistant: RCSB ChatBot v2"
```

**If KB init fails:**
- Check RAGFlow Model Providers has OpenAI configured (Step 2.3)
- Check secrets have correct API keys
- Re-run by deleting job and upgrading helm:
  ```bash
  kubectl delete job rcsb-pdb-chatbot-kb-init -n vivek-chithari
  helm upgrade rcsb-pdb-chatbot k8s/helm/rcsb-pdb-chatbot -n vivek-chithari
  ```

---

## Step 7: Verify Deployment

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

**Access the chatbot:**
- URL: https://pdb-chatbot.k8s.rcsb.org
- Login with any research ID
- Create a chat and test messaging

---

## Known Issues & Solutions

### "Model(@None) not authorized" Error

**Symptom:** Chat responses show `Model(@None) not authorized` error.

**Cause:** The LLM model is not properly configured in RAGFlow or the assistant wasn't created with the correct model settings.

**Solution:**
1. Access RAGFlow UI via port-forward: `kubectl port-forward svc/ragflow 8080:80 -n vivek-chithari`
2. Go to **User Profile** → **Model Providers**
3. Ensure OpenAI is configured with a valid API key
4. Verify that chat models are enabled (e.g., `gpt-4-turbo`, `gpt-4o-mini`)
5. Delete and recreate the assistant in RAGFlow UI, selecting a valid LLM model

### RAGFlow API Bug with LLM Settings

**Issue:** When programmatically updating assistant settings, RAGFlow throws `KeyError('model_type')` if `llm` block is included in the update payload.

**Workaround:** The code has been updated to NOT include `llm` settings in API updates. LLM configuration must be done via RAGFlow UI instead.

**Affected file:** `src/ragflow_assistant_manager.py` (see comments in code)

---

## Performance Analysis

### Response Time Breakdown (~22 seconds total)

| Component | Time | Notes |
|-----------|------|-------|
| Direct OpenAI API call | ~3 seconds | Fast - not the bottleneck |
| RAGFlow RAG processing | ~19 seconds | Query embedding, vector search, context assembly |
| Code overhead | ~100-400ms | Minimal impact |

**Key Finding:** The ~22 second response time is due to RAGFlow's internal RAG processing, NOT Kubernetes scaling or resource constraints.

### Current Pod Resource Usage

```
NAME                           CPU     MEMORY
ragflow                        54m     5.6GB   (no limits - BestEffort QoS)
ragflow-infinity               1m      1.1GB
ragflow-mysql                  2m      456Mi
rcsb-pdb-chatbot              1m      47Mi    (barely using resources)
```

### Will K8s Scaling Help?

| Action | Response Time | Concurrent Users |
|--------|--------------|------------------|
| Scale chatbot replicas | ❌ No improvement | ✅ Helps |
| Scale RAGFlow replicas | ❌ No improvement | ✅ Helps |
| Add HPA autoscaling | ❌ No improvement | ✅ Helps |

**Answer:** Scaling pods will NOT reduce response time. The bottleneck is RAGFlow's internal processing.

---

## RAGFlow Performance Optimization

To reduce response time, adjust these settings in **RAGFlow UI** (http://localhost:8080):

### Settings to Disable (for faster responses)

1. **Multi-turn optimization** - Chat Configuration → Prompt Engine
2. **Rerank model** - Leave empty (slow without GPU)
3. **Keyword analysis** - Assistant settings
4. **Reasoning toggle** - Assistant settings

### Settings to Adjust

| Setting | Current | Recommended | Effect |
|---------|---------|-------------|--------|
| Top N | 8 | 4-5 | Fewer chunks to process |
| Similarity Threshold | 0.2 | 0.3-0.4 | More selective retrieval |
| Top K | 1024 | 512 | Reduce search space |

### Profile Response Time

Click the **light bulb icon** in RAGFlow chat to see time breakdown for each processing step.

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
  curl -s http://ragflow-api/api/v1/datasets
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

Since we use `latest` tag with `imagePullPolicy: Always`, updating is simple:

```bash
# Build and push new image (same tag)
docker buildx build --platform linux/amd64 \
  -t harbor.devops.k8s.rcsb.org/vivek.chithari/rcsb-pdb-chatbot:latest \
  --push .

# Restart deployment to pull new image
kubectl rollout restart deploy/rcsb-pdb-chatbot -n vivek-chithari

# Monitor rollout
kubectl rollout status deploy/rcsb-pdb-chatbot -n vivek-chithari
```

**Alternative (if you want to use versioned tags):**
```bash
# Build with version tag
docker buildx build --platform linux/amd64 \
  -t harbor.devops.k8s.rcsb.org/vivek.chithari/rcsb-pdb-chatbot:1.0.1 \
  --push .

# Upgrade with new tag
helm upgrade rcsb-pdb-chatbot k8s/helm/rcsb-pdb-chatbot \
  -n vivek-chithari \
  --set image.tag=1.0.1 \
  --wait
```
