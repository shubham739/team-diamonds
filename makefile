.PHONY: install generate-client setup lint typecheck test

install:
	uv sync --all-packages --extra dev

# Regenerate jira_service_api_client from the live service's OpenAPI spec.
# Usage: make generate-client
# Requires: service env vars set (JIRA_BASE_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN).
generate-client:
	@echo "Starting jira-service locally to fetch OpenAPI spec..."
	@uv run uvicorn components.jira_service.src.jira_service.main:app --port 8000 & \
	SERVER_PID=$$!; \
	trap "kill $$SERVER_PID 2>/dev/null" EXIT; \
	sleep 3; \
	echo "Fetching OpenAPI spec..."; \
	curl -fsSL http://localhost:8000/openapi.json -o openapi.json; \
	echo "Generating client from spec..."; \
	uv run openapi-python-client generate \
		--path openapi.json \
		--config openapi_client_config.yaml \
		--meta none \
		--output-path components/jira_service_api_client/src/jira_service_api_client \
		--overwrite; \
	echo "Re-syncing workspace..."; \
	uv sync --all-packages --extra dev; \
	echo "Done. Client regenerated at components/jira_service_api_client/src/jira_service_api_client/"

lint:
	uv run ruff check .

typecheck:
	uv run mypy components/ --explicit-package-bases

test:
	uv run pytest components/ tests/ -m "not local_credentials" -v

setup: install
