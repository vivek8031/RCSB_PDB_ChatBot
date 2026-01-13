# RCSB PDB ChatBot - Universal Dockerfile
# Works on any Docker host - local, cloud, VPS

FROM python:3.10-slim as builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.10-slim

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages/ /usr/local/lib/python3.10/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application source code
COPY src/ .

# Copy knowledge base scripts and documents (for KB init job)
COPY knowledge_base/ knowledge_base/

# Create user data directory with proper permissions
RUN mkdir -p user_data && chmod 755 user_data

# Use environment variable for port (configurable via .env)
ARG APP_PORT=8501
EXPOSE ${APP_PORT}

# Health check using configurable port
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:${APP_PORT}/_stcore/health || exit 1

# Set base environment variables (override via .env file)
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Run Streamlit with environment-configurable settings
ENTRYPOINT ["streamlit", "run", "rcsb_pdb_chatbot.py", \
            "--server.address=0.0.0.0", \
            "--server.headless=true", \
            "--browser.gatherUsageStats=false"]