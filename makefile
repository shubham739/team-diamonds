.PHONY: install generate-client setup

install:
	uv sync

generate-client:
	uvicorn main:app &
	sleep 2
	curl http://localhost:8000/openapi.json -o openapi.json
	uv run openapi-python-client generate \
		--path openapi.json \
		--config openapi_client_config.yaml \
		--meta none
	pkill -f "uvicorn main:app"
	uv sync

setup: install generate-client