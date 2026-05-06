# Multi-stage build for TAC AgentCore Server
FROM python:3.13.5 AS builder

# Set working directory
WORKDIR /app

# Install dependencies from PyPI
RUN pip install --no-cache-dir \
    'twilio-agent-connect-aws[agentcore,server]' \
    'python-dotenv>=1.0.0' \
    'bedrock-agentcore>=1.4.8' \
    'boto3>=1.42.0' \
    'mypy-boto3-bedrock-agentcore>=1.42.0'

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
COPY deploy/agentcore_aws_fargate/agentcore_server.py ./

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the application
CMD ["python", "agentcore_server.py"]
