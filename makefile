.PHONY: generate-client

generate-client:
	uvicorn main:app &
	sleep 2
	curl http://localhost:8000/openapi.json -o openapi.json
	uv run openapi-python-client generate \
		--path openapi.json \
		--config openapi_client_config.yaml \
		--meta none
	cp jira_service_api_client/pyproject.toml.bak jira_service_api_client/pyproject.toml || true
	pkill -f "uvicorn main:app"
```

But there's a problem — the `pyproject.toml` inside `jira_service_api_client/` gets wiped on regeneration and needs to be manually re-added every time. The clean solution is to **keep `pyproject.toml` in version control** but ignore the rest:

Update `.gitignore`:
```
jira_service_api_client/*
!jira_service_api_client/pyproject.toml
openapi.json