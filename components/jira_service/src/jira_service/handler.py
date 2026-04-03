"""Adds mangum support for lambda deployment."""

from mangum import Mangum
from jira_service.main import app  # type: ignore[import-not-found]

handler = Mangum(app, lifespan="off", api_gateway_base_path="/default-deployment")
