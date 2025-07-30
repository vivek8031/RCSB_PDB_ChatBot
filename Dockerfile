# RCSB PDB ChatBot Production Dockerfile
# Multi-stage build for optimized production deployment

FROM python:3.9-slim as builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.9-slim

# Set working directory (required for Streamlit 1.10.0+)
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.9/site-packages/ /usr/local/lib/python3.9/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY . .

# Create user_data directory for session storage
RUN mkdir -p user_data && chmod 755 user_data

# Expose port 3002 (matches HAProxy backend configuration)
EXPOSE 3002

# Health check for HAProxy integration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:3002/_stcore/health || exit 1

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=3002
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Run Streamlit app on port 3002 for HAProxy integration
ENTRYPOINT ["streamlit", "run", "rcsb_pdb_chatbot.py", \
            "--server.port=3002", \
            "--server.address=0.0.0.0", \
            "--server.headless=true", \
            "--browser.gatherUsageStats=false"]