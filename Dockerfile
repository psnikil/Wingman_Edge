FROM python:3.13-slim
# Install system dependencies (pciutils for hardware scanning)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    zstd \
    pciutils \
    && rm -rf /var/lib/apt/lists/*

# Install uv for dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Ollama
RUN curl -L https://ollama.com/install.sh | sh

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV OLLAMA_HOST=0.0.0.0:11434

# Copy dependency files
COPY pyproject.toml uv.lock .python-version ./

# Install python dependencies
RUN uv sync --frozen --no-cache

# Copy the rest of the application
COPY . .

# Pull qwen3.5:2b during build so it's ready when the container starts
RUN (ollama serve &) \
    && echo "Waiting for Ollama to start..." \
    && until curl -s http://localhost:11434/api/tags > /dev/null; do sleep 2; done \
    && ollama pull qwen3.5:2b \
    && echo "Model pulled successfully!"

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Expose the application port and Ollama port
EXPOSE 8000 11434

# Use entrypoint script to start both services
ENTRYPOINT ["./entrypoint.sh"]
