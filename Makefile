.PHONY: generate-client

generate-client:
	rm -rf components/jira_service_api_client
	cd components && openapi-python-client generate --path ../openapi.json --config ../openapi_client_config.yaml
