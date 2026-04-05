FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first for caching
COPY pyproject.toml .python-version ./

# Install dependencies
RUN uv sync --no-dev --no-install-project

# Copy application code
COPY . .

# Install the project itself
RUN uv sync --no-dev

EXPOSE 5000

CMD ["uv", "run", "gunicorn", "-w", "8", "--threads", "4", "-b", "0.0.0.0:5000", "app:create_app()"]
