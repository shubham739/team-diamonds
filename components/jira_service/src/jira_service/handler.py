"""Adds mangum support for lambda deployment."""

from main import app  # type: ignore[import-not-found]
from mangum import Mangum

handler = Mangum(app, lifespan="off", api_gateway_base_path="/default-deployment")
