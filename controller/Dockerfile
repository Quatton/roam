FROM ghcr.io/astral-sh/uv:debian

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8001

# Run the application
CMD ["uv", "run", "python", "-m", "app.main"]