# Multi-stage build for TAC Bedrock Server
FROM python:3.13.5 AS builder

# Set working directory
WORKDIR /app

# Copy wheel files for private dependencies
COPY bedrock_aws_fargate/wheels/*.whl /app/wheels/

# Copy requirements file (without git-sourced packages)
COPY bedrock_aws_fargate/requirements.txt /app/requirements.txt

# Install the git-sourced packages from wheels first (without dependencies)
RUN pip install --no-cache-dir --no-deps /app/wheels/twilio_agent_connect-0.0.2-py3-none-any.whl /app/wheels/tac_aws-0.1.0-py3-none-any.whl

# Install all other dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.13.5

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY bedrock_aws_fargate/bedrock_server.py ./

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the application
CMD ["python", "bedrock_server.py"]
