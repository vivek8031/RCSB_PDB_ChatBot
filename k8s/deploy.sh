#!/bin/bash
# =============================================================================
# RCSB PDB Chatbot Kubernetes Deployment Script
# =============================================================================

set -e

# Configuration
NAMESPACE="${NAMESPACE:-vivek-chithari}"
HARBOR_REGISTRY="harbor.devops.k8s.rcsb.org"
HARBOR_PROJECT="${HARBOR_PROJECT:-vivek.chithari}"
IMAGE_NAME="rcsb-pdb-chatbot"
IMAGE_TAG="${IMAGE_TAG:-1.0.0}"
RAGFLOW_REPO="${RAGFLOW_REPO:-/tmp/ragflow}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELM_CHART_DIR="${SCRIPT_DIR}/helm/rcsb-pdb-chatbot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "=============================================="
echo "RCSB PDB Chatbot K8s Deployment"
echo "=============================================="
echo "Namespace: $NAMESPACE"
echo "Image: ${HARBOR_REGISTRY}/${HARBOR_PROJECT}/${IMAGE_NAME}:${IMAGE_TAG}"
echo "=============================================="

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."

    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl not found. Please install kubectl."
        exit 1
    fi

    if ! command -v helm &> /dev/null; then
        print_error "helm not found. Please install helm."
        exit 1
    fi

    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Check your kubeconfig."
        exit 1
    fi

    print_status "Prerequisites OK"
}

# Create namespace if it doesn't exist
ensure_namespace() {
    print_status "Ensuring namespace exists..."
    kubectl get namespace "$NAMESPACE" &> /dev/null || kubectl create namespace "$NAMESPACE"
    print_status "Namespace $NAMESPACE ready"
}

# Create secrets
create_secrets() {
    print_status "Creating secrets..."

    # Harbor image pull secret
    if [ -n "$HARBOR_USERNAME" ] && [ -n "$HARBOR_PASSWORD" ]; then
        kubectl create secret docker-registry harbor-docker-registry-conf \
            --docker-server="$HARBOR_REGISTRY" \
            --docker-username="$HARBOR_USERNAME" \
            --docker-password="$HARBOR_PASSWORD" \
            --docker-email="${HARBOR_EMAIL:-$HARBOR_USERNAME@rcsb.org}" \
            -n "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
        print_status "Harbor image pull secret created"
    else
        print_warning "HARBOR_USERNAME/PASSWORD not set. Skipping harbor secret creation."
    fi

    # Application secrets
    if [ -n "$RAGFLOW_API_KEY" ] && [ -n "$OPENAI_API_KEY" ]; then
        kubectl create secret generic chatbot-secrets \
            --from-literal=RAGFLOW_API_KEY="$RAGFLOW_API_KEY" \
            --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
            --from-literal=GOOGLE_DRIVE_FOLDER_URL="${GOOGLE_DRIVE_FOLDER_URL:-}" \
            --from-literal=GOOGLE_DRIVE_EXPORT_FOLDER_ID="${GOOGLE_DRIVE_EXPORT_FOLDER_ID:-}" \
            -n "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
        print_status "Application secrets created"
    else
        print_warning "RAGFLOW_API_KEY/OPENAI_API_KEY not set. Skipping secrets creation."
    fi

    # Google Drive credentials
    CREDS_DIR="${SCRIPT_DIR}/../credentials"
    if [ -f "${CREDS_DIR}/google_drive_credentials.json" ]; then
        kubectl create secret generic gdrive-credentials \
            --from-file=credentials.json="${CREDS_DIR}/google_drive_credentials.json" \
            --from-file=token.pickle="${CREDS_DIR}/google_drive_token.pickle" \
            -n "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null || true
        print_status "Google Drive credentials secret created"
    else
        print_warning "Google Drive credentials not found. Skipping."
    fi
}

# Deploy RAGFlow
deploy_ragflow() {
    print_status "Deploying RAGFlow..."

    # Clone RAGFlow if needed
    if [ ! -d "$RAGFLOW_REPO/helm" ]; then
        print_status "Cloning RAGFlow repository..."
        git clone --depth 1 https://github.com/infiniflow/ragflow.git "$RAGFLOW_REPO"
    fi

    # Deploy RAGFlow
    helm upgrade --install ragflow "$RAGFLOW_REPO/helm" \
        -f "${HELM_CHART_DIR}/ragflow-values.yaml" \
        -n "$NAMESPACE" \
        --wait \
        --timeout 15m

    print_status "RAGFlow deployed successfully"
}

# Build and push Docker image
build_and_push_image() {
    print_status "Building and pushing Docker image..."

    cd "${SCRIPT_DIR}/.."

    docker build -t "${HARBOR_REGISTRY}/${HARBOR_PROJECT}/${IMAGE_NAME}:${IMAGE_TAG}" .
    docker push "${HARBOR_REGISTRY}/${HARBOR_PROJECT}/${IMAGE_NAME}:${IMAGE_TAG}"

    print_status "Image pushed: ${HARBOR_REGISTRY}/${HARBOR_PROJECT}/${IMAGE_NAME}:${IMAGE_TAG}"
}

# Deploy chatbot
deploy_chatbot() {
    print_status "Deploying RCSB PDB Chatbot..."

    helm upgrade --install rcsb-pdb-chatbot "$HELM_CHART_DIR" \
        -n "$NAMESPACE" \
        --set image.repository="${HARBOR_REGISTRY}/${HARBOR_PROJECT}/${IMAGE_NAME}" \
        --set image.tag="${IMAGE_TAG}" \
        --wait \
        --timeout 5m

    print_status "Chatbot deployed successfully"
}

# Verify deployment
verify_deployment() {
    print_status "Verifying deployment..."

    echo ""
    echo "=== Pods ==="
    kubectl get pods -n "$NAMESPACE"

    echo ""
    echo "=== Services ==="
    kubectl get svc -n "$NAMESPACE"

    echo ""
    echo "=== Ingress ==="
    kubectl get ingress -n "$NAMESPACE"

    echo ""
    echo "=== PVCs ==="
    kubectl get pvc -n "$NAMESPACE"
}

# Main deployment flow
main() {
    local command="${1:-full}"

    case "$command" in
        full)
            check_prerequisites
            ensure_namespace
            create_secrets
            deploy_ragflow
            build_and_push_image
            deploy_chatbot
            verify_deployment
            ;;
        secrets)
            check_prerequisites
            create_secrets
            ;;
        ragflow)
            check_prerequisites
            ensure_namespace
            deploy_ragflow
            ;;
        build)
            build_and_push_image
            ;;
        chatbot)
            check_prerequisites
            deploy_chatbot
            ;;
        verify)
            verify_deployment
            ;;
        *)
            echo "Usage: $0 [full|secrets|ragflow|build|chatbot|verify]"
            echo ""
            echo "Commands:"
            echo "  full     - Full deployment (default)"
            echo "  secrets  - Create/update secrets only"
            echo "  ragflow  - Deploy RAGFlow only"
            echo "  build    - Build and push Docker image"
            echo "  chatbot  - Deploy chatbot only"
            echo "  verify   - Verify deployment status"
            echo ""
            echo "Environment variables:"
            echo "  NAMESPACE          - K8s namespace (default: vivek.chithari)"
            echo "  HARBOR_PROJECT     - Harbor project name"
            echo "  IMAGE_TAG          - Image tag (default: 1.0.0)"
            echo "  HARBOR_USERNAME    - Harbor OIDC username"
            echo "  HARBOR_PASSWORD    - Harbor CLI secret"
            echo "  RAGFLOW_API_KEY    - RAGFlow API key"
            echo "  OPENAI_API_KEY     - OpenAI API key"
            exit 1
            ;;
    esac

    echo ""
    echo "=============================================="
    print_status "Deployment complete!"
    echo "=============================================="
    echo "Access the chatbot at: https://pdb-chatbot.k8s.rcsb.org"
    echo "=============================================="
}

main "$@"
