FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy workspace configuration first (for layer caching)
COPY pyproject.toml uv.lock ./
COPY components/work_mgmt_client_interface ./components/work_mgmt_client_interface
COPY components/jira_client_impl ./components/jira_client_impl
COPY components/jira_service ./components/jira_service
COPY components/jira_service_api_client ./components/jira_service_api_client
COPY components/jira_service_adapter ./components/jira_service_adapter

# Install only production deps (no dev extras)
RUN uv sync --no-dev

# Copy application entry point
COPY main.py ./

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "components.jira_service.src.jira_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
